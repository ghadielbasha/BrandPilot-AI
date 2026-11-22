"""AI provider selection and structured-generation adapters."""

from __future__ import annotations

import copy
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Mapping


OLLAMA_PROVIDER = "ollama"
GROQ_PROVIDER = "groq"
SUPPORTED_AI_PROVIDERS = frozenset({OLLAMA_PROVIDER, GROQ_PROVIDER})
DEFAULT_MODELS = {
    OLLAMA_PROVIDER: "qwen3:4b",
    GROQ_PROVIDER: "qwen/qwen3.8-27b",
}

LOGGER = logging.getLogger("brandpilot.ai_provider")
_MAX_DIAGNOSTIC_MESSAGE_LENGTH = 500
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|authorization|password|secret|token)\b"
    r"\s*[:=]\s*(?:bearer\s+)?(?:['\"])?[^\s,;}\]\"']+"
)
_BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_GROQ_KEY = re.compile(r"\bgsk_[A-Za-z0-9_-]+\b", re.IGNORECASE)


class AIProviderError(RuntimeError):
    """Safe provider error that never contains credentials."""


class AIProviderConfigurationError(AIProviderError):
    """Raised for invalid provider configuration."""


@dataclass(frozen=True)
class AIProviderSettings:
    provider: str
    model: str


def get_ai_provider_settings(
    environment: Mapping[str, str] | None = None,
) -> AIProviderSettings:
    env = environment if environment is not None else os.environ
    provider = env.get("AI_PROVIDER", OLLAMA_PROVIDER).strip().casefold()
    if provider not in SUPPORTED_AI_PROVIDERS:
        allowed = ", ".join(sorted(SUPPORTED_AI_PROVIDERS))
        raise AIProviderConfigurationError(
            f"Unknown AI_PROVIDER. Allowed values: {allowed}."
        )
    configured_model = env.get("BRANDPILOT_MODEL", "").strip()
    return AIProviderSettings(
        provider=provider,
        model=configured_model or DEFAULT_MODELS[provider],
    )


def _strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Close every object for Groq strict structured-output mode."""
    strict_schema = copy.deepcopy(schema)

    def close_objects(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("type") == "object" or "properties" in value:
                value["additionalProperties"] = False
            for child in value.values():
                close_objects(child)
        elif isinstance(value, list):
            for child in value:
                close_objects(child)

    close_objects(strict_schema)
    return strict_schema


def _ollama_chat(**kwargs):
    from ollama import chat

    return chat(**kwargs)


def _create_groq_client(api_key: str):
    from groq import Groq

    return Groq(api_key=api_key)


def _groq_api_key(environment: Mapping[str, str] | None = None) -> str:
    env = environment if environment is not None else os.environ
    api_key = env.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise AIProviderConfigurationError(
            "GROQ_API_KEY is required when AI_PROVIDER=groq."
        )
    return api_key


def _sanitize_groq_diagnostic(value: object, api_key: str) -> str:
    """Return a bounded single-line diagnostic with credential-shaped data removed."""
    text = str(value or "Unavailable")
    if api_key:
        text = text.replace(api_key, "[REDACTED]")
    text = _GROQ_KEY.sub("[REDACTED]", text)
    text = _BEARER_TOKEN.sub("Bearer [REDACTED]", text)
    text = _SENSITIVE_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        text,
    )
    text = " ".join(text.split())
    return text[:_MAX_DIAGNOSTIC_MESSAGE_LENGTH]


def _groq_error_details(error: Exception) -> tuple[object, object, object]:
    """Extract status, provider code, and message without headers or requests."""
    status: object = "n/a"
    code: object = "n/a"
    message: object = str(error)

    try:
        from groq import APIConnectionError, APIStatusError

        if isinstance(error, APIStatusError):
            status = getattr(error, "status_code", None) or getattr(
                getattr(error, "response", None), "status_code", "n/a"
            )
        elif isinstance(error, APIConnectionError):
            status = "connection_error"
    except ImportError:
        pass

    body = getattr(error, "body", None)
    if isinstance(body, Mapping):
        provider_error = body.get("error", body)
        if isinstance(provider_error, Mapping):
            code = provider_error.get("code") or provider_error.get("type") or code
            message = provider_error.get("message") or message

    return status, code, message


def _log_groq_failure(error: Exception, *, model: str, api_key: str) -> None:
    """Log safe provider diagnostics without exception tracebacks or credentials."""
    status, code, message = _groq_error_details(error)
    LOGGER.error(
        'Groq request failed: type=%s status=%s code=%s model=%s message="%s"',
        _sanitize_groq_diagnostic(type(error).__name__, api_key),
        _sanitize_groq_diagnostic(status, api_key),
        _sanitize_groq_diagnostic(code, api_key),
        _sanitize_groq_diagnostic(model, api_key),
        _sanitize_groq_diagnostic(message, api_key),
    )


def generate_structured_text(
    *,
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
) -> str:
    """Generate one schema-shaped JSON string with the configured provider."""
    settings = get_ai_provider_settings()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    if settings.provider == OLLAMA_PROVIDER:
        try:
            response = _ollama_chat(
                model=settings.model,
                messages=messages,
                format=schema,
                think=False,
                options={"temperature": 0},
            )
            content = response.message.content
        except Exception as error:
            raise AIProviderError(
                "Could not connect to the local Ollama model. "
                f"Make sure Ollama is running and {settings.model} is installed. "
                f"Details: {error}"
            ) from error
    else:
        api_key = _groq_api_key()
        try:
            client = _create_groq_client(api_key)
            response = client.chat.completions.create(
                model=settings.model,
                messages=messages,
                temperature=0,
                reasoning_effort="none",
                reasoning_format="hidden",
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "marketing_content",
                        "strict": True,
                        "schema": _strict_json_schema(schema),
                    },
                },
            )
            content = response.choices[0].message.content
        except AIProviderError:
            raise
        except Exception as error:
            _log_groq_failure(error, model=settings.model, api_key=api_key)
            raise AIProviderError(
                f"Groq request failed for configured model {settings.model}."
            ) from None

    if not content:
        raise AIProviderError(
            f"The configured {settings.provider} AI provider returned an empty response."
        )
    return content


def check_ai_provider_health(ollama_host: str) -> str:
    """Perform a provider-specific connectivity and model availability check."""
    settings = get_ai_provider_settings()
    if settings.provider == OLLAMA_PROVIDER:
        import json
        import urllib.request

        try:
            with urllib.request.urlopen(
                f"{ollama_host.rstrip('/')}/api/tags", timeout=3
            ) as response:
                models = json.load(response).get("models", [])
            available = any(
                item.get("name", "").split(":")[0]
                == settings.model.split(":")[0]
                for item in models
            )
            return "Healthy" if available else "Model unavailable"
        except Exception:
            return "Unreachable"

    try:
        api_key = _groq_api_key()
        client = _create_groq_client(api_key)
        client.models.retrieve(settings.model)
        return "Healthy"
    except AIProviderConfigurationError:
        return "Unhealthy: GROQ_API_KEY is not configured"
    except Exception:
        return "Unreachable"
