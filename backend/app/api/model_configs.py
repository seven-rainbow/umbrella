from fastapi import APIRouter, Depends

from app.db.clickhouse import ClickHouseRepository, get_repository
from app.models.model_config import (
    DefaultModelRequest,
    ModelConfigsResponse,
    ModelCreateRequest,
    ModelResponse,
    ProviderCreateRequest,
    ProviderResponse,
    TestConnectionResponse,
)
from app.services.llm_gateway import LLMGateway
from app.services.model_config import ModelConfigService

router = APIRouter(prefix="/model-configs", tags=["model-configs"])


@router.get("", response_model=ModelConfigsResponse)
def list_model_configs(repository: ClickHouseRepository = Depends(get_repository)) -> ModelConfigsResponse:
    return ModelConfigService(repository).list_configs()


@router.post("/providers", response_model=ProviderResponse)
def create_provider(
    request: ProviderCreateRequest,
    repository: ClickHouseRepository = Depends(get_repository),
) -> ProviderResponse:
    return ModelConfigService(repository).create_provider(request)


@router.post("/models", response_model=ModelResponse)
def create_model(
    request: ModelCreateRequest,
    repository: ClickHouseRepository = Depends(get_repository),
) -> ModelResponse:
    return ModelConfigService(repository).create_model(request)


@router.post("/models/{model_id}/test", response_model=TestConnectionResponse)
def test_model_connection(
    model_id: str,
    repository: ClickHouseRepository = Depends(get_repository),
) -> TestConnectionResponse:
    service = ModelConfigService(repository)
    config = service.get_runtime_config(model_id)
    message = LLMGateway().test_connection(config)
    return TestConnectionResponse(ok=True, message=message)


@router.put("/default", response_model=ModelResponse)
def set_default_model(
    request: DefaultModelRequest,
    repository: ClickHouseRepository = Depends(get_repository),
) -> ModelResponse:
    return ModelConfigService(repository).set_default_model(request)
