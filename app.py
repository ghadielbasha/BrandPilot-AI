"""BrandPilot AI internal-team Streamlit workspace."""

from __future__ import annotations

import streamlit as st

from ai_engine import CONFIG, generate_campaign_strategy
from auth import Role
from config import AI_PROVIDER, DB_PATH, ENVIRONMENT, MODEL_NAME
from content_generator import generate_marketing_content
from grounding_engine import SUPPORTED_BRANDS, build_grounding_context
from health import check_health
from repositories import Repository
from services import AuthorizationError, BrandPilotService, WorkflowError


st.set_page_config(page_title="BrandPilot AI", page_icon="BP", layout="wide")
repository = Repository(DB_PATH)
service = BrandPilotService(repository)


def safe_error(message: str, error: Exception | None = None) -> None:
    st.error(message)
    if error and st.session_state.get("user", {}).get("role") == Role.ADMIN.value:
        with st.expander("Technical details"):
            st.code(str(error))


def login_page() -> None:
    st.title("BrandPilot AI")
    st.caption("OMSAR internal branding and digital-marketing pilot")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
    if submitted:
        user = service.authenticate(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        st.error("Sign-in failed. Check your credentials or contact an administrator.")
    if not repository.list_users():
        st.info("No users exist. An administrator must run: python scripts/create_admin.py")


def campaign_payload(brief: str, strategy: dict, content: dict | None) -> dict:
    validation = {}
    normalization, repair = [], {}
    if content:
        validation = {
            key: content.get(key)
            for key in ("security_validation", "terminology_validation", "factual_validation", "language_validation")
        }
        normalization = content.get("terminology_normalization", {}).get("changes", [])
        repair = content.get("repair", {})
    return {
        "brand": strategy["brand_key"], "original_brief": brief,
        "objective": strategy["objective"], "target_audience": strategy["target_audience"],
        "platform": strategy["platform"], "requested_languages": strategy["languages"],
        "generated_strategy": strategy, "generated_content": content,
        "validation_results": validation, "normalization_changes": normalization,
        "repair_metadata": repair,
    }


def dashboard(actor: dict) -> None:
    st.header("Dashboard")
    campaigns = service.list_campaigns(actor)
    counts = {status: sum(item["status"] == status for item in campaigns) for status in ("DRAFT", "SUBMITTED_FOR_REVIEW", "APPROVED", "REJECTED")}
    columns = st.columns(4)
    for column, label, status in zip(columns, ("My Drafts", "Waiting for Review", "Approved", "Rejected"), counts):
        column.metric(label, counts[status])
    st.info("Human review is mandatory. BrandPilot never publishes content automatically.")


def create_campaign(actor: dict) -> None:
    st.header("Create Campaign")
    brands = CONFIG["brands"]
    with st.form("campaign_strategy"):
        brief = st.text_area("Campaign brief", height=150)
        selected_brand = st.selectbox("Brand", ["Auto Detect"] + [item["display_name"] for item in brands.values()])
        objective = st.selectbox("Objective", ["Auto Detect", "Awareness", "Engagement", "Service Adoption", "Institutional Update"])
        platform = st.selectbox("Platform", ["Instagram", "LinkedIn", "Facebook"])
        languages = st.multiselect("Languages", ["Arabic", "English"], default=["Arabic", "English"])
        audience = st.text_input("Target audience (comma-separated)")
        make_strategy = st.form_submit_button("Generate strategy", type="primary")
    if make_strategy:
        if not brief.strip() or not languages:
            st.warning("Enter a brief and select at least one language.")
        else:
            try:
                st.session_state.draft_brief = brief
                st.session_state.draft_strategy = generate_campaign_strategy(brief, selected_brand, objective, platform, languages, audience)
                st.session_state.draft_content = None
                repository.audit(actor["id"], "strategy_generated", "campaign_draft")
            except Exception as error:
                safe_error("BrandPilot could not create a compliant strategy.", error)
    strategy = st.session_state.get("draft_strategy")
    if not strategy:
        return
    st.subheader("Approved strategy")
    left, right = st.columns(2)
    left.write(f"**Brand:** {strategy['brand']}  \n**Objective:** {strategy['objective']}  \n**Audience:** {', '.join(strategy['target_audience'])}")
    right.write(f"**Platform:** {strategy['platform']}  \n**Format:** {strategy['recommended_format']}  \n**Languages:** {', '.join(strategy['languages'])}")
    st.info(strategy["campaign_angle"])
    if st.button("Generate marketing content", type="primary"):
        try:
            with st.spinner("Generating locally and running all validators..."):
                st.session_state.draft_content = generate_marketing_content(st.session_state.draft_brief, strategy)
                repository.audit(actor["id"], "content_generated", "campaign_draft", metadata={
                    "repair_attempted": bool(st.session_state.draft_content.get("repair", {}).get("repair_attempted"))
                })
        except Exception as error:
            repository.audit(actor["id"], "content_generation_blocked", "campaign_draft")
            safe_error("BrandPilot could not produce a compliant campaign after one automatic correction attempt.", error)
    content = st.session_state.get("draft_content")
    if content:
        render_content(content)
    if st.button("Save draft", disabled=content is None):
        try:
            saved = service.create_campaign(actor, campaign_payload(st.session_state.draft_brief, strategy, content))
            st.success(f"Campaign #{saved['id']} saved as Draft.")
            st.session_state.draft_strategy = st.session_state.draft_content = None
        except Exception as error:
            safe_error("The draft could not be saved.", error)


def render_content(content: dict) -> None:
    tabs = st.tabs(["Arabic", "English", "Structure", "Visual", "Validation"])
    tabs[0].write(content.get("caption_ar") or "Not requested")
    tabs[1].write(content.get("caption_en") or "Not requested")
    with tabs[2]:
        for item in content.get("content_structure", []):
            st.markdown(f"**{item['number']}. {item['headline']}** — {item['body']}")
    with tabs[3]:
        st.write(content.get("visual_concept", ""))
        st.code(content.get("visual_generation_prompt", ""), language=None)
        st.write(f"**CTA:** {content.get('cta', '')}")
        st.write(" ".join(content.get("hashtags", [])))
    with tabs[4]:
        cols = st.columns(4)
        for col, key, label in zip(cols, ("security_validation", "terminology_validation", "factual_validation", "language_validation"), ("Security", "Terminology", "Factual", "Language")):
            col.metric(label, (content.get(key) or {}).get("status", "N/A"))
        repair = content.get("repair", {})
        st.write(f"**Repair attempted:** {'Yes' if repair.get('repair_attempted') else 'No'}")
        if repair.get("initial_validation_error"):
            with st.expander("Initial validator reason"):
                st.write(repair["initial_validation_error"])


def campaign_detail(actor: dict, campaign: dict) -> None:
    st.subheader(f"Campaign #{campaign['id']} · {campaign['status'].replace('_', ' ').title()}")
    st.write(f"**Brand:** {campaign['brand']} · **Version:** {campaign['version']} · **Platform:** {campaign['platform']}")
    st.write(f"**Brief:** {campaign['original_brief']}")
    if campaign.get("generated_strategy"):
        with st.expander("Strategy", expanded=True): st.json(campaign["generated_strategy"])
    if campaign.get("generated_content"): render_content(campaign["generated_content"])
    if campaign.get("review_comment"): st.warning(f"Review comment: {campaign['review_comment']}")
    if campaign["status"] in {"DRAFT", "REJECTED"} and actor["role"] in {Role.ADMIN.value, Role.EDITOR.value}:
        if st.button("Submit for review", key=f"submit-{campaign['id']}"):
            try: service.submit(actor, campaign["id"]); st.rerun()
            except Exception as error: safe_error("Campaign could not be submitted.", error)
    with st.expander("Version history"):
        st.dataframe(repository.versions(campaign["id"]), hide_index=True, use_container_width=True)
    if actor["role"] in {Role.ADMIN.value, Role.REVIEWER.value}:
        with st.expander("Campaign audit history"):
            st.dataframe(repository.audit_events(campaign["id"]), hide_index=True, use_container_width=True)


def campaigns_page(actor: dict) -> None:
    st.header("Campaigns")
    status = st.selectbox("Status filter", ["All", "DRAFT", "SUBMITTED_FOR_REVIEW", "APPROVED", "REJECTED"])
    campaigns = service.list_campaigns(actor, status=None if status == "All" else status)
    if not campaigns: st.info("No campaigns match this filter."); return
    labels = {f"#{item['id']} · {item['brand']} · {item['status']}": item for item in campaigns}
    campaign_detail(actor, labels[st.selectbox("Campaign", list(labels))])


def review_queue(actor: dict) -> None:
    st.header("Review Queue")
    campaigns = service.list_campaigns(actor, status="SUBMITTED_FOR_REVIEW")
    if not campaigns: st.info("No campaigns are waiting for review."); return
    labels = {f"#{item['id']} · {item['brand']} · creator {item['creator_user_id']}": item for item in campaigns}
    campaign = labels[st.selectbox("Campaign", list(labels))]
    campaign_detail(actor, campaign)
    comment = st.text_area("Review comment")
    approve, reject = st.columns(2)
    if approve.button("Approve", type="primary", use_container_width=True):
        try: service.approve(actor, campaign["id"], comment); st.rerun()
        except Exception as error: safe_error("Campaign approval was blocked.", error)
    if reject.button("Reject", use_container_width=True):
        try: service.reject(actor, campaign["id"], comment); st.rerun()
        except Exception as error: safe_error("A rejection reason is required and the campaign must await review.", error)


def users_page(actor: dict) -> None:
    st.header("User Management")
    st.dataframe(repository.list_users(), hide_index=True, use_container_width=True)
    with st.form("new_user"):
        username, display = st.text_input("Username"), st.text_input("Display name")
        role = st.selectbox("Role", [item.value for item in Role])
        password = st.text_input("Temporary password", type="password")
        if st.form_submit_button("Create user"):
            try: service.create_user(actor, username, display, role, password); st.success("User created."); st.rerun()
            except Exception as error: safe_error("User could not be created.", error)
    user_ids = {f"{item['username']} ({item['role']})": item for item in repository.list_users()}
    selected = user_ids[st.selectbox("Manage user", list(user_ids))]
    new_role = st.selectbox("Assigned role", [item.value for item in Role], index=[item.value for item in Role].index(selected["role"]))
    active = st.checkbox("Active", value=bool(selected["is_active"]))
    reset = st.text_input("New password (leave blank to keep)", type="password")
    if st.button("Update user"):
        try: service.update_user(actor, selected["id"], role=new_role, active=active, **({"password": reset} if reset else {})); st.success("User updated."); st.rerun()
        except Exception as error: safe_error("User could not be updated.", error)


def system_page() -> None:
    st.header("Knowledge & System Information")
    for brand in sorted(SUPPORTED_BRANDS):
        context = build_grounding_context(brand)
        st.write(f"**{brand.title()}** — {len(context.source_ids)} approved sources; records: {', '.join(context.record_names)}")
    st.caption(
        f"Environment: {ENVIRONMENT} · Provider: {AI_PROVIDER} · Model: {MODEL_NAME}"
    )
    st.json(check_health(check_model=True))


if "user" not in st.session_state:
    login_page()
    st.stop()

actor = st.session_state.user
st.sidebar.title("BrandPilot AI")
st.sidebar.write(f"{actor['display_name']} · {actor['role']}")
pages = ["Dashboard", "Create Campaign", "Campaigns", "Knowledge & System"]
if actor["role"] in {Role.ADMIN.value, Role.REVIEWER.value}: pages.insert(3, "Review Queue")
if actor["role"] == Role.ADMIN.value: pages.extend(["User Management", "Audit Log"])
page = st.sidebar.radio("Workspace", pages)
if st.sidebar.button("Sign out"):
    del st.session_state.user
    st.rerun()

try:
    if page == "Dashboard": dashboard(actor)
    elif page == "Create Campaign": create_campaign(actor)
    elif page == "Campaigns": campaigns_page(actor)
    elif page == "Review Queue": review_queue(actor)
    elif page == "User Management": users_page(actor)
    elif page == "Audit Log": st.header("Audit Log"); st.dataframe(repository.audit_events(), hide_index=True, use_container_width=True)
    else: system_page()
except (AuthorizationError, WorkflowError) as error:
    safe_error("This action is not permitted in the current workflow.", error)
except Exception as error:
    safe_error("BrandPilot could not complete this request.", error)
