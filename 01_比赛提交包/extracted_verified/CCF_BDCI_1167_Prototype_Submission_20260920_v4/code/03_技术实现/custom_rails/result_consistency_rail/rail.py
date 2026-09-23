"""F03 结果一致性 Rail：论文数字必须有 results.json 出处。

防"捏造结果（最高 77%）"。策略：paper.tex 每次写入后抽验 → 未验证数字清单
注入系统提示（result_check 段）引导下一轮修正；after_task_iteration 做最终清点。

plan 勾稽语义（v2 起）：experiment.status 缺省视为 completed（防捏造从严）；
显式声明 planned/partial 的实验视为进行中，仅提示不阻断，待转 completed 后强制勾稽。
"""
from __future__ import annotations

import sys
import pathlib

from openjiuwen.harness.rails import DeepAgentRail
from openjiuwen.core.single_agent.rail.base import AgentCallbackContext
from openjiuwen.harness.prompts import PromptSection

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import (  # noqa: E402
    build_value_set, extract_numeric_claims, load_json,
    resolve_workspace_root, tool_args_dict,
)

SECTION_NAME = "result_check"
SECTION_PRIORITY = 120          # 与 project_memory_rail 同级（section 优先级≠rail 优先级）


class ResultConsistencyRail(DeepAgentRail):
    priority: int = 45

    def __init__(self, workspace_root: str | None = None, max_unverified: int = 20):
        self._workspace_root = workspace_root
        self._max_unverified = max_unverified
        self._builder = None
        self._pending_experiments: list[str] = []

    def init(self, agent):
        self._builder = getattr(agent, "system_prompt_builder", None)

    # ---- 每次 paper.tex 写入后校验 ----
    async def after_tool_call(self, ctx: AgentCallbackContext):
        args = tool_args_dict(getattr(ctx.inputs, "tool_args", {}))
        path_str = str(args.get("path") or args.get("file_path") or "")
        if "paper.tex" not in path_str:
            return
        text = args.get("content") or self._read_paper(ctx)
        if not text:
            return
        await self._check_paper(ctx, text)

    # ---- 任务结束时最终清点（防止 paper 由其他工具生成） ----
    async def after_task_iteration(self, ctx: AgentCallbackContext):
        root = resolve_workspace_root(self._workspace_root)
        p = root / "paper" / "paper.tex"
        if p.exists():
            await self._check_paper(ctx, p.read_text(encoding="utf-8", errors="ignore"))

    async def _check_paper(self, ctx: AgentCallbackContext, text: str):
        root = resolve_workspace_root(self._workspace_root)
        results = self._load_all_results(root)
        values = build_value_set(results)
        unverified = [
            t for t in extract_numeric_claims(text)
            if not self._match(t, values)
        ]
        # 勾稽：plan 声明且状态为 completed/缺省的实验是否都有 results.json（与 F02 联动）
        missing = self._plan_results_missing(root)
        if missing:
            ctx.extra["_missing_experiments"] = missing
        pending = self._pending_experiments
        if pending:
            ctx.extra["_pending_experiments"] = pending

        if unverified or missing or pending:
            ctx.extra["_unverified_numbers"] = unverified[: self._max_unverified]
            lines = ["以下数字在 results.json 中无出处，请核实并修正（可改数字或补实验）："]
            lines += [f"- {u}" for u in unverified[: self._max_unverified]]
            if missing:
                lines.append("以下 plan 声明且状态为 completed 的实验缺少 results.json（补跑或从论文删除相关论断）：")
                lines += [f"- {m}" for m in missing]
            if pending:
                lines.append("以下实验状态为 planned/partial（进行中，仅提示不阻断；转 completed 后强制勾稽）：")
                lines += [f"- {p}" for p in pending]
            self._inject(ctx, "\n".join(lines))

    def _inject(self, ctx, content: str):
        if self._builder is None:
            return
        self._builder.remove_section(SECTION_NAME)
        self._builder.add_section(PromptSection(
            name=SECTION_NAME, content={"cn": content, "en": content},
            priority=SECTION_PRIORITY,
        ))

    # ---- 匹配：精确 + 推导 ----
    def _match(self, token: str, values: set[float]) -> bool:
        try:
            v = float(token)
        except ValueError:
            return True                 # 非数值 token 不拦
        return round(v, 2) in values

    def _load_all_results(self, root: pathlib.Path) -> dict:
        """递归合并 experiments/ 下全部 results.json（支持 <eid>/results.json 与
        <eid>/<seed>/results.json 两级结构；key 用相对路径便于溯源）。"""
        merged: dict = {}
        exp_dir = root / "experiments"
        if exp_dir.is_dir():
            for rp in sorted(exp_dir.rglob("results.json")):
                data = load_json(rp) or {}
                merged[str(rp.relative_to(exp_dir))] = data
        return merged

    #: 缺省视为 completed：plan 未声明 status 时从严勾稽（防捏造优先）
    _PENDING_STATUS = ("planned", "partial")

    def _plan_results_missing(self, root: pathlib.Path) -> list[str]:
        plan = load_json(root / "plan.json")
        if not plan:
            return []
        missing: list[str] = []
        pending: list[str] = []
        exp_dir = root / "experiments"
        for e in plan.get("experiments", []):
            eid = e.get("id")
            if not eid:
                continue
            status = e.get("status", "completed")
            if status in self._PENDING_STATUS:
                pending.append(f"{eid}({status})")
                continue
            rp = (exp_dir / str(eid) / "results.json") if exp_dir.is_dir() else None
            if rp is None or not rp.exists():
                missing.append(str(eid))
        self._pending_experiments = pending
        return missing

    def _read_paper(self, ctx: AgentCallbackContext) -> str | None:
        root = resolve_workspace_root(self._workspace_root)
        p = root / "paper" / "paper.tex"
        return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else None
