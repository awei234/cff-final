# v3 运行指南

## 快速验证

```powershell
python verify_submission.py
cd code/03_技术实现/competition_runner
python main.py paths
```

## 离线合同测试

```powershell
python run_research_matrix.py --provider deepseek --offline-mock --output-root demo_runs/research_matrix_v3_mock
```

该命令不会联网和读取 API Key。它只用于检查三主题目录、JSON 结构、PDF、provenance 和 verification report。

## 真实矩阵运行

```powershell
$env:DEEPSEEK_API_KEY = "<本机环境变量>"
python run_research_matrix.py --provider deepseek --confirm-live --allow-research-matrix-demo --allow-public-retrieval --max-calls-per-topic 3 --max-total-calls 9 --output-root demo_runs/research_matrix_v3_new
```

运行完成后先看：

```powershell
Get-Content demo_runs/research_matrix_v3_new/matrix_execution_report.json
Get-Content demo_runs/research_matrix_v3_new/context-engineering/verification_report.json
```

如果某个主题失败，查看其 `execution_report.json`、`tool_trace.jsonl` 和 `human_interventions.jsonl`。不要把失败主题的 `paper.pdf` 当成成功论文；它只是失败状态的审计载体。

## 人工确认

自动运行不会写入 `approved`。人工需要分别确认研究问题、资料适用性、实验真实性、结论边界和最终提交。确认之前，状态只能是 `completed_pending_human_review`，矩阵不能写成已提交。
