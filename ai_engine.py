import yaml
from pathlib import Path


CONFIG_PATH = Path("brandpilot_brand_intelligence.yaml")


def load_brand_intelligence():
    """Load BrandPilot's structured brand intelligence."""

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "brandpilot_brand_intelligence.yaml was not found."
        )

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


CONFIG = load_brand_intelligence()


# --------------------------------------------------
# Brand Detection
# --------------------------------------------------

def detect_brand(brief: str) -> str:
    """
    Detect which BrandPilot brand should handle the campaign.
    """

    text = brief.lower()

    dawlati_keywords = [
        "dawlati",
        "دولتي",
        "government service",
        "government services",
        "online service",
        "online services",
        "apply online",
        "digital service",
        "digital services",
    ]

    matchmaking_keywords = [
        "matchmaking",
        "internship",
        "internships",
        "job opportunity",
        "opportunity",
        "fresh graduate",
        "student",
        "expert",
        "technical assistance",
        "research collaboration",
    ]

    if any(keyword in text for keyword in dawlati_keywords):
        return "dawlati"

    if any(keyword in text for keyword in matchmaking_keywords):
        return "matchmaking"

    return "omsar"


# --------------------------------------------------
# Objective Detection
# --------------------------------------------------

def detect_objective(brief: str, brand: str) -> str:
    """
    Determine the most likely marketing objective.
    """

    text = brief.lower()

    engagement_keywords = [
        "register",
        "join",
        "participate",
        "feedback",
        "survey",
        "discussion",
        "focus group",
        "share your opinion",
    ]

    opportunity_keywords = [
        "internship",
        "apply",
        "candidate",
        "vacancy",
        "expert",
        "opportunity",
        "recruit",
    ]

    service_keywords = [
        "service available",
        "services available",
        "available online",
        "apply online",
        "online service",
        "digital service",
        "launched on dawlati",
    ]

    institutional_keywords = [
        "meeting",
        "minister",
        "conference",
        "strategy",
        "reform",
        "agreement",
        "workshop",
        "consultation",
    ]

    if any(keyword in text for keyword in engagement_keywords):
        return "engagement"

    if brand == "matchmaking" and any(
        keyword in text for keyword in opportunity_keywords
    ):
        return "opportunity_recruitment"

    if brand == "dawlati" and any(
        keyword in text for keyword in service_keywords
    ):
        return "service_adoption"

    if brand == "omsar" and any(
        keyword in text for keyword in institutional_keywords
    ):
        return "institutional_update"

    return "awareness"


# --------------------------------------------------
# Audience Detection
# --------------------------------------------------

def detect_audience(brief: str, brand: str):
    """
    Suggest a likely audience based on the campaign.
    """

    text = brief.lower()

    audience_map = {
        "farmer": ["Farmers", "Agricultural businesses"],
        "agriculture": [
            "Farmers",
            "Producers",
            "Agricultural businesses"
        ],
        "student": [
            "University students",
            "Fresh graduates"
        ],
        "graduate": [
            "Fresh graduates"
        ],
        "expert": [
            "Professionals",
            "Experts"
        ],
        "investor": [
            "Investors",
            "Businesses"
        ],
        "tourism": [
            "Tourism-sector businesses"
        ],
        "hotel": [
            "Hotel owners",
            "Tourism-sector businesses"
        ],
        "restaurant": [
            "Restaurant owners",
            "Tourism-sector businesses"
        ],
        "citizen": [
            "Citizens"
        ],
        "municipality": [
            "Municipalities",
            "Local government institutions"
        ],
    }

    for keyword, audiences in audience_map.items():
        if keyword in text:
            return audiences

    default_audiences = {
        "omsar": [
            "Citizens",
            "Government institutions",
            "Partners"
        ],
        "dawlati": [
            "Citizens",
            "Businesses"
        ],
        "matchmaking": [
            "Students",
            "Fresh graduates",
            "Professionals",
            "Experts"
        ],
    }

    return default_audiences.get(
        brand,
        ["General public"]
    )


# --------------------------------------------------
# Audience Formatting
# --------------------------------------------------

def format_audience_list(audiences):
    """
    Convert an audience list into a natural sentence fragment.
    """

    if not audiences:
        return "the target audience"

    audiences = [
        audience.lower()
        for audience in audiences
    ]

    if len(audiences) == 1:
        return audiences[0]

    if len(audiences) == 2:
        return f"{audiences[0]} and {audiences[1]}"

    return (
        ", ".join(audiences[:-1])
        + f", and {audiences[-1]}"
    )


