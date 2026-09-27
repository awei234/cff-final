from __future__ import annotations

from hashlib import sha256
import re
import textwrap


class PaperPdfError(ValueError):
    pass


_STRUCTURAL = re.compile(r"\\(?:title|author|section|subsection|subsubsection)\{([^{}]*)\}")
_INLINE = re.compile(r"\\(?:textbf|textit|emph)\{([^{}]*)\}")
_ENVIRONMENT = re.compile(r"\\(?:begin|end)\{(?:document|abstract)\}")
_COMMAND = re.compile(r"\\[A-Za-z@]+(?:\[[^\]]*\])?")


def _ascii_render_source(paper_tex: str) -> str:
    rendered: list[str] = []
    for character in paper_tex:
        codepoint = ord(character)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise PaperPdfError("paper_tex must contain valid Unicode")
        rendered.append(character if codepoint < 128 else f"[U+{codepoint:04X}]")
    return "".join(rendered)


def _plain_lines(paper_tex: str) -> list[str]:
    if not isinstance(paper_tex, str) or not paper_tex.strip():
        raise PaperPdfError("paper_tex must be non-empty")
    text = _ascii_render_source(paper_tex)
    text = _STRUCTURAL.sub(lambda match: "\n" + match.group(1) + "\n", text)
    while _INLINE.search(text):
        text = _INLINE.sub(lambda match: match.group(1), text)
    text = _ENVIRONMENT.sub("\n", text)
    text = re.sub(r"\\documentclass(?:\[[^\]]*\])?\{[^{}]*\}", "", text)
    text = re.sub(r"\\usepackage(?:\[[^\]]*\])?\{[^{}]*\}", "", text)
    text = text.replace(r"\\", "\n").replace("~", " ")
    text = _COMMAND.sub("", text).replace("{", "").replace("}", "")
    paragraphs = [" ".join(part.split()) for part in text.splitlines() if part.strip()]
    lines = [line for part in paragraphs for line in textwrap.wrap(part, width=88)]
    if not lines:
        raise PaperPdfError("paper_tex has no renderable text")
    return lines


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def derive_paper_pdf(paper_tex: str) -> bytes:
    lines = _plain_lines(paper_tex)
    source_hash = sha256(paper_tex.encode("utf-8")).hexdigest().upper()
    pages = [lines[index:index + 52] for index in range(0, len(lines), 52)]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    }
    page_ids: list[int] = []
    next_id = 4
    for page_lines in pages:
        page_id, content_id = next_id, next_id + 1
        next_id += 2
        page_ids.append(page_id)
        operators = ["BT", "/F1 10 Tf", "48 760 Td", "12 TL"]
        for line in page_lines:
            operators.extend((f"({_escape_pdf_text(line)}) Tj", "T*"))
        operators.append("ET")
        stream = ("\n".join(operators) + "\n").encode("ascii")
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream + b"endstream"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
    info_id = next_id
    objects[info_id] = (
        f"<< /Producer (competition_runner stdlib-latex-text-pdf-v1) "
        f"/Subject (paper.tex SHA256 {source_hash}) >>"
    ).encode("ascii")
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {0: 0}
    for object_id in range(1, info_id + 1):
        offsets[object_id] = len(output)
        output.extend(f"{object_id} 0 obj\n".encode("ascii"))
        output.extend(objects[object_id])
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {info_id + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for object_id in range(1, info_id + 1):
        output.extend(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {info_id + 1} /Root 1 0 R /Info {info_id} 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)
