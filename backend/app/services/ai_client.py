"""Small async client for OpenAI-compatible and Anthropic chat APIs."""
import json
import re

import httpx

from app.core.config import settings


def _json_from_text(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("AI response did not contain a JSON object")
    # Some providers incorrectly leave literal newlines/tabs inside JSON strings.
    # Python's non-strict decoder accepts those while Pydantic still validates fields.
    value = json.loads(text[start:end + 1], strict=False)
    if not isinstance(value, dict):
        raise ValueError("AI response JSON must be an object")
    return value


async def ask_json(system: str, prompt: str) -> dict:
    """Call the configured provider and parse its first JSON object."""
    if not settings.AI_API_KEY.strip():
        raise RuntimeError("AI_API_KEY is not configured")

    base = settings.AI_BASE_URL.rstrip("/")
    timeout = httpx.Timeout(settings.AI_QUESTION_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        if settings.AI_PROVIDER.lower() == "anthropic":
            if base.endswith("/v1/messages"):
                url = base
            elif base.endswith("/v1"):
                url = f"{base}/messages"
            else:
                url = f"{base}/v1/messages"
            response = await client.post(
                url,
                headers={"x-api-key": settings.AI_API_KEY,
                         "anthropic-version": "2023-06-01"},
                json={"model": settings.AI_MODEL, "max_tokens": 6000,
                      "system": system, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            parts = response.json().get("content", [])
            text = "\n".join(p.get("text", "") for p in parts if p.get("type") == "text")
        else:
            url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
            body = {"model": settings.AI_MODEL, "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]}
            if settings.AI_PROVIDER.lower() in {"openai", "gemini", "openrouter"}:
                body["response_format"] = {"type": "json_object"}
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                json=body,
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("AI returned an empty response")
    return _json_from_text(text)
