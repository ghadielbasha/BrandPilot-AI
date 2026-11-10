import streamlit as st
import yaml
from pathlib import Path

# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="BrandPilot AI",
    page_icon="🚀",
    layout="wide"
)

# --------------------------------------------------
# Load Brand Intelligence
# --------------------------------------------------

CONFIG_PATH = Path("brandpilot_brand_intelligence.yaml")

if not CONFIG_PATH.exists():
    st.error(
        "brandpilot_brand_intelligence.yaml was not found. "
        "Make sure it is inside the BrandPilot-AI folder."
    )
    st.stop()

with open(CONFIG_PATH, "r", encoding="utf-8") as file:
    brand_config = yaml.safe_load(file)

brands = brand_config.get("brands", {})

# --------------------------------------------------
# Header
# --------------------------------------------------

st.title("🚀 BrandPilot AI")
st.subheader("AI-Powered Branding & Digital Marketing Assistant")

st.write(
    "Create brand-aligned marketing strategies and content based on "
    "organizational context, audience, platform, and communication objectives."
)

st.divider()

# --------------------------------------------------
# Campaign Brief
# --------------------------------------------------

st.header("Create a Campaign")

brief = st.text_area(
    "What do you want to communicate?",
    placeholder=(
        "Example: Seven Ministry of Agriculture services "
        "are now available online through Dawlati."
    ),
    height=150
)

# --------------------------------------------------
# Brand
# --------------------------------------------------

brand_options = ["Auto Detect"]

for brand_key, brand_data in brands.items():
    brand_options.append(
        brand_data.get("display_name", brand_key)
    )

selected_brand = st.selectbox(
    "Brand",
    brand_options
)

# --------------------------------------------------
# Objective
# --------------------------------------------------

selected_objective = st.selectbox(
    "Campaign Objective",
    [
        "Auto Detect",
        "Awareness",
        "Engagement",
        "Service Adoption",
        "Opportunity Recruitment",
        "Institutional Update"
    ]
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

st.write("Languages")

col1, col2 = st.columns(2)

with col1:
    arabic = st.checkbox("Arabic", value=True)

with col2:
    english = st.checkbox("English", value=True)

# --------------------------------------------------
# Target Audience
# --------------------------------------------------

audience = st.text_input(
    "Target Audience",
    placeholder="Example: Farmers and agricultural businesses"
)

# --------------------------------------------------
# Generate Strategy
# --------------------------------------------------

if st.button(
    "Generate Campaign Strategy",
    type="primary",
    use_container_width=True
):

    if not brief.strip():
        st.warning("Please enter a campaign brief.")

    else:
        selected_languages = []

        if arabic:
            selected_languages.append("Arabic")

        if english:
            selected_languages.append("English")

        st.success("Campaign brief received successfully.")

        st.subheader("Campaign Input")

        st.write("**Brief:**", brief)
        st.write("**Brand:**", selected_brand)
        st.write("**Objective:**", selected_objective)
        st.write("**Platform:**", platform)

        st.write(
            "**Languages:**",
            ", ".join(selected_languages)
            if selected_languages
            else "None selected"
        )

        st.write(
            "**Target Audience:**",
            audience if audience else "Auto Detect"
        )

        st.info(
            "The next development step will connect this interface "
            "to the BrandPilot AI strategy engine."
        )

# --------------------------------------------------
# Brand Intelligence
# --------------------------------------------------

st.divider()

with st.expander("View Brand Intelligence"):

    for brand_key, brand_data in brands.items():

        st.subheader(
            brand_data.get("display_name", brand_key)
        )

        st.write(
            "**Role:**",
            brand_data.get("role", "")
        )

        st.write(
            "**Personality:**",
            ", ".join(
                brand_data.get("personality", [])
            )
        )

        st.write(
            "**Default Tone:**",
            ", ".join(
                brand_data.get("default_tone", [])
            )
        )

        st.write(
            "**Main Audiences:**",
            ", ".join(
                brand_data.get("audiences", [])
            )
        )

        st.divider()
        