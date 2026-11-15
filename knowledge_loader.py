import json
from pathlib import Path
from typing import Any


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

REQUIRED_FILES = [
    "sources.json",
    "organization.json",
    "terminology.json",
]

OPTIONAL_FILES = [
    "services.json",
]


# --------------------------------------------------
# Custom Error
# --------------------------------------------------

class KnowledgeError(Exception):
    """Raised when BrandPilot knowledge is invalid or unsafe to load."""
    pass


# --------------------------------------------------
# JSON Loader
# --------------------------------------------------

def load_json_file(path: Path) -> dict:
    """
    Load a JSON file safely.

    BrandPilot fails closed:
    malformed or missing knowledge is not silently ignored.
    """

    if not path.exists():
        raise KnowledgeError(
            f"Knowledge file not found: {path}"
        )

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

    except json.JSONDecodeError as error:
        raise KnowledgeError(
            f"Invalid JSON in {path}: {error}"
        ) from error

    if not isinstance(data, dict):
        raise KnowledgeError(
            f"Expected a JSON object in {path}"
        )

    return data


# --------------------------------------------------
# Brand Directory
# --------------------------------------------------

def get_brand_directory(brand: str) -> Path:

    brand = brand.strip().lower()

    if not brand:
        raise KnowledgeError(
            "Brand cannot be empty."
        )

    brand_dir = KNOWLEDGE_DIR / brand

    if not brand_dir.exists():
        raise KnowledgeError(
            f"Knowledge directory does not exist for brand: {brand}"
        )

    if not brand_dir.is_dir():
        raise KnowledgeError(
            f"Knowledge path is not a directory: {brand_dir}"
        )

    return brand_dir


# --------------------------------------------------
# Approved Sources
# --------------------------------------------------

def load_approved_sources(
    brand: str
) -> dict[str, dict]:

    brand_dir = get_brand_directory(
        brand
    )

    source_file = brand_dir / "sources.json"

    data = load_json_file(
        source_file
    )

    file_brand = data.get(
        "brand"
    )

    if file_brand != brand.lower():
        raise KnowledgeError(
            f"Brand mismatch in {source_file}. "
            f"Expected '{brand.lower()}', found '{file_brand}'."
        )

    sources = data.get(
        "sources"
    )

    if not isinstance(sources, list):
        raise KnowledgeError(
            f"'sources' must be a list in {source_file}"
        )

    approved_sources = {}

    for source in sources:

        if not isinstance(source, dict):
            raise KnowledgeError(
                f"Invalid source record in {source_file}"
            )

        source_id = source.get(
            "id"
        )

        if not source_id:
            raise KnowledgeError(
                f"Source without an ID in {source_file}"
            )

        if source_id in approved_sources:
            raise KnowledgeError(
                f"Duplicate source ID: {source_id}"
            )

        status = source.get(
            "status"
        )

        # Fail closed:
        # only explicitly approved sources are loaded.
        if status != "approved":
            continue

        approved_sources[
            source_id
        ] = source

    if not approved_sources:
        raise KnowledgeError(
            f"No approved sources found for brand '{brand}'."
        )

    return approved_sources


# --------------------------------------------------
# Source Reference Validation
# --------------------------------------------------

def validate_source_ids_recursive(
    value: Any,
    approved_sources: dict[str, dict],
    location: str = "record"
) -> None:
    """
    Recursively locate every 'source_ids' field
    and verify that all referenced sources exist
    and are approved.
    """

    if isinstance(value, dict):

        for key, child in value.items():

            current_location = (
                f"{location}.{key}"
            )

            if key == "source_ids":

                if not isinstance(child, list):
                    raise KnowledgeError(
                        f"{current_location} must be a list."
                    )

                for source_id in child:

                    if not isinstance(
                        source_id,
                        str
                    ):
                        raise KnowledgeError(
                            f"Invalid source ID in "
                            f"{current_location}"
                        )

                    if source_id not in approved_sources:
                        raise KnowledgeError(
                            f"Unapproved or unknown source "
                            f"'{source_id}' referenced at "
                            f"{current_location}"
                        )

            else:

                validate_source_ids_recursive(
                    child,
                    approved_sources,
                    current_location
                )

    elif isinstance(value, list):

        for index, child in enumerate(
            value
        ):

            validate_source_ids_recursive(
                child,
                approved_sources,
                f"{location}[{index}]"
            )


# --------------------------------------------------
# Record Validation
# --------------------------------------------------

def validate_record(
    brand: str,
    file_name: str,
    record: dict,
    approved_sources: dict[str, dict]
) -> None:

    # Only explicitly approved records
    # are trusted by BrandPilot.
    status = record.get(
        "status"
    )

    if status != "approved":
        raise KnowledgeError(
            f"{file_name} is not approved. "
            f"Current status: {status}"
        )

    record_brand = (
        record.get("brand_key")
        or record.get("brand")
    )

    if record_brand != brand.lower():
        raise KnowledgeError(
            f"Brand mismatch in {file_name}. "
            f"Expected '{brand.lower()}', "
            f"found '{record_brand}'."
        )

    classification = record.get(
        "classification"
    )

    if not classification:
        raise KnowledgeError(
            f"{file_name} does not define a classification."
        )

    validate_source_ids_recursive(
        record,
        approved_sources,
        file_name
    )


# --------------------------------------------------
# Main Knowledge Loader
# --------------------------------------------------

def load_brand_knowledge(
    brand: str
) -> dict:

    brand = brand.strip().lower()

    brand_dir = get_brand_directory(
        brand
    )

    approved_sources = (
        load_approved_sources(
            brand
        )
    )

    knowledge = {
        "brand": brand,
        "sources": approved_sources,
        "records": {}
    }

    # Required knowledge files
    for file_name in REQUIRED_FILES:

        if file_name == "sources.json":
            continue

        path = brand_dir / file_name

        record = load_json_file(
            path
        )

        validate_record(
            brand,
            file_name,
            record,
            approved_sources
        )

        knowledge[
            "records"
        ][file_name] = record

    # Optional files are loaded only when
    # they exist and contain approved knowledge.
    for file_name in OPTIONAL_FILES:

        path = brand_dir / file_name

        if not path.exists():
            continue

        # Ignore completely empty placeholder files.
        if path.stat().st_size == 0:
            continue

        record = load_json_file(
            path
        )

        validate_record(
            brand,
            file_name,
            record,
            approved_sources
        )

        knowledge[
            "records"
        ][file_name] = record

    return knowledge


# --------------------------------------------------
# Summary Helper
# --------------------------------------------------

def get_knowledge_summary(
    brand: str
) -> dict:

    knowledge = load_brand_knowledge(
        brand
    )

    return {
        "brand": knowledge["brand"],
        "approved_sources": len(
            knowledge["sources"]
        ),
        "loaded_records": list(
            knowledge["records"].keys()
        ),
    }


# --------------------------------------------------
# Manual Test
# --------------------------------------------------

if __name__ == "__main__":

    try:

        summary = get_knowledge_summary(
            "omsar"
        )

        print(
            json.dumps(
                summary,
                indent=2,
                ensure_ascii=False
            )
        )

        print(
            "\nBrandPilot knowledge validation: PASS"
        )

    except KnowledgeError as error:

        print(
            "\nBrandPilot knowledge validation: FAIL"
        )

        print(
            error
        )

        raise SystemExit(1)