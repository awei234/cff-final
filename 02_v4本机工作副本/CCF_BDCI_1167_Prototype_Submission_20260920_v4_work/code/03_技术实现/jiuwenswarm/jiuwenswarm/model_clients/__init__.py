"""JiuwenSwarm-owned model clients registered with OpenJiuwen."""

from __future__ import annotations


def ensure_model_clients_registered() -> None:
    """Import extension clients once; BaseModelClient registers subclasses."""
    from jiuwenswarm.model_clients.gemini import GeminiModelClient
    from jiuwenswarm.model_clients.openai_compatible import OpenAICompatibleModelClient

    # Keep explicit references so static analyzers and frozen builds retain imports.
    _ = (GeminiModelClient, OpenAICompatibleModelClient)


ensure_model_clients_registered()

__all__ = ["ensure_model_clients_registered"]
