import streamlit as st
import yaml
from pathlib import Path

from ai_engine import generate_campaign_strategy


# --------------------------------------------------
# Page Configuration
# --------------------------------------------------

st.set_page_config(
    page_title="BrandPilot AI",
    page_icon="🚀",
    layout="wide"
)


# --------------------------------------------------
# Load Brand Intelligence
# --------------------------------------------------

CONFIG_PATH = Path(
    "brandpilot_brand_intelligence.yaml"
)

if not CONFIG_PATH.exists():

    st.error(
        "brandpilot_brand_intelligence.yaml was not found. "
        "Make sure it is inside the BrandPilot-AI folder."
    )

    st.stop()


with open(
    CONFIG_PATH,
    "r",
    encoding="utf-8"
) as file:

    brand_config = yaml.safe_load(
        file
    )


brands = brand_config.get(
    "brands",
    {}
)


# --------------------------------------------------
# Header
# --------------------------------------------------

st.title(
    "🚀 BrandPilot AI"
)

st.subheader(
    "AI-Powered Branding & Digital Marketing Assistant"
)

st.write(
    "Create brand-aligned marketing strategies and content "
    "based on organizational context, target audience, "
    "platform, and communication objectives."
)

st.divider()


# --------------------------------------------------
# Campaign Creation
# --------------------------------------------------

st.header(
    "Create a Campaign"
)


brief = st.text_area(
    "What do you want to communicate?",
    placeholder=(
        "Example: Seven Ministry of Agriculture services "
        "are now available online through Dawlati."
    ),
    height=150
)


# --------------------------------------------------
# Brand Selection
# --------------------------------------------------

brand_options = [
    "Auto Detect"
]

for brand_key, brand_data in brands.items():

    brand_options.append(
        brand_data.get(
            "display_name",
            brand_key
        )
    )


selected_brand = st.selectbox(
    "Brand",
    brand_options
)


# --------------------------------------------------
# Campaign Objective
# --------------------------------------------------

objective_options = [
    "Auto Detect",
    "Awareness",
    "Engagement",
    "Service Adoption",
    "Opportunity Recruitment",
    "Institutional Update"
]


selected_objective = st.selectbox(
    "Campaign Objective",
    objective_options
)


# --------------------------------------------------
# Platform
# --------------------------------------------------

platform = st.selectbox(
    "Platform",
    [
        "Instagram",
        "LinkedIn",
        "Facebook"
    ]
)


# --------------------------------------------------
# Languages
# --------------------------------------------------

st.write(
    "Languages"
)


col1, col2 = st.columns(
    2
)


with col1:

    arabic = st.checkbox(
        "Arabic",
        value=True
    )


with col2:

    english = st.checkbox(
        "English",
        value=True
    )


# --------------------------------------------------
# Target Audience
# --------------------------------------------------

audience = st.text_input(
    "Target Audience",
    placeholder=(
        "Example: Farmers and agricultural businesses"
    )
)


# --------------------------------------------------
# Generate Campaign Strategy
# --------------------------------------------------

if st.button(
    "Generate Campaign Strategy",
    type="primary",
    use_container_width=True
):

    if not brief.strip():

        st.warning(
            "Please enter a campaign brief."
        )

    else:

        selected_languages = []

        if arabic:
            selected_languages.append(
                "Arabic"
            )

        if english:
            selected_languages.append(
                "English"
            )


        strategy = generate_campaign_strategy(
            brief=brief,
            selected_brand=selected_brand,
            selected_objective=selected_objective,
            platform=platform,
            languages=selected_languages,
            audience_input=audience,
        )


        st.success(
            "Campaign strategy generated."
        )


        st.header(
            "AI Campaign Strategy"
        )


        # --------------------------------------------------
        # Strategy Overview
        # --------------------------------------------------

        col1, col2 = st.columns(
            2
        )


        with col1:

            st.metric(
                "Brand",
                strategy["brand"]
            )

            st.write(
                "**Objective:**",
                strategy["objective"]
            )

            st.write(
                "**Target Audience:**"
            )

            for item in strategy[
                "target_audience"
            ]:

                st.write(
                    f"- {item}"
                )


        with col2:

            st.metric(
                "Recommended Format",
                strategy[
                    "recommended_format"
                ]
            )

            st.write(
                "**Platform:**",
                strategy["platform"]
            )

            st.write(
                "**Languages:**",
                ", ".join(
                    strategy["languages"]
                )
                if strategy["languages"]
                else "None selected"
            )


        # --------------------------------------------------
        # Tone
        # --------------------------------------------------

        st.subheader(
            "Recommended Tone"
        )

        st.write(
            " · ".join(
                strategy["tone"]
            )
        )


        # --------------------------------------------------
        # Campaign Angle
        # --------------------------------------------------

        st.subheader(
            "Campaign Angle"
        )

        st.info(
            strategy[
                "campaign_angle"
            ]
        )


        # --------------------------------------------------
        # CTA
        # --------------------------------------------------

        st.subheader(
            "Recommended CTA"
        )

        st.success(
            strategy["cta"]
        )


# --------------------------------------------------
# Brand Intelligence Preview
# --------------------------------------------------

st.divider()


with st.expander(
    "View Brand Intelligence"
):

    for brand_key, brand_data in brands.items():

        st.subheader(
            brand_data.get(
                "display_name",
                brand_key
            )
        )


        st.write(
            "**Role:**",
            brand_data.get(
                "role",
                ""
            )
        )


        st.write(
            "**Personality:**",
            ", ".join(
                brand_data.get(
                    "personality",
                    []
                )
            )
        )


        st.write(
            "**Default Tone:**",
            ", ".join(
                brand_data.get(
                    "default_tone",
                    []
                )
            )
        )


        st.write(
            "**Main Audiences:**",
            ", ".join(
                brand_data.get(
                    "audiences",
                    []
                )
            )
        )


        st.divider()
        