# --------------------------------------------------
# Tone Selection
# --------------------------------------------------

def select_tone(
    brand_data,
    objective: str
):
    """
    Select contextual tone based on campaign objective.
    """

    tone_context_map = {
        "service_adoption": "service_announcement",
        "engagement": "citizen_engagement",
        "opportunity_recruitment": "internship",
        "institutional_update": "official_announcement",
    }

    tone_context = tone_context_map.get(objective)

    if tone_context:
        contextual_tone = (
            brand_data
            .get("tone_by_context", {})
            .get(tone_context)
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
    """
    Recommend a content format based on platform and objective.
    """

    platform = platform.lower()
    text = brief.lower()

    if platform == "instagram":

        if "how to" in text or "tutorial" in text:
            return "Reel"

        if objective == "service_adoption":
            return "Carousel"

        if objective == "engagement":
            return "Carousel"

        if objective == "opportunity_recruitment":
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
    audience
) -> str:
    """
    Generate the strategic communication angle.
    """

    audience_text = format_audience_list(
        audience
    )

    if brand == "dawlati":

        if objective == "service_adoption":
            return (
                f"Show {audience_text} how the digital service "
                "can make government procedures easier and more efficient."
            )

        if objective == "engagement":
            return (
                f"Encourage {audience_text} to participate and "
                "share their feedback to help improve citizen services."
            )

        return (
            "Highlight how Dawlati makes government services "
            "easier to find, understand, and access."
        )

    if brand == "matchmaking":

        if objective == "opportunity_recruitment":
            return (
                f"Show {audience_text} how they can contribute "
                "their skills and expertise to meaningful "
                "public-sector initiatives."
            )

        return (
            "Highlight opportunities for collaboration between "
            "Lebanese talent and public-sector institutions."
        )

    if objective == "institutional_update":
        return (
            "Explain the initiative clearly, show why it matters, "
            "and connect it to public-sector modernization "
            "and citizen impact."
        )

    return (
        "Communicate the initiative clearly and focus on "
        "its value for citizens and public institutions."
    )


# --------------------------------------------------
# CTA Selection
# --------------------------------------------------

def select_cta(
    brand: str,
    objective: str
) -> str:
    """
    Select the most appropriate call to action.
    """

    if objective == "service_adoption":
        return "Explore the available service on Dawlati"

    if objective == "engagement":
        return "Participate and share your feedback"

    if objective == "opportunity_recruitment":
        return "Explore the opportunity and apply"

    if objective == "institutional_update":
        return "Learn more about the initiative"

    if brand == "dawlati":
        return "Discover available services on Dawlati"

    if brand == "matchmaking":
        return "Explore available opportunities"

    return "Learn more"


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
    """
    Generate the complete BrandPilot campaign strategy.
    """

    brands = CONFIG["brands"]

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
                for key, value in brands.items()
                if value["display_name"] == selected_brand
            ),
            "omsar",
        )

    brand_data = brands[brand_key]

    # --------------------------------------------------
    # Objective
    # --------------------------------------------------

    if selected_objective == "Auto Detect":
        objective = detect_objective(
            brief,
            brand_key
        )

    else:
        objective = (
            selected_objective
            .lower()
            .replace(" ", "_")
        )

    # --------------------------------------------------
    # Audience
    # --------------------------------------------------

    if audience_input.strip():

        audiences = [
            audience.strip()
            for audience in audience_input.split(",")
            if audience.strip()
        ]

    else:

        audiences = detect_audience(
            brief,
            brand_key
        )

    # --------------------------------------------------
    # Tone
    # --------------------------------------------------

    tone = select_tone(
        brand_data,
        objective
    )

    # --------------------------------------------------
    # Recommended Format
    # --------------------------------------------------

    recommended_format = recommend_format(
        brief,
        brand_key,
        objective,
        platform
    )

    # --------------------------------------------------
    # Campaign Angle
    # --------------------------------------------------

    campaign_angle = generate_campaign_angle(
        brand_key,
        objective,
        audiences
    )

    # --------------------------------------------------
    # CTA
    # --------------------------------------------------

    cta = select_cta(
        brand_key,
        objective
    )

    # --------------------------------------------------
    # Return Strategy
    # --------------------------------------------------

    return {
        "brand_key": brand_key,
        "brand": brand_data["display_name"],
        "objective": objective
        .replace("_", " ")
        .title(),
        "target_audience": audiences,
        "platform": platform,
        "languages": languages,
        "tone": tone,
        "recommended_format": recommended_format,
        "campaign_angle": campaign_angle,
        "cta": cta,
    }
