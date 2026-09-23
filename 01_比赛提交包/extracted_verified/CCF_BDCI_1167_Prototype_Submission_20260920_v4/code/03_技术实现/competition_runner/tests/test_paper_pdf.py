from hashlib import sha256

import pytest

from competition_runner.paper_pdf import PaperPdfError, derive_paper_pdf


PAPER = r"""\documentclass{article}
\title{Deterministic Agent Study}
\author{S4 Runner}
\begin{document}
\maketitle
\begin{abstract}
Measured evidence only.
\end{abstract}
\section{Results (seed 42)}
The rail accepted \\ one recorded event.
\end{document}
"""


def test_pdf_is_deterministic_and_bound_to_source_hash():
    first = derive_paper_pdf(PAPER)
    second = derive_paper_pdf(PAPER)
    source_hash = sha256(PAPER.encode("utf-8")).hexdigest().upper().encode("ascii")
    assert first == second
    assert first.startswith(b"%PDF-1.4")
    assert first.endswith(b"%%EOF\n")
    assert source_hash in first
    assert b"Deterministic Agent Study" in first
    assert b"Results \\(seed 42\\)" in first


def test_pdf_changes_when_source_changes():
    assert derive_paper_pdf(PAPER) != derive_paper_pdf(PAPER.replace("accepted", "rejected"))


def test_pdf_paginates_long_source_deterministically():
    body = "\n\n".join(f"Evidence paragraph {index}." for index in range(120))
    paper = "\\begin{document}\n" + body + "\n\\end{document}\n"
    pdf = derive_paper_pdf(paper)
    assert b"/Count 3" in pdf
    assert pdf == derive_paper_pdf(paper)


def test_pdf_preserves_unicode_source_hash_with_deterministic_ascii_fallback():
    paper = "\\begin{document}\n上下文工程 — measured evidence.\n\\end{document}\n"
    pdf = derive_paper_pdf(paper)
    source_hash = sha256(paper.encode("utf-8")).hexdigest().upper().encode("ascii")
    assert source_hash in pdf
    assert b"[U+4E0A][U+4E0B][U+6587][U+5DE5][U+7A0B]" in pdf
    assert b"[U+2014]" in pdf
    assert pdf == derive_paper_pdf(paper)


@pytest.mark.parametrize("paper_tex", ["", "   ", "\ud800"])
def test_pdf_rejects_empty_or_invalid_unicode_source(paper_tex):
    with pytest.raises(PaperPdfError):
        derive_paper_pdf(paper_tex)
