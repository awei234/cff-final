# JIT Harness 四臂对照实验

运行环境固定为 UCR fixture，比较以下实验臂：

| 对外名称 | 底层 UCR arm | Harness |
|---|---|---|
| baseline | no-rail | 无 |
| prompt-only | prompt-only | 无 |
| full-rail | full-rail | 固定 Rail |
| jit-constrained | full-rail | 受约束 Manifest、白名单、预算、Rail 校验和归档 |

固定 seeds 为 `42`、`43`、`44`。所有 arm 使用同一任务、fixture adapter、工具和预算。

在工作副本根目录运行：

```powershell
$env:PYTHONPATH='code/03_技术实现/competition_runner;code/03_技术实现/ucr_benchmark'
python experiments/jit_comparison_v1/run_comparison.py --output demo_runs/jit_comparison_v1_final
```

输出包括逐 seed/arm 的 UCR 决策、Harness Manifest、Harness archive、成本、时延、证据覆盖率、误引用率状态及 `comparison_results.json`。运行器拒绝覆盖已有非空输出目录。

本实验是 `process_evidence_only` fixture。它评估执行报告的证据约束和审计轨迹，不能推断真实模型能力、外部来源引用质量或领域研究效果。误引用率会标记为 `not_measured_no_quoted_sources`，直到接入人工审核的真实来源任务集。
