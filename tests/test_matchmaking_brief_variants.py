"""Matchmaking provider-failure fallback must accept ordinary brief wording safely."""
import unittest
from unittest.mock import patch

from ai_engine import generate_campaign_strategy
from ai_provider import AIOutputTruncatedError, AIRateLimitError
from content_generator import generate_marketing_content
from safe_fallback import SafeFallbackError, build_safe_fallback_campaign


BRIEFS = [
    "Create a carousel for university students introducing the Matchmaking portal.",
    "Promote internships for university students via the Matchmaking portal.",
    "Public sector internships for university students on Matchmaking: Instagram carousel.",
    "Make a carousel about public sector job opportunities on Matchmaking for university students.",
    "Show Matchmaking training opportunities to university students.",
    "Promote the Match-making portal to university students on Instagram.",
    "Match making: Awareness campaign for university students.",
]


class MatchmakingBriefVariantTests(unittest.TestCase):
    def _strategy(self, brief):
        return generate_campaign_strategy(
            brief, "Auto Detect", "Auto Detect", "Instagram", ["Arabic", "English"]
        )

    def test_variants_successfully_generate_after_truncation(self):
        for brief in BRIEFS:
            with self.subTest(brief=brief), patch(
                "content_generator._generate_initial_content",
                side_effect=AIOutputTruncatedError("max completion tokens reached")
            ):
                strategy = self._strategy(brief)
                self.assertEqual(strategy["brand_key"], "omsar")
                self.assertEqual(strategy["target_audience"], ["University students"])
                result = generate_marketing_content(brief, strategy)
                self.assertEqual(result["generation_source"], "deterministic fallback")
                self.assertTrue(result["fallback"]["successful"])
                self.assertIn("Matchmaking", result["caption_en"])
                self.assertIn("Matchmaking", result["caption_ar"])
                self.assertTrue(result["content_structure"])
                for key in (
                    "security_validation", "terminology_validation",
                    "factual_validation", "language_validation"
                ):
                    self.assertEqual(result[key]["status"], "PASS", (brief,key))

    def test_no_unstated_public_sector_or_internship_claim(self):
        brief = "Create a carousel for university students introducing Matchmaking."
        result = build_safe_fallback_campaign(brief, self._strategy(brief))
        visible = str(result).lower()
        self.assertNotIn("internship", visible)
        self.assertNotIn("job opportunities", visible)
        self.assertNotIn("public-sector internship", visible)

    def test_internship_does_not_add_unstated_public_sector(self):
        brief = "Promote internships for university students through Matchmaking."
        result = build_safe_fallback_campaign(brief, self._strategy(brief))
        self.assertIn("internship opportunities", result["caption_en"])
        self.assertNotIn("public-sector", result["caption_en"])

    def test_unsupported_audience_is_blocked(self):
        brief = "Promote Matchmaking internships for citizens."
        strategy = self._strategy(brief)
        strategy["target_audience"] = ["Citizens"]
        with self.assertRaises(SafeFallbackError):
            build_safe_fallback_campaign(brief, strategy)

    @patch("content_generator._generate_initial_content")
    def test_rate_limit_accepts_simple_matchmaking_brief(self, initial):
        brief = "Promote the Matchmaking portal for university students."
        initial.side_effect = AIRateLimitError("429")
        result = generate_marketing_content(brief, self._strategy(brief))
        self.assertEqual(result["fallback"]["reason"], "provider_rate_limit")
        self.assertEqual(result["factual_validation"]["status"], "PASS")
