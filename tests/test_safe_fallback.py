import unittest
from unittest.mock import patch

import content_generator
from content_generator import (
    BrandCheck,
    ContentItem,
    MarketingContent,
    generate_marketing_content,
)
from safe_fallback import build_safe_fallback_campaign


class SafeFallbackTests(unittest.TestCase):

    def setUp(self):
        self.brief = (
            "Seven Ministry of Agriculture services are now available "
            "online through Dawlati."
        )
        self.strategy = {
            "brand_key": "dawlati",
            "brand": "DAWLATI",
            "target_audience": [
                "Farmers", "Producers", "Agricultural businesses",
            ],
            "languages": ["Arabic", "English"],
            "platform": "Instagram",
            "recommended_format": "Carousel",
        }

    def _payload(self):
        return build_safe_fallback_campaign(self.brief, self.strategy, {})

    def _invalid_factual_content(self):
        return MarketingContent(
            caption_ar="7 خدمات حكومية جديدة عبر منصة «دولتي».",
            caption_en="Seven new government services are available on Dawlati.",
            content_structure=[
                ContentItem(
                    number=1,
                    type="Slide",
                    headline="Government Service Directory",
                    body="Citizens can apply online anytime from anywhere.",
                )
            ],
            visual_concept="Seven named government service cards.",
            visual_generation_prompt=(
                "Create 7 named service cards with descriptions and URLs."
            ),
            cta="Apply now",
            hashtags=["#Dawlati", "#دولتي"],
            brand_check=BrandCheck(status="PASS", issues=[], recommendations=[]),
        )

    def test_builder_makes_no_ollama_call(self):
        with patch("content_generator.chat") as model_call:
            payload = self._payload()
        model_call.assert_not_called()
        self.assertEqual(payload["caption_en"], self.brief)

    def test_fallback_preserves_explicit_number(self):
        payload = self._payload()
        self.assertIn("Seven", payload["caption_en"])
        self.assertIn("7 Ministry of Agriculture services", str(payload))

    def test_fallback_preserves_responsible_entity(self):
        payload = self._payload()
        visible = str(payload)
        self.assertIn("Ministry of Agriculture", visible)
        self.assertNotIn("7 government services", visible)
        self.assertNotIn("7 Dawlati services", visible)

    def test_fallback_preserves_only_approved_audience(self):
        payload = self._payload()
        audience_body = payload["content_structure"][2]["body"]
        self.assertEqual(
            audience_body,
            "For farmers, producers, and agricultural businesses.",
        )
        self.assertNotIn("citizens", str(payload).casefold())

    def test_fallback_does_not_enumerate_unknown_services(self):
        visible = str(self._payload())
        for forbidden in (
            "Government Service Directory", "Government Information",
            "Digital Application", "Online Payment", "Request Tracking",
        ):
            self.assertNotIn(forbidden, visible)

    def test_fallback_adds_no_transaction_capability(self):
        visible = str(self._payload()).casefold()
        for forbidden in ("apply online", "online payment", "request tracking"):
            self.assertNotIn(forbidden, visible)

    def test_fallback_visual_is_generic_and_has_no_urls(self):
        prompt = self._payload()["visual_generation_prompt"].casefold()
        self.assertIn("generic", prompt)
        self.assertNotIn("url", prompt)
        self.assertNotIn("service name", prompt)
        self.assertNotIn("service cards", prompt)

    def test_fallback_does_not_turn_now_available_into_new(self):
        visible = str(self._payload()).casefold()
        self.assertNotIn("new services", visible)
        self.assertNotIn("خدمات جديدة", visible)

    def test_fallback_arabic_uses_official_dawlati_spelling(self):
        caption = self._payload()["caption_ar"]
        self.assertIn("منصة «دولتي»", caption)
        self.assertIn("وزارة الزراعة", caption)

    @patch("content_generator._generate_initial_content")
    @patch("content_generator._generate_repaired_content")
    def test_bad_ai_repair_routes_to_validated_fallback(
        self, mock_repair, mock_initial
    ):
        mock_initial.return_value = self._invalid_factual_content()
        mock_repair.return_value = self._invalid_factual_content()

        result = generate_marketing_content(self.brief, self.strategy)

        mock_repair.assert_called_once()
        self.assertTrue(result["fallback"]["attempted"])
        self.assertTrue(result["fallback"]["successful"])
        self.assertEqual(result["fallback"]["reason"], "factual_grounding_failure")
        self.assertTrue(result["repair"]["repair_attempted"])
        self.assertFalse(result["repair"]["repair_successful"])
        for key in (
            "security_validation", "terminology_validation",
            "factual_validation", "language_validation",
        ):
            self.assertEqual(result[key]["status"], "PASS")

    @patch("content_generator._generate_safe_fallback_content")
    @patch("content_generator._generate_initial_content")
    @patch("content_generator._generate_repaired_content")
    def test_security_failure_does_not_trigger_factual_fallback(
        self, mock_repair, mock_initial, mock_fallback
    ):
        unsafe = self._invalid_factual_content()
        unsafe.caption_en = "password: SuperSecret123!"
        mock_initial.return_value = unsafe
        mock_repair.return_value = unsafe

        with self.assertRaises(RuntimeError):
            generate_marketing_content(self.brief, self.strategy)

        mock_repair.assert_called_once()
        mock_fallback.assert_not_called()

    @patch("content_generator._generate_safe_fallback_content")
    def test_unknown_brand_does_not_trigger_fallback(self, mock_fallback):
        strategy = dict(self.strategy)
        strategy["brand_key"] = "unknown"
        with self.assertRaises(RuntimeError):
            generate_marketing_content(self.brief, strategy)
        mock_fallback.assert_not_called()

    @patch("content_generator._generate_safe_fallback_content")
    @patch("content_generator.build_grounding_context")
    def test_knowledge_failure_does_not_trigger_fallback(
        self, mock_grounding, mock_fallback
    ):
        mock_grounding.side_effect = RuntimeError("knowledge unavailable")
        with self.assertRaises(RuntimeError):
            generate_marketing_content(self.brief, self.strategy)
        mock_fallback.assert_not_called()

    @patch("content_generator._generate_initial_content")
    @patch("content_generator._generate_repaired_content")
    def test_fallback_runs_every_output_validator(
        self, mock_repair, mock_initial
    ):
        mock_initial.return_value = self._invalid_factual_content()
        mock_repair.return_value = self._invalid_factual_content()

        with (
            patch(
                "content_generator.enforce_object_security",
                wraps=content_generator.enforce_object_security,
            ) as security,
            patch(
                "content_generator.enforce_terminology",
                wraps=content_generator.enforce_terminology,
            ) as terminology,
            patch(
                "content_generator.enforce_structured_factual_claims",
                wraps=content_generator.enforce_structured_factual_claims,
            ) as factual,
            patch(
                "content_generator.enforce_campaign_language_quality",
                wraps=content_generator.enforce_campaign_language_quality,
            ) as language,
        ):
            result = generate_marketing_content(self.brief, self.strategy)

        self.assertTrue(result["fallback"]["successful"])
        self.assertGreaterEqual(security.call_count, 3)
        self.assertGreaterEqual(terminology.call_count, 3)
        self.assertGreaterEqual(factual.call_count, 3)
        self.assertEqual(language.call_count, 1)

    @patch("content_generator._generate_safe_fallback_content")
    @patch("content_generator._generate_initial_content")
    @patch("content_generator._generate_repaired_content")
    def test_invalid_fallback_is_still_blocked(
        self, mock_repair, mock_initial, mock_fallback
    ):
        invalid = self._invalid_factual_content()
        mock_initial.return_value = invalid
        mock_repair.return_value = invalid
        mock_fallback.return_value = invalid

        with self.assertRaises(RuntimeError) as context:
            generate_marketing_content(self.brief, self.strategy)

        mock_repair.assert_called_once()
        mock_fallback.assert_called_once()
        self.assertIn("deterministic factual fallback", str(context.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
