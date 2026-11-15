"""Parameterized data access for users, campaigns, versions, and audits."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from database import connect, initialize_database, transaction


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for key in ("target_audience", "requested_languages", "generated_strategy", "generated_content", "validation_results", "normalization_changes", "repair_metadata", "metadata"):
        if key in result and result[key] is not None:
            result[key] = json.loads(result[key])
    return result


class Repository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        initialize_database(self.db_path)

    def audit(self, actor_id: int | None, action: str, entity_type: str, entity_id: Any = None, metadata: dict | None = None, connection=None) -> None:
        executor = connection or connect(self.db_path)
        try:
            executor.execute(
                "INSERT INTO audit_events(actor_user_id,action,entity_type,entity_id,metadata) VALUES(?,?,?,?,?)",
                (actor_id, action, entity_type, None if entity_id is None else str(entity_id), _json(metadata or {})),
            )
            if connection is None:
                executor.commit()
        finally:
            if connection is None:
                executor.close()

    def create_user(self, username: str, display_name: str, role: str, password_hash: str, actor_id: int | None = None) -> dict:
        try:
            with transaction(self.db_path) as db:
                cursor = db.execute(
                    "INSERT INTO users(username,display_name,role,password_hash) VALUES(?,?,?,?)",
                    (username.strip(), display_name.strip(), role, password_hash),
                )
                self.audit(actor_id, "user_created", "user", cursor.lastrowid, {"role": role}, db)
                row = db.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
                return _decode_row(row)
        except sqlite3.IntegrityError as error:
            raise ValueError("Username already exists.") from error

    def get_user_by_username(self, username: str) -> dict | None:
        with connect(self.db_path) as db:
            return _decode_row(db.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone())

    def get_user(self, user_id: int) -> dict | None:
        with connect(self.db_path) as db:
            return _decode_row(db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())

    def list_users(self) -> list[dict]:
        with connect(self.db_path) as db:
            return [_decode_row(row) for row in db.execute("SELECT id,username,display_name,role,is_active,created_at FROM users ORDER BY username")]

    def update_user(self, user_id: int, *, role: str | None = None, active: bool | None = None, password_hash: str | None = None, actor_id: int) -> None:
        changes, values, actions = [], [], []
        if role is not None:
            changes.append("role=?"); values.append(role); actions.append(("user_role_changed", {"role": role}))
        if active is not None:
            changes.append("is_active=?"); values.append(int(active)); actions.append(("user_activated" if active else "user_deactivated", {}))
        if password_hash is not None:
            changes.append("password_hash=?"); values.append(password_hash); actions.append(("password_reset", {}))
        if not changes:
            return
        with transaction(self.db_path) as db:
            db.execute(f"UPDATE users SET {','.join(changes)} WHERE id=?", (*values, user_id))
            for action, metadata in actions:
                self.audit(actor_id, action, "user", user_id, metadata, db)

    def create_campaign(self, creator_id: int, payload: dict) -> dict:
        with transaction(self.db_path) as db:
            cursor = db.execute(
                """INSERT INTO campaigns(creator_user_id,brand,original_brief,objective,target_audience,platform,requested_languages,
                generated_strategy,generated_content,validation_results,normalization_changes,repair_metadata)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (creator_id, payload["brand"], payload["original_brief"], payload["objective"], _json(payload.get("target_audience", [])), payload["platform"], _json(payload.get("requested_languages", [])), _json(payload.get("generated_strategy")), _json(payload.get("generated_content")), _json(payload.get("validation_results")), _json(payload.get("normalization_changes")), _json(payload.get("repair_metadata"))),
            )
            campaign_id = cursor.lastrowid
            self._add_version(db, campaign_id, 1, creator_id, payload)
            self.audit(creator_id, "campaign_created", "campaign", campaign_id, {}, db)
            if payload.get("generated_strategy"):
                self.audit(creator_id, "strategy_generated", "campaign", campaign_id, {}, db)
            if payload.get("generated_content"):
                self.audit(creator_id, "content_generated", "campaign", campaign_id, {}, db)
            repair = payload.get("repair_metadata") or {}
            if repair.get("repair_attempted"):
                self.audit(
                    creator_id,
                    "automatic_repair_succeeded" if repair.get("repair_successful") else "automatic_repair_failed",
                    "campaign",
                    campaign_id,
                    {},
                    db,
                )
        return self.get_campaign(campaign_id)

    def _add_version(self, db, campaign_id: int, number: int, actor_id: int, payload: dict) -> None:
        db.execute(
            "INSERT INTO campaign_versions(campaign_id,version_number,brief_snapshot,strategy_snapshot,content_snapshot,validation_snapshot,repair_metadata,created_by) VALUES(?,?,?,?,?,?,?,?)",
            (campaign_id, number, payload["original_brief"], _json(payload.get("generated_strategy")), _json(payload.get("generated_content")), _json(payload.get("validation_results")), _json(payload.get("repair_metadata")), actor_id),
        )

    def get_campaign(self, campaign_id: int) -> dict | None:
        with connect(self.db_path) as db:
            return _decode_row(db.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone())

    def list_campaigns(self, *, status: str | None = None, creator_id: int | None = None) -> list[dict]:
        clauses, values = [], []
        if status: clauses.append("status=?"); values.append(status)
        if creator_id: clauses.append("creator_user_id=?"); values.append(creator_id)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with connect(self.db_path) as db:
            return [_decode_row(row) for row in db.execute("SELECT * FROM campaigns" + where + " ORDER BY updated_at DESC", values)]

    def revise_campaign(self, campaign_id: int, actor_id: int, payload: dict) -> dict:
        current = self.get_campaign(campaign_id)
        if not current: raise ValueError("Campaign not found.")
        version = current["version"] + 1
        with transaction(self.db_path) as db:
            db.execute(
                """UPDATE campaigns SET original_brief=?,brand=?,objective=?,target_audience=?,platform=?,requested_languages=?,
                generated_strategy=?,generated_content=?,validation_results=?,normalization_changes=?,repair_metadata=?,status='DRAFT',version=?,
                approved_at=NULL,approved_by=NULL,rejected_at=NULL,rejected_by=NULL,review_comment=NULL,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (payload["original_brief"], payload["brand"], payload["objective"], _json(payload.get("target_audience", [])), payload["platform"], _json(payload.get("requested_languages", [])), _json(payload.get("generated_strategy")), _json(payload.get("generated_content")), _json(payload.get("validation_results")), _json(payload.get("normalization_changes")), _json(payload.get("repair_metadata")), version, campaign_id),
            )
            self._add_version(db, campaign_id, version, actor_id, payload)
            self.audit(actor_id, "campaign_edited", "campaign", campaign_id, {"version": version}, db)
        return self.get_campaign(campaign_id)

    def transition(self, campaign_id: int, actor_id: int, status: str, comment: str | None = None) -> dict:
        fields = {"SUBMITTED_FOR_REVIEW": "submitted_at=CURRENT_TIMESTAMP", "APPROVED": "approved_at=CURRENT_TIMESTAMP,approved_by=?,approved_version=version", "REJECTED": "rejected_at=CURRENT_TIMESTAMP,rejected_by=?"}
        params: list[Any] = [] if status == "SUBMITTED_FOR_REVIEW" else [actor_id]
        params.extend([status, comment, campaign_id])
        with transaction(self.db_path) as db:
            db.execute(f"UPDATE campaigns SET {fields[status]},status=?,review_comment=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", params)
            self.audit(actor_id, status.casefold(), "campaign", campaign_id, {}, db)
        return self.get_campaign(campaign_id)

    def versions(self, campaign_id: int) -> list[dict]:
        with connect(self.db_path) as db:
            return [dict(row) for row in db.execute("SELECT * FROM campaign_versions WHERE campaign_id=? ORDER BY version_number DESC", (campaign_id,))]

    def audit_events(self, campaign_id: int | None = None) -> list[dict]:
        query, values = "SELECT * FROM audit_events", []
        if campaign_id is not None:
            query += " WHERE entity_type='campaign' AND entity_id=?"; values.append(str(campaign_id))
        query += " ORDER BY id DESC"
        with connect(self.db_path) as db:
            return [_decode_row(row) for row in db.execute(query, values)]

