"""F03 用例：① 伪造数字被标记 ② 合法数字放行 ③ 章节号不误伤 ④ plan-产物勾稽缺失被报"""
import json
import pathlib

import pytest

from conftest import make_ctx, FakeAgent
from result_consistency_rail.rail import ResultConsistencyRail


def _write(root: pathlib.Path, rel: str, content: str):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _paper_with(number: str) -> str:
    return (r"\section{Introduction} We achieve accuracy " + number
            + r"\% on MNIST. \section{Method} Our approach is straightforward. \section{Conclusion}")


def _results_json():
    return {"metrics": {"acc": {"mean": 87.3, "std": 0.2}}}


@pytest.mark.asyncio
async def test_mark_unverified_number(tmp_path):
    root = pathlib.Path(tmp_path)
    _write(root, "experiments/exp1/results.json", json.dumps(_results_json()))
    rail = ResultConsistencyRail(workspace_root=str(root))
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "paper/paper.tex", "content": _paper_with("99.9")})
    await rail.after_tool_call(ctx)
    assert ctx.extra.get("_unverified_numbers")


@pytest.mark.asyncio
async def test_pass_verified_number(tmp_path):
    root = pathlib.Path(tmp_path)
    _write(root, "experiments/exp1/results.json", json.dumps(_results_json()))
    rail = ResultConsistencyRail(workspace_root=str(root))
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "paper/paper.tex", "content": _paper_with("87.3")})
    await rail.after_tool_call(ctx)
    assert not ctx.extra.get("_unverified_numbers")


@pytest.mark.asyncio
async def test_section_number_not_flagged(tmp_path):
    root = pathlib.Path(tmp_path)
    _write(root, "experiments/exp1/results.json", json.dumps(_results_json()))
    rail = ResultConsistencyRail(workspace_root=str(root))
    # "Section 3.2" 与年份 2026 不应进入未验证清单
    text = r"\section{Introduction} See Section 3.2 and 2026 for context. \section{Conclusion}"
    ctx = make_ctx(FakeAgent(), "write_file", {"path": "paper/paper.tex", "content": text})
    await rail.after_tool_call(ctx)
    assert not ctx.extra.get("_unverified_numbers")


@pytest.mark.asyncio
async def test_missing_experiment_reported(tmp_path):
    root = pathlib.Path(tmp_path)
    _write(root, "plan.json", json.dumps({
        "experiments": [
            {"id": "exp1"}, {"id": "exp2"}, {"id": "exp3"},
        ]}))
    _write(root, "experiments/exp1/results.json", json.dumps(_results_json()))
    rail = ResultConsistencyRail(workspace_root=str(root))
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "paper/paper.tex", "content": _paper_with("87.3")})
    await rail.after_tool_call(ctx)
    assert {"exp2", "exp3"} <= set(ctx.extra.get("_missing_experiments", []))


@pytest.mark.asyncio
async def test_pending_experiment_not_reported(tmp_path):
    """⑤ status=planned/partial 的实验豁免强勾稽，仅进 pending 提示。"""
    root = pathlib.Path(tmp_path)
    _write(root, "plan.json", json.dumps({
        "experiments": [
            {"id": "exp1"},
            {"id": "exp2", "status": "planned"},
            {"id": "exp3", "status": "partial"},
        ]}))
    _write(root, "experiments/exp1/results.json", json.dumps(_results_json()))
    rail = ResultConsistencyRail(workspace_root=str(root))
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "paper/paper.tex", "content": _paper_with("87.3")})
    await rail.after_tool_call(ctx)
    assert not ctx.extra.get("_missing_experiments")
    assert {"exp2(planned)", "exp3(partial)"} <= set(ctx.extra.get("_pending_experiments", []))


@pytest.mark.asyncio
async def test_nested_results_loaded(tmp_path):
    """⑥ 两级结构 experiments/<eid>/<seed>/results.json 能被递归读取（v2 正式实验结构）。"""
    root = pathlib.Path(tmp_path)
    _write(root, "experiments/exp1/seed42/results.json", json.dumps(_results_json()))
    rail = ResultConsistencyRail(workspace_root=str(root))
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "paper/paper.tex", "content": _paper_with("87.3")})
    await rail.after_tool_call(ctx)
    assert not ctx.extra.get("_unverified_numbers")


@pytest.mark.asyncio
async def test_preamble_params_not_flagged(tmp_path):
    """⑦ preamble 命令参数（\documentclass[10pt]、\newcommand{\fit}[1]{...}）不产生数值论断（v3 修复）。"""
    root = pathlib.Path(tmp_path)
    _write(root, "experiments/exp1/results.json", json.dumps(_results_json()))
    text = (r"\documentclass[10pt,twocolumn]{article}" + "\n"
            + r"\newcommand{\fit}[1]{\resizebox{\columnwidth}{!}{#1}}" + "\n"
            + r"\setlength{\tabcolsep}{4pt}" + "\n"
            + r"\begin{document} Accuracy is 87.3\%. \end{document}")
    rail = ResultConsistencyRail(workspace_root=str(root))
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "paper/paper.tex", "content": text})
    await rail.after_tool_call(ctx)
    uv = ctx.extra.get("_unverified_numbers", [])
    assert "10" not in uv
    assert "1" not in uv
    assert "4" not in uv
    assert "87.3" not in uv   # 有出处，放行
