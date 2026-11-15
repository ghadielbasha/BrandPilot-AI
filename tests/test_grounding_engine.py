import unittest
from unittest.mock import patch

from grounding_engine import build_grounding_context
from knowledge_loader import KnowledgeError


class GroundingEngineTests(unittest.TestCase):
    def test_all_approved_brands_have_compact_provenance(self):
        for brand in ("omsar", "dawlati"):
            grounding = build_grounding_context(brand)
            self.assertTrue(grounding.source_ids)
            self.assertIn('"provenance"', grounding.prompt_context)
            self.assertIn("organization.json", grounding.record_names)

    def test_unknown_brand_is_blocked(self):
        with self.assertRaises(KnowledgeError):
            build_grounding_context("unknown")

    @patch("grounding_engine.load_brand_knowledge")
    def test_empty_dawlati_services_are_safe(self, loader):
        loader.return_value = {
            "records": {
                "organization.json": {"summary": {"en": "Approved"}},
                "terminology.json": {"terms": []},
                "services.json": {
                    "brand": "dawlati", "status": "approved",
                    "classification": "public", "services": [],
                },
            },
            "sources": {"S1": {"title": "Official", "source_type": "official"}},
        }
        context = build_grounding_context("dawlati")
        self.assertIn('"services":[]', context.prompt_context)

    def test_content_prompt_uses_governed_grounding(self):
        from content_generator import build_content_prompt
        prompt = build_content_prompt("Administrative reform update", {
            "brand_key": "omsar", "languages": ["English"]
        })
        self.assertIn("APPROVED GOVERNED KNOWLEDGE", prompt)
        self.assertIn("approved_source_ids", prompt)


if __name__ == "__main__":
    unittest.main()
