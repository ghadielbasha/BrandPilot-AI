import json
from typing import Literal

from pydantic import BaseModel, PrivateAttr

from ai_provider import AIProviderError, AIRateLimitError, generate_structured_text
from ai_engine import CONFIG
from grounding_engine import GroundingContext, build_grounding_context
from prompt_compaction import compact_strategy_for_prompt
from safe_fallback import SafeFallbackError, build_safe_fallback_campaign
from validators.terminology_validator import normalize_global_terminology

from repair_engine import (
    MAX_REPAIR_ATTEMPTS,
    build_repair_prompt,
    create_repair_metadata,
)

from validators.factual_validator import (
    FactualValidationError,
    enforce_structured_factual_claims,
)

from validators.language_validator import (
    LanguageValidationError,
    enforce_campaign_language_quality,
)

from validators.security_validator import (
    SecurityValidationError,
    enforce_object_security,
    enforce_security,
)

from validators.terminology_validator import (
    TerminologyValidationError,
    enforce_terminology,
    normalize_terminology,
)


# --------------------------------------------------
# Structured Output Models
# --------------------------------------------------

class ContentItem(BaseModel):
    number: int
    type: str
    headline: str
    body: str


class BrandCheck(BaseModel):
    status: Literal[
        "PASS",
        "REVISE"
    ]

    issues: list[str]
    recommendations: list[str]


class MarketingContent(BaseModel):
    _provider_fallback_reason: str | None = PrivateAttr(default=None)
    caption_ar: str
    caption_en: str

    content_structure: list[
        ContentItem
    ]

    visual_concept: str
    visual_generation_prompt: str

    cta: str

    hashtags: list[str]

    brand_check: BrandCheck


# --------------------------------------------------
# Internal Validation Error
# --------------------------------------------------

class ContentValidationError(Exception):
    """
    Raised internally when deterministic campaign
    validation blocks a generated draft.
    """

    def __init__(
        self,
        stage: str,
        message: str,
        details: dict | None = None,
    ):

        self.stage = stage
        self.message = message
        self.details = details or {
            "validation_stage": stage,
            "issues": [],
        }

        super().__init__(
            f"{stage}: {message}"
        )


FALLBACK_FACTUAL_ISSUE_TYPES = frozenset({
    "subject_binding_violation",
    "subject_preservation_failure",
    "unsupported_audience",
    "unsupported_service_detail",
    "ungrounded_service_enumeration",
    "unknown_service_visual_detail",
    "missing_explicit_number",
})

FALLBACK_FACTUAL_CAPABILITIES = frozenset({
    "digital_application",
    "online_payment",
    "request_tracking",
    "continuous_availability",
    "unrestricted_access",
    "faster_processing",
    "efficiency_improvement",
    "ease_of_process",
    "productivity_improvement",
    "new_service_claim",
})


def _is_high_confidence_factual_failure(error: ContentValidationError) -> bool:
    if error.stage != "factual_validation":
        return False
    issues = error.details.get("issues", [])
    if not issues:
        return False
    for issue in issues:
        if not isinstance(issue, dict):
            return False
        if issue.get("type") in FALLBACK_FACTUAL_ISSUE_TYPES:
            continue
        if (
            issue.get("type") == "unsupported_claim"
            and issue.get("capability") in FALLBACK_FACTUAL_CAPABILITIES
        ):
            continue
        return False
    return True


def _generate_safe_fallback_content(
    brief: str,
    strategy: dict,
    grounding: GroundingContext,
) -> MarketingContent:
    try:
        approved_grounding = json.loads(grounding.prompt_context)
    except (TypeError, ValueError) as error:
        raise SafeFallbackError(
            "Approved grounding metadata could not be parsed."
        ) from error
    payload = build_safe_fallback_campaign(
        brief=brief,
        strategy=strategy,
        approved_grounding=approved_grounding,
    )
    return MarketingContent.model_validate(payload)


# --------------------------------------------------
# Initial Prompt Builder
# --------------------------------------------------

