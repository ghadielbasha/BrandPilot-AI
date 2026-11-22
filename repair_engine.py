import json
from typing import Any

from prompt_compaction import compact_strategy_for_prompt, compact_validation_context


# --------------------------------------------------
# Configuration
# --------------------------------------------------

MAX_REPAIR_ATTEMPTS = 1


# --------------------------------------------------
# Errors
# --------------------------------------------------

class RepairEngineError(Exception):
    """Raised when BrandPilot cannot prepare a repair request."""
    pass


# --------------------------------------------------
# Repair Prompt
# --------------------------------------------------

def build_repair_prompt(
    brief: str,
    strategy: dict[str, Any],
    failed_content: dict[str, Any],
    validation_error: str,
    validation_context: dict[str, Any] | None = None,
) -> str:
    """
    Build a controlled repair prompt for a failed campaign draft.

    The repair model receives:
    - original campaign brief
    - approved strategy
    - failed generated draft
    - exact deterministic validator feedback

    It must return a complete corrected draft.
    """

    if not isinstance(brief, str) or not brief.strip():
        raise RepairEngineError(
            "Campaign brief cannot be empty."
        )

    if not isinstance(strategy, dict):
        raise RepairEngineError(
            "Campaign strategy must be a dictionary."
        )

    if not isinstance(failed_content, dict):
        raise RepairEngineError(
            "Failed campaign content must be a dictionary."
        )

    if (
        not isinstance(validation_error, str)
        or not validation_error.strip()
    ):
        raise RepairEngineError(
            "Validation error cannot be empty."
        )


    strategy_json = json.dumps(
        compact_strategy_for_prompt(strategy),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    failed_content_json = json.dumps(
        failed_content,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    if validation_context is not None and not isinstance(validation_context, dict):
        raise RepairEngineError(
            "Validation context must be a dictionary when provided."
        )

    validation_context_json = json.dumps(
        compact_validation_context(validation_context),
        ensure_ascii=False,
        indent=2,
    )

    target_audience = strategy.get("target_audience", [])
    if isinstance(target_audience, str):
        target_audience = [target_audience]
    target_audience = [
        audience.strip() for audience in target_audience
        if isinstance(audience, str) and audience.strip()
    ]

    context_issues = (validation_context or {}).get("issues", [])
    audience_expansion = (
        "Unsupported audience expansion" in validation_error
        or any(
            isinstance(issue, dict)
            and issue.get("type") == "unsupported_audience"
            for issue in context_issues
        )
    )

    audience_repair_section = ""
    if audience_expansion and target_audience:
        approved_lines = "\n".join(f"- {audience}" for audience in target_audience)
        approved_text = " ".join(target_audience).casefold()
        removal_candidates = [
            "Citizens",
            "Citizens of Lebanon",
            "General public",
            "Rural communities",
            "generic businesses",
        ]
        if "citizen" in approved_text:
            removal_candidates = [
                value for value in removal_candidates
                if "citizen" not in value.casefold()
            ]
        removal_lines = "\n".join(
            f"- {value}" for value in removal_candidates
        )
        audience_repair_section = f"""

MANDATORY AUDIENCE REPAIR
=========================
The previous draft used an unauthorized audience.

APPROVED AUDIENCE:
{approved_lines}

REMOVE ALL UNSUPPORTED AUDIENCE REFERENCES including:
{removal_lines}
- any audience not present in the approved strategy

Replace those phrases with wording based only on the APPROVED AUDIENCE.
Do not preserve an invalid audience just because it appeared in the failed draft.

IMPORTANT:
Validator errors override the wording of the failed draft.
The failed draft is NOT authoritative.
The approved strategy is authoritative.
"""

    subject_issues = [
        issue for issue in context_issues
        if isinstance(issue, dict) and issue.get("type") in {
            "subject_binding_violation",
            "subject_preservation_failure",
            "unknown_service_visual_detail",
        }
    ]
    subject_repair_section = ""
    if subject_issues:
        subjects = list(dict.fromkeys(
            issue.get("campaign_subject") for issue in subject_issues
            if issue.get("campaign_subject")
        ))
        subject_lines = "\n".join(f"- {subject}" for subject in subjects)
        subject_repair_section = f"""

MANDATORY SUBJECT-BINDING REPAIR
================================
The failed draft substituted general brand/platform facts for the campaign
subject or requested unavailable service-level details.

CAMPAIGN SUBJECT:
{subject_lines or '- Preserve the subject exactly as stated in the brief.'}

REMOVE every substituted platform feature, directory, capability, invented
service item, named service card, individual description, link, URL, and
identity-specific icon that lacks approved service-level evidence.

Approved general brand knowledge is context only. It must not fill missing
service names or become an item in the campaign's quantified service list.

Replace removed items with generic wording that preserves the service count,
responsible ministry/entity, platform, and approved audience.
Validator feedback overrides the failed draft.
"""


    return f"""
You are BrandPilot AI Repair Mode.

A previously generated marketing campaign failed
BrandPilot's deterministic validation checks.

Your job is to correct the failed campaign.

This is a REPAIR operation.
Do not create a different campaign.

You must preserve the original campaign brief,
approved strategy,
brand,
audience,
platform,
languages,
and supported facts.


ORIGINAL CAMPAIGN BRIEF
=======================
{brief}


APPROVED CAMPAIGN STRATEGY
==========================
{strategy_json}


FAILED CAMPAIGN DRAFT
=====================
{failed_content_json}


DETERMINISTIC VALIDATION ERROR
==============================
{validation_error}


STRUCTURED VALIDATION CONTEXT
=============================
{validation_context_json}

{audience_repair_section}

{subject_repair_section}


REPAIR RULES
============

1. Correct every issue identified by the validator.

2. Do NOT ignore or argue with the validator.

3. Do NOT invent new facts while repairing the draft.

4. Do NOT invent:
   - service names
   - URLs
   - statistics
   - dates
   - eligibility rules
   - fees
   - documents
   - processing times
   - partnerships
   - capabilities
   - benefits
   - audience groups
   - platform behaviors such as "link in bio"

   If the brief gives the number of services but does not name them,
   remove every inferred service title and enumeration. Keep only safe
   generic wording such as "7 Ministry services", "the available
   services", or "services now available online through Dawlati".

5. Preserve explicit numbers from the campaign brief.

6. Preserve the requested languages.

7. Preserve the correct brand.

8. DAWLATI always refers to Lebanon.

9. The official Arabic spelling of Dawlati is:

دولتي

10. When appropriate, use:

منصة «دولتي»

11. Do not infer that "available online" means:
   - apply online
   - submit online
   - pay online
   - track a request
   - complete the service digitally

12. Do not add unsupported benefits such as:
   - easier
   - simpler
   - faster
   - more efficient
   - convenient
   - time saving
   - 24/7

12a. "Available online" does not support "access anytime",
"from anywhere", "wherever you are", "في أي وقت", "من أي مكان",
or "أينما كنت". Remove those claims unless the approved evidence
explicitly contains them.

12b. When the strategy has an explicit target_audience, keep the
repaired audience within that scope. Do not replace a narrow audience
with citizens, the general public, rural communities, or businesses
generally unless that broader group is explicitly approved.

12c. Preserve subject/entity binding. General organization or platform facts
must not replace the specific campaign subject. A quantified service subject
must retain its responsible ministry/entity.

12d. Approved general Dawlati features and capabilities are context only.
Never use them to fill unnamed service lists. If service-level names,
descriptions, links, or URLs are unavailable, remove them and use generic,
subject-preserving wording.

12e. "Now available" does not mean "new services". Remove "new" or "جديدة"
unless the original brief or approved strategy explicitly says the services
themselves are new.

13. Use grammatically correct Arabic.

14. Use grammatically correct English.

15. Fix malformed carousel headlines and bodies too,
not only the captions.

16. Fix the CTA if it contains an unsupported claim.

17. Fix visual text if it contains malformed language
or unsupported factual claims.

17a. Check and repair every field independently: both captions,
every structure headline and body, visual concept, visual-generation
prompt, CTA, and hashtags. Removing an invention from the caption is
not enough if it remains in a slide, CTA, visual instruction, or tag.

17b. Replace unsupported "Apply now", "Link in bio", benefit claims,
and invented beneficiary groups with neutral wording grounded in the
brief and approved strategy.

18. Return the COMPLETE corrected campaign object.

19. Do not return only the corrected field.

20. Do not include explanations outside the JSON.

The corrected draft will be checked again by
BrandPilot's independent validators.

If it still fails validation,
BrandPilot will block the campaign.

Return only the corrected structured JSON.
""".strip()


# --------------------------------------------------
# Repair Metadata
# --------------------------------------------------

def create_repair_metadata(
    attempted: bool,
    successful: bool,
    initial_error: str | None = None,
) -> dict[str, Any]:

    return {
        "max_repair_attempts": MAX_REPAIR_ATTEMPTS,
        "repair_attempted": attempted,
        "repair_successful": successful,
        "initial_validation_error": initial_error,
    }


# --------------------------------------------------
# Manual Test
# --------------------------------------------------

if __name__ == "__main__":

    sample_brief = (
        "Seven Ministry of Agriculture services "
        "are now available online through Dawlati."
    )

    sample_strategy = {
        "brand_key": "dawlati",
        "brand": "DAWLATI",
        "objective": "Service Adoption",
        "languages": [
            "Arabic",
            "English",
        ],
    }

    sample_failed_content = {
        "caption_ar": (
            "منصة «دولتي» تُعَدُّ الآن "
            "7 خدمات حكومية."
        ),

        "caption_en": (
            "Seven Ministry of Agriculture services "
            "are available through Dawlati."
        ),
    }

    sample_error = (
        "caption_ar: Malformed Arabic structure detected."
    )


    prompt = build_repair_prompt(
        brief=sample_brief,
        strategy=sample_strategy,
        failed_content=sample_failed_content,
        validation_error=sample_error,
    )


    print(
        "BrandPilot Repair Engine: PASS"
    )

    print()

    print(
        prompt
    )
    
