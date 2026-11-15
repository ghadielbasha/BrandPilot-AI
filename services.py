"""Server-side authentication, authorization, and campaign workflow."""

from __future__ import annotations

from auth import Role, hash_password, verify_password
from grounding_engine import SUPPORTED_BRANDS
from repositories import Repository
from validators.security_validator import SecurityValidationError, enforce_security


class AuthorizationError(PermissionError):
    pass


class WorkflowError(ValueError):
    pass


class BrandPilotService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def _require(self, actor: dict, *roles: Role) -> None:
        current = self.repository.get_user(actor.get("id")) if actor else None
        if not current or not current.get("is_active") or current.get("role") not in {role.value for role in roles}:
            raise AuthorizationError("You are not authorized to perform this action.")

    def authenticate(self, username: str, password: str) -> dict | None:
        user = self.repository.get_user_by_username(username)
        if not user or not user["is_active"] or not verify_password(user["password_hash"], password):
            self.repository.audit(user["id"] if user else None, "login_failure", "authentication")
            return None
        self.repository.audit(user["id"], "login_success", "authentication")
        return {key: user[key] for key in ("id", "username", "display_name", "role", "is_active")}

    def create_user(self, actor: dict, username: str, display_name: str, role: str, password: str) -> dict:
        self._require(actor, Role.ADMIN)
        if role not in {item.value for item in Role}: raise ValueError("Invalid role.")
        return self.repository.create_user(username, display_name, role, hash_password(password), actor["id"])

    def update_user(self, actor: dict, user_id: int, **changes) -> None:
        self._require(actor, Role.ADMIN)
        if "password" in changes:
            changes["password_hash"] = hash_password(changes.pop("password"))
        self.repository.update_user(user_id, actor_id=actor["id"], **changes)

    def create_campaign(self, actor: dict, payload: dict) -> dict:
        self._require(actor, Role.ADMIN, Role.EDITOR)
        self._validate_brand(payload)
        return self.repository.create_campaign(actor["id"], payload)

    def list_campaigns(self, actor: dict, status: str | None = None) -> list[dict]:
        self._require(actor, Role.ADMIN, Role.EDITOR, Role.REVIEWER)
        current = self.repository.get_user(actor["id"])
        if current["role"] == Role.EDITOR.value:
            return self.repository.list_campaigns(status=status, creator_id=actor["id"])
        campaigns = self.repository.list_campaigns(status=status)
        if current["role"] == Role.REVIEWER.value:
            return [item for item in campaigns if item["status"] != "DRAFT"]
        return campaigns

    def revise_campaign(self, actor: dict, campaign_id: int, payload: dict) -> dict:
        self._require(actor, Role.ADMIN, Role.EDITOR)
        self._validate_brand(payload)
        campaign = self._campaign(campaign_id)
        current = self.repository.get_user(actor["id"])
        if current["role"] == Role.EDITOR.value and campaign["creator_user_id"] != actor["id"]:
            raise AuthorizationError("Editors may revise only their own campaigns.")
        if campaign["status"] not in {"DRAFT", "REJECTED", "APPROVED"}: raise WorkflowError("Submitted campaigns cannot be edited.")
        return self.repository.revise_campaign(campaign_id, actor["id"], payload)

    def submit(self, actor: dict, campaign_id: int) -> dict:
        self._require(actor, Role.ADMIN, Role.EDITOR)
        campaign = self._campaign(campaign_id)
        current = self.repository.get_user(actor["id"])
        if current["role"] == Role.EDITOR.value and campaign["creator_user_id"] != actor["id"]:
            raise AuthorizationError("Editors may submit only their own campaigns.")
        if campaign["status"] not in {"DRAFT", "REJECTED"}: raise WorkflowError("Only drafts or rejected campaigns can be submitted.")
        return self.repository.transition(campaign_id, actor["id"], "SUBMITTED_FOR_REVIEW")

    def approve(self, actor: dict, campaign_id: int, comment: str | None = None) -> dict:
        self._require(actor, Role.ADMIN, Role.REVIEWER)
        campaign = self._campaign(campaign_id)
        if campaign["status"] != "SUBMITTED_FOR_REVIEW": raise WorkflowError("Campaign is not awaiting review.")
        if campaign["creator_user_id"] == actor["id"]: raise AuthorizationError("Creators cannot approve their own campaigns.")
        self._validate_comment(comment)
        return self.repository.transition(campaign_id, actor["id"], "APPROVED", comment)

    def reject(self, actor: dict, campaign_id: int, comment: str) -> dict:
        self._require(actor, Role.ADMIN, Role.REVIEWER)
        if not comment.strip(): raise WorkflowError("A rejection reason is required.")
        self._validate_comment(comment)
        if self._campaign(campaign_id)["status"] != "SUBMITTED_FOR_REVIEW": raise WorkflowError("Campaign is not awaiting review.")
        return self.repository.transition(campaign_id, actor["id"], "REJECTED", comment.strip())

    def _campaign(self, campaign_id: int) -> dict:
        campaign = self.repository.get_campaign(campaign_id)
        if not campaign: raise WorkflowError("Campaign not found.")
        return campaign

    @staticmethod
    def _validate_brand(payload: dict) -> None:
        brand = str(payload.get("brand", "")).strip().casefold()
        strategy_brand = str((payload.get("generated_strategy") or {}).get("brand_key", brand)).strip().casefold()
        if brand not in SUPPORTED_BRANDS or strategy_brand != brand:
            raise WorkflowError("Campaign brand is unsupported or inconsistent.")

    @staticmethod
    def _validate_comment(comment: str | None) -> None:
        if not comment:
            return
        try:
            enforce_security(comment, "review_comment")
        except SecurityValidationError as error:
            raise WorkflowError("The review comment failed security validation.") from error