def build_content_prompt(
    brief: str,
    strategy: dict,
    grounding: GroundingContext | None = None,
) -> str:

    brand_key = strategy[
        "brand_key"
    ]

    brand_data = CONFIG[
        "brands"
    ][brand_key]

    brand_prompt_keys = (
        "display_name", "personality", "language_strategy",
        "content_structure_rules", "cta_style", "emoji_policy",
        "hashtag_policy", "avoid",
    )
    brand_rules = json.dumps(
        {key: brand_data[key] for key in brand_prompt_keys if key in brand_data},
        ensure_ascii=False,
        separators=(",", ":"),
    )

    strategy_json = json.dumps(
        compact_strategy_for_prompt(strategy),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    languages = strategy.get(
        "languages",
        []
    )

    target_audience = strategy.get("target_audience", [])
    if isinstance(target_audience, str):
        target_audience = [target_audience]
    target_audience = [
        audience.strip() for audience in target_audience
        if isinstance(audience, str) and audience.strip()
    ]
    authoritative_audience_section = ""
    if target_audience:
        audience_lines = "\n".join(target_audience)
        authoritative_audience_section = f"""

AUTHORITATIVE CAMPAIGN AUDIENCE
===============================
{audience_lines}

STRICT AUDIENCE RULE:
The audience above is authoritative for this campaign.

Do not broaden, replace, generalize, or infer additional audiences from:
- brand intelligence
- organization-wide audiences
- general Dawlati users
- grounded organizational knowledge

If you create a "Who benefits?" slide, an audience slide, a CTA directed
at a group, or a visual description containing people, use only the
approved campaign audience.

If uncertain, repeat the approved campaign audience instead of inventing
another audience.
"""

    grounding = grounding or build_grounding_context(brand_key)

    return f"""
APPROVED GOVERNED KNOWLEDGE
===========================
{grounding.prompt_context}

KNOWLEDGE SCOPE AND PRIORITY
============================
GENERAL BRAND KNOWLEDGE IS CONTEXT ONLY.
Campaign facts in the brief and approved strategy define the subject.
Do not transform general Dawlati capabilities into service names.
If the brief refers to unnamed services, keep them unnamed.

CAMPAIGN BRIEF
==============
{brief}

APPROVED CAMPAIGN STRATEGY
==========================
{strategy_json}
{authoritative_audience_section}

BRAND DELIVERY RULES
====================
{brand_rules}

REQUESTED LANGUAGES
===================
{", ".join(languages)}

Create the requested caption(s), content structure, visual concept, visual
prompt, CTA, hashtags, and brand check. For a carousel, use 4-6 slides; for a
reel, use scenes; otherwise describe the main post components.

Use correct professional Arabic/English. Unrequested caption fields must be
empty. Write DAWLATI as Ø¯ÙˆÙ„ØªÙŠ in Arabic. Describe services as available
through Dawlati; never describe Dawlati itself as the services.

Use only the brief, compact strategy, governed knowledge, and brand delivery
rules. Preserve explicit numbers and entity relationships. Never invent or
infer service names, missing list items, facts, benefits, eligibility, dates,
URLs, statistics, partnerships, capabilities, platform behavior, audiences,
credentials, secrets, personal data, or private infrastructure. "Available
online" does not establish application, payment, tracking, 24/7, anytime,
anywhere, convenience, speed, ease, or efficiency. These constraints apply to
every caption, slide/scene, visual field, CTA, and hashtag.

Visuals must remain generic where service-level evidence is absent; do not
invent official colors, logos, fonts, service cards, links, or icons. Use a
small number of factual hashtags. Brand check is PASS only if every rule is
met. Human approval remains required. Return only the required JSON object.
"""

    return f"""
You are BrandPilot AI.

You are a controlled AI-powered branding and
digital-marketing assistant for Lebanese
public-sector organizations.

Follow the supplied ground truth,
campaign brief,
approved strategy,
and brand intelligence strictly.


APPROVED GOVERNED KNOWLEDGE
===========================
{grounding.prompt_context}

KNOWLEDGE SCOPE AND PRIORITY
============================
CAMPAIGN FACTS from the brief and approved strategy define the campaign
subject. Service-level records may add details only for the specific service
and entity to which those records are bound.

GENERAL BRAND KNOWLEDGE IS CONTEXT ONLY.
Do not substitute general brand features, directories, platform functions,
or capabilities for specific entities or services in the campaign brief.
Do not transform general Dawlati capabilities into service names.
If the brief refers to unnamed services, keep them unnamed.


CAMPAIGN BRIEF
==============
{brief}


APPROVED CAMPAIGN STRATEGY
==========================
{strategy_json}

{authoritative_audience_section}


BRAND INTELLIGENCE
==================
{brand_rules}


REQUESTED LANGUAGES
===================
{", ".join(languages)}


TASK
====

Generate complete marketing content for the campaign.

Generate:

1. Arabic caption if Arabic is requested.
2. English caption if English is requested.
3. Content structure for the recommended format.
4. Visual concept.
5. Visual-generation prompt.
6. CTA.
7. Hashtags.
8. Brand compliance review.


LANGUAGE REQUIREMENTS
=====================

If Arabic appears in REQUESTED LANGUAGES:

caption_ar MUST contain a complete,
grammatically correct Arabic caption.

caption_ar MUST NOT be empty.

Use natural professional Arabic.

For Dawlati service announcements,
use clear Modern Standard Arabic.

Always spell DAWLATI in Arabic as:

دولتي

When referring explicitly to the platform,
prefer:

منصة «دولتي»

Do not translate English literally.

Avoid malformed Arabic sentence structures.

When announcing services,
describe the SERVICES as being available
through Dawlati.

Correct conceptual structure:

أصبحت 7 خدمات تابعة لوزارة الزراعة
متاحة الآن إلكترونياً عبر منصة «دولتي».

Do NOT describe Dawlati itself as being
the seven services.

Incorrect:

منصة «دولتي» هي 7 خدمات...

Incorrect:

منصة «دولتي» تعد 7 خدمات...


If English appears in REQUESTED LANGUAGES:

caption_en MUST contain a complete,
grammatically correct English caption.

caption_en MUST NOT be empty.

Write natural professional English.

Do not translate Arabic literally.


If Arabic was NOT requested:

caption_ar must be "".


If English was NOT requested:

caption_en must be "".


CAROUSEL RULES
==============

If the recommended format is Carousel:

Create between 4 and 6 slides.

Each item in content_structure represents one slide.

Suggested flow:

Slide 1:
Factual announcement.

Slide 2:
Explain what is available using only the brief.

Slide 3:
Explain who the information is relevant to.

Slide 4:
Encourage users to explore the available services.

Slide 5:
CTA.

Do not invent information simply to fill a slide.

If the brief gives a service count but not the service names,
repeat the count only in generic phrases such as
"7 Ministry services" or "the available services".
NEVER turn that count into an enumerated service list.
Every named service, bullet item, slide title, and section label
must appear verbatim in the brief or approved service catalog.

Do not claim:

- application capability
- payment capability
- tracking capability
- time savings
- easier procedures
- simplified procedures
- efficiency improvement
- 24/7 availability

unless explicitly supported.


REEL RULES
==========

If the recommended format is Reel:

Each content_structure item represents one scene.

Each scene should include:

- purpose
- headline
- short message

Do not add unsupported functionality,
results,
or benefits.


POST RULES
==========

If the recommended format is:

- Professional Post
- Informational Post

Use content_structure to describe
the main visual and message components.


FACTUAL SAFETY RULES
====================

Use only information from:

- GROUND TRUTH
- CAMPAIGN BRIEF
- APPROVED CAMPAIGN STRATEGY
- BRAND INTELLIGENCE

Never invent missing facts.

Preserve the campaign subject and its entity relationship. A number attached
to services must stay attached to the same responsible ministry or entity.
"7 Ministry of Agriculture services" must not become "7 government
services", "7 Dawlati services", or "7 digital services".

"Now available" describes availability. It does not mean the services are
new or newly created. Do not write "new services" unless explicitly stated.

These rules apply independently to every output field, including
captions, every structure headline and body, visual concept,
visual-generation prompt, CTA, and hashtags.

Never invent:

- services
- service names
- statistics
- dates
- URLs
- partnerships
- policies
- organizations
- achievements
- eligibility conditions
- project results
- application capabilities
- payment capabilities
- tracking capabilities
- fees
- documents
- processing times
- beneficiaries or audience groups not named in the approved inputs
- "link in bio" or other platform behavior not requested by the strategy

Do not add placeholder links.

Do not exaggerate what "available online" means.

"Available online" does NOT automatically mean:

- apply online
- submit a request online
- pay online
- track a request online
- complete the entire service digitally

Do not claim:

- faster processing
- reduced waiting
- saved time
- greater efficiency
- easier procedures
- simplified procedures
- easier access
- convenience
- 24/7 availability
- access at any time or "anytime"
- access from anywhere or "wherever you are"

unless explicitly supported.

Do not expose confidential information.

Do not include credentials.

Do not include personal information.


BRAND RULES
===========

Match the selected brand personality.

Match the selected tone only where the tone
does not introduce unsupported factual claims.

A tone such as "Benefit-focused"
does NOT authorize the invention of benefits.

Avoid exaggerated marketing language.

Avoid political or partisan statements.

Keep public-sector communication trustworthy.

Respect the selected platform.

Use emojis only when appropriate.

Use a limited number of relevant hashtags.

Use the strategy CTA only when it does not
create unsupported factual claims.


OMSAR RULES
===========

For OMSAR:

- use professional institutional language
- remain factual
- use public-sector terminology carefully
- avoid excessive promotional language
- avoid overly casual language
- do not invent impact or results


DAWLATI RULES
=============

For DAWLATI:

- use clear citizen-friendly communication
- explain service information simply
- remain factual
- use clear Modern Standard Arabic
- always write DAWLATI in Arabic as دولتي
- preferably write منصة «دولتي»
- never invent service names
- preserve exact numbers stated in the brief
- do not add unsupported functionality
- do not add unsupported benefits
- do not add placeholder links

If a service is only described as "available online",
prefer CTAs such as:

English:

- Explore the available services on Dawlati
- Discover the available services
- Learn more on Dawlati

Arabic:

- اكتشف الخدمات المتاحة عبر منصة «دولتي»
- تعرّف على الخدمات المتاحة عبر منصة «دولتي»

Do NOT automatically write:

- Start your application
- Submit your request
- Pay online
- Track your request
- Access the service easily
- Simplify your procedures

Do NOT automatically write:

- ابدأ بطلبك
- قدّم طلبك
- ادفع إلكترونياً
- تتبّع طلبك
- استفد بسهولة
- سهّل إجراءاتك
- بسّط إجراءاتك


VISUAL RULES
============

Create a useful visual concept.

The visual-generation prompt should describe:

- composition
- hierarchy
- visual subject
- typography style
- mood
- photography or illustration style
- CTA placement

Do not invent official:

- colors
- logos
- fonts
- identity assets

unless provided in Brand Intelligence.

Do not include fabricated government information.

Do not place invented service names inside the visual.

Do not depict, label, iconize, or imply a specific service category
unless that service category is present in approved evidence.

When individual service records are unavailable, do not request named service
cards, individual descriptions, service-page links or URLs, or identity-specific
icons. Use generic subject-preserving visual elements instead.


HASHTAGS
========

Use a small number of relevant hashtags.

Do not invent campaign names.

Prefer general factual hashtags
when uncertain.

For DAWLATI Arabic hashtags,
use only the official spelling:

#دولتي


BRAND CHECK
===========

After generating the content,
review it.

Check:

- country is Lebanon
- correct brand
- correct Arabic spelling of دولتي
- correct tone
- audience relevance
- factual grounding
- explicit numbers preserved
- no invented services
- no invented facts
- no placeholder links
- no unsupported functionality claims
- no unsupported benefit claims
- grammatically correct Arabic
- grammatically correct English
- semantic clarity
- CTA quality
- platform suitability
- confidentiality
- no partisan wording

Return PASS only if the content follows all rules.

Return REVISE if something should be corrected.

Human approval is always required before publication.


IMPORTANT
=========

Return only the JSON structure.

Do not add explanations outside JSON.
"""


# --------------------------------------------------
# Provider-backed Structured Generation
# --------------------------------------------------

def _call_structured_model(
    system_prompt: str,
    user_prompt: str,
    *,
    is_repair: bool = False,
) -> MarketingContent:

    try:

        raw_content = generate_structured_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=MarketingContent.model_json_schema(),
            is_repair=is_repair,
        )

    except AIRateLimitError:
        raise

    except AIProviderError as error:

        raise RuntimeError(
            f"BrandPilot AI provider error: {error}"
        ) from error


    try:

        return MarketingContent.model_validate_json(
            raw_content
        )

    except Exception as error:

        raise RuntimeError(
            "The AI provider response could not be validated "
            "against the BrandPilot schema. "
            f"Details: {error}"
        )


