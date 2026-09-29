# 模块调用与复现说明

## 1. 主要模块

| 模块 | 入口 | 职责 |
|---|---|---|
| JiuwenSwarm | `code/03_技术实现/jiuwenswarm/` | Agent 编排、模型配置、工具与网页交互 |
| Competition Runner | `competition_runner/run_research_matrix.py` | 公开检索、三阶段研究流程、Claim/引用审核 |
| UCR Runner | `ucr_benchmark/run_experiment.py` | 四臂多 seed 对照和执行证据评分 |
| JIT Harness | `competition_runner/competition_runner/harness/` | Manifest、Profile、选择、预算和 Rail 校验 |
| 发布校验 | 根目录 `verify_submission.py` | 正式提交目录、安全、PDF 和哈希检查 |

## 2. 研究矩阵调用顺序

1. 校验主题、Provider、调用预算和显式授权开关。
2. 读取 `DEEPSEEK_API_KEY`；密钥只进入当前进程环境。
3. 调用 OpenAlex、arXiv、Crossref 并保存来源哈希。
4. 依次执行 plan、review、report 三次模型调用。
5. 运行 Claim–Evidence 审核和引用白名单。
6. 写出论文材料、人工决策、provenance 与 verification report。

受控真实运行示例：

```powershell
cd code/03_技术实现/competition_runner
python run_research_matrix.py --provider deepseek --confirm-live --allow-research-matrix-demo --allow-public-retrieval --max-calls-per-topic 3 --max-total-calls 9 --output-root <new-output-dir>
```

输出目录必须不存在；程序不覆盖历史实验。

## 3. 四臂 JIT 对照

```powershell
cd code/03_技术实现/ucr_benchmark
python run_experiment.py --all --mode fixture --output <new-output-dir>
python aggregate_results.py <new-output-dir> --output <new-output-dir>/summary.json
python verify_jit_comparison.py <new-output-dir>
```

`--all` 固定执行：

- `no-rail`：baseline；
- `prompt-only`：只有提示词约束；
- `full-rail`：固定硬 Rail；
- `jit-constrained`：JIT 选择安全 Profile，同时保留硬 Rail。

每臂使用 seeds 42、43、44。fixture 不调用外部模型，不能作为模型性能证据。

## 4. 正式提交校验

```powershell
python verify_submission.py --stage final
```

正式校验检查目录、必需文件、PDF 页数、敏感内容和 SHA-256 清单；Token 仅检查存在与非空。深度实验校验另行执行 JIT 验证器。

## 5. 稳定错误语义

- `retrieval_failed`：公开资料未取得；
- `provider_invalid_json`：模型输出不符合 JSON 契约；
- `citation_mapping_blocked`：引用不存在或未批准的来源；
- `budget_exceeded`：Provider 调用或重试预算越界；
- `rail_rejected`：完成性 Claim 缺少成功证据；
- `completed_reviewed`：自动流程完成且来源/Claim 审核已记录。

错误会保存证据，不包装成成功结果。
