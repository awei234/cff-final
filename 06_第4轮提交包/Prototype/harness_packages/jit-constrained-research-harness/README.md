# JIT Constrained Research Harness

这是一个可导入的策略包，不包含 API Key、模型配置、可执行脚本或自动启用逻辑。

## 导入

在网页的 **Harness 包** 页面选择 `jit-constrained-research-harness.zip` 并导入。导入后保持未激活状态；需要使用时再手动启用，停用即可回退到 Native Agent。

## 包含的约束

- 受约束的 `full-rail` 默认 Manifest；
- 四个确定性安全 Profile；
- 工具白名单：`retrieval`、`ucr`、`citation_rail`；
- 最大 3 次 provider 调用、最大 1 次重试；
- Rail 不可关闭，不合法配置回退 `full-rail`。

## 运行边界

此 ZIP 供现有 Auto Harness 导入器识别和登记。实际 JIT Profile 选择、Schema 校验、预算拦截与 Rail 校验由项目内的 `competition_runner` 模块执行；该包只提供可审计的策略副本，避免向运行中的 Agent 注入未经验证的代码。