# --------------------------------------------------
# Initial Generation
# --------------------------------------------------

def _generate_initial_content(
    brief: str,
    strategy: dict,
    grounding: GroundingContext | None = None,
) -> MarketingContent:

    prompt = build_content_prompt(
        brief,
        strategy,
        grounding,
    )


    system_prompt = (
        "You are BrandPilot AI, a controlled "
        "marketing assistant for Lebanese "
        "public-sector organizations. "
        "OMSAR is Lebanese. "
        "DAWLATI is Lebanon's government-services "
        "platform developed by OMSAR. "
        "In Arabic, DAWLATI must always be written "
        "as دولتي. "
        "Never assume another country. "
        "Never invent facts. "
        "Never invent service names. "
        "If a brief supplies a service count without names, never "
        "enumerate or infer the missing names in any field. "
        "Never add placeholder links. "
        "Never infer application, payment, or "
        "tracking capabilities from the phrase "
        "'available online'. "
        "Never invent benefits such as easier "
        "procedures, efficiency improvements, "
        "time savings, faster processing, or "
        "24/7 availability. Never turn 'available online' into "
        "'access anytime', 'from anywhere', or 'wherever you are'. "
        "Never broaden the approved campaign target audience. "
        "Preserve explicit numbers from the brief. "
        "Use grammatically correct Arabic and English. "
        "Do not expose credentials, secrets, "
        "private infrastructure, or sensitive data. "
        "Use only supplied context. "
        "Return structured JSON only."
    )


    return _call_structured_model(
        system_prompt=system_prompt,
        user_prompt=prompt
    )


