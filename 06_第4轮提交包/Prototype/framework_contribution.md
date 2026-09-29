# openJiuwen / JiuwenSwarm 贡献说明

## 1. 贡献定位

本项目在 JiuwenSwarm 基础上实现可审计科研 Agent 流程。当前没有声称补丁已被上游合并，也没有虚构 PR；提交材料提供源码、测试、Git commit、feature 分支和 patch，供评审复核。

代码仓库：<https://github.com/awei234/cff-final>  
开发分支：<https://github.com/awei234/cff-final/tree/feature>

## 2. 主要贡献

| 贡献 | 位置 | 验证 |
|---|---|---|
| 执行证据 Rail 与 UCR 评分 | `code/03_技术实现/ucr_benchmark/` | UCR 单元、聚合、Rail 和交付测试 |
| 三主题研究矩阵 | `code/03_技术实现/competition_runner/` | 公开检索、Provider、Claim、PDF 与 provenance 测试 |
| Claim–Evidence 与引用审核 | `competition_runner/research_matrix*.py`、授权 evidence | `allow_paper=true` 与审核审计 |
| 受约束 JIT Harness | `competition_runner/competition_runner/harness/`、`ucr_benchmark/jit_*.py` | 四臂 × 三 seed 独立验证 |
| 网页模型配置校验 | `jiuwenswarm/.../ConfigPanel/` | `modelConfigValidation.test.mjs` |
| 研究 Skill 和 Rails | `custom_skills/`、`custom_rails/` | 配置、Schema 与测试 |

## 3. Git 与 patch 证据

关键提交：

- [来源与 Claim 审核决策](https://github.com/awei234/cff-final/commit/c4a7e25)
- [批准背景 Claim 与正式引用](https://github.com/awei234/cff-final/commit/03891cf)
- [重跑审核并允许论文发布](https://github.com/awei234/cff-final/commit/311dad8)
- [JIT 与发布验证说明](https://github.com/awei234/cff-final/commit/a7e9504)
- [真实多 seed Context-Engineering 对照](https://github.com/awei234/cff-final/commit/a4c46de)
- [授权研究运行发布校验](https://github.com/awei234/cff-final/commit/5772991)

已有补丁：

`code/patches/execution_evidence_rail.patch`

JIT v2 与网页模型配置修复已选择性整合至本正式提交包；相关实现、测试与证据均包含在本目录中。

## 4. 复核建议

1. 阅读上述源码与对应测试。
2. 运行 Competition Runner、UCR 和前端验证测试。
3. 运行 `verify_submission.py --stage final`。
4. 对照 `evidence/jit_comparison_v2_final/` 核验 12 个运行及哈希。

## 5. 上游状态

- 上游 PR：暂无；
- 上游合并：未声明；
- 可复核材料：feature 分支、commit 链接、patch、完整源码与测试。
