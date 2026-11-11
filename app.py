import streamlit as st
import yaml
from pathlib import Path

from ai_engine import generate_campaign_strategy
from content_generator import generate_marketing_content


# --------------------------------------------------
# Page Configuration
# --------------------------------------------------

st.set_page_config(
    page_title="BrandPilot AI",
    page_icon="🚀",
    layout="wide"
)


# --------------------------------------------------
# Session State
# --------------------------------------------------

if "strategy" not in st.session_state:
    st.session_state.strategy = None

if "strategy_brief" not in st.session_state:
    st.session_state.strategy_brief = None

if "generated_content" not in st.session_state:
    st.session_state.generated_content = None


# --------------------------------------------------
# Load Brand Intelligence
# --------------------------------------------------

CONFIG_PATH = Path(
    "brandpilot_brand_intelligence.yaml"
)

if not CONFIG_PATH.exists():

    st.error(
        "brandpilot_brand_intelligence.yaml was not found."
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
# Objective
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
# Audience
# --------------------------------------------------

audience = st.text_input(
    "Target Audience",
    placeholder=(
        "Example: Farmers and agricultural businesses"
    )
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


        if not selected_languages:

            st.warning(
                "Please select at least one language."
            )

        else:

            strategy = generate_campaign_strategy(
                brief=brief,
                selected_brand=selected_brand,
                selected_objective=selected_objective,
                platform=platform,
                languages=selected_languages,
                audience_input=audience,
            )


            st.session_state.strategy = (
                strategy
            )

            st.session_state.strategy_brief = (
                brief
            )

            st.session_state.generated_content = (
                None
            )


# --------------------------------------------------
# Display Strategy
# --------------------------------------------------

strategy = st.session_state.strategy


if strategy:

    st.success(
        "Campaign strategy generated."
    )


    st.header(
        "AI Campaign Strategy"
    )


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
        )


    st.subheader(
        "Recommended Tone"
    )


    st.write(
        " · ".join(
            strategy["tone"]
        )
    )


    st.subheader(
        "Campaign Angle"
    )


    st.info(
        strategy[
            "campaign_angle"
        ]
    )


    st.subheader(
        "Recommended CTA"
    )


    st.success(
        strategy[
            "cta"
        ]
    )


    st.divider()


    # --------------------------------------------------
    # Generate Marketing Content
    # --------------------------------------------------

    st.header(
        "Generate Marketing Content"
    )


    st.write(
        "BrandPilot will now use the approved strategy "
        "and brand intelligence to create the campaign."
    )


    if st.button(
        "✨ Generate Marketing Content",
        use_container_width=True
    ):

        try:

            with st.spinner(
                "BrandPilot is generating the campaign locally..."
            ):

                content = generate_marketing_content(
                    brief=(
                        st.session_state
                        .strategy_brief
                    ),
                    strategy=strategy
                )


                st.session_state.generated_content = (
                    content
                )


        except Exception as error:

            st.session_state.generated_content = None


            st.error(
                f"Content generation failed: {error}"
            )


# --------------------------------------------------
# Display Generated Content
# --------------------------------------------------

content = (
    st.session_state
    .generated_content
)


if content:

    st.divider()


    st.header(
        "Generated Campaign Content"
    )


    (
        tab_ar,
        tab_en,
        tab_structure,
        tab_visual,
        tab_check
    ) = st.tabs(
        [
            "🇱🇧 Arabic",
            "🇬🇧 English",
            "📑 Content Structure",
            "🎨 Visual",
            "✅ Brand Check"
        ]
    )


    # --------------------------------------------------
    # Arabic
    # --------------------------------------------------

    with tab_ar:

        if "Arabic" not in strategy[
            "languages"
        ]:

            st.info(
                "Arabic was not requested."
            )


        elif content[
            "caption_ar"
        ]:

            st.subheader(
                "Arabic Caption"
            )


            st.write(
                content[
                    "caption_ar"
                ]
            )


        else:

            st.warning(
                "Arabic was requested, but the AI "
                "did not generate an Arabic caption."
            )


    # --------------------------------------------------
    # English
    # --------------------------------------------------

    with tab_en:

        if "English" not in strategy[
            "languages"
        ]:

            st.info(
                "English was not requested."
            )


        elif content[
            "caption_en"
        ]:

            st.subheader(
                "English Caption"
            )


            st.write(
                content[
                    "caption_en"
                ]
            )


        else:

            st.warning(
                "English was requested, but the AI "
                "did not generate an English caption."
            )


    # --------------------------------------------------
    # Content Structure
    # --------------------------------------------------

    with tab_structure:

        st.subheader(
            strategy[
                "recommended_format"
            ]
        )


        for item in content[
            "content_structure"
        ]:

            st.markdown(
                f"### {item['number']}. "
                f"{item['headline']}"
            )


            st.caption(
                item[
                    "type"
                ]
            )


            st.write(
                item[
                    "body"
                ]
            )


            st.divider()


    # --------------------------------------------------
    # Visual
    # --------------------------------------------------

    with tab_visual:

        st.subheader(
            "Visual Concept"
        )


        st.write(
            content[
                "visual_concept"
            ]
        )


        st.subheader(
            "AI Visual Prompt"
        )


        st.code(
            content[
                "visual_generation_prompt"
            ],
            language=None
        )


        st.subheader(
            "Call to Action"
        )


        st.success(
            content[
                "cta"
            ]
        )


        st.subheader(
            "Hashtags"
        )


        st.write(
            " ".join(
                content[
                    "hashtags"
                ]
            )
        )


    # --------------------------------------------------
    # Brand Check
    # --------------------------------------------------

    with tab_check:

        brand_check = content[
            "brand_check"
        ]


        status = brand_check[
            "status"
        ]


        if status == "PASS":

            st.success(
                "Brand Check: PASS"
            )


        else:

            st.warning(
                "Brand Check: REVISE"
            )


        st.subheader(
            "Issues"
        )


        if brand_check[
            "issues"
        ]:

            for issue in brand_check[
                "issues"
            ]:

                st.write(
                    f"- {issue}"
                )


        else:

            st.write(
                "No major issues detected."
            )


        st.subheader(
            "Recommendations"
        )


        if brand_check[
            "recommendations"
        ]:

            for recommendation in brand_check[
                "recommendations"
            ]:

                st.write(
                    f"- {recommendation}"
                )


        else:

            st.write(
                "No additional recommendations."
            )


        st.info(
            "Human approval is required before publication."
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
        