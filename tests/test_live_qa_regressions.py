import unittest
from unittest.mock import patch

from ai_engine import generate_campaign_strategy
from campaign_policy import can_save_draft, content_is_compliant
from health import check_health
from validators.factual_validator import validate_structured_factual_claims


MATCHMAKING_BRIEF = (
    "Create an Instagram carousel encouraging university students to explore "
    "public-sector internship opportunities through Matchmaking."
)


class LiveQARegressionTests(unittest.TestCase):
    def test_exact_matchmaking_brief_preserves_explicit_audience(self):
        strategy = generate_campaign_strategy(
            MATCHMAKING_BRIEF, "Auto Detect", "Auto Detect", "Instagram", ["English"]
        )
        self.assertEqual(strategy["brand_key"], "omsar")
        self.assertEqual(strategy["target_audience"], ["University students"])
        self.assertFalse(strategy["audience_confirmation_required"])
        self.assertEqual(strategy["recommended_format"], "Carousel")

    def test_arabic_audience_aliases_match_approved_english_audiences(self):
        aliases = {
            "Farmers": "المزارعين",
            "Producers": "المنتجين",
            "Students": "الطلاب",
            "University students": "طلاب الجامعات",
        }
        for approved, arabic in aliases.items():
            with self.subTest(approved=approved):
                result = validate_structured_factual_claims(
                    brief=f"Campaign for {approved}",
                    content={"caption_ar": arabic},
                    approved_strategy={"target_audience": [approved]},
                    approved_knowledge={},
                )
                self.assertEqual(result["status"], "PASS", result["issues"])

    def test_role_and_compliance_save_policy(self):
        compliant = {
            key: {"status": "PASS"}
            for key in (
                "security_validation", "terminology_validation",
                "factual_validation", "language_validation",
            )
        }
        self.assertTrue(can_save_draft("ADMIN"))
        self.assertTrue(can_save_draft("EDITOR"))
        self.assertFalse(can_save_draft("REVIEWER"))
        self.assertTrue(content_is_compliant(compliant))
        compliant["factual_validation"] = {"status": "BLOCK"}
        self.assertFalse(content_is_compliant(compliant))

    @patch("health.check_ai_provider_health", return_value="Healthy")
    @patch("health.get_ai_provider_settings")
    def test_health_reports_generation_provider_model_and_probe_time(self, settings, probe):
        settings.return_value.provider = "groq"
        settings.return_value.model = "qwen/qwen3.8-27b"
        result = check_health(check_model=True)
        self.assertEqual(result["provider"], "groq")
        self.assertEqual(result["model"], "qwen/qwen3.8-27b")
        self.assertEqual(result["provider_status"], "Healthy")
        self.assertIsNotNone(result["last_probe_time"])
        probe.assert_called_once()


if __name__ == "__main__":
    unittest.main()
