# Competition Runner

This directory is the formal portable configuration entry point.

```powershell
python main.py paths
python main.py provider-check --provider glm
python main.py provider-check --provider qwen
python main.py provider-check --provider deepseek
python main.py reserve-output --output-root "<output-root>" --run-id "<run-id>"
python main.py generate --topic "<topic>" --provider glm --model "<model-id>" --seed 42 --output "<new-run-dir>" --mode fixture
python main.py verify --run "<run-dir>"
python freeze_cross_topic_protocol.py
python run_cross_topic_protocol.py --dry-run
python run_cross_topic_live.py --task-id "<frozen-task-id>" --confirm-live --max-calls "<positive-limit>"
```

Path precedence is CLI value, JSON configuration, then repository-relative default. Provider API keys are read only from `ZHIPUAI_API_KEY`, `DASHSCOPE_API_KEY`, or `DEEPSEEK_API_KEY`; configuration and diagnostic output contain only the environment-variable name and presence status.

These commands perform configuration checks. They do not prove that JiuwenSwarm, Rails, or a live model request succeeded.

`reserve-output` atomically creates one new formal run directory. A run ID is one ASCII path segment containing only letters, digits, `.`, `_`, or `-`, and must start with a letter or digit. Existing targets are rejected even when empty; there is no force or overwrite option. Stable failure codes are `run_id_invalid`, `output_root_invalid`, and `output_exists`.

UCR single runs use an exclusive directory creation step, and `run_experiment.py --all` checks all nine arm/seed targets before starting the batch. Failed or historical run directories are never silently deleted or reused.

## Unified generation contract

One successful generation run contains exactly these required artifacts:

- `run_manifest.json`
- `prompt.txt`
- `tool_trace.jsonl`
- `results.json`
- `paper.tex`
- `paper.pdf`
- `resource.json`
- `verification_report.json`
- `provenance.json`

The protected prompt, trace, results, TeX, PDF, and resource files are hashed in `provenance.json`. The verification report binds the manifest and provenance hashes. `verify` recomputes the complete contract without modifying the run and returns exit code 2 for missing files, invalid fields, run-identity disagreement, invalid PDF boundaries, stale reports, or hash changes.

Use fixture mode for offline contract verification:

```powershell
py -3 main.py generate --topic "Agent上下文工程" --provider glm --model "glm-fixture" --seed 42 --output "<new-run-dir>" --mode fixture
py -3 main.py verify --run "<run-dir>"
```

Fixture artifacts are explicitly labeled and are not model output or experimental evidence. They contain no measured token, duration, or cost values; those fields are `null` with `measurement_status: not_applicable`.

The default mode is `live`. Until the real JiuwenSwarm generation backend is implemented, live generation stops with `generation_backend_unavailable`, preserves a failed manifest, and does not call a provider or fabricate paper/results artifacts. There is no overwrite option: each `--output` path must be a new directory.

## Cross-topic protocol freeze

`freeze_cross_topic_protocol.py` is an offline-only S4 preflight. It freezes the three official topics (Agent context engineering, Agent memory engine, and Agent self-evolution) against one shared prompt template and one 14-artifact contract. The matrix contains one seed-42 task per topic/provider pair: GLM and Qwen tasks remain `pending_authorization`, while every DeepSeek task remains `blocked_budget`.

The command writes `config/cross_topic_protocol_s4_v1.json` and `config/cross_topic_preflight_s4_v1.json` with exclusive creation. It never creates a formal run directory, loads an API key, or calls a model. A second run returns exit code 2 instead of replacing frozen evidence.

`run_cross_topic_protocol.py --dry-run` revalidates the frozen protocol, current Provider configuration hash, all nine task hashes, the 14-artifact contract, and every reserved output path. It classifies the six GLM/Qwen tasks as `eligible_not_executed` and the three DeepSeek tasks as `blocked_budget`. The dry-run does not load credentials, enable live execution, create a result directory, or call a model. Its report is also write-once.

## Cross-topic live backend

`run_cross_topic_live.py` prepares and executes exactly one frozen S4 task. It requires both `--confirm-live` and a positive `--max-calls`; those gates are checked before the selected Provider credential is read. DeepSeek remains unconditionally `task_blocked_budget`, including when confirmation and a credential are present.

The command adapter removes all configured Provider key names from the child environment, exposes only the selected key through `OPENAI_COMPAT_API_KEY`, and requests one strict provider-neutral JSON bundle. The model returns text and JSON evidence only. `paper.pdf` is derived locally and deterministically from validated UTF-8 `paper.tex` using the Python standard library; non-ASCII characters use visible `[U+XXXX]` code-point tokens in the PDF text layer while the original TeX remains unchanged. Provenance records the derivation method and original source hash. Every subprocess launch consumes one authorized call slot.

For GLM models, the adapter explicitly sends `thinking.type: disabled` so the structured response budget is used for the final JSON content instead of a separate reasoning channel. Qwen requests do not receive this Provider-specific parameter. Empty Provider content is rejected with bounded metadata rather than being printed as a blank bundle.

A completed run must contain exactly the frozen 14-artifact contract. A Provider or bundle failure preserves only a failed manifest and execution report. The failure report records a bounded, redacted Provider response, its full SHA-256, byte count, truncation status, and top-level field types; it never records request headers, environment variables, or API keys.

Implementing this backend does not authorize a paid run. The user must separately approve the exact GLM/Qwen call limit before invoking live mode. There is no force or overwrite option, and DeepSeek remains prohibited.
