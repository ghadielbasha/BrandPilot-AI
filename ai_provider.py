"""AI provider selection and structured-generation adapters."""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from typing import Any, Mapping


OLLAMA_PROVIDER = "ollama"
GROQ_PROVIDER = "groq"
SUPPORTED_AI_PROVIDERS = frozenset({OLLAMA_PROVIDER, GROQ_PROVIDER})
DEFAULT_MODELS = {
    OLLAMA_PROVIDER: "qwen3:4b",
    GROQ_PROVIDER: "qwen/qwen3.8-27b",
}


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
        except Exception:
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
