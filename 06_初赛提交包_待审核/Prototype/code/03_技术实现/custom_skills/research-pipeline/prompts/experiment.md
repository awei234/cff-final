# Experiment 实验执行操作手册

> 如何高效、严谨地执行实验计划。改编自 FARS 附录 B Experiment Execution Guidelines。
> 实验设计原则见 `planning.md`——创建 plan.json 时已经应用过。
> 执法者：F03 rail 会勾稽"plan 声明的实验是否都有 results.json"、论文数字是否与 results.json 一致。

## 阶段 A：资源最大化

目标是**高效利用所有可用资源**。开始前先检查：

```bash
nvidia-smi          # GPU：数量、显存、当前占用
nproc               # CPU 核数
free -h             # 内存
```

### 异步启动策略（训练不阻塞 agent）

识别计划中独立的实验（不同种子、baseline、消融、数据集），**全部后台启动，立即返回，不 `wait` 阻塞**（服务器 SSH 环境实测可靠版）：

```bash
# 示例：2 块 GPU，4 个独立实验（每个实验在自己的目录里启动）
cd experiments/baseline1
( setsid /home/vergil/CCF/.venv/bin/python run.py > logs/train.log 2>&1 < /dev/null & echo $! > logs/run.pid )
cd ../baseline2
( setsid /home/vergil/CCF/.venv/bin/python run.py > logs/train.log 2>&1 < /dev/null & echo $! > logs/run.pid )
cd ../method
( setsid /home/vergil/CCF/.venv/bin/python run.py > logs/train.log 2>&1 < /dev/null & echo $! > logs/run.pid )
cd ../ablation1
( setsid /home/vergil/CCF/.venv/bin/python run.py > logs/train.log 2>&1 < /dev/null & echo $! > logs/run.pid )
```

> ⚠️ 远程启动三要素（缺一不可）：
> 1. **括号子 shell** `( ... & )`——防止 `&` 把整条命令链后台化（`A && B & C` 会把 `A && B` 全部丢后台）
> 2. **venv 绝对路径**（如 `/home/vergil/CCF/.venv/bin/python`）——SSH 非交互 shell 不加载 venv 的 PATH，写 `python` 会报"没有那个文件或目录"
> 3. **`setsid` + `< /dev/null`**——让 SSH 会话立即返回（否则 ssh 会等训练结束，命令挂起直到超时），且断连不杀训练

CPU 密集任务（数据预处理、评估、API 调用）同样后台启动：
```bash
cd experiments
( setsid /home/vergil/CCF/.venv/bin/python preprocess1.py > logs/preprocess1.log 2>&1 < /dev/null & echo $! > logs/preprocess1.pid )
( setsid /home/vergil/CCF/.venv/bin/python preprocess2.py > logs/preprocess2.log 2>&1 < /dev/null & echo $! > logs/preprocess2.pid )
```

启动后立即向用户汇报：每个实验的 PID、预计时长、检查间隔。

### 后台训练规范（训练期间的核心动作）

**启动**：`( setsid <venv绝对路径>/python run.py > logs/train.log 2>&1 < /dev/null & echo $! > logs/run.pid )`。三要素：括号子 shell、venv 绝对路径、setsid + stdin 重定向（详见上方「远程启动三要素」）。PID 落盘供后续检查。

**轮询**（每次检查执行）：
```bash
PID=$(cat logs/run.pid)
if ps -p $PID > /dev/null 2>&1; then echo "状态: RUNNING"; else echo "状态: DONE/DEAD"; fi
tail -n 20 logs/train.log          # 最新进度
ls -la results.json 2>/dev/null    # 产物是否生成
```

**判定三态**：
- **完成**：进程退出 且 `results.json` 完整（含 metrics）→ 记入 logs/progress.md，开始下一个实验
- **失败**：进程退出 但无 results.json，或日志有 Traceback → 读日志定位 → 修复后重启
- **超时**：超过 plan.json 预算估算 ×1.5 仍未完成 → 检查原因（卡住/OOM）→ 继续等 / 修复 / 砍（砍需写 `SKIPPED.md`）

