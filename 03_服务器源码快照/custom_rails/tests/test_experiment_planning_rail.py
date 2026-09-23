"""F02 用例（对应 行动_Rail实现规格 §6）：
① 缺 baseline 被拦 ② 合法 plan 放行 ③ 非法 JSON 被拦 ④ 修正后重写放行
"""
import pytest
import json

from conftest import make_ctx, FakeAgent
from experiment_planning_rail.rail import ExperimentPlanningRail


def _good_plan():
    return {
        "project": "测试题目",
        "experiments": [
            {"id": "exp1", "type": "main", "baselines": ["BaseA", "BaseB"],
             "ablation": "去掉组件X", "seeds": [42, 2024, 2026],
             "datasets": ["d1"], "budget": {"tokens_est": 1000, "time_min": 5},
             "metrics": ["acc"]},
            {"id": "exp2", "type": "baseline", "baselines": ["BaseA", "BaseB"],
             "ablation": "n/a", "seeds": [42, 2024, 2026],
             "datasets": ["d1"], "budget": {"tokens_est": 500, "time_min": 3},
             "metrics": ["acc"]},
            {"id": "exp3", "type": "comparison", "baselines": ["BaseA", "BaseB"],
             "ablation": "n/a", "seeds": [42, 2024, 2026],
             "datasets": ["d1"], "budget": {"tokens_est": 800, "time_min": 4},
             "metrics": ["acc"]},
        ],
        "reproducibility": "Python 3.12, seed 固定",
    }


@pytest.mark.asyncio
async def test_reject_missing_baselines():
    rail = ExperimentPlanningRail()
    plan = _good_plan()
    plan["experiments"][0]["baselines"] = ["BaseA"]          # <2
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "plan.json", "content": json.dumps(plan, ensure_ascii=False)})
    await rail.before_tool_call(ctx)
    assert ctx.extra.get("_skip_tool") is True
    assert ctx.extra.get("_plan_rejected") is True
    assert "baselines" in ctx.inputs.tool_msg.content


@pytest.mark.asyncio
async def test_pass_good_plan():
    rail = ExperimentPlanningRail()
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "plan.json", "content": json.dumps(_good_plan(), ensure_ascii=False)})
    await rail.before_tool_call(ctx)
    assert not ctx.extra.get("_skip_tool")
    await rail.after_tool_call(ctx)
    assert ctx.extra.get("_plan_valid") is True


@pytest.mark.asyncio
async def test_reject_invalid_json():
    rail = ExperimentPlanningRail()
    ctx = make_ctx(FakeAgent(), "write_file", {"path": "plan.json", "content": "not json"})
    await rail.before_tool_call(ctx)
    assert ctx.extra.get("_skip_tool") is True
    assert "合法 JSON" in ctx.inputs.tool_msg.content


@pytest.mark.asyncio
async def test_rewrite_after_fix_passes():
    """④ 修正后重写放行：先拒后放。"""
    rail = ExperimentPlanningRail()
    bad = _good_plan()
    bad["experiments"][0]["seeds"] = [42]
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "plan.json", "content": json.dumps(bad, ensure_ascii=False)})
    await rail.before_tool_call(ctx)
    assert ctx.extra.get("_skip_tool")

    ctx2 = make_ctx(FakeAgent(), "write_file",
                    {"path": "plan.json", "content": json.dumps(_good_plan(), ensure_ascii=False)})
    await rail.before_tool_call(ctx2)
    assert not ctx2.extra.get("_skip_tool")


@pytest.mark.asyncio
async def test_reject_invalid_status():
    """⑤ status 非法枚举被拦；合法枚举放行。"""
    rail = ExperimentPlanningRail()
    bad = _good_plan()
    bad["experiments"][0]["status"] = "done"
    ctx = make_ctx(FakeAgent(), "write_file",
                   {"path": "plan.json", "content": json.dumps(bad, ensure_ascii=False)})
    await rail.before_tool_call(ctx)
    assert ctx.extra.get("_skip_tool") is True
    assert "status" in ctx.inputs.tool_msg.content

    good = _good_plan()
    good["experiments"][0]["status"] = "partial"
    good["experiments"][1]["status"] = "planned"
    good["experiments"][2]["status"] = "completed"
    ctx2 = make_ctx(FakeAgent(), "write_file",
                    {"path": "plan.json", "content": json.dumps(good, ensure_ascii=False)})
    await rail.before_tool_call(ctx2)
    assert not ctx2.extra.get("_skip_tool")
