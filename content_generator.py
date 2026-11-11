import json
from typing import Literal

from ollama import chat
from pydantic import BaseModel

from ai_engine import CONFIG


# --------------------------------------------------
# Structured Output Models
# --------------------------------------------------

class ContentItem(BaseModel):
    number: int
    type: str
    headline: str
    body: str


class BrandCheck(BaseModel):
    status: Literal["PASS", "REVISE"]
    issues: list[str]
    recommendations: list[str]


class MarketingContent(BaseModel):
    caption_ar: str
    caption_en: str

    content_structure: list[ContentItem]

    visual_concept: str
    visual_generation_prompt: str

    cta: str

    hashtags: list[str]

    brand_check: BrandCheck


# --------------------------------------------------
# Local Model
# --------------------------------------------------

MODEL_NAME = "qwen3:4b"


# --------------------------------------------------
# Ground Truth
# --------------------------------------------------

GROUND_TRUTH = """
GROUND TRUTH
============

Country: Lebanon

OMSAR:
The Office of the Minister of State for Administrative Reform
is a Lebanese public-sector institution.

OMSAR works on:
- administrative reform
- digital transformation
- anti-corruption
- modernization of public administration
- citizen-centered public services

DAWLATI:
DAWLATI is Lebanon's digital platform for government services.

DAWLATI is developed by OMSAR.

Its purpose is to help citizens and businesses:
- discover government services
- understand service requirements
- access available digital services
- apply online where supported
- track requests where supported

OMSAR MATCHMAKING PORTAL:
The OMSAR Matchmaking Portal is a Lebanese platform that
connects public-sector needs with relevant talent and expertise.

Possible users include:
- university students
- fresh graduates
- professionals
- academics
- researchers
- experts
- Lebanese diaspora talent


OFFICIAL NAMING RULES
=====================

The official Arabic spelling of DAWLATI is:

دولتي

When writing Arabic, always use:

منصة «دولتي»

Never write:
- داولاتي
- دوالتي
- داولتي


CRITICAL RULES
==============

DAWLATI always refers to Lebanon.

Never reinterpret DAWLATI as belonging to:
- Saudi Arabia
- UAE
- Egypt
- or any other country

Do not use outside knowledge to guess missing information.

Never invent:
- service names
- government services
- dates
- statistics
- partnerships
- organizations
- URLs
- policies
- achievements
- project results
- eligibility requirements

If the campaign brief says seven services exist,
but does not name those seven services,
you may mention that seven services are available,
but you MUST NOT invent their names.

If information is missing,
use general wording instead of guessing.


SOURCE FIDELITY RULES
=====================

Preserve important explicit facts from the campaign brief.

If the brief states a number,
such as "seven services",
the generated content should preserve that number when relevant.

Do not add placeholders such as:
- [link]
- [الرابط]
- [URL]
- [website]

unless an actual URL was provided in the campaign brief.

Do not claim:
- 24/7 availability
- reduced waiting time
- faster processing
- online payment capability
- request tracking
- full online application capability

unless those capabilities are explicitly supported
by the campaign brief or specifically confirmed for that service.

Do not convert a general statement such as
"available online"
into a stronger unsupported statement such as
"complete the entire transaction online anytime."
"""


# --------------------------------------------------
# Prompt Builder
# --------------------------------------------------

def build_content_prompt(
    brief: str,
    strategy: dict
) -> str:

    brand_key = strategy[
        "brand_key"
    ]

    brand_data = CONFIG[
        "brands"
    ][brand_key]

    brand_rules = json.dumps(
        brand_data,
        ensure_ascii=False,
        indent=2
    )

    strategy_json = json.dumps(
        strategy,
        ensure_ascii=False,
        indent=2
    )

    languages = strategy.get(
        "languages",
        []
    )

    return f"""
You are BrandPilot AI.

You are a controlled AI-powered branding and digital
marketing assistant for Lebanese public-sector organizations.

Follow the supplied ground truth,
campaign strategy,
and brand intelligence strictly.


{GROUND_TRUTH}


CAMPAIGN BRIEF
==============
{brief}


APPROVED CAMPAIGN STRATEGY
==========================
{strategy_json}


BRAND INTELLIGENCE
==================
{brand_rules}


REQUESTED LANGUAGES
===================
{", ".join(languages)}


TASK
====

Generate complete marketing content for the campaign.

You must generate:

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

caption_ar MUST contain a complete Arabic caption.

caption_ar MUST NOT be empty.

Write natural Arabic.

For Dawlati service announcements:
use clear Modern Standard Arabic.

Always spell DAWLATI in Arabic as:
«دولتي»

Do not translate English literally.


If English appears in REQUESTED LANGUAGES:

caption_en MUST contain a complete English caption.

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
Strong headline.

Slide 2:
Explain what is available.

Slide 3:
Explain who benefits.

Slide 4:
Explain the practical benefit.

Slide 5:
CTA.

Do not invent information simply to fill a slide.


REEL RULES
==========

If the recommended format is Reel:

Each content_structure item represents a scene.

Each scene should include:
- purpose
- headline
- short message


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
- APPROVED STRATEGY
- BRAND INTELLIGENCE

Never invent missing facts.

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

Do not add placeholder links.

Do not exaggerate what "available online" means.

Do not expose confidential information.

Do not include credentials.

Do not include personal information.


BRAND RULES
===========

Match the selected brand personality.

Match the selected tone.

Focus on audience benefit.

Avoid exaggerated marketing language.

Avoid political or partisan statements.

Keep public-sector communication trustworthy.

Respect the selected platform.

Use emojis only when appropriate.

Use a limited number of relevant hashtags.

Use the strategy CTA whenever possible.


OMSAR RULES
===========

For OMSAR:

- use professional institutional language
- emphasize public-sector impact
- emphasize reform or modernization where relevant
- remain factual
- avoid excessive promotional language
- avoid overly casual language


DAWLATI RULES
=============

For DAWLATI:

- use clear citizen-friendly communication
- emphasize practical benefit
- explain services simply
- use actionable CTAs
- use clear Modern Standard Arabic for service announcements
- always write DAWLATI in Arabic as «دولتي»
- never invent service names
- preserve exact numbers stated in the brief
- do not add unsupported functionality
- do not add placeholder links

Example of safe Arabic phrasing:

"أصبحت 7 خدمات تابعة لوزارة الزراعة متاحة الآن إلكترونياً عبر منصة «دولتي»."

This is safer than inventing details about those seven services.


MATCHMAKING RULES
=================

For Matchmaking:

- focus on opportunities
- focus on skills and contribution
- use professional motivating language
- do not describe every opportunity as a traditional job
- never invent eligibility requirements


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


HASHTAGS
========

Use a small number of relevant hashtags.

Do not invent campaign names.

Prefer general factual hashtags
when uncertain.


BRAND CHECK
===========

After generating the content,
review it.

Check:

- country is Lebanon
- correct brand
- correct Arabic spelling of «دولتي»
- correct tone
- audience relevance
- factual grounding
- explicit numbers preserved
- no invented services
- no invented facts
- no placeholder links
- no unsupported functionality claims
- CTA quality
- platform suitability
- Arabic quality
- English quality
- confidentiality
- no partisan wording

Return:

PASS

only if the content follows all rules.

Return:

REVISE

if something should be corrected.

Human approval is always required before publication.


IMPORTANT
=========

Return only the JSON structure.

Do not add any explanation outside JSON.
"""


