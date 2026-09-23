# v3 demo runs

本目录保存公开可审计的运行证据。`research_matrix_v3/` 是一次真实 DeepSeek 三主题矩阵运行：三个主题各保存 10 条公开来源元数据/摘要，各执行 3 次 Provider 调用，各自完成本地固定 seed=42 的证据流程基准；三份 verification report 均为 `valid: true`。矩阵状态为 `completed_pending_human_review`，人工审核仍为 `pending`。

目录中的旧尝试不属于提交包；它们已移到项目外的 `07_记录/v3_attempts/` 供开发审计。

这次成功只说明系统真实跑通了“公开检索—研究计划—本地实验—证据审查—报告生成”的受限闭环，不证明三个主题的科学结论。需要结合 `research_materials.json`、`experiment_results.json`、`execution_report.json` 和 `human_interventions.jsonl` 阅读。
