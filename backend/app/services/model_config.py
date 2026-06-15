from __future__ import annotations

import os
import uuid
from typing import Protocol

from fastapi import HTTPException

from app.models.model_config import (
    DefaultModelRequest,
    ModelConfigsResponse,
    ModelCreateRequest,
    ModelResponse,
    ModelRuntimeConfig,
    ProviderCreateRequest,
    ProviderResponse,
)


class ModelConfigRepository(Protocol):
    def insert_provider(self, provider: dict) -> None:
        ...

    def insert_model_config(self, model: dict) -> None:
        ...

    def fetch_providers(self) -> list[dict]:
        ...

    def fetch_models(self) -> list[dict]:
        ...

    def set_default_model(self, model_id: str) -> None:
        ...

    def get_model_with_provider(self, model_id: str | None = None) -> dict | None:
        ...


class ModelConfigService:
    def __init__(self, repository: ModelConfigRepository):
        self.repository = repository

    def list_configs(self) -> ModelConfigsResponse:
        providers = [
            ProviderResponse(
                provider_id=provider["provider_id"],
                name=provider["name"],
                provider_type=provider["provider_type"],
                base_url=provider["base_url"],
                has_api_key=bool(provider.get("api_key_secret_ref")),
                enabled=provider["enabled"],
            )
            for provider in self.repository.fetch_providers()
        ]
        models = [ModelResponse(**model) for model in self.repository.fetch_models()]
        return ModelConfigsResponse(providers=providers, models=models)

    def create_provider(self, request: ProviderCreateRequest) -> ProviderResponse:
        provider = {
            "provider_id": str(uuid.uuid4()),
            "name": request.name,
            "provider_type": request.provider_type,
            "base_url": str(request.base_url).rstrip("/"),
            "api_key_secret_ref": request.api_key_secret_ref,
            "enabled": request.enabled,
        }
        self.repository.insert_provider(provider)
        return ProviderResponse(
            provider_id=provider["provider_id"],
            name=provider["name"],
            provider_type=provider["provider_type"],
            base_url=provider["base_url"],
            has_api_key=bool(provider["api_key_secret_ref"]),
            enabled=provider["enabled"],
        )

    def create_model(self, request: ModelCreateRequest) -> ModelResponse:
        provider_ids = {provider["provider_id"] for provider in self.repository.fetch_providers()}
        if request.provider_id not in provider_ids:
            raise HTTPException(status_code=404, detail="Provider not found")
        model = {
            "model_id": str(uuid.uuid4()),
            "provider_id": request.provider_id,
            "model_name": request.model_name,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "timeout_seconds": request.timeout_seconds,
            "is_default": request.is_default,
        }
        self.repository.insert_model_config(model)
        if request.is_default:
            self.repository.set_default_model(model["model_id"])
        return ModelResponse(**model)

    def set_default_model(self, request: DefaultModelRequest) -> ModelResponse:
        target = next((model for model in self.repository.fetch_models() if model["model_id"] == request.model_id), None)
        if target is None:
            raise HTTPException(status_code=404, detail="Model not found")
        self.repository.set_default_model(request.model_id)
        target["is_default"] = True
        return ModelResponse(**target)

    def get_runtime_config(self, model_id: str | None = None) -> ModelRuntimeConfig:
        row = self.repository.get_model_with_provider(model_id)
        if row is None:
            raise HTTPException(status_code=400, detail="No default model configured")
        provider = row["provider"]
        model = row["model"]
        secret_ref = provider.get("api_key_secret_ref") or ""
        api_key = os.getenv(secret_ref, "") if secret_ref else ""
        return ModelRuntimeConfig(
            model_id=model["model_id"],
            provider_id=provider["provider_id"],
            provider_name=provider["name"],
            provider_type=provider["provider_type"],
            base_url=provider["base_url"],
            api_key=api_key,
            model_name=model["model_name"],
            temperature=model["temperature"],
            max_tokens=model["max_tokens"],
            timeout_seconds=model["timeout_seconds"],
        )
