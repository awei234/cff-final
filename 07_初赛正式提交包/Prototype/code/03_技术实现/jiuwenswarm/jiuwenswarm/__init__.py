"""JiuwenSwarm package initialization."""

from jiuwenswarm.model_clients import ensure_model_clients_registered

ensure_model_clients_registered()

__all__ = ["ensure_model_clients_registered"]