# --------------------------------------------------
# Generate Content
# --------------------------------------------------

def generate_marketing_content(
    brief: str,
    strategy: dict
) -> dict:

    prompt = build_content_prompt(
        brief,
        strategy
    )

    try:

        response = chat(
            model=MODEL_NAME,

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are BrandPilot AI, a controlled "
                        "marketing assistant for Lebanese "
                        "public-sector organizations. "
                        "OMSAR is Lebanese. "
                        "DAWLATI is Lebanon's digital platform "
                        "for government services developed by OMSAR. "
                        "In Arabic, DAWLATI must always be written "
                        "as «دولتي». "
                        "The OMSAR Matchmaking Portal is Lebanese. "
                        "Never assume another country. "
                        "Never invent facts. "
                        "Never invent service names. "
                        "Never add placeholder links. "
                        "Preserve explicit numbers from the brief. "
                        "Use only supplied context. "
                        "Return structured JSON only."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            format=MarketingContent.model_json_schema(),

            think=False,

            options={
                "temperature": 0
            }
        )

    except Exception as error:

        raise RuntimeError(
            "Could not connect to the local Ollama model. "
            "Make sure Ollama is running and qwen3:4b "
            f"is installed. Details: {error}"
        )


    raw_content = response.message.content


    if not raw_content:

        raise RuntimeError(
            "The local AI returned an empty response."
        )


    try:

        content = MarketingContent.model_validate_json(
            raw_content
        )

    except Exception as error:

        raise RuntimeError(
            "The local AI response could not be validated "
            "against the BrandPilot schema. "
            f"Details: {error}"
        )


    # --------------------------------------------------
    # Validate Requested Languages
    # --------------------------------------------------

    requested_languages = set(
        strategy.get(
            "languages",
            []
        )
    )


    if (
        "Arabic" in requested_languages
        and not content.caption_ar.strip()
    ):

        raise RuntimeError(
            "Arabic was requested, but the local model "
            "returned an empty Arabic caption. "
            "Please generate the content again."
        )


    if (
        "English" in requested_languages
        and not content.caption_en.strip()
    ):

        raise RuntimeError(
            "English was requested, but the local model "
            "returned an empty English caption. "
            "Please generate the content again."
        )


    # --------------------------------------------------
    # Additional Safety Validation
    # --------------------------------------------------

    combined_text = " ".join(
        [
            content.caption_ar,
            content.caption_en,
            content.visual_concept,
            content.visual_generation_prompt,
            content.cta,
            " ".join(content.hashtags),
            " ".join(
                item.headline + " " + item.body
                for item in content.content_structure
            )
        ]
    )


    forbidden_placeholders = [
        "[link]",
        "[الرابط]",
        "[url]",
        "[website]"
    ]


    if any(
        placeholder.lower() in combined_text.lower()
        for placeholder in forbidden_placeholders
    ):

        raise RuntimeError(
            "The local model generated a placeholder link. "
            "Please generate the content again."
        )


    forbidden_country_terms = [
        "Saudi Arabia",
        "Saudi",
        "Vision 2030",
        "السعودية",
        "رؤية 2030"
    ]


    if any(
        term.lower() in combined_text.lower()
        for term in forbidden_country_terms
    ):

        raise RuntimeError(
            "The local model introduced an incorrect country "
            "or unrelated external context. "
            "Please generate the content again."
        )


    if (
        "Arabic" in requested_languages
        and "دولتي" not in content.caption_ar
        and strategy.get("brand_key") == "dawlati"
    ):

        raise RuntimeError(
            "The Arabic Dawlati caption did not use the official "
            "Arabic spelling «دولتي». "
            "Please generate the content again."
        )


    return content.model_dump()
