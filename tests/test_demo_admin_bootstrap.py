import io
import logging
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from auth import Role
from database import DemoAdminBootstrapError, bootstrap_demo_admin
from repositories import Repository
from services import BrandPilotService


USERNAME = "demo-admin"
PASSWORD = "Secure-Demo-9!Password"
DISPLAY_NAME = "Demo Administrator"
DEMO_ENV = {
    "BRANDPILOT_DEMO_ADMIN_USERNAME": USERNAME,
    "BRANDPILOT_DEMO_ADMIN_PASSWORD": PASSWORD,
    "BRANDPILOT_DEMO_ADMIN_DISPLAY_NAME": DISPLAY_NAME,
}


class DemoAdminBootstrapTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = Path(self.temp.name) / "bootstrap.db"

    def tearDown(self):
        self.temp.cleanup()

    def _repository(self, environment=None):
        with patch.dict("os.environ", environment or {}, clear=True):
            return Repository(self.path)

    def _stored_user(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT * FROM users").fetchone()
            return dict(row) if row else None

    def test_empty_database_with_all_variables_creates_admin(self):
        repository = self._repository(DEMO_ENV)
        users = repository.list_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["username"], USERNAME)
        self.assertEqual(users[0]["display_name"], DISPLAY_NAME)
        self.assertEqual(users[0]["role"], Role.ADMIN.value)

    def test_password_is_hashed(self):
        self._repository(DEMO_ENV)
        password_hash = self._stored_user()["password_hash"]
        self.assertNotEqual(password_hash, PASSWORD)
        self.assertTrue(password_hash.startswith("$argon2"))

    def test_created_user_authenticates(self):
        repository = self._repository(DEMO_ENV)
        authenticated = BrandPilotService(repository).authenticate(USERNAME, PASSWORD)
        self.assertIsNotNone(authenticated)
        self.assertEqual(authenticated["role"], Role.ADMIN.value)

    def test_existing_users_prevent_bootstrap(self):
        repository = self._repository()
        repository.create_user("existing", "Existing User", Role.EDITOR.value, "stored-hash")
        with patch.dict("os.environ", DEMO_ENV, clear=True):
            self.assertFalse(bootstrap_demo_admin(self.path))
        users = repository.list_users()
        self.assertEqual([user["username"] for user in users], ["existing"])

    def test_missing_password_does_not_bootstrap(self):
        environment = {key: value for key, value in DEMO_ENV.items() if "PASSWORD" not in key}
        self.assertEqual(self._repository(environment).list_users(), [])

    def test_missing_username_does_not_bootstrap(self):
        environment = {key: value for key, value in DEMO_ENV.items() if "USERNAME" not in key}
        self.assertEqual(self._repository(environment).list_users(), [])

    def test_missing_display_name_does_not_bootstrap(self):
        environment = {key: value for key, value in DEMO_ENV.items() if "DISPLAY_NAME" not in key}
        self.assertEqual(self._repository(environment).list_users(), [])

    def test_repeated_bootstrap_does_not_duplicate_user(self):
        repository = self._repository(DEMO_ENV)
        with patch.dict("os.environ", DEMO_ENV, clear=True):
            self.assertFalse(bootstrap_demo_admin(self.path))
            Repository(self.path)
        self.assertEqual(len(repository.list_users()), 1)

    def test_plaintext_password_does_not_appear_in_database(self):
        self._repository(DEMO_ENV)
        database_bytes = self.path.read_bytes()
        self.assertNotIn(PASSWORD.encode("utf-8"), database_bytes)
        with closing(sqlite3.connect(self.path)) as connection:
            dump = "\n".join(connection.iterdump())
        self.assertNotIn(PASSWORD, dump)

    def test_password_does_not_appear_in_logs_or_errors(self):
        log_output = io.StringIO()
        handler = logging.StreamHandler(log_output)
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            with patch.dict("os.environ", DEMO_ENV, clear=True), patch(
                "database.hash_password",
                side_effect=RuntimeError(f"hashing failed for {PASSWORD}"),
            ):
                with self.assertRaises(DemoAdminBootstrapError) as context:
                    Repository(self.path)
        finally:
            root_logger.removeHandler(handler)

        self.assertNotIn(PASSWORD, str(context.exception))
        self.assertNotIn(PASSWORD, log_output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
