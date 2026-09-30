"""Slightly tighten line spacing so the revised paper stays within the 15-page limit.

The review site only reads the first 15 pages, so after the round-1 revision the
paper is compressed by reducing the auto line value (240 = single spacing) to a
smaller multiple. Layout-only change: no text, table, figure or reference is altered.

Usage: python tighten_layout.py [target_line]   (default 224)
"""
import os
import sys

from docx import Document
from docx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
DOCX = os.path.join(HERE, "..", "paper.docx")


def tighten(target):
    doc = Document(os.path.abspath(DOCX))
    changed = 0
    for p in doc.paragraphs:
        pPr = p._p.find(qn("w:pPr"))
        if pPr is None:
            continue
        sp = pPr.find(qn("w:spacing"))
        if sp is None:
            continue
        if sp.get(qn("w:lineRule")) == "auto" and sp.get(qn("w:line")) == "240":
            sp.set(qn("w:line"), str(target))
            changed += 1
    doc.save(os.path.abspath(DOCX))
    print("paragraphs tightened to", target, ":", changed)


if __name__ == "__main__":
    tighten(int(sys.argv[1]) if len(sys.argv) > 1 else 224)
