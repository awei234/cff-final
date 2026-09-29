# 03_技术实现

> 本目录是参赛系统的开发基地：源码副本 + 自定义 skill + 自定义 rail + 提示词。
> 更新日期：2026-08-11

---

## 目录结构

```
03_技术实现/
├── jiuwenswarm/          # JiuwenSwarm 官方源码副本（0.2.4.beta4，含 .git 历史，348MB）
│   └── ...               # 修改源码就在这里改（可提 PR）
├── custom_skills/        # 自研科研 skill（流水线提示词 + 脚本）
├── custom_rails/         # 自研 rail 开发目录（开发完移植进 jiuwenswarm 源码注册）
├── prompts/              # 四阶段提示词（FARS 附录 B 提取/改编）
├── tools/                # 配套工具脚本（图表生成/引用核验/资源日志）← 待建
└── README.md             # 本文件
```

---

## 1. 源码副本说明

- **来源**：`<USER_HOME> git clone）
- **版本**：0.2.4.beta4
- **含 .git 历史**：可基于 develop 分支工作、本地 commit、最终整理成 PR
- **关键路径**：
  - rail 实现范式：`jiuwenswarm/agents/harness/code/rails/*.py`
  - rail 注册：`jiuwenswarm/agents/swarm/providers/*.py`
  - 内置 skill：`jiuwenswarm/resources/agent/workspace/skills/`（21 个）
  - Auto Harness：`jiuwenswarm/agents/harness/common/auto_harness/`
  - 文档：`jiuwenswarm/docs/zh/`
- **另有一份打包版可运行环境**：`D:\download\JiuwenSwarm\`（PyInstaller 打包，含 exe；源码不可改，仅作环境备用）

---

## 2. 环境搭建（阶段 0）

> 官方快速上手：`jiuwenswarm/docs/zh/Quickstart.md`

### 2.1 前置条件
- Python `>=3.11,<3.14`（建议 3.12）
- 推荐包管理：`uv`（官方使用 uv.lock）
- Git（已有）

### 2.2 步骤

```bash
# 1. 安装 uv（若没有）
#    Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. 进入源码目录创建 venv
cd "D:/download/CCF/03_技术实现/jiuwenswarm"
uv venv
source .venv/Scripts/activate   # Git Bash 下

# 3. 安装依赖（注意 openjiuwen 是 git 依赖，需要网络）
uv pip install -e ".[test]"

# 4. 检查 CLI
jiuwenswarm --help

# 5. 按 Quickstart.md 初始化配置
jiuwenswarm init   # 生成 config.yaml（在 resources/config.yaml 基础上）

# 6. 配置 DeepSeek（OpenAI 兼容接口）→ 见下方 2.3
```

> ⚠️ 若 `uv pip install` 卡在 git 依赖，可用 pip 替代：
> `pip install -e ".[test]"`；网络问题可配置镜像。

### 2.3 配置 DeepSeek 模型

JiuwenSwarm 支持 OpenAI 兼容多模型。在 config.yaml 中配置：

```yaml
# config.yaml 关键片段（以框架实际字段为准，参考 resources/config.yaml）
model:
  provider: openai-compatible   # 或框架支持的 deepseek 方式
  base_url: https://api.deepseek.com/v1
  api_key: ${DEEPSEEK_API_KEY}  # 环境变量
  model: deepseek-chat          # 或 deepseek-reasoner（写作/规划阶段可用）
```

**API Key**：https://platform.deepseek.com/ 注册申请，充值小额即可（单篇目标 $10 量级）。

### 2.4 跑通最小 demo

```bash
# 目标：agent 完成一次简单任务（生成 500 词短文）
# 方式：按 Quickstart.md 启动 CLI 或 web，发起任务
# 验收：输出正常 + 记录首次 Token/时长 → 07_记录/资源日志.md
```

---

## 3. 开发约定（本工作区内部规范）

| 约定 | 说明 |
|---|---|
| 源码修改位置 | 直接在 `jiuwenswarm/` 副本内改（git 管理，可回溯）|
| rail 开发 | 先在 `custom_rails/` 写逻辑 → 单测通过 → 移植进源码注册 |
| skill 开发 | 直接在 `custom_skills/` 写（SKILL.md 规范）→ 需要时复制进 resources |
| 提示词 | `prompts/` 维护四阶段提示词，skill 引用 |
| 提交前检查 | 对照 06_提交物/提交物清单.md |

---

## 4. 计划中的组件（对方向库的落点）

| 组件 | 落点 | 方向 |
|---|---|---|
| 科研 skill（四阶段流水线）| `custom_skills/research-pipeline/` | D01 |
| plan.json 协议 + 校验 rail | `custom_rails/experiment_planning_rail.py` | F02 |
| 结果一致性校验 rail | `custom_rails/result_consistency_rail.py` | F03 |
| 引用核验 rail + 工具 | `custom_rails/citation_verification_rail.py` + `tools/` | F04 |
| 写作质量 rail + 指标脚本 | `custom_rails/writing_quality_rail.py` + `tools/paper_metrics.py` | F01 |
| 图表生成工具 | `tools/figure_generator.py` / `table_generator.py` | F07 |
| 资源日志工具 | `tools/resource_logger.py` | F06 |

> 各组件详细规格见 `01_方向库/F_功能模块/F0x/README.md`
