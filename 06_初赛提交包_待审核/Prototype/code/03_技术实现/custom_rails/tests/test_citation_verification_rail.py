"""F04 用例：① 池中引用通过 ② 未知引用被引导 ③ 多键 \citep 解析 ④ 无 \cite 不报"""
import pathlib

import pytest

from conftest import make_ctx, FakeAgent
from citation_verification_rail.rail import CitationVerificationRail


def _write(root, rel, content):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _paper(cite_block: str) -> str:
    return (r"\section{Introduction} Some claim " + cite_block
            + r" \section{Method} O(1). \section{Conclusion}")


@pytest.mark.asyncio
async def test_pool_hit_passes(tmp_path):
    root = pathlib.Path(tmp_path)
    _write(root, "references/smith2023/meta/meta_info.txt", "title: Smith 2023")
    rail = CitationVerificationRail(workspace_root=str(root))
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "paper/paper.tex", "content": _paper(r"\cite{smith2023}")})
    await rail.after_tool_call(ctx)
    assert not ctx.extra.get("_unverified_citations")


@pytest.mark.asyncio
async def test_unknown_cite_flagged(tmp_path):
    root = pathlib.Path(tmp_path)
    rail = CitationVerificationRail(workspace_root=str(root))
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "paper/paper.tex", "content": _paper(r"\cite{ghost2025}")})
    await rail.after_tool_call(ctx)
    assert ctx.extra.get("_unverified_citations") == ["ghost2025"]


@pytest.mark.asyncio
async def test_multi_key_citep(tmp_path):
    root = pathlib.Path(tmp_path)
    _write(root, "references/smith2023/meta/meta_info.txt", "x")
    _write(root, "references/jones2024/meta/meta_info.txt", "x")
    rail = CitationVerificationRail(workspace_root=str(root))
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "paper/paper.tex",
                    "content": _paper(r"\citep{smith2023,jones2024,ghost2025}")})
    await rail.after_tool_call(ctx)
    assert ctx.extra.get("_unverified_citations") == ["ghost2025"]


@pytest.mark.asyncio
async def test_no_cite_no_report(tmp_path):
    root = pathlib.Path(tmp_path)
    rail = CitationVerificationRail(workspace_root=str(root))
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "paper/paper.tex", "content": r"\section{A} text \section{B}"})
    await rail.after_tool_call(ctx)
    assert not ctx.extra.get("_unverified_citations")
