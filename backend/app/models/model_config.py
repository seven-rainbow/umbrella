from pydantic import BaseModel, Field


class ProviderCreateRequest(BaseModel):
    name: str
    provider_type: str = "openai-compatible"
    base_url: str
    api_key_secret_ref: str = ""
    enabled: bool = True


class ProviderResponse(BaseModel):
    provider_id: str
    name: str
    provider_type: str
    base_url: str
    has_api_key: bool
    enabled: bool


class ModelCreateRequest(BaseModel):
    provider_id: str
    model_name: str
    temperature: float = 0.2
    max_tokens: int = 1200
    timeout_seconds: float = 30
    is_default: bool = False


class ModelResponse(BaseModel):
    model_id: str
    provider_id: str
    model_name: str
    temperature: float
    max_tokens: int
    timeout_seconds: float
    is_default: bool


class ModelConfigsResponse(BaseModel):
    providers: list[ProviderResponse]
    models: list[ModelResponse]


class DefaultModelRequest(BaseModel):
    model_id: str


class TestConnectionResponse(BaseModel):
    ok: bool
    message: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ModelRuntimeConfig(BaseModel):
    model_id: str
    provider_id: str
    provider_name: str
    provider_type: str
    base_url: str
    api_key: str = Field(default="", exclude=True)
    model_name: str
    temperature: float
    max_tokens: int
    timeout_seconds: float
