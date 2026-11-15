import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from auth import Role, hash_password, verify_password
from repositories import Repository
from services import AuthorizationError, BrandPilotService, WorkflowError


PASSWORD = "Correct-Horse-9!Battery"


class PilotServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = Path(self.temp.name) / "pilot.db"
        self.repo = Repository(self.path)
        admin_row = self.repo.create_user("admin", "Admin", Role.ADMIN.value, hash_password(PASSWORD))
        self.admin = {**admin_row, "is_active": 1}
        self.service = BrandPilotService(self.repo)
        self.editor = self.service.create_user(self.admin, "editor", "Editor", Role.EDITOR.value, PASSWORD)
        self.reviewer = self.service.create_user(self.admin, "reviewer", "Reviewer", Role.REVIEWER.value, PASSWORD)
        self.payload = {
            "brand": "omsar", "original_brief": "Approved brief", "objective": "Awareness",
            "target_audience": ["Citizens"], "platform": "LinkedIn",
            "requested_languages": ["English"], "generated_strategy": {"brand_key": "omsar"},
            "generated_content": {"caption_en": "Approved draft"},
            "validation_results": {"security": "PASS"}, "normalization_changes": [],
            "repair_metadata": {"repair_attempted": False},
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_password_hashing_and_inactive_login(self):
        user = self.repo.get_user_by_username("editor")
        self.assertNotEqual(user["password_hash"], PASSWORD)
        self.assertTrue(verify_password(user["password_hash"], PASSWORD))
        self.assertFalse(verify_password(user["password_hash"], "wrong"))
        self.service.update_user(self.admin, user["id"], active=False)
        self.assertIsNone(self.service.authenticate("editor", PASSWORD))

    def test_duplicate_username_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.create_user(self.admin, "EDITOR", "Duplicate", Role.EDITOR.value, PASSWORD)

    def test_non_admin_cannot_manage_users(self):
        for actor in (self.editor, self.reviewer):
            with self.assertRaises(AuthorizationError):
                self.service.create_user(actor, "blocked", "Blocked", Role.EDITOR.value, PASSWORD)

    def test_editor_scope_and_reviewer_visibility_are_enforced(self):
        other = self.service.create_user(self.admin, "other", "Other", Role.EDITOR.value, PASSWORD)
        campaign = self.service.create_campaign(other, self.payload)
        with self.assertRaises(AuthorizationError):
            self.service.revise_campaign(self.editor, campaign["id"], self.payload)
        self.assertEqual(self.service.list_campaigns(self.editor), [])
        self.assertEqual(self.service.list_campaigns(self.reviewer), [])
        self.service.submit(other, campaign["id"])
        self.assertEqual(len(self.service.list_campaigns(self.reviewer)), 1)

    def test_workflow_separation_and_versions(self):
        campaign = self.service.create_campaign(self.editor, self.payload)
        submitted = self.service.submit(self.editor, campaign["id"])
        self.assertEqual(submitted["status"], "SUBMITTED_FOR_REVIEW")
        with self.assertRaises(AuthorizationError):
            self.service.approve(self.editor, campaign["id"])
        approved = self.service.approve(self.reviewer, campaign["id"], "Approved")
        self.assertEqual(approved["approved_version"], 1)
        revised_payload = {**self.payload, "original_brief": "Revised approved brief"}
        revised = self.service.revise_campaign(self.editor, campaign["id"], revised_payload)
        self.assertEqual((revised["status"], revised["version"]), ("DRAFT", 2))
        self.assertEqual(len(self.repo.versions(campaign["id"])), 2)

    def test_creator_reviewer_cannot_self_approve(self):
        campaign = self.repo.create_campaign(self.reviewer["id"], self.payload)
        self.repo.transition(campaign["id"], self.reviewer["id"], "SUBMITTED_FOR_REVIEW")
        with self.assertRaises(AuthorizationError):
            self.service.approve(self.reviewer, campaign["id"])

    def test_rejection_requires_comment_and_can_resubmit(self):
        campaign = self.service.submit(self.editor, self.service.create_campaign(self.editor, self.payload)["id"])
        with self.assertRaises(WorkflowError):
            self.service.reject(self.reviewer, campaign["id"], " ")
        rejected = self.service.reject(self.reviewer, campaign["id"], "Clarify scope")
        revised = self.service.revise_campaign(self.editor, campaign["id"], self.payload)
        self.assertEqual(self.service.submit(self.editor, revised["id"])["status"], "SUBMITTED_FOR_REVIEW")
        self.assertEqual(rejected["status"], "REJECTED")

    def test_persistence_audit_and_foreign_keys(self):
        campaign = self.service.create_campaign(self.editor, self.payload)
        reconstructed = Repository(self.path)
        self.assertEqual(reconstructed.get_campaign(campaign["id"])["original_brief"], "Approved brief")
        self.assertTrue(reconstructed.audit_events(campaign["id"]))
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA foreign_keys=ON")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO campaigns(creator_user_id,brand,original_brief,objective,target_audience,platform,requested_languages) VALUES(999,'x','x','x','[]','x','[]')")


if __name__ == "__main__":
    unittest.main()
