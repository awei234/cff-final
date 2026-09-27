"""验证当前环境 openjiuwen 的 rail API（阶段 0 装完环境后先跑）。
用法：source ~/CCF/.venv/bin/activate && python 03_技术实现/custom_rails/verify_api.py
"""
import inspect

# 三个候选导入路径（docs 用顶层；vendored 代码用 .base；都试，打印哪个通）
paths = {
    "DeepAgentRail A": ("openjiuwen.harness.rails", "DeepAgentRail"),
    "DeepAgentRail B": ("openjiuwen.harness.rails.base", "DeepAgentRail"),
    "Ctx/Inputs": ("openjiuwen.core.single_agent.rail.base", "AgentCallbackContext"),
    "ToolCallInputs": ("openjiuwen.core.single_agent.rail.base", "ToolCallInputs"),
    "ToolMessage A": ("openjiuwen.core.foundation.llm", "ToolMessage"),
    "ToolMessage B": ("openjiuwen.core.foundation.llm.schema.message", "ToolMessage"),
    "PromptSection": ("openjiuwen.harness.prompts", "PromptSection"),
}
import importlib
objs = {}
for label, (mod, name) in paths.items():
    try:
        m = importlib.import_module(mod)
        objs[label] = getattr(m, name)
        print(f"[OK]   {label}: {mod}.{name}")
    except Exception as e:
        print(f"[FAIL] {label}: {mod}.{name} -> {type(e).__name__}: {e}")

rail_cls = objs.get("DeepAgentRail A") or objs.get("DeepAgentRail B")
if rail_cls is not None:
    print("\n--- DeepAgentRail 钩子签名 ---")
    for h in ("init", "uninit", "before_invoke", "after_invoke",
              "before_task_iteration", "after_task_iteration",
              "before_model_call", "after_model_call",
              "before_tool_call", "after_tool_call",
              "on_model_exception", "on_tool_exception", "get_callbacks"):
        if hasattr(rail_cls, h):
            try:
                print(f"{h}: {inspect.signature(getattr(rail_cls, h))}")
            except (TypeError, ValueError) as e:
                print(f"{h}: <签名不可见 {e}>")   # mypyc 编译态常见
    print("\n-- 类上的全部公共方法 --")
    print([m for m in dir(rail_cls) if not m.startswith("_")])

tm = objs.get("ToolMessage A") or objs.get("ToolMessage B")
if tm is not None:
    try:
        print("\nToolMessage:", inspect.signature(tm))
    except Exception as e:
        print("\nToolMessage 签名不可见:", e)

ps = objs.get("PromptSection")
if ps is not None:
    try:
        print("PromptSection:", inspect.signature(ps))
    except Exception as e:
        print("PromptSection 签名不可见:", e)
