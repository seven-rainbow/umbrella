from fastapi.testclient import TestClient

from app.db.clickhouse import get_repository
from app.main import app


class FakeRepository:
    def fetch_providers(self):
        return [
            {
                "provider_id": "provider-1",
                "name": "OpenAI Compatible",
                "provider_type": "openai-compatible",
                "base_url": "https://models.example/v1",
                "api_key_secret_ref": "MODEL_API_KEY",
                "enabled": True,
            }
        ]

    def fetch_models(self):
        return [
            {
                "model_id": "model-1",
                "provider_id": "provider-1",
                "model_name": "gpt-test",
                "temperature": 0.2,
                "max_tokens": 1200,
                "timeout_seconds": 30,
                "is_default": True,
            }
        ]


def test_model_configs_api_does_not_return_api_key_secret_ref():
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    try:
        response = TestClient(app).get("/api/v1/model-configs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["providers"][0]["has_api_key"] is True
    assert "api_key_secret_ref" not in body["providers"][0]
