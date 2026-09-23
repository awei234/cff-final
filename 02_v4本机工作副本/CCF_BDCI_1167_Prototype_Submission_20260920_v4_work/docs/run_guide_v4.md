# JiuwenSwarm v4 运行指南

## 本机验证

```powershell
cd D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_work\code\03_技术实现\competition_runner
python run_research_matrix.py --provider deepseek --offline-mock --output-root demo_runs/research_matrix_v4_mock
```

## 服务器执行

服务器：`vergil@10.182.68.242`；目录：`/data/vergil-CCF/ccf/v4_server_workspace`。先执行离线命令，再执行带三个安全开关的真实命令。输出目录必须不存在或为空；已有目录禁止覆盖。

## 如何读结果

- `research_materials.json`：找到的公开来源及其评分；`citation_allowed=false` 表示尚未人工批准。
- `experiment_results.json`：三种 UCR arm 的原始汇总。
- `claim_ledger.json`：每条结论绑定的 JSON Pointer 和文件哈希。
- `execution_report.json`：每阶段成功或失败。
- `verification_report.json`：运行结构校验。
- `paper.tex`：用户本机编译的论文源文件。

## 状态解释

`completed_pending_human_review` 不是已经提交；它表示自动流程完成，但人工还要确认来源、实验和结论。`partial_failed` 表示至少一个主题失败，失败证据必须保留。