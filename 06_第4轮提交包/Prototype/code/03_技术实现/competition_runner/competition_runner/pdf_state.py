"""Explicit, auditable state transitions for LaTeX/PDF artifacts."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path


class PdfStateError(ValueError):
    """Raised when a PDF artifact transition would create an invalid record."""


class PdfStateMachine:
    def __init__(self) -> None:
        self.record: dict[str, str] = {"state": "initialized"}

    def _require(self, *states: str) -> None:
        if self.record["state"] not in states:
            expected = ", ".join(states)
            raise PdfStateError(
                f"state {self.record['state']} cannot transition; expected {expected}"
            )

    def _require_not_terminal(self) -> None:
        if self.record["state"] in {"compiled_verified", "compile_failed"}:
            raise PdfStateError("PDF run is terminal")

    def mark_tex_generated(self, tex_path: Path) -> dict[str, str]:
        self._require("initialized")
        path = Path(tex_path).expanduser().resolve()
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            raise PdfStateError("tex_generated requires a non-empty TeX file")
        self.record = {"state": "tex_generated", "tex_path": str(path)}
        return dict(self.record)

    def mark_compile_started(self) -> dict[str, str]:
        self._require_not_terminal()
        self._require("tex_generated")
        self.record = {**self.record, "state": "pdf_compile_started"}
        return dict(self.record)

    def mark_compiled_verified(self, pdf_path: Path) -> dict[str, str]:
        self._require("pdf_compile_started")
        path = Path(pdf_path).expanduser().resolve()
        content = path.read_bytes() if path.is_file() else b""
        if not content.startswith(b"%PDF-") or not content.endswith(b"%%EOF\n"):
            raise PdfStateError("compiled_verified requires a readable, complete PDF")
        self.record = {
            **self.record,
            "state": "compiled_verified",
            "pdf_path": str(path),
            "pdf_sha256": sha256(content).hexdigest(),
        }
        return dict(self.record)

    def mark_compile_failed(self, error: str) -> dict[str, str]:
        self._require_not_terminal()
        message = str(error).strip()
        if not message:
            raise PdfStateError("compile_failed requires an error message")
        self.record = {"state": "compile_failed", "error": message}
        return dict(self.record)
