"""Provider strict-JSON truncation recovery and safety regressions."""
import os
import unittest
from unittest.mock import MagicMock, patch

import httpx
from groq import BadRequestError

from ai_engine import generate_campaign_strategy
from ai_provider import (
    AIOutputTruncatedError,
    AIProviderError,
    generate_structured_text,
)
from content_generator import MarketingContent, generate_marketing_content
from safe_fallback import build_safe_fallback_campaign


MATCHMAKING_BRIEF = (
    "Create an Instagram carousel encouraging university students "
    "to explore public-sector internship opportunities through Matchmaking."
)


class TruncationFallbackTests(unittest.TestCase):
    def setUp(self):
        self.strategy = generate_campaign_strategy(
            MATCHMAKING_BRIEF, "Auto Detect", "Auto Detect",
            "Instagram", ["Arabic", "English"],
        )

    @staticmethod
    def groq_400_error(*, code="json_validate_failed", message=None):
        request = httpx.Request(
            "POST", "https://api.groq.com/openai/v1/chat/completions"
        )
        response = httpx.Response(400, request=request)
        return BadRequestError(
            message or "Groq rejected strict JSON output",
            response=response,
            body={
                "error": {
                    "code": code,
                    "message": message or (
                        "max completion tokens reached before generating "
                        "a valid document: output was truncated"
                    ),
                }
            },
        )

    @patch("ai_provider._create_groq_client")
    def test_groq_400_json_truncated_is_classified(self, create_client):
        client = MagicMock()
        client.chat.completions.create.side_effect = self.groq_400_error()
        create_client.return_value = client
        with patch.dict(os.environ, {"AI_PROVIDER": "groq", "GROQ_API_KEY": "gsk_test_value"}, clear=True):
            with self.assertRaises(AIOutputTruncatedError):
                generate_structured_text(
                    system_prompt="sys", user_prompt="brief",
                    schema=MarketingContent.model_json_schema(),
                )
        self.assertEqual(client.chat.completions.create.call_count, 1)

    @patch("ai_provider._create_groq_client")
    def test_non_truncation_400_not_mislabeled(self, create_client):
        client = MagicMock()
        client.chat.completions.create.side_effect = self.groq_400_error(
            code="invalid_request_error", message="Malformed request"
        )
        create_client.return_value = client
        with patch.dict(os.environ, {"AI_PROVIDER": "groq", "GROQ_API_KEY": "gsk_test_value"}, clear=True):
            with self.assertRaises(AIProviderError) as ctx:
                generate_structured_text(
                    system_prompt="sys", user_prompt="brief",
                    schema=MarketingContent.model_json_schema(),
                )
            self.assertNotIsInstance(ctx.exception, AIOutputTruncatedError)

    @patch("ai_provider._create_groq_client")
    def test_matchmaking_truncated_strict_json_uses_validated_fallback(self, create_client):
        client = MagicMock()
        client.chat.completions.create.side_effect = self.groq_400_error()
        create_client.return_value = client
        with patch.dict(os.environ, {
            "AI_PROVIDER": "groq", "GROQ_API_KEY": "gsk_test_value"
        }, clear=True):
            result = generate_marketing_content(
                MATCHMAKING_BRIEF, self.strategy
            )
        self.assertEqual(client.chat.completions.create.call_count, 1)
        self.assertEqual(result["generation_source"], "deterministic fallback")
        self.assertEqual(result["fallback"]["reason"], "provider_output_truncated")
        self.assertTrue(result["fallback"]["successful"])
        self.assertIn("Matchmaking", result["caption_en"])
        self.assertIn("طلاب الجامعات", result["caption_ar"])
        self.assertFalse(result["repair"]["repair_attempted"])
        for key in ("security_validation", "terminology_validation", "factual_validation", "language_validation"):
            self.assertEqual(result[key]["status"], "PASS", key)

    @patch("content_generator._generate_repaired_content")
    @patch("content_generator._generate_initial_content")
    def test_matchmaking_repair_truncated_json_uses_validated_fallback(self, initial, repair):
        # A fabricated access promise forces repair; repair hits 400 truncation.
        payload = build_safe_fallback_campaign(
            MATCHMAKING_BRIEF, self.strategy, {}
        )
        payload["content_structure"][1]["body"] = (
            "Students can access public-sector internships anywhere, "
            "anytime through Matchmaking."
        )
        initial.return_value = MarketingContent.model_validate(payload)
        repair.side_effect = AIOutputTruncatedError("truncated")
        result = generate_marketing_content(
            MATCHMAKING_BRIEF, self.strategy
        )
        repair.assert_called_once()
        self.assertEqual(result["generation_source"], "deterministic fallback")
        self.assertEqual(result["fallback"]["reason"], "provider_output_truncated")
        self.assertTrue(result["fallback"]["successful"])
        self.assertTrue(result["repair"]["repair_attempted"])
        self.assertFalse(result["repair"]["repair_successful"])
        for key in ("security_validation", "terminology_validation", "factual_validation", "language_validation"):
            self.assertEqual(result[key]["status"], "PASS", key)

    @patch("content_generator._generate_initial_content")
    def test_unsupported_brief_still_blocked(self, initial):
        initial.side_effect = AIOutputTruncatedError("truncated")
        with self.assertRaisesRegex(RuntimeError, "no safe, supported fallback"):
            generate_marketing_content(
                "Create a campaign about an unspecified initiative.",
                self.strategy
            )
