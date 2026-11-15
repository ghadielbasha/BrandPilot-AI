"""Create timestamped, non-overwriting pilot backups."""
from datetime import datetime, timezone
from pathlib import Path
from contextlib import closing
import shutil
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import BASE_DIR, DB_PATH, KNOWLEDGE_DIR

def main() -> None:
    destination = BASE_DIR / "backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination.mkdir(parents=True, exist_ok=False)
    if DB_PATH.exists():
        with closing(sqlite3.connect(DB_PATH)) as source, closing(sqlite3.connect(destination / "brandpilot.db")) as target:
            source.backup(target)
            target.commit()
    shutil.copytree(KNOWLEDGE_DIR, destination / "knowledge")
    print(f"Backup created: {destination}")

if __name__ == "__main__":
    main()
