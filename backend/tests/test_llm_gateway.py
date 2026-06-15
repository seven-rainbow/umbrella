import pytest
from fastapi import HTTPException

from app.models.model_config import ChatMessage, ModelRuntimeConfig
from app.services.llm_gateway import LLMGateway


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {"choices": [{"message": {"content": '{"ok": true}'}}]}

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("bad status", request=None, response=self)

    def json(self):
        return self._body


def runtime_config():
    return ModelRuntimeConfig(
        model_id="model-1",
        provider_id="provider-1",
        provider_name="Provider",
        provider_type="openai-compatible",
        base_url="https://models.example/v1",
        api_key="token",
        model_name="gpt-test",
        temperature=0.1,
        max_tokens=100,
        timeout_seconds=10,
    )


def test_llm_gateway_sends_openai_compatible_request(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("app.services.llm_gateway.httpx.post", fake_post)

    result = LLMGateway().chat_json(runtime_config(), [ChatMessage(role="user", content="return json")])

    assert result == {"ok": True}
    assert captured["url"] == "https://models.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["json"]["model"] == "gpt-test"
    assert captured["json"]["response_format"] == {"type": "json_object"}


def test_llm_gateway_maps_auth_errors(monkeypatch):
    monkeypatch.setattr("app.services.llm_gateway.httpx.post", lambda *args, **kwargs: FakeResponse(status_code=401))

    with pytest.raises(HTTPException) as exc:
        LLMGateway().chat_json(runtime_config(), [ChatMessage(role="user", content="return json")])

    assert exc.value.status_code == 502
    assert exc.value.detail == "Model provider authentication failed"


def test_llm_gateway_rejects_non_json_model_content(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_gateway.httpx.post",
        lambda *args, **kwargs: FakeResponse(body={"choices": [{"message": {"content": "not json"}}]}),
    )

    with pytest.raises(HTTPException) as exc:
        LLMGateway().chat_json(runtime_config(), [ChatMessage(role="user", content="return json")])

    assert exc.value.detail == "Model returned non-JSON assessment"