# --------------------------------------------------
# Repair Generation
# --------------------------------------------------

def _generate_repaired_content(
    brief: str,
    strategy: dict,
    failed_content: dict,
    validation_error: str,
    validation_context: dict | None = None,
    grounding: GroundingContext | None = None,
) -> MarketingContent:

    repair_prompt = build_repair_prompt(
        brief=brief,
        strategy=strategy,
        failed_content=failed_content,
        validation_error=validation_error,
        validation_context=validation_context,
    )

    grounding = grounding or build_grounding_context(strategy["brand_key"])
    repair_prompt += (
        "\n\nAPPROVED GOVERNED KNOWLEDGE\n"
        "===========================\n"
        + grounding.prompt_context
    )


    system_prompt = (
        "You are BrandPilot AI Repair Mode. "
        "A previous campaign draft failed independent "
        "deterministic validation. "
        "Correct only what is necessary while preserving "
        "the original brief, approved strategy, brand, "
        "audience, languages, platform, and supported facts. "
        "Do not invent facts, benefits, capabilities, "
        "service names, URLs, or statistics. "
        "Do not include credentials, authentication tokens, "
        "private infrastructure, or sensitive identifiers. "
        "The repaired result will be validated again. "
        "Return the complete corrected JSON object only."
    )


    return _call_structured_model(
        system_prompt=system_prompt,
        user_prompt=repair_prompt,
        is_repair=True,
    )


