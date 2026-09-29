"""Shared construction of a configured OpenJiuwen model instance."""

from __future__ import annotations

from typing import Any

from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig

from jiuwenswarm.common.model_providers import validate_model_connection_config
from jiuwenswarm.common.reasoning_injector import build_reasoning_model_request_kwargs
from jiuwenswarm.model_clients import ensure_model_clients_registered


def create_configured_model(
    model_client_config: dict[str, Any],
    model_config_obj: dict[str, Any] | None = None,
) -> Model:
    """Validate one config entry and route it to its exact provider client."""
    ensure_model_clients_registered()
    mcc = dict(model_client_config or {})
    validated = validate_model_connection_config(
        str(mcc.get("client_provider") or ""),
        str(mcc.get("api_base") or ""),
        str(mcc.get("api_key") or ""),
        str(mcc.get("model_name") or ""),
    )
    mcc["client_provider"] = validated.provider
    mcc["api_base"] = validated.api_base
    mcc["api_key"] = validated.api_key
    mcc_fields = {key: value for key, value in mcc.items() if key != "model_name"}
    request_config = ModelRequestConfig(
        **build_reasoning_model_request_kwargs(
            model_client_config=mcc_fields,
            model_config_obj=model_config_obj or {},
            model_name=validated.model_name,
        )
    )
    return Model(
        model_client_config=ModelClientConfig(**mcc_fields),
        model_config=request_config,
    )


__all__ = ["create_configured_model"]
