import re
from pathlib import Path

import yaml

from grounding_engine import build_grounding_context
from validators.factual_validator import (
    validate_factual_claims,
)


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

CONFIG_PATH = (
    BASE_DIR
    / "brandpilot_brand_intelligence.yaml"
)


class StrategyValidationError(Exception):
    """Raised when a generated campaign strategy is unsafe."""
    pass


# --------------------------------------------------
# Brand Intelligence Loader
# --------------------------------------------------

def load_brand_intelligence():
    """Load BrandPilot's structured brand intelligence."""

    if not CONFIG_PATH.exists():

        raise FileNotFoundError(
            "brandpilot_brand_intelligence.yaml "
            "was not found."
        )

    with open(
        CONFIG_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        data = yaml.safe_load(
            file
        )

    if not isinstance(
        data,
        dict
    ):

        raise ValueError(
            "Brand intelligence configuration "
            "must contain a YAML object."
        )

    if "brands" not in data:

        raise ValueError(
            "Brand intelligence configuration "
            "does not contain 'brands'."
        )

    return data


CONFIG = load_brand_intelligence()


# --------------------------------------------------
# Brand Detection
# --------------------------------------------------

def detect_brand(
    brief: str
) -> str:

    text = brief.casefold()

    # Explicit brand references receive priority.

    dawlati_explicit = [
        "dawlati",
        "دولتي",
    ]

    if any(
        keyword in text
        for keyword in dawlati_explicit
    ):
        return "dawlati"

    # Context-based detection.

    dawlati_keywords = [
        "government service",
        "government services",
        "online service",
        "online services",
        "apply online",
        "digital service",
        "digital services",
        "خدمة حكومية",
        "خدمات حكومية",
        "خدمة إلكترونية",
        "خدمات إلكترونية",
    ]

    if any(
        keyword in text
        for keyword in dawlati_keywords
    ):
        return "dawlati"


    return "omsar"


# --------------------------------------------------
# Objective Detection
# --------------------------------------------------

def detect_objective(
    brief: str,
    brand: str
) -> str:

    text = brief.casefold()


    service_keywords = [
        "service available",
        "services available",
        "available online",
        "apply online",
        "online service",
        "online services",
        "digital service",
        "digital services",
        "launched on dawlati",
        "available through dawlati",
        "متاحة إلكترونياً",
        "متاحة إلكترونيًا",
        "خدمات متاحة",
    ]


    engagement_keywords = [
        "register",
        "join",
        "participate",
        "feedback",
        "survey",
        "discussion",
        "focus group",
        "share your opinion",
        "consultation",
    ]


    institutional_keywords = [
        "meeting",
        "minister",
        "conference",
        "strategy",
        "reform",
        "agreement",
        "workshop",
    ]


    # Brand-specific objectives receive priority.

    if (
        brand == "dawlati"
        and any(
            keyword in text
            for keyword in service_keywords
        )
    ):
        return "service_adoption"


    if any(
        keyword in text
        for keyword in engagement_keywords
    ):
        return "engagement"


    if (
        brand == "omsar"
        and any(
            keyword in text
            for keyword in institutional_keywords
        )
    ):
        return "institutional_update"


    return "awareness"


# --------------------------------------------------
# Audience Detection
# --------------------------------------------------

def detect_audience(
    brief: str,
    brand: str
):

    text = brief.casefold()

    explicit_patterns = (
        ("University students", r"\buniversity students?\b|طلاب الجامعات"),
        ("Farmers", r"\bfarmers?\b|المزارعين|المزارعون"),
        ("Producers", r"\bproducers?\b|المنتجين|المنتجون"),
    )
    explicit_audiences = [
        label for label, pattern in explicit_patterns
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]
    if explicit_audiences:
        return explicit_audiences


    audience_map = {
        "farmer": [
            "Farmers",
        ],

        "agriculture": [
            "Farmers",
            "Producers",
            "Agricultural businesses",
        ],

        "وزارة الزراعة": [
            "Farmers",
            "Producers",
            "Agricultural businesses",
        ],

        "student": [
            "University students",
        ],

        "graduate": [
            "Fresh graduates",
        ],

        "expert": [
            "Professionals",
            "Experts",
        ],

        "investor": [
            "Investors",
            "Businesses",
        ],

        "tourism": [
            "Tourism-sector businesses",
        ],

        "hotel": [
            "Hotel owners",
            "Tourism-sector businesses",
        ],

        "restaurant": [
            "Restaurant owners",
            "Tourism-sector businesses",
        ],

        "citizen": [
            "Citizens",
        ],

        "municipality": [
            "Municipalities",
            "Local government institutions",
        ],
    }


    for keyword, audiences in (
        audience_map.items()
    ):

        if keyword in text:
            return audiences


    default_audiences = {
        "omsar": [
            "Citizens",
            "Government institutions",
            "Partners",
        ],

        "dawlati": [
            "Citizens",
            "Businesses",
        ],

    }


    return default_audiences.get(
        brand,
        [
            "General public"
        ]
    )


# --------------------------------------------------
# Audience Formatting
# --------------------------------------------------

def format_audience_list(
    audiences
) -> str:

    if not audiences:
        return "the target audience"


    audiences = [
        audience.lower()
        for audience in audiences
    ]


    if len(
        audiences
    ) == 1:

        return audiences[
            0
        ]


    if len(
        audiences
    ) == 2:

        return (
            f"{audiences[0]} "
            f"and {audiences[1]}"
        )


    return (
        ", ".join(
            audiences[
                :-1
            ]
        )
        + f", and {audiences[-1]}"
    )


# --------------------------------------------------
# Explicit Service Count Extraction
# --------------------------------------------------

NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
}