# --------------------------------------------------
# Terminology Normalization Helper
# --------------------------------------------------

def _normalize_generated_text(
    text: str,
    brand: str,
    normalization_changes: list[dict]
) -> str:

    if not text:
        return text

    text = normalize_global_terminology(text)


    result = normalize_terminology(
        text=text,
        brand=brand
    )


    normalization_changes.extend(
        result[
            "changes"
        ]
    )


    return result[
        "text"
    ]


# --------------------------------------------------
# Normalize Complete Campaign
# --------------------------------------------------

def _normalize_content(
    content: MarketingContent,
    brand_key: str
) -> list[dict]:

    normalization_changes = []


    try:

        content.caption_ar = (
            _normalize_generated_text(
                content.caption_ar,
                brand_key,
                normalization_changes
            )
        )


        content.caption_en = (
            _normalize_generated_text(
                content.caption_en,
                brand_key,
                normalization_changes
            )
        )


        content.visual_concept = (
            _normalize_generated_text(
                content.visual_concept,
                brand_key,
                normalization_changes
            )
        )


        content.visual_generation_prompt = (
            _normalize_generated_text(
                content.visual_generation_prompt,
                brand_key,
                normalization_changes
            )
        )


        content.cta = (
            _normalize_generated_text(
                content.cta,
                brand_key,
                normalization_changes
            )
        )


        content.hashtags = [
            _normalize_generated_text(
                hashtag,
                brand_key,
                normalization_changes
            )

            for hashtag
            in content.hashtags
        ]


        for item in content.content_structure:

            item.headline = (
                _normalize_generated_text(
                    item.headline,
                    brand_key,
                    normalization_changes
                )
            )


            item.body = (
                _normalize_generated_text(
                    item.body,
                    brand_key,
                    normalization_changes
                )
            )


    except TerminologyValidationError as error:

        raise ContentValidationError(
            stage="terminology_normalization",
            message=str(error)
        )


    return normalization_changes


# --------------------------------------------------
# Requested Language Handling
# --------------------------------------------------

