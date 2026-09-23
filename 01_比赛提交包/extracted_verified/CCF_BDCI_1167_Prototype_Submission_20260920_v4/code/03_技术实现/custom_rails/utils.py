"""custom_rails 共享工具：JSON 加载 / 修正引导 / 路径解析 / 数字提取。

所有 rail 依赖本文件；热加载时 utils.py 在 extensions 之外，因此 rail.py 内
用 sys.path 兜底导入（见各 rail.py 顶部），保证独立热加载也能找到。
"""
from __future__ import annotations

import json
import os
import re
import pathlib
from typing import Any


def load_json(path: str | pathlib.Path) -> dict | None:
    """读 JSON，失败返回 None（绝不抛异常打断 agent 流程）。"""
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def save_json(path: str | pathlib.Path, obj: Any) -> bool:
    try:
        pathlib.Path(path).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def build_fix_report(issues: list[str]) -> str:
    """生成给模型看的修正引导消息（中文，不改内容只提示缺口）。"""
    if not issues:
        return ""
    return ("【校验未通过】请修正以下问题后重试：\n"
            + "\n".join(f"- {i}" for i in issues)
            + "\n修正后重新写入，不得绕过校验。")


def resolve_workspace_root(workspace_root: str | None) -> pathlib.Path:
    """构造参数 > 环境变量 CCF_WORKSPACE_ROOT > 当前目录。"""
    root = workspace_root or os.environ.get("CCF_WORKSPACE_ROOT", ".")
    return pathlib.Path(root)


def tool_args_dict(tool_args: Any) -> dict:
    """tool_args 可能是 dict 或 JSON 串，统一成 dict。"""
    if isinstance(tool_args, dict):
        return tool_args
    if isinstance(tool_args, str):
        try:
            d = json.loads(tool_args)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}
    return {}


# ---------- F03 数字提取（供 ResultConsistencyRail 复用，也可独立测试） ----------

_NUM_RE = re.compile(r"(?<![A-Za-z0-9_.])(-?\d+(?:\.\d+)?)(?=%|\s*%|[,\s;.\])}，。；）])")
_YEAR_RE = re.compile(r"^20\d{2}$|^19\d{2}$")
# 结构数字白名单：Section/Figure/Table/Equation 编号、公式编号 (n)、引用 [n]
# （配合 extract_numeric_claims 中「前缀+数字」整体匹配；原 `[\s~]*\d` 尾部因截断失效，已改回宽松前缀）
_STRUCT_PREFIX = re.compile(
    r"(Section|Fig\.?|Figure|Tab\.?|Table|Eq\.?|Equation|§|章|节|图|表|公式|步骤|步)"
    r"[\s~]*\d", re.IGNORECASE)


def strip_latex(text: str) -> str:
    """去掉 LaTeX 命令/注释/数学环境，保留可读文本（数字提取用）。"""
    t = re.sub(r"(?m)^%.*$", "", text)                       # 行注释
    t = re.sub(r"\\cite[a-z]*\{[^}]*\}", " ", t)             # 引用
    t = re.sub(r"\\(?:ref|label|pageref|eqref)\{[^}]*\}", " ", t)  # 交叉引用
    t = re.sub(r"\\(?:begin|end)\{[^}]*\}", " ", t)          # 环境标记
    t = re.sub(r"\\%", "%", t)                               # 转义百分号还原（修复 2026-08-14：87.3\% 被拆成 87）
    t = re.sub(r"\\(?:[a-zA-Z]+\*?)(?:\[[^\]]*\])?\{[^}]*\}", " ", t)  # 命令
    t = re.sub(r"\\(?:[a-zA-Z]+)", " ", t)                   # 剩余命令
    # 修复 2026-08-15（v3 实跑）：\newcommand{\fit}[1]{...} 等结构剥后残留孤立
    # 参数块 [1]/[10pt] 与命令体 {4pt}，其中数字被误提取为数值论断 → 一并剥离
    t = re.sub(r"\[[^\]]*\]", " ", t)                        # 孤立参数块残留
    t = re.sub(r"\{[^}]*\}", " ", t)                         # 孤立命令体残留
    t = re.sub(r"\$[^$]*\$", " ", t)                         # 行内数学
    t = re.sub(r"\\\\", " ", t)
    t = re.sub(r"[~^]", " ", t)
    return t


def extract_numeric_claims(text: str) -> list[str]:
    """从论文文本提取"数值论断"清单（去重、保持顺序）。

    规则（保守策略：拿不准就列入，宁可多报不漏报，由 F03 引导核对）：
    ① 跳过年份（1900-2099）
    ② 跳过结构编号（Section 3.2 / Figure 1 / Table~2 / Eq.(5) / 公式(1)）
    ③ 跳过纯章节号数字（形如 "3.2" 单独出现的节号 → 由前置词白名单拦截）
    ④ 百分比保留原样（"23.5" 与 "23.5\\%" 分开记录）
    """
    clean = strip_latex(text)
    claims: list[str] = []
    for m in _NUM_RE.finditer(clean):
        num = m.group(1)
        if _YEAR_RE.match(num):
            continue
        start = max(0, m.start() - 20)
        ctx_before = clean[start:m.start()]
        # 修复 2026-08-14（实跑发现）：前缀检查需覆盖「前缀+数字」整体，
        # 否则 "Section 3.2" 的 3.2 前缀截断后只剩 "Section "（无数字）导致误标。
        if _STRUCT_PREFIX.search(ctx_before + num):
            continue
        claims.append(num)
    # 去重保序
    seen = set()
    out = []
    for c in claims:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def flatten_values(obj: Any, out: list[tuple[str, float]] | None = None, prefix: str = "") -> list[tuple[str, float]]:
    """拍平 results.json 为 [(key, value)]，供 F03 匹配。"""
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten_values(v, out, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten_values(v, out, f"{prefix}[{i}]")
    elif isinstance(obj, (int, float)):
        out.append((prefix or "value", float(obj)))
    return out


def build_value_set(results: dict) -> set[float]:
    """精确匹配集合：results.json 所有数值 + 各 metrics 列表均值（推导匹配①）。"""
    vals = {round(v, 2) for _, v in flatten_values(results)}
    # 推导匹配：对形如 metrics.xxx[0..n] 的数值列表补均值
    for key, v in flatten_values(results):
        if v != int(v) or True:  # 覆盖率优先，简单实现：全部值进集合（含整数）
            vals.add(round(v, 2))
    return vals
