import json
import os
import unittest
import httpx
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ai_provider import (
    AIProviderConfigurationError,
    AIProviderError,
    DEFAULT_GROQ_MAX_OUTPUT_TOKENS,
    DEFAULT_GROQ_REPAIR_MAX_OUTPUT_TOKENS,
    DEFAULT_MODELS,
    _create_groq_client,
    check_ai_provider_health,
    generate_structured_text,
    get_groq_max_output_tokens,
    get_groq_output_token_limits,
    get_groq_repair_max_output_tokens,
    get_ai_provider_settings,
)
from content_generator import (
    MarketingContent,
    _call_structured_model,
    _generate_initial_content,
    _generate_repaired_content,
    generate_marketing_content,
)


class AIProviderTests(unittest.TestCase):

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
        self.payload = {
            "caption_ar": (
                "أصبحت 7 خدمات تابعة لوزارة الزراعة متاحة الآن إلكترونياً "
                "عبر منصة «دولتي»."
            ),
            "caption_en": self.brief,
            "content_structure": [
                {
                    "number": 1,
                    "type": "Slide",
                    "headline": "7 Ministry of Agriculture services",
                    "body": self.brief,
                },
                {
                    "number": 2,
                    "type": "Slide",
                    "headline": "For the agricultural sector",
                    "body": (
                        "For farmers, producers, and agricultural businesses."
                    ),
                },
            ],
            "visual_concept": (
                "A professional announcement for seven Ministry of Agriculture "
                "services available through Dawlati."
            ),
            "visual_generation_prompt": (
                "Create a professional announcement for seven Ministry of "
                "Agriculture services using generic agricultural imagery."
            ),
            "cta": (
                "Explore the 7 available Ministry of Agriculture services on Dawlati"
            ),
            "hashtags": ["#Dawlati", "#دولتي", "#Lebanon"],
            "brand_check": {
                "status": "PASS",
                "issues": [],
                "recommendations": [],
            },
        }
        self.raw_payload = json.dumps(self.payload, ensure_ascii=False)

    def test_default_provider_is_ollama(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = get_ai_provider_settings()
        self.assertEqual(settings.provider, "ollama")
        self.assertEqual(settings.model, "qwen3:4b")

    def test_groq_output_caps_default_to_500_and_400(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_groq_max_output_tokens(), 500)
            self.assertEqual(get_groq_repair_max_output_tokens(), 400)
            self.assertEqual(DEFAULT_GROQ_MAX_OUTPUT_TOKENS, 500)
            self.assertEqual(DEFAULT_GROQ_REPAIR_MAX_OUTPUT_TOKENS, 400)
            self.assertLess(sum(get_groq_output_token_limits()), 1000)

    def test_groq_output_cap_environment_override(self):
        with patch.dict(
            os.environ,
            {
                "GROQ_MAX_OUTPUT_TOKENS": "540",
                "GROQ_REPAIR_MAX_OUTPUT_TOKENS": "350",
            },
            clear=True,
        ):
            self.assertEqual(get_groq_output_token_limits(), (540, 350))

    def test_groq_output_cap_override_cannot_reach_otpm_limit(self):
        with patch.dict(
            os.environ,
            {
                "GROQ_MAX_OUTPUT_TOKENS": "600",
                "GROQ_REPAIR_MAX_OUTPUT_TOKENS": "400",
            },
            clear=True,
        ), self.assertRaises(AIProviderConfigurationError):
            get_groq_output_token_limits()

    @patch("groq.Groq")
    def test_groq_sdk_retries_are_disabled(self, groq_class):
        _create_groq_client("test-key")
        groq_class.assert_called_once_with(api_key="test-key", max_retries=0)

    @patch("ai_provider._ollama_chat")
    def test_ollama_provider_uses_mocked_ollama_call(self, ollama_chat):
        ollama_chat.return_value = SimpleNamespace(
            message=SimpleNamespace(content=self.raw_payload)
        )
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "ollama", "BRANDPILOT_MODEL": "qwen3:4b"},
            clear=True,
        ):
            raw = generate_structured_text(
                system_prompt="system",
                user_prompt="user",
                schema=MarketingContent.model_json_schema(),
            )
        self.assertEqual(raw, self.raw_payload)
        self.assertEqual(ollama_chat.call_args.kwargs["model"], "qwen3:4b")
        self.assertFalse(ollama_chat.call_args.kwargs["think"])
        self.assertNotIn("max_completion_tokens", ollama_chat.call_args.kwargs)

    @patch("ai_provider._create_groq_client")
    def test_groq_provider_uses_strict_structured_output(self, create_client):
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.raw_payload))]
        )
        create_client.return_value = client
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key"},
            clear=True,
        ):
            raw = generate_structured_text(
                system_prompt="system",
                user_prompt="user",
                schema=MarketingContent.model_json_schema(),
            )

        self.assertEqual(raw, self.raw_payload)
        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "qwen/qwen3.8-27b")
        self.assertEqual(kwargs["reasoning_effort"], "none")
        self.assertEqual(kwargs["reasoning_format"], "hidden")
        self.assertEqual(kwargs["max_completion_tokens"], 500)
        response_format = kwargs["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        schema = response_format["json_schema"]["schema"]
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["$defs"]["ContentItem"]["additionalProperties"])

    @patch("ai_provider._create_groq_client")
    def test_groq_repair_uses_400_output_tokens(self, create_client):
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.raw_payload))]
        )
        create_client.return_value = client
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key"},
            clear=True,
        ):
            generate_structured_text(
                system_prompt="system",
                user_prompt="repair",
                schema=MarketingContent.model_json_schema(),
                is_repair=True,
            )
        self.assertEqual(
            client.chat.completions.create.call_args.kwargs["max_completion_tokens"],
            400,
        )

    def test_groq_default_model_id(self):
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key"},
            clear=True,
        ):
            settings = get_ai_provider_settings()
        self.assertEqual(settings.model, DEFAULT_MODELS["groq"])
        self.assertEqual(settings.model, "qwen/qwen3.8-27b")

    def test_missing_groq_api_key_fails_safely(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "groq"}, clear=True):
            with self.assertRaises(AIProviderConfigurationError) as context:
                generate_structured_text(
                    system_prompt="system",
                    user_prompt="user",
                    schema=MarketingContent.model_json_schema(),
                )
        self.assertIn("GROQ_API_KEY", str(context.exception))

    @patch("ai_provider._create_groq_client")
    def test_groq_api_key_never_appears_in_errors(self, create_client):
        secret = "never-print-this-secret"
        create_client.side_effect = RuntimeError(f"failed with {secret}")
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "groq", "GROQ_API_KEY": secret},
            clear=True,
        ), self.assertLogs("brandpilot.ai_provider", level="ERROR") as logs:
            with self.assertRaises(AIProviderError) as context:
                generate_structured_text(
                    system_prompt="system",
                    user_prompt="user",
                    schema=MarketingContent.model_json_schema(),
                )
        self.assertNotIn(secret, str(context.exception))
        self.assertNotIn(secret, "\n".join(logs.output))
        self.assertEqual(
            str(context.exception),
            "Groq request failed for configured model qwen/qwen3.8-27b.",
        )

    @patch("ai_provider._create_groq_client")
    def test_groq_status_code_type_and_code_are_logged_safely(self, create_client):
        from groq import RateLimitError

        secret = "gsk_never_log_this_key"
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        response = httpx.Response(429, request=request)
        provider_error = RateLimitError(
            f"Rate limit response included {secret}",
            response=response,
            body={
                "error": {
                    "code": "rate_limit_exceeded",
                    "type": "rate_limit_error",
                    "message": f"Quota exceeded for token Bearer {secret}",
                }
            },
        )
        client = MagicMock()
        client.chat.completions.create.side_effect = provider_error
        create_client.return_value = client

        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "groq", "GROQ_API_KEY": secret},
            clear=True,
        ), self.assertLogs("brandpilot.ai_provider", level="ERROR") as logs:
            with self.assertRaises(AIProviderError) as context:
                generate_structured_text(
                    system_prompt="system",
                    user_prompt="user",
                    schema=MarketingContent.model_json_schema(),
                )

        logged = "\n".join(logs.output)
        self.assertIn("type=RateLimitError", logged)
        self.assertIn("status=429", logged)
        self.assertIn("code=rate_limit_exceeded", logged)
        self.assertIn("model=qwen/qwen3.8-27b", logged)
        self.assertIn("message=", logged)
        self.assertNotIn(secret, logged)
        self.assertEqual(
            str(context.exception),
            "Groq request failed for configured model qwen/qwen3.8-27b.",
        )
        self.assertEqual(client.chat.completions.create.call_count, 1)

    def test_unknown_provider_is_rejected(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "unknown"}, clear=True):
            with self.assertRaises(AIProviderConfigurationError):
                get_ai_provider_settings()

    @patch("content_generator.generate_structured_text")
    def test_initial_generation_uses_provider_abstraction(self, provider_call):
        provider_call.return_value = self.raw_payload
        content = _generate_initial_content(self.brief, self.strategy)
        self.assertIsInstance(content, MarketingContent)
        provider_call.assert_called_once()
        self.assertFalse(provider_call.call_args.kwargs["is_repair"])

    @patch("content_generator.generate_structured_text")
    def test_repair_generation_uses_provider_abstraction(self, provider_call):
        provider_call.return_value = self.raw_payload
        content = _generate_repaired_content(
            brief=self.brief,
            strategy=self.strategy,
            failed_content=self.payload,
            validation_error="factual_validation: test",
            validation_context={"validation_stage": "factual_validation", "issues": []},
        )
        self.assertIsInstance(content, MarketingContent)
        provider_call.assert_called_once()
        self.assertTrue(provider_call.call_args.kwargs["is_repair"])

    @patch("ai_provider._create_groq_client")
    def test_groq_output_parses_into_marketing_content(self, create_client):
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.raw_payload))]
        )
        create_client.return_value = client
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key"},
            clear=True,
        ):
            content = _call_structured_model("system", "user")
        self.assertIsInstance(content, MarketingContent)
        self.assertEqual(content.caption_en, self.brief)

    @patch("ai_provider._create_groq_client")
    def test_validators_run_with_groq_provider(self, create_client):
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.raw_payload))]
        )
        create_client.return_value = client
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key"},
            clear=True,
        ):
            result = generate_marketing_content(self.brief, self.strategy)
        for key in (
            "security_validation", "terminology_validation",
            "factual_validation", "language_validation",
        ):
            self.assertEqual(result[key]["status"], "PASS")

    @patch("ai_provider._create_groq_client")
    def test_groq_health_check_does_not_use_ollama(self, create_client):
        client = MagicMock()
        create_client.return_value = client
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key"},
            clear=True,
        ), patch("ai_provider._ollama_chat") as ollama_call:
            status = check_ai_provider_health("http://127.0.0.1:11434")
        self.assertEqual(status, "Healthy")
        client.chat.completions.create.assert_called_once()
        self.assertEqual(
            client.chat.completions.create.call_args.kwargs["model"],
            "qwen/qwen3.8-27b",
        )
        self.assertEqual(
            client.chat.completions.create.call_args.kwargs["max_completion_tokens"],
            4,
        )
        client.models.retrieve.assert_not_called()
        ollama_call.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
