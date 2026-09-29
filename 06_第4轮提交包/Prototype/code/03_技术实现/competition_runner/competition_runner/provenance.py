"""Source review states and tamper-evident Claim–Evidence records."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


class ProvenanceError(ValueError):
    pass


_TRANSITIONS = {
    "discovered": {"retrieved"},
    "retrieved": {"verified"},
    "verified": {"approved_for_claim"},
    "approved_for_claim": set(),
}


@dataclass
class SourceRegistry:
    sources: dict[str, dict[str, Any]] | None = None
    claims: dict[str, dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        self.sources = {} if self.sources is None else self.sources
        self.claims = {} if self.claims is None else self.claims

    def register(self, source_id: str, locator: str, *, status: str = "discovered") -> dict[str, Any]:
        if status not in _TRANSITIONS:
            raise ProvenanceError(f"unknown source status: {status}")
        if not source_id.strip() or not locator.strip():
            raise ProvenanceError("source_id and locator are required")
        record = {"source_id": source_id, "locator": locator, "status": status}
        self.sources[source_id] = record
        return dict(record)

    def transition(self, source_id: str, status: str) -> dict[str, Any]:
        source = self._source(source_id)
        if status not in _TRANSITIONS:
            raise ProvenanceError(f"unknown source status: {status}")
        if status not in _TRANSITIONS[source["status"]]:
            raise ProvenanceError(f"invalid source transition: {source['status']} -> {status}")
        source["status"] = status
        return dict(source)

    def approve(self, source_id: str, *, reviewer: str) -> dict[str, Any]:
        if not reviewer.strip():
            raise ProvenanceError("reviewer is required")
        source = self.transition(source_id, "approved_for_claim")
        source["reviewer"] = reviewer
        self.sources[source_id] = source
        return dict(source)

    def add_claim(
        self,
        claim_id: str,
        claim_text: str,
        source_id: str,
        artifact_path: Path,
        locator: str,
    ) -> dict[str, Any]:
        source = self._source(source_id)
        if source["status"] != "approved_for_claim":
            raise ProvenanceError("source must be approved_for_claim")
        path = Path(artifact_path).expanduser().resolve()
        if not path.is_file():
            raise ProvenanceError(f"evidence artifact does not exist: {path}")
        if not locator.strip():
            raise ProvenanceError("evidence locator is required")
        content_hash = sha256(path.read_bytes()).hexdigest()
        claim = {
            "claim_id": claim_id,
            "claim_text": claim_text,
            "source_id": source_id,
            "artifact_path": str(path),
            "locator": locator,
            "artifact_sha256": content_hash,
            "status": "approved_for_claim",
        }
        self.claims[claim_id] = claim
        return dict(claim)

    def verify_claim(self, claim_id: str) -> bool:
        claim = self.claims.get(claim_id)
        if claim is None:
            raise ProvenanceError(f"unknown claim: {claim_id}")
        path = Path(claim["artifact_path"])
        current = sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        if current != claim["artifact_sha256"]:
            raise ProvenanceError("hash_mismatch")
        return True

    def _source(self, source_id: str) -> dict[str, Any]:
        source = self.sources.get(source_id)
        if source is None:
            raise ProvenanceError(f"unknown source: {source_id}")
        return source
