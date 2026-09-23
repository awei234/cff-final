"""F02 实验规划 Rail：强制 plan.json 合规。

热加载要求：本文件必须命名为 rail.py，类名以 Rail 结尾，priority 带类型注解。
"""
from __future__ import annotations

import json
import sys
import pathlib

from openjiuwen.harness.rails import DeepAgentRail          # 若失败改用 .base（见 verify_api）
from openjiuwen.core.single_agent.rail.base import AgentCallbackContext
from openjiuwen.core.foundation.llm import ToolMessage      # 若失败改用 .schema.message
from openjiuwen.harness.prompts import PromptSection

# 热加载时 utils.py 在 extensions 目录外 → sys.path 兜底导入
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import build_fix_report, load_json, tool_args_dict, resolve_workspace_root  # noqa: E402


class ExperimentPlanningRail(DeepAgentRail):
    priority: int = 50          # 热加载正则依赖此写法

    def __init__(self, workspace_root: str | None = None, strict: bool = True):
        self._workspace_root = workspace_root
        self._strict = strict
        self._builder = None

    # ---- 生命周期 ----
    def init(self, agent):      # 同步钩子，抓 agent 引用（project_memory_rail 范式）
        self._builder = getattr(agent, "system_prompt_builder", None)

    # ---- 拦截：写 plan.json 前校验（协议 A）----
    async def before_tool_call(self, ctx: AgentCallbackContext):
        args = tool_args_dict(getattr(ctx.inputs, "tool_args", {}))
        path_str = str(args.get("path") or args.get("file_path") or "")
        if not path_str.endswith("plan.json"):
            return
        content = args.get("content")
        if content is None:      # edit_file 场景：读磁盘现有文件
            content = self._read_plan(ctx)
        issues = self._validate(content)
        if issues:
            ctx.extra["_plan_rejected"] = True          # 持久标记（_skip_tool 会被弹出）
            ctx.extra["_skip_tool"] = True
            ctx.inputs.tool_result = {"success": False, "error": "plan.json 校验失败"}
            ctx.inputs.tool_msg = ToolMessage(
                content=build_fix_report(issues),
                tool_call_id=getattr(getattr(ctx.inputs, "tool_call", None), "id", None),
            )

    # ---- 通过标记：供 F03 勾稽 ----
    async def after_tool_call(self, ctx: AgentCallbackContext):
        args = tool_args_dict(getattr(ctx.inputs, "tool_args", {}))
        path_str = str(args.get("path") or args.get("file_path") or "")
        if not path_str.endswith("plan.json"):
            return
        if ctx.extra.get("_plan_rejected"):              # 被拒 → 不标记通过
            return
        ctx.extra["_plan_valid"] = True

    # ---- 校验逻辑（纯函数，单测直接调） ----
    def _validate(self, content: str | None) -> list[str]:
        issues: list[str] = []
        if not content or not content.strip():
            return ["plan.json 内容为空"]
        try:
            plan = json.loads(content)
        except Exception:
            return ["plan.json 不是合法 JSON"]
        if not isinstance(plan, dict):
            return ["plan.json 顶层必须是对象"]
        exps = plan.get("experiments")
        if not isinstance(exps, list) or len(exps) < 3:
            issues.append(f"experiments 数量 {len(exps) if isinstance(exps, list) else 'N/A'} < 3")
            exps = exps if isinstance(exps, list) else []
        has_comparison = False
        for e in exps:
            eid = e.get("id", "?")
            status = e.get("status")
            if status is not None and status not in ("planned", "partial", "completed"):
                issues.append(f"{eid}: status 必须是 planned|partial|completed（当前 {status!r}）")
            if len(e.get("baselines", [])) < 2:
                issues.append(f"{eid}: baselines < 2（公平基线要求，1 简单 1 强）")
            if not e.get("ablation"):
                issues.append(f"{eid}: 缺少 ablation 前置规划")
            if len(e.get("seeds", [])) < 3:
                issues.append(f"{eid}: seeds < 3（固定随机种子）")
            if not e.get("budget"):
                issues.append(f"{eid}: 缺少预算估算（tokens_est/time_min）")
            if not e.get("datasets"):
                issues.append(f"{eid}: 缺少 datasets 声明")
            if e.get("type") == "comparison":
                has_comparison = True
        if not has_comparison and self._strict:
            issues.append("主实验必须含 type=comparison 的实验（新 baseline 对比）")
        if not plan.get("reproducibility"):
            issues.append("缺少复现性声明（环境/依赖/随机性）")
        return issues

    def _read_plan(self, ctx: AgentCallbackContext) -> str | None:
        root = resolve_workspace_root(self._workspace_root)
        p = root / "plan.json"
        return p.read_text(encoding="utf-8") if p.exists() else None

    # ---- 注入：把校验规则写进系统提示（before_model_call 可选增强） ----
    async def before_model_call(self, ctx: AgentCallbackContext):
        if self._builder is None:
            return
        rules = ("【实验规划硬规则】plan.json 必须满足：experiments≥3；每实验 baselines≥2"
                 "（1 简单 1 强）；ablation 前置规划；seeds≥3；每实验独立声明 datasets；"
                 "每实验有 budget 估算；主实验含 comparison 类型；顶层含 reproducibility；"
                 "status 字段可选，取值 planned|partial|completed（缺省视为 completed，"
                 "F03 对 completed 强制勾稽 results.json）。")
        self._builder.remove_section("plan_rules")
        self._builder.add_section(PromptSection(
            name="plan_rules", content={"cn": rules, "en": rules}, priority=120,
        ))