ARABIC_NUMBER_WORDS = {
    "واحد": "1",
    "واحدة": "1",
    "اثنان": "2",
    "اثنين": "2",
    "ثلاثة": "3",
    "أربعة": "4",
    "اربعة": "4",
    "خمسة": "5",
    "ستة": "6",
    "سبعة": "7",
    "سبع": "7",
    "ثمانية": "8",
    "ثمان": "8",
    "تسعة": "9",
    "عشرة": "10",
}


def extract_service_count(
    brief: str
) -> str | None:
    """
    Extract an explicit number associated with services.

    Example:
    Seven Ministry of Agriculture services -> 7
    7 services -> 7
    سبع خدمات -> 7
    """

    text = brief.casefold()


    arabic_digit_map = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩",
        "0123456789"
    )

    normalized = text.translate(
        arabic_digit_map
    )


    english_words = (
        "|".join(
            NUMBER_WORDS.keys()
        )
    )


    # Supports cases such as:
    # Seven Ministry of Agriculture services

    english_pattern = (
        rf"\b("
        rf"\d+|{english_words}"
        rf")\b"
        rf"(?:\s+[\w'-]+){{0,6}}"
        rf"\s+services?\b"
    )


    english_match = re.search(
        english_pattern,
        normalized,
        flags=re.IGNORECASE
    )


    if english_match:

        value = (
            english_match
            .group(1)
            .casefold()
        )

        return NUMBER_WORDS.get(
            value,
            value
        )


    # Arabic service count.

    for word, value in (
        ARABIC_NUMBER_WORDS.items()
    ):

        pattern = (
            rf"{re.escape(word)}"
            rf"(?:\s+\S+){{0,4}}"
            rf"\s+(?:خدمة|خدمات)"
        )

        if re.search(
            pattern,
            normalized
        ):
            return value


    arabic_numeric_match = re.search(
        r"\b(\d+)\b"
        r"(?:\s+\S+){0,4}"
        r"\s+(?:خدمة|خدمات)",
        normalized
    )


    if arabic_numeric_match:

        return (
            arabic_numeric_match
            .group(1)
        )


    return None


# --------------------------------------------------
# Subject Detection
# --------------------------------------------------

def detect_service_subject(
    brief: str
) -> str:

    text = brief.casefold()


    if (
        "ministry of agriculture"
        in text
        or "وزارة الزراعة"
        in text
    ):

        return (
            "Ministry of Agriculture services"
        )


    return "government services"


# --------------------------------------------------
# Tone Selection
# --------------------------------------------------