def _enforce_requested_languages(
    content: MarketingContent,
    requested_languages: set[str]
):

    if (
        "Arabic" in requested_languages
        and not content.caption_ar.strip()
    ):

        raise ContentValidationError(
            stage="language_presence",
            message=(
                "Arabic was requested, but the model "
                "returned an empty Arabic caption."
            )
        )


    if (
        "English" in requested_languages
        and not content.caption_en.strip()
    ):

        raise ContentValidationError(
            stage="language_presence",
            message=(
                "English was requested, but the model "
                "returned an empty English caption."
            )
        )


    if (
        "Arabic" not in requested_languages
        and content.caption_ar.strip()
    ):

        content.caption_ar = ""


    if (
        "English" not in requested_languages
        and content.caption_en.strip()
    ):

        content.caption_en = ""


# --------------------------------------------------
# Combined Text Builder
# --------------------------------------------------

def _build_combined_text(
    content: MarketingContent
) -> str:

    generated_text_parts = [
        content.caption_ar,
        content.caption_en,
        content.visual_concept,
        content.visual_generation_prompt,
        content.cta,
        " ".join(
            content.hashtags
        ),
    ]


    for item in content.content_structure:

        generated_text_parts.append(
            item.headline
        )

        generated_text_parts.append(
            item.body
        )


    return "\n".join(
        part

        for part
        in generated_text_parts

        if part
    )


# --------------------------------------------------
# Deterministic Validation
# --------------------------------------------------

def _validate_content(
    brief: str,
    content: MarketingContent,
    brand_key: str,
    requested_languages: set[str],
    strategy: dict,
    grounding: GroundingContext,
) -> dict:

    combined_text = _build_combined_text(
        content
    )


    # --------------------------------------------------
    # Generated Content Security
    # --------------------------------------------------

    try:

        security_result = enforce_object_security(
            content=content.model_dump(),
            context="generated_campaign"
        )


    except SecurityValidationError as error:

        raise ContentValidationError(
            stage="security_validation",
            message=str(error)
        )


    # --------------------------------------------------
    # Placeholder Links
    # --------------------------------------------------

    forbidden_placeholders = [
        "[link]",
        "[الرابط]",
        "[url]",
        "[website]",
    ]


    if any(
        placeholder.casefold()
        in combined_text.casefold()

        for placeholder
        in forbidden_placeholders
    ):

        raise ContentValidationError(
            stage="placeholder_validation",
            message=(
                "Generated content contains "
                "a placeholder link."
            )
        )


    # --------------------------------------------------
    # Country Safety
    # --------------------------------------------------

    forbidden_country_terms = [
        "Saudi Arabia",
        "Saudi",
        "Vision 2030",
        "السعودية",
        "رؤية 2030",
    ]


    if any(
        term.casefold()
        in combined_text.casefold()

        for term
        in forbidden_country_terms
    ):

        raise ContentValidationError(
            stage="country_validation",
            message=(
                "Generated content introduced an incorrect "
                "country or unrelated external context."
            )
        )


    # --------------------------------------------------
    # Dawlati Arabic Name
    # --------------------------------------------------

    if (
        "Arabic" in requested_languages
        and brand_key == "dawlati"
        and "دولتي" not in content.caption_ar
    ):

        raise ContentValidationError(
            stage="brand_name_validation",
            message=(
                "The Arabic Dawlati caption does not "
                "contain the official Arabic name دولتي."
            )
        )


    # --------------------------------------------------
    # Terminology
    # --------------------------------------------------

    try:

        terminology_result = enforce_terminology(
            text=combined_text,
            brand=brand_key
        )


    except TerminologyValidationError as error:

        raise ContentValidationError(
            stage="terminology_validation",
            message=str(error)
        )


    # --------------------------------------------------
    # Factual Validation
    # --------------------------------------------------

    try:

        try:
            approved_knowledge = json.loads(grounding.prompt_context)
        except (TypeError, ValueError):
            approved_knowledge = {}

        factual_result = enforce_structured_factual_claims(
            brief=brief,
            content=content.model_dump(),
            approved_strategy=strategy,
            approved_knowledge=approved_knowledge,
        )


    except FactualValidationError as error:

        raise ContentValidationError(
            stage="factual_validation",
            message=str(error),
            details=error.details,
        )


    # --------------------------------------------------
    # Full Campaign Language Quality
    # --------------------------------------------------

    try:

        language_result = (
            enforce_campaign_language_quality(
                content=content.model_dump(),
                requested_languages=requested_languages
            )
        )


    except LanguageValidationError as error:

        raise ContentValidationError(
            stage="language_validation",
            message=str(error)
        )


    return {
        "security_validation": (
            security_result
        ),

        "terminology_validation": (
            terminology_result
        ),

        "factual_validation": (
            factual_result
        ),

        "language_validation": (
            language_result
        ),
    }


