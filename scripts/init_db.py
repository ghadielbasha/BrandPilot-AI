"""Initialize the BrandPilot database without destroying existing data."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DB_PATH
from database import initialize_database

if __name__ == "__main__":
    initialize_database()
    print(f"BrandPilot database initialized: {DB_PATH}")
