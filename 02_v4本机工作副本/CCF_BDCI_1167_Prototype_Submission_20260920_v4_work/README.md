# CCF JiuwenSwarm v4 提交包

版本：v4，状态：`prepared_not_uploaded`。

## 这版做了什么

v4 使用服务器执行实验。服务器地址为 `10.182.68.242`，实验副本放在 `/data/vergil-CCF/ccf/v4_server_workspace`，不修改服务器原始 `jiuwenswarm` 和 `custom_rails`。

本版优先打通 `context-engineering` 的 JiuwenSwarm/UCR 闭环，同时让三个固定主题都能走统一流程：

1. OpenAlex、arXiv、Crossref 公开资料元数据检索；
2. 相关性评分、去重、来源哈希和人工引用审批状态；
3. 研究计划、实验结果审查、研究报告三个阶段；
4. 真实调用已有 UCR runner 的 `no-rail`、`prompt-only`、`full-rail` 三种条件；
5. Claim--Evidence 账本、JSON Pointer、命令/工作目录/stdout/stderr 哈希；
6. 生成 LaTeX 源文件，并将用户本机编译通过的四份 PDF 纳入 v4 包。

UCR 输出标记为 `process_evidence_only`：它证明流程和证据链能力，不等于三个主题的领域科学结论。资料默认 `citation_allowed=false`，没有人工批准时只能是 `completed_pending_human_review`。

## 服务器运行

先上传本 v4 工作副本到服务器的 `/data/vergil-CCF/ccf/v4_server_workspace`，然后：

```bash
cd /data/vergil-CCF/ccf/v4_server_workspace/code/03_技术实现/competition_runner
python run_research_matrix.py --provider deepseek --offline-mock --output-root demo_runs/research_matrix_v4_mock
```

离线命令不联网、不读取 Key、不产生 Provider 调用。受控真实流程必须显式使用：

```bash
python run_research_matrix.py --provider deepseek --confirm-live --allow-research-matrix-demo --allow-public-retrieval --max-calls-per-topic 3 --max-total-calls 9 --output-root demo_runs/research_matrix_v4
```

真实模式要求服务器存在 `DEEPSEEK_API_KEY`，最多每主题 3 次、总计 9 次调用。失败会写 `failure_report.json`，不会伪造成功论文。

## 主要产物

每个主题目录至少包括 `research_materials.json`、`plan.json`、`review.json`、`experiment_config.json`、`experiment_results.json`、`claim_ledger.json`、`tool_trace.jsonl`、`rail_events.jsonl`、`execution_report.json`、`human_interventions.jsonl`、`provenance.json`、`verification_report.json`、`paper.tex`、`paper.pdf`。

## LaTeX 文件位置

统一论文源文件：

```text
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_work\paper\paper.tex
```

三个主题：

```text
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_work\demo_runs\research_matrix_v4\context-engineering\paper.tex
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_work\demo_runs\research_matrix_v4\memory-engine\paper.tex
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_work\demo_runs\research_matrix_v4\self-evolution\paper.tex
```

本机编译：

```powershell
cd D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_work\paper
xelatex -interaction=nonstopmode -halt-on-error paper.tex
xelatex -interaction=nonstopmode -halt-on-error paper.tex
```

已编译并纳入包的 PDF：

```text
paper/paper.pdf
demo_runs/research_matrix_v4/context-engineering/paper.pdf
demo_runs/research_matrix_v4/memory-engine/paper.pdf
demo_runs/research_matrix_v4/self-evolution/paper.pdf
```

四份 PDF 均由对应 UTF-8 `.tex` 使用 XeLaTeX 两遍编译，当前检查无致命错误、无明显 `Overfull \hbox`/`Overfull \vbox`。如果你之后修改 `.tex`，需要重新编译并重新计算校验值。

## 安全与边界

包中不应出现 API Key、Authorization Header、SAR Token、缓存、`.pyc`、`__pycache__` 或私人审稿材料。v1/v2/v3 ZIP 保持冻结。最终研究问题、资料引用、实验真实性、结论范围和网页提交仍需人工确认。
## 已完成的服务器实验（2026-09-20）

服务器离线测试已通过。真实 DeepSeek 运行最终使用了 9 次调用（每个主题 3 次：`plan`、`review`、`report`），三主题状态均为 `completed_pending_human_review`，矩阵验证为 `valid: true`。结果已经从服务器复制到本机的 `demo_runs/research_matrix_v4/`。

服务器上的首次 live 尝试曾因 Provider 返回截断 JSON 失败；失败目录仍保留在服务器上，最终包使用修正提示词和严格输出契约后的第二次成功运行。这个失败记录说明系统遇到模型异常时会保留失败证据，而不会把失败伪装成成功。

本次 UCR 实验的结论边界：`no-rail`、`prompt-only`、`full-rail` 比较的是证据记录和无证据完成声明的流程指标。它不是对“上下文工程”“记忆引擎”或“自我进化”领域效果的充分科学证明。来源默认没有人工批准，报告中的正式引用映射保持为空。

## 本地验收

```powershell
cd D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_work
python verify_submission.py
```

预期 `submission_ready: true`。最终上传状态仍是 `prepared_not_uploaded`。
## 最终打包与验证

本轮 v4 已完成最终整理。正式提交包为：

```text
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4.zip
```

对应的 ZIP SHA-256 保存在包外记录文件：

```text
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_ZIP_SHA256.txt
```

当前技术验证结果：

- ZIP integrity check：通过；
- 解压后 `verify_submission.py`：`submission_ready: true`；
- `CHECKSUMS.sha256`：全部匹配；
- 三个主题：`completed_pending_human_review`；
- DeepSeek 调用：每个主题 3 次，总计 9 次；
- LaTeX：四份 PDF 已编译并纳入包，`.tex` 源文件同时保留；
- 比赛网页：未上传，状态仍为 `prepared_not_uploaded`。

正式 v4 包不含旧 v3 运行目录、旧 PDF、LaTeX 临时文件、缓存、字节码、API Key、Authorization Header、SAR Token 或服务器原始工程；正式 PDF 仅包含上面列出的四份。
