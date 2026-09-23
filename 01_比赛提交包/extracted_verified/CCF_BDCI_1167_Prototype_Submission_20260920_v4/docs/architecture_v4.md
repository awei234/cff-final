# v4 架构说明

v4 在 v3 runner 外增加一层研究矩阵编排。编排层调用公开资料适配器、现有 UCR `run_experiment.py`、严格阶段校验和 LaTeX 源文件生成器。UCR 不被包装成领域实验：它的定位是 `process_evidence_only`。

数据流：检索 → 相关性/去重 → 计划 → UCR 三 arm → Claim--Evidence 账本 → 审查 → 报告 → `.tex` → 人工确认。

Provider 安全门由 `--confirm-live`、`--allow-research-matrix-demo`、`--allow-public-retrieval`、Key 环境变量和 1–3/9 调用上限共同组成。错误只生成 failure report，绝不把未执行步骤写成成功。