def select_tone(
    brand_data,
    objective: str
):

    tone_context_map = {
        "service_adoption": (
            "service_announcement"
        ),

        "engagement": (
            "citizen_engagement"
        ),

        "opportunity_recruitment": (
            "internship"
        ),

        "institutional_update": (
            "official_announcement"
        ),
    }


    tone_context = (
        tone_context_map.get(
            objective
        )
    )


    if tone_context:

        contextual_tone = (
            brand_data
            .get(
                "tone_by_context",
                {}
            )
            .get(
                tone_context
            )
        )


        if contextual_tone:
            return contextual_tone


    return brand_data.get(
        "default_tone",
        []
    )


# --------------------------------------------------
# Format Recommendation
# --------------------------------------------------

def recommend_format(
    brief: str,
    brand: str,
    objective: str,
    platform: str
) -> str:

    platform = (
        platform
        .strip()
        .casefold()
    )

    text = brief.casefold()


    if platform == "instagram":

        if (
            "how to" in text
            or "tutorial" in text
        ):

            return "Reel"


        if objective in [
            "service_adoption",
            "engagement",
            "opportunity_recruitment",
        ]:

            return "Carousel"


        return "Carousel"


    if platform == "linkedin":
        return "Professional Post"


    if platform == "facebook":
        return "Informational Post"


    return "Social Media Post"


# --------------------------------------------------
# Campaign Angle
# --------------------------------------------------

def generate_campaign_angle(
    brand: str,
    objective: str,
    audience,
    brief: str = ""
) -> str:

    audience_text = (
        format_audience_list(
            audience
        )
    )


    if brand == "dawlati":

        if objective == "service_adoption":

            service_count = (
                extract_service_count(
                    brief
                )
            )

            service_subject = (
                detect_service_subject(
                    brief
                )
            )


            if service_count:

                return (
                    f"Announce that {service_count} "
                    f"{service_subject} are now available "
                    f"online through Dawlati and encourage "
                    f"{audience_text} to explore the "
                    f"available services."
                )


            return (
                "Announce the government services described "
                "in the campaign brief and encourage "
                f"{audience_text} to explore the available "
                "service information through Dawlati."
            )


        if objective == "engagement":

            return (
                f"Invite {audience_text} to participate "
                "and share feedback on the topic described "
                "in the campaign brief."
            )


        return (
            "Communicate the Dawlati information stated in "
            "the campaign brief clearly and encourage users "
            "to explore the relevant government-service "
            "information."
        )


    if objective == "institutional_update":

        return (
            "Explain the initiative described in the "
            "campaign brief clearly and connect it only "
            "to the public-sector context supported by "
            "the brief."
        )


    return (
        "Communicate the information in the campaign brief "
        "clearly without adding unsupported benefits, "
        "results, or claims."
    )


# --------------------------------------------------
# CTA Selection
# --------------------------------------------------

def select_cta(
    brand: str,
    objective: str,
    brief: str = ""
) -> str:

    if (
        brand == "dawlati"
        and objective == "service_adoption"
    ):

        service_count = (
            extract_service_count(
                brief
            )
        )


        if service_count:

            return (
                f"Explore the {service_count} "
                "available services on Dawlati"
            )


        return (
            "Explore the available services "
            "on Dawlati"
        )


    if objective == "engagement":

        return (
            "Participate and share your feedback"
        )


    if objective == "institutional_update":

        return (
            "Learn more about the initiative"
        )


    if brand == "dawlati":

        return (
            "Discover available services on Dawlati"
        )


    return "Learn more"


# --------------------------------------------------
# Strategy Safety Validation
# --------------------------------------------------

def validate_campaign_strategy(
    brief: str,
    campaign_angle: str,
    cta: str
) -> dict:

    strategy_text = (
        campaign_angle
        + "\n"
        + cta
    )


    factual_result = (
        validate_factual_claims(
            brief=brief,
            generated_text=strategy_text
        )
    )


    # Number preservation is handled separately for
    # service counts. Other numbers such as years or
    # dates do not necessarily need to appear in the
    # high-level strategy.

    blocking_issues = [
        issue

        for issue
        in factual_result[
            "issues"
        ]

        if issue.get(
            "type"
        )
        != "missing_explicit_number"
    ]


    service_count = (
        extract_service_count(
            brief
        )
    )


    if (
        service_count
        and service_count
        not in strategy_text
    ):

        blocking_issues.append(
            {
                "type": (
                    "missing_service_count"
                ),

                "message": (
                    "The campaign strategy did not "
                    "preserve the explicit service "
                    f"count {service_count}."
                )
            }
        )


    if blocking_issues:

        messages = [
            issue.get(
                "message",
                "Unsafe strategy content."
            )

            for issue
            in blocking_issues
        ]

        raise StrategyValidationError(
            "Campaign strategy failed factual "
            "validation: "
            + "; ".join(
                messages
            )
        )


    return {
        "valid": True,
        "status": "PASS",
        "issues": [],
        "service_count": service_count,
    }


