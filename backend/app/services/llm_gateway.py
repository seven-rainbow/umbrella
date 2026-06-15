from __future__ import annotations

import json

import httpx
from fastapi import HTTPException

from app.models.model_config import ChatMessage, ModelRuntimeConfig


class LLMGateway:
    def chat_json(self, config: ModelRuntimeConfig, messages: list[ChatMessage]) -> dict:
        if config.provider_type != "openai-compatible":
            raise HTTPException(status_code=400, detail=f"Unsupported provider type: {config.provider_type}")

        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        payload = {
            "model": config.model_name,
            "messages": [message.model_dump() for message in messages],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            response = httpx.post(
                f"{config.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=config.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                raise HTTPException(status_code=502, detail="Model provider authentication failed") from exc
            raise HTTPException(status_code=502, detail=f"Model provider returned {exc.response.status_code}") from exc
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="Model provider request timed out") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Model provider request failed: {exc}") from exc

        body = response.json()
        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail="Model returned non-JSON assessment") from exc

    def test_connection(self, config: ModelRuntimeConfig) -> str:
        self.chat_json(
            config,
            [
                ChatMessage(role="system", content="Return a compact JSON object only."),
                ChatMessage(role="user", content='Return {"ok": true}.'),
            ],
        )
        return "Connection test succeeded"
