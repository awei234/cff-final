# 资源消耗报告

## 1. 统计范围

本报告只统计审核包所含的授权研究运行、多 seed 复现运行和 JIT fixture。无法从原始证据获得的指标标为“未记录”，不进行推算。

## 2. DeepSeek 与公开检索

| 运行 | 模型调用 | 模型调用总时延 | 状态 |
|---|---:|---:|---|
| 授权运行（seed 42） | 9 | 28.973 秒 | 三主题均 `completed_reviewed` |
| 复现运行（seed 43） | 9 | 29.103 秒 | 新来源未批准正式引用 |
| 复现运行（seed 44） | 9 | 30.923 秒 | 新来源未批准正式引用 |
| 合计 | 27 | 88.999 秒 | DeepSeek `deepseek-chat` |

每个 seed 执行 9 次公开元数据检索尝试（三主题 × OpenAlex/arXiv/Crossref），三组共 27 次；每个主题最多保留 10 条去重后的来源元数据。

API Key 只从环境变量读取，不保存在 evidence 中。

## 3. Token 与费用

| 指标 | 结果 |
|---|---|
| DeepSeek 输入/输出 Token | Adapter 未记录，不能补算 |
| DeepSeek实际费用 | Adapter 未上报，标记为 `not_reported_by_adapter` |
| JIT fixture Provider 调用 | 0 |
| JIT fixture 成本 | 0 USD，状态 `fixture_no_external_call` |

“未记录”不等同于 0；只有明确没有外部调用的 fixture 才记为 0。

## 4. JIT Harness

- 实验臂：4；
- seeds：42、43、44；
- 总运行：12；
- Provider 调用：0；
- 记录的总运行时延：0.463631 秒；
- 每次运行均保存策略、预算、Rail、证据和哈希。

该时延是当前机器上的 fixture 工程链路耗时，不代表线上模型延迟。

## 5. 本地计算与存储

| 资源 | 记录 |
|---|---|
| 审核包初始大小 | 约 95.99 MiB（补齐文档和校验和前） |
| GPU/显存 | 未使用、未测量 |
| CPU 峰值 | 未仪器化 |
| 内存峰值 | 未仪器化 |
| 网络 | 真实研究运行访问 DeepSeek、OpenAlex、arXiv、Crossref |
| JIT fixture 网络 | 无外部调用 |

依赖目录、虚拟环境、缓存、日志、运行态和会话历史不纳入提交包。

## 6. 测试成本

交接复验记录：

- UCR：80 passed / 9.65 秒；
- Competition Runner：97 passed / 5.27 秒；
- JIT 交付验证：12/12。

最终审核包会重新运行验证；机器差异可能导致耗时变化。