**节奏**：默认每 10-15 分钟检查一次（长训练）/ 2-5 分钟（短任务）；每次检查后在 `logs/progress.md` 记一行（时间 + 状态 + 最新 loss/指标）。**等待期间不空等**：并行准备下一个实验的 run.py、写分析脚本、整理 references、或写论文其他章节。

### 资源利用
- **GPU 实验钉到具体 GPU**：`CUDA_VISIBLE_DEVICES=N`
- 模型只用部分显存时，一块 GPU 跑多个实验
- 加大 batch size 填满显存
- 推理类实验（embedding、评估）可同 GPU 并行多个
- CPU 数据预处理用 `multiprocessing` / `concurrent.futures.ProcessPoolExecutor`
- API 类实验（LLM 打分）用 `asyncio` 或线程池并发调用

### 遵守计划，不许缩水
- plan.json 是照资源设计的。**执行全部步骤**。
- 某步确实跑不了（依赖失败、OOM）→ 在该步目录写 `SKIPPED.md` 说明原因，继续。
- 不许因为单 GPU 试点慢就砍实验——用并行把所有 GPU 用满。

### 执行顺序（依赖序）
1. 数据准备（必须最先完成）
2. baseline + 方法（可并行）
3. 消融（方法跑通后可并行）
4. 分析 + 可视化（结果出来后）

## 阶段 B：工作区结构

每个实验一个目录，代码、结果、日志分开，保证"哪份代码产出哪个结果"可验证：

```
workspace/<project_name>/
├── plan.json                    # 实验计划（F02 校验过）
├── experiments/
│   ├── <实验名>/                # 每实验/每条件一个目录
│   │   ├── run.py               # 实验脚本
│   │   ├── config.json          # 超参、设置、种子
│   │   ├── results.json         # 实验结果（F03 唯一数据源）
│   │   └── logs/                # 训练/评估日志、stdout
│   ├── <baseline 名>/
│   │   ├── run.py
│   │   ├── results.json
│   │   └── logs/
│   ├── <消融名>/
│   │   └── ...
│   └── shared/                  # 共享工具
│       ├── data_loader.py       # 数据加载、预处理
│       ├── metrics.py           # 评估指标
│       ├── models.py            # 模型定义
│       └── utils.py             # 通用助手
├── data/                        # 下载/处理后的数据集
└── paper/
    └── figures/                 # 论文用图（数据可追溯）
```

### 每实验结果格式

`experiments/<name>/results.json`：

```json
{
  "experiment": "<name>",
  "metrics": {"metric1": {"mean": 0.87, "std": 0.002}, "metric2": {...}},
  "config": {"lr": 0.001, "epochs": 50, "seed": 42},
  "runtime_minutes": 45,
  "notes": ""
}
```

### 图表
出版级图表存到 `paper/figures/`：
- 对比图（你的方法 vs baseline）
- 消融图（每个组件的影响）
- 训练曲线（loss/指标随 epoch）
- 分析可视化（分布、embedding 等）
- 每张图自包含：轴标签、图例、标题

## 阶段 C：计划合规

- 按 plan.json 逐步执行
- 每个计划步骤在 `experiments/` 下建对应子目录
- 某步不可行 → 在该步目录写 `SKIPPED.md`（说明原因）后继续
- 全部步骤完成后，核对计划的成功标准是否满足
- 结果与假设矛盾 → 如实报告——带良好分析的负结果很有价值

## 可复现性检查清单

- [ ] 全程使用固定随机种子
- [ ] 至少 2 个有意义的 baseline 公平对比
- [ ] 每个新组件有消融研究
- [ ] 无数据泄漏（已验证）
- [ ] 所有配置记录在每实验结果中
- [ ] 每实验在 experiments/ 下有独立目录（代码 + 结果）
- [ ] 关键结果保存了图表
- [ ] 负结果如实报告（若有）
