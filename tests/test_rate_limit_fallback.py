"""Rate-limited cloud generation uses only validated, supported templates."""
import unittest
from unittest.mock import patch
from ai_provider import AIRateLimitError
from content_generator import generate_marketing_content

class ProviderRateLimitFallbackTests(unittest.TestCase):
    def setUp(self):
        self.brief = "Seven Ministry of Agriculture services are now available online through Dawlati."
        self.strategy = {
            "brand_key": "dawlati", "brand": "DAWLATI",
            "target_audience": ["Farmers", "Producers", "Agricultural businesses"],
            "languages": ["Arabic", "English"],
            "platform": "Instagram", "recommended_format": "Carousel",
        }

    @patch("content_generator._generate_repaired_content")
    @patch("content_generator._generate_initial_content")
    def test_rate_limit_uses_fully_validated_fallback_without_repair(self, initial, repair):
        initial.side_effect = AIRateLimitError("Groq is rate limited")
        result = generate_marketing_content(self.brief, self.strategy)
        repair.assert_not_called()
        initial.assert_called_once()
        self.assertEqual(result["generation_source"], "deterministic fallback")
        self.assertEqual(result["fallback"]["reason"], "provider_rate_limit")
        self.assertTrue(result["fallback"]["successful"])
        self.assertFalse(result["repair"]["repair_attempted"])
        for key in ("security_validation", "terminology_validation", "factual_validation", "language_validation"):
            self.assertEqual(result[key]["status"], "PASS", key)

    @patch("content_generator._generate_repaired_content")
    @patch("content_generator._generate_initial_content")
    def test_rate_limit_unsupported_brief_still_blocks(self, initial, repair):
        initial.side_effect = AIRateLimitError("Groq is rate limited")
        with self.assertRaisesRegex(RuntimeError, "no safe, supported fallback"):
            generate_marketing_content("A completely unspecified government campaign.", self.strategy)
        repair.assert_not_called()

    @patch("content_generator._generate_repaired_content")
    @patch("content_generator._generate_initial_content")
    def test_matchmaking_falls_back_without_another_model_call(self, initial, repair):
        from ai_engine import generate_campaign_strategy
        brief = (
            "Create an Instagram carousel encouraging university students "
            "to explore public-sector internship opportunities through Matchmaking."
        )
        strategy = generate_campaign_strategy(
            brief, "Auto Detect", "Auto Detect", "Instagram", ["Arabic", "English"]
        )
        initial.side_effect = AIRateLimitError("quota")
        result = generate_marketing_content(brief, strategy)
        repair.assert_not_called()
        self.assertEqual(result["generation_source"], "deterministic fallback")
        self.assertIn("Matchmaking", result["caption_en"])
        self.assertIn("طلاب الجامعات", result["caption_ar"])
        for key in ("security_validation", "terminology_validation", "factual_validation", "language_validation"):
            self.assertEqual(result[key]["status"], "PASS", key)

    @patch("content_generator._generate_initial_content")
    def test_generic_provider_failure_does_not_trigger_fallback(self, initial):
        initial.side_effect = RuntimeError("generic provider failed")
        with self.assertRaisesRegex(RuntimeError, "generic provider failed"):
            generate_marketing_content(self.brief, self.strategy)

if __name__ == "__main__":
    unittest.main()

class RepairRateLimitFallbackTests(unittest.TestCase):
    @patch("content_generator._generate_repaired_content")
    @patch("content_generator._generate_initial_content")
    def test_matchmaking_repair_429_uses_validated_template(self, initial, repair):
        from ai_engine import generate_campaign_strategy
        from content_generator import MarketingContent
        brief = (
            "Create an Instagram carousel encouraging university students "
            "to explore public-sector internship opportunities through Matchmaking."
        )
        strategy = generate_campaign_strategy(
            brief, "Auto Detect", "Auto Detect", "Instagram", ["Arabic", "English"]
        )
        # Model returned structurally valid but factually invalid draft.
        from safe_fallback import build_safe_fallback_campaign
        payload = build_safe_fallback_campaign(brief, strategy, {})
        payload["content_structure"][1]["body"] = (
            "Students can access public-sector internships anywhere, anytime through Matchmaking."
        )
        initial.return_value = MarketingContent.model_validate(payload)
        repair.side_effect = AIRateLimitError("provider 429")
        result = generate_marketing_content(brief, strategy)
        repair.assert_called_once()
        self.assertEqual(result["generation_source"], "deterministic fallback")
        self.assertEqual(result["fallback"]["reason"], "provider_rate_limit")
        self.assertTrue(result["fallback"]["successful"])
        self.assertTrue(result["repair"]["repair_attempted"])
        self.assertFalse(result["repair"]["repair_successful"])
        for key in ("security_validation", "terminology_validation", "factual_validation", "language_validation"):
            self.assertEqual(result[key]["status"], "PASS", key)
