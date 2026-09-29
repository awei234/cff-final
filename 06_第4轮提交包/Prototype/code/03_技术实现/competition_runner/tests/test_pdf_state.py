from pathlib import Path

import pytest

from competition_runner.pdf_state import PdfStateError, PdfStateMachine


def test_pdf_state_requires_compile_start_before_verification(tmp_path: Path):
    tex = tmp_path / "paper.tex"
    pdf = tmp_path / "paper.pdf"
    tex.write_text("\\begin{document}evidence\\end{document}", encoding="utf-8")
    pdf.write_bytes(b"%PDF-1.4\nbody\n%%EOF\n")

    state = PdfStateMachine()
    state.mark_tex_generated(tex)
    with pytest.raises(PdfStateError, match="pdf_compile_started"):
        state.mark_compiled_verified(pdf)


def test_pdf_state_records_verified_pdf_hash(tmp_path: Path):
    tex = tmp_path / "paper.tex"
    pdf = tmp_path / "paper.pdf"
    tex.write_text("\\begin{document}evidence\\end{document}", encoding="utf-8")
    pdf.write_bytes(b"%PDF-1.4\nbody\n%%EOF\n")

    state = PdfStateMachine()
    state.mark_tex_generated(tex)
    state.mark_compile_started()
    record = state.mark_compiled_verified(pdf)

    assert record["state"] == "compiled_verified"
    assert record["pdf_sha256"]
    assert record["tex_path"] == str(tex.resolve())


def test_pdf_state_failure_is_terminal_for_run():
    state = PdfStateMachine()
    state.mark_compile_failed("latex returned 1")

    assert state.record == {
        "state": "compile_failed",
        "error": "latex returned 1",
    }
    with pytest.raises(PdfStateError, match="terminal"):
        state.mark_compile_started()
