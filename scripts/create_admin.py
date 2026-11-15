"""Securely bootstrap a BrandPilot administrator."""
from getpass import getpass
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auth import Role, hash_password
from config import DB_PATH
from repositories import Repository

def main() -> None:
    repository = Repository(DB_PATH)
    username = input("Username: ").strip()
    display_name = input("Display name: ").strip()
    if not username or not display_name:
        raise SystemExit("Username and display name are required.")
    password = getpass("Password: ")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")
    try:
        repository.create_user(username, display_name, Role.ADMIN.value, hash_password(password))
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(f"Administrator '{username}' created.")

if __name__ == "__main__":
    main()
