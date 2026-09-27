# 实验证据索引

本目录保存可审计的研究、复现与 JIT 实验材料；其中日志仅限 Claim–Evidence provenance 与实验复现必需的编译日志、stdout/stderr，不包含应用运行日志、会话历史或密钥。

- `research_matrix_authorized/`：已获正式引用批准的授权研究运行（seed 42）；
- `context_engineering_seed43/`、`context_engineering_seed44/`：多 seed 复现记录。新增来源未获正式引用批准，不能进入论文；
- `jit_comparison_v2_final/`：baseline、prompt-only、full-rail、jit-constrained 四臂、三个 seed 的 JIT fixture 结果。

JIT 深度验证入口：`../code/03_技术实现/ucr_benchmark/verify_jit_comparison.py`。引用批准状态与排除 Claim 以包根 `submission_manifest.json` 和 `审核清单.md` 为准。
