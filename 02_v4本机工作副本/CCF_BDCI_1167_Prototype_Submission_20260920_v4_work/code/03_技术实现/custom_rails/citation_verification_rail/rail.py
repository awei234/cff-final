"""F04 引用核验 Rail：写作阶段核验 \cite 键真实存在。

本地优先：命中 references/ 池 → 通过；未命中 → 提示走 citation_checker.py 在线核验
（rail 不做网络调用，避免阻塞；在线核验作为提交前独立步骤执行，见 §7.2）。
"""
from __future__ import annotations

import re
import sys
import pathlib

from openjiuwen.harness.rails import DeepAgentRail
from openjiuwen.core.single_agent.rail.base import AgentCallbackContext
from openjiuwen.harness.prompts import PromptSection

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import resolve_workspace_root, tool_args_dict  # noqa: E402

SECTION_NAME = "citation_check"
CITE_RE = re.compile(r"\\cite[a-z]*\{([^}]*)\}")


class CitationVerificationRail(DeepAgentRail):
    priority: int = 40

    def __init__(self, workspace_root: str | None = None, max_bad: int = 20):
        self._workspace_root = workspace_root
        self._max_bad = max_bad
        self._builder = None

    def init(self, agent):
        self._builder = getattr(agent, "system_prompt_builder", None)

    async def after_tool_call(self, ctx: AgentCallbackContext):
        args = tool_args_dict(getattr(ctx.inputs, "tool_args", {}))
        path_str = str(args.get("path") or args.get("file_path") or "")
        if "paper.tex" not in path_str:
            return
        text = args.get("content") or self._read_paper(ctx)
        if not text:
            return
        await self._check_citations(ctx, text)

    async def after_task_iteration(self, ctx: AgentCallbackContext):
        root = resolve_workspace_root(self._workspace_root)
        p = root / "paper" / "paper.tex"
        if p.exists():
            await self._check_citations(ctx, p.read_text(encoding="utf-8", errors="ignore"))

    async def _check_citations(self, ctx: AgentCallbackContext, text: str):
        root = resolve_workspace_root(self._workspace_root)
        pool = self._load_pool(root)
        keys = self._extract_cite_keys(text)
        bad = [k for k in keys if k not in pool]
        if bad:
            ctx.extra["_unverified_citations"] = bad[: self._max_bad]
            lines = ["以下引用未在 references/ 池中命中，请替换为池中真实文献，"
                     "或先跑 tools/citation_checker.py --file paper.tex 在线核验："]
            lines += [f"- {k}" for k in bad[: self._max_bad]]
            self._inject(ctx, "\n".join(lines))

    def _inject(self, ctx, content: str):
        if self._builder is None:
            return
        self._builder.remove_section(SECTION_NAME)
        self._builder.add_section(PromptSection(
            name=SECTION_NAME, content={"cn": content, "en": content}, priority=120,
        ))

    # ---- 纯函数（可单测） ----
    @staticmethod
    def _extract_cite_keys(text: str) -> list[str]:
        keys: list[str] = []
        for m in CITE_RE.finditer(text):
            for k in m.group(1).split(","):
                k = k.strip()
                if k:
                    keys.append(k)
        # 去重保序
        seen, out = set(), []
        for k in keys:
            if k not in seen:
                seen.add(k)
                out.append(k)
        return out

    @staticmethod
    def _load_pool(root: pathlib.Path) -> set[str]:
        """池 = references/ 下每文献目录名（bibkey）或 references_index.json 的键。"""
        ref_dir = root / "references"
        pool: set[str] = set()
        idx = ref_dir / "references_index.json"
        if idx.exists():
            import json
            try:
                data = json.loads(idx.read_text(encoding="utf-8"))
                pool |= set(data.keys())
            except Exception:
                pass
        if ref_dir.is_dir():
            for sub in ref_dir.iterdir():
                if sub.is_dir():
                    pool.add(sub.name)
        return pool

    def _read_paper(self, ctx: AgentCallbackContext) -> str | None:
        root = resolve_workspace_root(self._workspace_root)
        p = root / "paper" / "paper.tex"
        return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else None