# --------------------------------------------------
# Main Strategy Function
# --------------------------------------------------

def generate_campaign_strategy(
    brief: str,
    selected_brand: str,
    selected_objective: str,
    platform: str,
    languages,
    audience_input: str = "",
):

    if not isinstance(
        brief,
        str
    ) or not brief.strip():

        raise ValueError(
            "Campaign brief cannot be empty."
        )


    brands = CONFIG[
        "brands"
    ]


    # --------------------------------------------------
    # Brand
    # --------------------------------------------------

    if selected_brand == "Auto Detect":

        brand_key = detect_brand(
            brief
        )

    else:

        brand_key = next(
            (
                key

                for key, value
                in brands.items()

                if value[
                    "display_name"
                ] == selected_brand
            ),

            "omsar",
        )


    if brand_key not in brands:

        raise ValueError(
            f"Unknown brand key: {brand_key}"
        )

    # Fail closed unless the selected brand's approved knowledge loads.
    grounding = build_grounding_context(brand_key)


    brand_data = brands[
        brand_key
    ]


    # --------------------------------------------------
    # Objective
    # --------------------------------------------------

    if (
        selected_objective
        == "Auto Detect"
    ):

        objective = detect_objective(
            brief,
            brand_key
        )

    else:

        objective = (
            selected_objective
            .strip()
            .casefold()
            .replace(
                " ",
                "_"
            )
        )


    # --------------------------------------------------
    # Audience
    # --------------------------------------------------

    if audience_input.strip():

        audiences = [
            audience.strip()

            for audience
            in audience_input.split(
                ","
            )

            if audience.strip()
        ]

    else:

        audiences = (
            detect_audience(
                brief,
                brand_key
            )
        )

    default_audiences = {
        "omsar": ["Citizens", "Government institutions", "Partners"],
        "dawlati": ["Citizens", "Businesses"],
    }
    audience_source = "user_input" if audience_input.strip() else "brief"
    audience_confirmation_required = (
        not audience_input.strip()
        and audiences == default_audiences.get(brand_key)
    )
    if audience_confirmation_required:
        audience_source = "inferred_default"


    # --------------------------------------------------
    # Tone
    # --------------------------------------------------

    tone = select_tone(
        brand_data,
        objective
    )


    # --------------------------------------------------
    # Format
    # --------------------------------------------------

    recommended_format = (
        recommend_format(
            brief,
            brand_key,
            objective,
            platform
        )
    )


    # --------------------------------------------------
    # Campaign Angle
    # --------------------------------------------------

    campaign_angle = (
        generate_campaign_angle(
            brand_key,
            objective,
            audiences,
            brief=brief
        )
    )


    # --------------------------------------------------
    # CTA
    # --------------------------------------------------

    cta = select_cta(
        brand_key,
        objective,
        brief=brief
    )


    # --------------------------------------------------
    # Independent Strategy Validation
    # --------------------------------------------------

    strategy_validation = (
        validate_campaign_strategy(
            brief=brief,
            campaign_angle=campaign_angle,
            cta=cta
        )
    )


    # --------------------------------------------------
    # Result
    # --------------------------------------------------

    return {
        "brand_key": brand_key,

        "brand": brand_data[
            "display_name"
        ],

        "objective": (
            objective
            .replace(
                "_",
                " "
            )
            .title()
        ),

        "target_audience": audiences,

        "audience_source": audience_source,

        "audience_confirmation_required": audience_confirmation_required,

        "platform": platform,

        "languages": languages,

        "tone": tone,

        "recommended_format": (
            recommended_format
        ),

        "campaign_angle": (
            campaign_angle
        ),

        "cta": cta,

        "strategy_validation": (
            strategy_validation
        ),

        "grounding_provenance": {
            "source_ids": list(grounding.source_ids),
            "record_names": list(grounding.record_names),
        },
    }
