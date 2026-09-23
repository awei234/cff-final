# v4 服务器执行记录

## 服务器和隔离目录

- 服务器：`10.182.68.242`（SSH 别名 `ws`）
- v4 独立目录：`/data/vergil-CCF/ccf/v4_server_workspace`
- 原始 JiuwenSwarm：`/data/vergil-CCF/ccf/jiuwenswarm`，未修改
- 原始 Rail 工程：`/data/vergil-CCF/ccf/custom_rails`，未修改
- 实验输出：`/data/vergil-CCF/ccf/v4_server_workspace/demo_runs/research_matrix_v4_retry2`

实验结果随后复制到 Windows：

`D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_work\demo_runs\research_matrix_v4`

## 执行顺序

1. 服务器先运行 `--offline-mock`，不访问网络、不读取 API Key，三主题流程通过。
2. 第一次真实运行因为模型响应为截断 JSON 而失败；该失败目录保留，不作为成功结果。
3. 收紧三阶段 JSON 输出契约、缩短输入摘要并提高合法 JSON 响应容量后重新运行。
4. 第二次真实运行成功完成三个主题，每个主题恰好 3 次调用，总计 9 次。
5. 每个主题均完成资料检索、本地 UCR 三臂实验、计划、审查和报告生成。
6. 最终状态为 `completed_pending_human_review`，不是 `approved_for_submission`。

## 真实运行结果

矩阵文件：`demo_runs/research_matrix_v4/matrix_execution_report.json`。

验证文件：`demo_runs/research_matrix_v4/matrix_verification_report.json`。

验证结果：`valid: true`。

三个实验条件：

- `no-rail`：不启用程序级证据护栏；
- `prompt-only`：只用提示词约束；
- `full-rail`：提示词加程序级证据护栏。

UCR 的含义是“未执行但被写成已完成的比例”。在本次 fixture/UCR 流程基准中，`no-rail` 的 UCR 为 0.5556，`prompt-only` 和 `full-rail` 为 0.0。这个结果只能说明流程证据层面的差异，不能推导真实任务质量、领域效果或自我进化能力。

## 安全和预算

- DeepSeek Key 只在服务器进程环境中使用，没有写入代码、prompt、trace、manifest、provenance 或 ZIP。
- 每主题最多 3 次 Provider 调用，总预算 9 次，实际使用 9 次。
- 公开资料默认 `citation_allowed=false`、`human_review_status=pending`。
- 服务器根分区空间较紧，实验数据放在 `/data`；没有把模型或缓存放到 `/` 或 `/home`。
- 实验开始时 GPU 已有其他进程占用，因此 UCR 实验使用本地 fixture/CPU 逻辑，没有抢占其他任务。

## 本机编译论文

服务器只负责实验，不在服务器编译最终 PDF；Windows 本机已完成四份 PDF 的 XeLaTeX 编译验证，并将 PDF 与源文件一起纳入 v4 包。统一源文件：

`D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_work\paper\paper.tex`

编译：

```powershell
cd D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_work\paper
xelatex -interaction=nonstopmode -halt-on-error paper.tex
xelatex -interaction=nonstopmode -halt-on-error paper.tex
```
## 最终归档与验证

服务器成功运行结果已从以下目录复制回 Windows v4 工作副本：

```text
服务器：/data/vergil-CCF/ccf/v4_server_workspace/demo_runs/research_matrix_v4_retry2
本机：D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4_work\demo_runs\research_matrix_v4
```

最终 v4 ZIP：

```text
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260920_v4.zip
```

打包前已排除旧 v3/mock 运行目录、旧 PDF、缓存和字节码。解压后的独立验证结果为 `submission_ready: true`，但这只表示技术结构、安全和证据链检查通过，不表示人工审核完成，也不表示比赛网页已经提交。
