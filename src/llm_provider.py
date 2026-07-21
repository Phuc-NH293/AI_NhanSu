"""Provider-aware LLM helpers for OpenAI and Gemini."""

from __future__ import annotations

import os
from typing import Literal

import requests
from openai import OpenAI

ProviderName = Literal["openai", "gemini"]

_DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
_DEFAULT_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _normalized_provider(value: str | None) -> ProviderName:
    provider = (value or "").strip().lower()
    if provider == "gemini":
        return "gemini"
    return "openai"


def get_llm_provider() -> ProviderName:
    configured = os.getenv("LLM_PROVIDER")
    if configured:
        return _normalized_provider(configured)

    if os.getenv("GEMINI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        return "gemini"
    return "openai"


def get_llm_api_key(provider: ProviderName | None = None, override: str | None = None) -> str:
    if override and override.strip():
        return override.strip()

    resolved_provider = provider or get_llm_provider()
    if resolved_provider == "gemini":
        return (os.getenv("GEMINI_API_KEY") or "").strip()
    return (os.getenv("OPENAI_API_KEY") or "").strip()


def get_generation_model(provider: ProviderName | None = None) -> str:
    resolved_provider = provider or get_llm_provider()
    if resolved_provider == "gemini":
        return (
            os.getenv("LLM_MODEL")
            or os.getenv("GEMINI_MODEL")
            or _DEFAULT_GEMINI_MODEL
        ).strip()
    return (
        os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or _DEFAULT_OPENAI_MODEL
    ).strip()


def get_ocr_provider() -> ProviderName:
    explicit = os.getenv("OCR_PROVIDER")
    if explicit:
        return _normalized_provider(explicit)
    if os.getenv("OCR_WITH_OPENAI", "0") == "1":
        return "openai"
    return get_llm_provider()


def ocr_enabled() -> bool:
    if os.getenv("OCR_ENABLED") is not None:
        return os.getenv("OCR_ENABLED", "0") == "1"
    return os.getenv("OCR_WITH_OPENAI", "0") == "1"


def get_ocr_model(provider: ProviderName | None = None) -> str:
    resolved_provider = provider or get_ocr_provider()
    if resolved_provider == "gemini":
        return (
            os.getenv("OCR_MODEL")
            or os.getenv("GEMINI_OCR_MODEL")
            or os.getenv("GEMINI_MODEL")
            or _DEFAULT_GEMINI_MODEL
        ).strip()
    return (
        os.getenv("OCR_MODEL")
        or os.getenv("OPENAI_OCR_MODEL")
        or os.getenv("OPENAI_MODEL")
        or _DEFAULT_OPENAI_MODEL
    ).strip()


def missing_llm_configuration_notice() -> str:
    provider = get_llm_provider()
    if provider == "gemini":
        return "Chế độ evidence-only: chưa cấu hình GEMINI_API_KEY"
    if provider == "openai":
        return "Chế độ evidence-only: chưa cấu hình OPENAI_API_KEY"
    return "Chế độ evidence-only: chưa cấu hình LLM provider/API key"


def provider_display_name(provider: ProviderName | None = None) -> str:
    resolved_provider = provider or get_llm_provider()
    return "Gemini" if resolved_provider == "gemini" else "OpenAI"


def _gemini_api_base() -> str:
    return (os.getenv("GEMINI_API_BASE") or _DEFAULT_GEMINI_API_BASE).rstrip("/")


def _gemini_endpoint(model: str, api_key: str) -> str:
    return f"{_gemini_api_base()}/models/{model}:generateContent?key={api_key}"


def _gemini_payload(
    *,
    system_prompt: str | None,
    user_parts: list[dict],
    temperature: float,
    top_p: float,
) -> dict:
    payload: dict = {
        "contents": [
            {
                "role": "user",
                "parts": user_parts,
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "topP": top_p,
        },
    }
    if system_prompt:
        payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
    return payload


def _parse_gemini_text(data: dict) -> str:
    texts: list[str] = []
    for candidate in data.get("candidates", []) or []:
        content = candidate.get("content", {}) or {}
        for part in content.get("parts", []) or []:
            text = part.get("text")
            if text:
                texts.append(text)
    return "\n".join(texts).strip()


def generate_text(
    *,
    system_prompt: str,
    user_message: str,
    temperature: float,
    top_p: float,
    api_key_override: str | None = None,
) -> str:
    provider = get_llm_provider()
    api_key = get_llm_api_key(provider, api_key_override)
    model = get_generation_model(provider)

    if provider == "gemini":
        response = requests.post(
            _gemini_endpoint(model, api_key),
            json=_gemini_payload(
                system_prompt=system_prompt,
                user_parts=[{"text": user_message}],
                temperature=temperature,
                top_p=top_p,
            ),
            timeout=60,
        )
        response.raise_for_status()
        return _parse_gemini_text(response.json())

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        top_p=top_p,
    )
    return (response.choices[0].message.content or "").strip()


def ocr_image_with_provider(
    *,
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    temperature: float = 0,
) -> str:
    provider = get_ocr_provider()
    api_key = get_llm_api_key(provider)
    model = get_ocr_model(provider)

    if provider == "gemini":
        import base64

        response = requests.post(
            _gemini_endpoint(model, api_key),
            json=_gemini_payload(
                system_prompt=None,
                user_parts=[
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        }
                    },
                ],
                temperature=temperature,
                top_p=1,
            ),
            timeout=120,
        )
        response.raise_for_status()
        return _parse_gemini_text(response.json())

    import base64

    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL") or None)
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                    },
                ],
            }
        ],
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()