# --------------------------------------------------
# Prepare + Validate Draft
# --------------------------------------------------

def _prepare_and_validate_content(
    brief: str,
    content: MarketingContent,
    brand_key: str,
    requested_languages: set[str],
    strategy: dict,
    grounding: GroundingContext,
) -> tuple[
    MarketingContent,
    list[dict],
    dict
]:

    _enforce_requested_languages(
        content=content,
        requested_languages=requested_languages
    )


    normalization_changes = (
        _normalize_content(
            content=content,
            brand_key=brand_key
        )
    )


    validation_results = (
        _validate_content(
            brief=brief,
            content=content,
            brand_key=brand_key,
            requested_languages=requested_languages,
            strategy=strategy,
            grounding=grounding,
        )
    )


    return (
        content,
        normalization_changes,
        validation_results
    )


# --------------------------------------------------
# Main Generation Function
# --------------------------------------------------

def generate_marketing_content(
    brief: str,
    strategy: dict
) -> dict:

    # --------------------------------------------------
    # Input Validation
    # --------------------------------------------------

    if not isinstance(
        brief,
        str
    ) or not brief.strip():

        raise RuntimeError(
            "Campaign brief cannot be empty."
        )


    if not isinstance(
        strategy,
        dict
    ):

        raise RuntimeError(
            "Campaign strategy must be a dictionary."
        )


    brand_key = strategy.get(
        "brand_key"
    )


    if not brand_key:

        raise RuntimeError(
            "Campaign strategy does not contain a brand_key."
        )


    if brand_key not in CONFIG.get(
        "brands",
        {}
    ):

        raise RuntimeError(
            f"Unknown BrandPilot brand: {brand_key}"
        )


    requested_languages = set(
        strategy.get(
            "languages",
            []
        )
    )

    fallback_metadata = {
        "attempted": False,
        "successful": False,
        "reason": None,
    }
    generation_source = "AI"

    try:
        grounding = build_grounding_context(brand_key)
    except Exception as error:
        raise RuntimeError(
            "BrandPilot blocked generation because approved knowledge "
            f"could not be loaded. Details: {error}"
        ) from error


    # --------------------------------------------------
    # Input Security Validation
    # --------------------------------------------------

    try:

        brief_security_result = enforce_security(
            text=brief,
            context="campaign_brief"
        )


        strategy_security_result = enforce_object_security(
            content=strategy,
            context="campaign_strategy"
        )


    except SecurityValidationError as error:

        raise RuntimeError(
            "BrandPilot blocked the campaign before AI generation "
            "because the input failed security validation. "
            f"Details: {error}"
        )


    # --------------------------------------------------
    # Initial Generation
    # --------------------------------------------------

    try:
        content = _generate_initial_content(
            brief=brief,
            strategy=strategy,
            grounding=grounding,
        )
    except AIRateLimitError:
        # A quota failure is not a validation failure. Try only a supported,
        # model-free template, then run every validator as usual.
        try:
            content = _generate_safe_fallback_content(
                brief=brief, strategy=strategy, grounding=grounding
            )
        except (SafeFallbackError, ValueError, TypeError) as error:
            raise RuntimeError(
                "Groq usage limit reached and no safe, supported fallback is available."
            ) from None
        content._provider_fallback_reason = "provider_rate_limit"


    if content._provider_fallback_reason:
        fallback_metadata = {
            "attempted": True, "successful": True,
            "reason": content._provider_fallback_reason,
        }
        generation_source = "deterministic fallback"

    # --------------------------------------------------
    # Initial Validation
    # --------------------------------------------------

    try:

        (
            content,
            normalization_changes,
            validation_results
        ) = _prepare_and_validate_content(
            brief=brief,
            content=content,
            brand_key=brand_key,
            requested_languages=requested_languages,
            strategy=strategy,
            grounding=grounding,
        )


        repair_metadata = (
            create_repair_metadata(
                attempted=False,
                successful=False,
                initial_error=None,
            )
        )


    # --------------------------------------------------
    # Automatic Repair
    # --------------------------------------------------

    except ContentValidationError as initial_error:

        if content._provider_fallback_reason:
            raise RuntimeError(
                "BrandPilot blocked a non-compliant deterministic provider fallback."
            ) from None

        if MAX_REPAIR_ATTEMPTS < 1:

            raise RuntimeError(
                "BrandPilot blocked the generated content. "
                f"Details: {initial_error}"
            )


        failed_content = (
            content.model_dump()
        )


        try:
            repaired_content = _generate_repaired_content(
                brief=brief,
                strategy=strategy,
                failed_content=failed_content,
                validation_error=str(initial_error),
                validation_context=initial_error.details,
                grounding=grounding,
            )
        except AIRateLimitError:
            # Avoid another model request when Groq rejects the repair.
            try:
                repaired_content = _generate_safe_fallback_content(
                    brief=brief, strategy=strategy, grounding=grounding
                )
            except (SafeFallbackError, ValueError, TypeError):
                raise RuntimeError(
                    "Groq rate limit reached during repair and no safe fallback "
                    "is available for this campaign."
                ) from None
            fallback_metadata = {
                "attempted": True,
                "successful": False,
                "reason": "provider_rate_limit",
            }
            generation_source = "deterministic fallback"
            repair_metadata = create_repair_metadata(
                attempted=True,
                successful=False,
                initial_error=str(initial_error),
            )


        # --------------------------------------------------
        # Re-run ALL validation on repaired draft
        # --------------------------------------------------

        try:

            (
                content,
                normalization_changes,
                validation_results
            ) = _prepare_and_validate_content(
                brief=brief,
                content=repaired_content,
                brand_key=brand_key,
                requested_languages=requested_languages,
                strategy=strategy,
                grounding=grounding,
            )


        except ContentValidationError as repair_error:
            if fallback_metadata["reason"] == "provider_rate_limit":
                raise RuntimeError(
                    "Rate-limit fallback failed output validation."
                ) from None
            if not _is_high_confidence_factual_failure(repair_error):
                raise RuntimeError(
                    "BrandPilot blocked the campaign after "
                    "one automatic repair attempt. "
                    f"Initial validation error: {initial_error}. "
                    f"Repair validation error: {repair_error}"
                )

            fallback_metadata = {
                "attempted": True,
                "successful": False,
                "reason": "factual_grounding_failure",
            }
            try:
                fallback_content = _generate_safe_fallback_content(
                    brief=brief,
                    strategy=strategy,
                    grounding=grounding,
                )
            except (SafeFallbackError, ValueError, TypeError) as fallback_error:
                raise RuntimeError(
                    "BrandPilot blocked the campaign after one automatic "
                    "repair attempt because the deterministic factual fallback "
                    f"could not be constructed safely. Details: {fallback_error}"
                ) from fallback_error

            try:
                (
                    content,
                    normalization_changes,
                    validation_results,
                ) = _prepare_and_validate_content(
                    brief=brief,
                    content=fallback_content,
                    brand_key=brand_key,
                    requested_languages=requested_languages,
                    strategy=strategy,
                    grounding=grounding,
                )
            except ContentValidationError as fallback_error:
                raise RuntimeError(
                    "BrandPilot blocked the campaign after one automatic "
                    "repair attempt and one deterministic factual fallback. "
                    f"Initial validation error: {initial_error}. "
                    f"Repair validation error: {repair_error}. "
                    f"Fallback validation error: {fallback_error}"
                ) from fallback_error

            fallback_metadata["successful"] = True
            generation_source = "deterministic fallback"
            repair_metadata = create_repair_metadata(
                attempted=True,
                successful=False,
                initial_error=str(initial_error),
            )


        if fallback_metadata["reason"] == "provider_rate_limit":
            fallback_metadata["successful"] = True

        if not fallback_metadata["attempted"]:
            generation_source = "AI repair"
            repair_metadata = (
                create_repair_metadata(
                    attempted=True,
                    successful=True,
                    initial_error=str(
                        initial_error
                    ),
                )
            )


    # --------------------------------------------------
    # Final Result
    # --------------------------------------------------

    result = content.model_dump()


    result[
        "input_security_validation"
    ] = {
        "brief": (
            brief_security_result
        ),

        "strategy": (
            strategy_security_result
        ),
    }


    result[
        "security_validation"
    ] = validation_results[
        "security_validation"
    ]


    result[
        "terminology_validation"
    ] = validation_results[
        "terminology_validation"
    ]


    result[
        "factual_validation"
    ] = validation_results[
        "factual_validation"
    ]


    result[
        "language_validation"
    ] = validation_results[
        "language_validation"
    ]


    result[
        "terminology_normalization"
    ] = {
        "changed": (
            len(
                normalization_changes
            ) > 0
        ),

        "changes": (
            normalization_changes
        )
    }


    result[
        "repair"
    ] = repair_metadata


    result[
        "fallback"
    ] = fallback_metadata

    result["generation_source"] = generation_source


    return result
