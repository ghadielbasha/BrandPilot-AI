"""Deterministic retrieval from BrandPilot's approved knowledge store."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from knowledge_loader import KnowledgeError, load_brand_knowledge


SUPPORTED_BRANDS = frozenset({"omsar", "dawlati"})


@dataclass(frozen=True)
class GroundingContext:
    brand: str
    prompt_context: str
    source_ids: tuple[str, ...]
    sources: tuple[dict[str, Any], ...]
    record_names: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "brand": self.brand,
            "prompt_context": self.prompt_context,
            "source_ids": list(self.source_ids),
            "sources": list(self.sources),
            "record_names": list(self.record_names),
        }


def _compact_organization(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "official_names", "country", "summary", "mission", "vision",
        "core_areas", "core_functions", "primary_audiences",
        "institutional_principles", "communication_principles",
        "communication_guardrails", "service_claim_rules", "digitization_status",
    )
    return {key: record[key] for key in keys if key in record}


def _compact_terminology(record: dict[str, Any]) -> dict[str, Any]:
    terms = []
    for term in record.get("terms", []):
        terms.append({
            key: term[key]
            for key in ("concept", "preferred", "allowed_variants", "forbidden_variants")
            if key in term
        })
    return {"terms": terms, "rules": record.get("rules", {})}


def _compact_services(record: dict[str, Any]) -> dict[str, Any]:
    """Include only explicitly approved service records and their evidence."""
    result: dict[str, Any] = {}
    for key, value in record.items():
        if key in {"status", "classification", "brand", "brand_key", "record_type", "last_verified"}:
            continue
        if isinstance(value, list):
            result[key] = [item for item in value if not isinstance(item, dict) or item.get("status", "approved") == "approved"]
        else:
            result[key] = value
    return result


def build_grounding_context(brand: str) -> GroundingContext:
    normalized = brand.strip().casefold()
    if normalized not in SUPPORTED_BRANDS:
        raise KnowledgeError(f"Unsupported brand: {brand}")

    knowledge = load_brand_knowledge(normalized)
    records = knowledge["records"]
    compact: dict[str, Any] = {
        "authority": "Only these approved records may be treated as organizational facts.",
        "brand": normalized,
    }
    if "organization.json" in records:
        compact["organization"] = _compact_organization(records["organization.json"])
    if "terminology.json" in records:
        compact["terminology"] = _compact_terminology(records["terminology.json"])
    if "services.json" in records:
        compact["approved_services"] = _compact_services(records["services.json"])
    elif normalized == "dawlati":
        compact["approved_services"] = {"services": []}

    sources = tuple(
        {
            "id": source_id,
            "title": source.get("title", ""),
            "source_type": source.get("source_type", ""),
            "last_verified": source.get("last_verified", ""),
        }
        for source_id, source in sorted(knowledge["sources"].items())
    )
    source_ids = tuple(source["id"] for source in sources)
    compact["provenance"] = {"approved_source_ids": list(source_ids)}

    return GroundingContext(
        brand=normalized,
        prompt_context=json.dumps(compact, ensure_ascii=False, separators=(",", ":")),
        source_ids=source_ids,
        sources=sources,
        record_names=tuple(sorted(records)),
    )

