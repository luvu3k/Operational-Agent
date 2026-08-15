# Operational_Agent · 运筹优化智能体

一个**自研的运筹优化智能体**（ReAct 模式），面向「远海岛礁应急物资补给」及组合优化问题。用户用自然语言描述问题，智能体先**分解出数学模型**供确认，用户可**反复纠正**直到模型符合预期，再一键求解；结果直接在网页对话中展示**目标函数值、车辆/补给舰路径、路线图与甘特图**，并附上**完整可运行代码**。

不依赖 LangChain 等框架，基于官方 OpenAI 兼容 SDK 自研 ReAct 循环、工具注册中心、记忆与 RAG，逻辑显式、易于审计与扩展。

- **核心问题**：MDVRPTW-P（带时间窗与优先级约束的多仓库车辆路径问题），源自论文《基于知识引导的多智能体DRL求解远海岛礁应急物资补给规划》第 5 节真实算例（3 保障中心 + 22 无人机起飞点）。
- **两种求解方式**：Gurobi 精确求解（最优 82.64）与遗传算法启发式（可行 86.08，gap≈4%），已交叉验证求解正确性。

---

## 目录

1. [快速上手（别人拿到后如何开始）](#1-快速上手别人拿到后如何开始)
2. [运行流程：输入什么 / 输出什么 / 存在哪里](#2-运行流程输入什么--输出什么--存在哪里)
3. [如何查看与删除输出文件](#3-如何查看与删除输出文件)
4. [架构设计](#4-架构设计)
5. [核心功能](#5-核心功能)
6. [MDVRPTW-P 模型口径与验证结果](#6-mdvrptw-p-模型口径与验证结果)
7. [测试](#7-测试)
8. [二次开发约定与可优化方向](#8-二次开发约定与可优化方向)

---

## 1. 快速上手（别人拿到后如何开始）

### 1.1 环境准备
项目基于 Python 3.9+（本机在 `/Applications/yhy/.venv`，Python 3.9.6 上验证通过）。

```bash
cd /Applications/yhy/Operational_Agent

# 建议使用虚拟环境（若已有 .venv 则激活它）
python3 -m venv .venv && source .venv/bin/activate    # 首次创建；已存在则只需 source

# 安装依赖
pip install -r requirements.txt

# 可选：精确求解需要 Gurobi Python 接口 + license（本机已验证 gurobipy 12.0.3）
pip install gurobipy
```

> ⚠️ **常见坑：环境不一致**。务必确认 `pip` 和 `python` 属于同一个环境。若在 `.venv` 里运行却报 `ModuleNotFoundError: No module named 'uvicorn'`，说明依赖被装到了别的 Python。用 `which python && python -c "import sys;print(sys.executable)"` 核对，再 `pip install -r requirements.txt`。

### 1.2 配置 LLM（可选）
在项目根目录创建 `.env`（不配置也能跑，会自动回退到规则实现）：

```bash
LLM_MODEL_ID=Qwen/Qwen2.5-72B-Instruct
LLM_API_KEY=sk-xxxxxxxx
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_TIMEOUT=60
```

### 1.3 启动
```bash
# 方式一：Web 全栈应用（推荐）
python3 main.py            # 默认 web 模式
# 浏览器打开 http://127.0.0.1:8000

# 端口被占用时换端口：
WEB_PORT=8010 python3 main.py      # 然后访问 http://127.0.0.1:8010

# 方式二：终端命令行交互
python3 main.py cli

# 方式三：仅用 uvicorn 起后端
PYTHONPATH=. python3 -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

### 1.4 先跑通论文算例（验证求解正确性）
```bash
cd experiments/mdvrptw && python3 validate.py
# 期望输出：Gurobi 最优 82.64、GA 可行 86.08（gap 4.17%）、✅ 求解正确性验证通过
```

---

## 2. 运行流程：输入什么 / 输出什么 / 存在哪里

### 2.1 交互流程（多轮对话 + 分解纠正）

```
用户自然语言输入
   │  POST /api/analyze
   ▼
[分解] 意图识别 + LLM/规则抽取 → ProblemSpec → 网页展示“数学模型草案”卡片
   │
   ├── 不满意：输入纠正指令  POST /api/refine  ──┐（可多次循环，直到满意）
   │      （改求解方式 / 惩罚系数 / 航速 / JSON 数据…）│
   │◄──────────────────────────────────────────────┘
   │  满意：点击“✓ 模型正确，开始求解”
   ▼  POST /api/solve
[求解] ReAct → mdvrptw_solver 工具 → 生成完整求解代码落盘 → 子进程执行 → result.json
   ▼
网页对话内展示：目标值 / 路径 / 路线图SVG / 甘特图SVG / 完整代码（可复制保存）
```

- **输入**：自然语言问题描述。**确认前**输入的任何消息都会被当作**纠正指令**，触发重新分析。
- 纠正可识别：求解方式（精确 Gurobi / 遗传算法）、优先级惩罚系数、航速、服务时长、每中心车辆数，以及 ` ```json ` 代码块里的自定义实例数据。

### 2.2 输出内容与存储位置

每次求解都会在 **`artifacts/runs/`** 下自动创建一个独立目录，命名规则：

```
artifacts/runs/{任务名}_{日期}_{求解方式}_{时刻}/
例如：artifacts/runs/mdvrptw_island_supply_20260815_gurobi_143208/
```

目录内文件：

| 文件 | 内容 |
| --- | --- |
| `generated_solver.py` | **完整可独立运行的求解代码**（保存后可 `python generated_solver.py` 复现） |
| `result.json` | 结构化结果：目标值、各车辆/补给舰路径、到达时刻、可行性 |
| `problem_spec.json` | 本次结构化问题定义与实例数据 |
| `route_graph.svg` | 路线图（浏览器可直接打开） |
| `gantt.svg` | 到达时间甘特图（MDVRPTW 任务） |
| `stdout.txt` / `stderr.txt` | 子进程执行日志 |

其它输出位置：
- **对话/经验记忆**：`storage/db/agent.db`（SQLite，自动生成）。
- **论文算例验证产物**：`experiments/mdvrptw/results/`（`validate.py` 生成的 SVG 与 JSON）。

> Web 界面上，结果卡片会直接内嵌路线图与甘特图，并给出 `generated_solver.py` 的完整代码（可一键复制）与文件路径。

---

## 3. 如何查看与删除输出文件

### 查看
```bash
# 列出所有运行产物（按时间倒序）
ls -t artifacts/runs/

# 查看最近一次运行的结果与代码
D=$(ls -t artifacts/runs/ | head -1)
cat "artifacts/runs/$D/result.json"
open "artifacts/runs/$D/route_graph.svg"   # macOS 用浏览器打开路线图
open "artifacts/runs/$D/gantt.svg"

# 查看记忆数据库
sqlite3 storage/db/agent.db ".tables"
```

### 删除
```bash
# 清空全部运行产物（保留目录）
rm -rf artifacts/runs/*

# 只删某一次运行
rm -rf artifacts/runs/mdvrptw_island_supply_20260815_gurobi_143208

# 删除超过 7 天的产物
find artifacts/runs -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +

# 清空记忆（会丢失历史对话与经验，谨慎）
rm -f storage/db/agent.db

# 清空论文算例验证产物
rm -rf experiments/mdvrptw/results/*
```

> `artifacts/runs/`、`storage/db/`、`experiments/mdvrptw/results/` 均已加入 `.gitignore`，不会被提交。删除它们不影响项目运行（会在下次求解时重新生成）。

---

## 4. 架构设计

### 4.1 目录结构

```
Operational_Agent/
├── main.py                     # 统一入口：python3 main.py [web|cli]
├── app/
│   ├── api.py                  # FastAPI 后端（单用户，会话状态存内存）
│   ├── static/index.html       # 单文件现代聊天前端
│   ├── cli.py                  # 终端交互式命令行
│   └── session.py              # 会话上下文（session_id）
├── core/                       # 编排与 ReAct 核心
│   ├── agent.py                # 顶层入口 run_agent
│   ├── conversation.py         # 多轮对话 + 问题分解纠正引擎（analyze/refine/solve）
│   ├── intent_parser.py        # 意图识别 + skill 匹配 + 求解偏好
│   ├── problem_extractor.py    # LLM few-shot 抽取 + 规则兜底 + 归一化
│   ├── problem_builder.py      # 合并抽取/skill/RAG/经验 -> ProblemSpec
│   ├── confirmation.py         # 生成确认文本
│   ├── react_agent.py          # 最小 ReAct 闭环：校验->规划->执行->观察->总结
│   ├── tool_calling.py         # core 与 tool_registry 的桥接层
│   └── recovery.py             # 失败恢复（占位）
├── llm/client.py               # 统一 LLM 客户端（LLM_* 环境变量）
├── tools/                      # @tool 注册的可调用工具
│   ├── tool_registry.py        # @tool 装饰器 + 自动扫描 + OpenAI schema 导出
│   ├── mdvrptw_solver_tool.py  # MDVRPTW-P 求解（Gurobi 精确 / 遗传算法）
│   ├── exact_solver_tool.py    # 岛礁补给运输模型：Gurobi 精确
│   ├── heuristic_solver_tool.py# 岛礁补给运输模型：贪心+局部搜索
│   ├── validator_tool.py       # 问题结构校验
│   ├── code_repair_tool.py     # LLM 驱动的代码修复
│   └── visualization_tool.py   # 路线/运输图 SVG（零依赖）
├── solver/
│   ├── artifact_store.py       # 每次运行创建独立目录，落盘代码/日志/结果
│   └── mdvrptw/                # MDVRPTW-P 求解包
│       ├── presets.py          # 实例（论文算例 + 归一化）
│       ├── model.py            # 唯一目标评估口径
│       ├── exact.py            # Gurobi MILP 精确求解
│       ├── genetic.py          # 记忆式遗传算法（GA+2opt+relocate+split）
│       ├── viz.py              # 路线图 + 甘特图 SVG
│       └── codegen.py          # 生成可独立运行的完整脚本
├── schemas/                    # ProblemSpec / ToolSpec 等统一数据结构
├── skills/                     # 问题族知识（Markdown）
│   ├── mdvrptw_island_supply/  # MDVRPTW-P 技能
│   ├── emergency_island_supply/# 岛礁应急补给（运输模型）
│   └── vehicle_routing/        # 车辆路径问题
├── memory/                     # SQLite 记忆（short_term / long_term / summarizer）
├── rag/                        # 资源与经验检索（retrievers / ingestors / indexes）
├── config/                     # 日志与全局配置
├── experiments/mdvrptw/        # 论文算例求解正确性验证（含 validate.py）
├── tests/                      # 集成测试
├── artifacts/runs/             # ★ 求解产物目录（自动生成，已 gitignore）
└── storage/db/agent.db         # ★ 记忆数据库（自动生成，已 gitignore）
```

### 4.2 全栈调用链

```
浏览器（app/static/index.html，单文件聊天 UI）
        │  fetch /api/*
        ▼
FastAPI（app/api.py）——— 单用户，会话状态存内存
        │
        ▼
ConversationManager（core/conversation.py）  analyze / refine（多轮纠正）/ solve
        │                                          │
        ▼                                          ▼
   问题分解（intent_parser / problem_builder    ReAct 求解（react_agent）
   / problem_extractor）                         └─ tools/mdvrptw_solver_tool.py（@tool 自动注册）
                                                       │
                                                       ▼
                                              solver/mdvrptw/ 求解包
                                              （presets/model/exact/genetic/viz/codegen）
                                                       │
                                                       ▼
                                      solver/artifact_store.py：代码落盘 → 子进程执行 → result.json
```

### 4.3 FastAPI 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 单文件前端页面 |
| POST | `/api/analyze` | `{session_id?, message}` 首轮分析，返回数学模型草案 |
| POST | `/api/refine` | `{session_id, message}` 纠正并重新分析（可多次） |
| POST | `/api/solve` | `{session_id}` 确认并求解，返回目标值/路径/SVG/完整代码 |
| POST | `/api/reset` | `{session_id}` 重置会话 |
| GET | `/api/history?session_id=` | 拉取对话历史 |

---

## 5. 核心功能

- **统一 LLM 客户端**（`llm/client.py`）：只认 `LLM_MODEL_ID / LLM_API_KEY / LLM_BASE_URL / LLM_TIMEOUT`，任何 OpenAI 兼容服务可接入；不可用时全链路自动回退规则实现。
- **工具注册与发现**（`tools/tool_registry.py`）：`@tool` 装饰器 + 自动扫描 `tools/`，导出 OpenAI tools schema。已注册：`mdvrptw_solver`、`exact_solver`、`heuristic_solver`、`validate_problem`、`repair_code`。
- **多轮对话 + 分解纠正**（`core/conversation.py`）：analyze → refine（可反复）→ solve 闭环，确认前的输入都被当作纠正指令。
- **MDVRPTW-P 求解**（`solver/mdvrptw/`）：Gurobi 精确 MILP + 记忆式遗传算法，共用同一目标评估口径，生成可独立运行脚本。
- **代码即产物**：所有求解都先生成物理 `.py` 文件再子进程执行，结果落盘为 `result.json`，可复现可审计。
- **零依赖可视化**：路线图 / 甘特图用纯 Python 生成 SVG，浏览器直接渲染，无需 matplotlib。
- **记忆与 RAG**：SQLite 持久化短期/长期记忆；资源/经验检索补齐实例数据。

---

## 6. MDVRPTW-P 模型口径与验证结果

- **目标**：`最小化 总航行时间 + 优先级违反惩罚`
  - 总航行时间 = 所有车辆航行总距离 / v₁
  - 优先级惩罚 = L · Σ_{同路径相邻 i→j} max(0, τ_j − τ_i)
- **约束**：每客户被服务一次；每条路径归属单一仓库并返回原点；每仓库车辆数上限；到达时刻 ≤ 最晚服务时间（硬时间窗）；子回路消除。
- **参数假设**（论文未给出，自洽建模，写在 `solver/mdvrptw/presets.py`）：v₁=40 km/h、服务时长=0.5 h、每中心≤8 艘、L=1.0。

| 方法 | 目标值 | 状态 | 路径数 | gap | 耗时 |
| --- | --- | --- | --- | --- | --- |
| Gurobi 精确 | 82.64 | OPTIMAL | 8 | 0% | ~0.5s |
| 遗传算法 | 86.08 | 可行 | 6 | 4.17% | ~18s |

> 因论文缺 v₁/服务时长/岛礁级坐标等参数，采用自洽口径，最优值为 82.64（非论文的 268.8），但 Gurobi 与遗传算法互相验证、求解逻辑正确。`experiments/mdvrptw/validate.py` 可一键复现。

---

## 7. 测试

```bash
cd /Applications/yhy/Operational_Agent
export PYTHONPATH=/Applications/yhy/Operational_Agent
for t in test_intent_parser test_problem_builder test_tools test_memory test_react_loop; do
  python3 -m tests.$t
done
```
覆盖：意图识别、问题构建、工具注册与执行、记忆读写、ReAct 闭环。当前 5 个测试模块全部通过。

---

## 8. 二次开发约定与可优化方向

### 约定
- 所有求解工具**必须先生成物理 `.py` 文件再执行**，禁止只返回代码字符串。
- LLM 客户端只通过 `LLM_*` 环境变量或显式传参初始化。
- 每个可测试模块都应含 `if __name__ == "__main__":` 自测块。
- 新增工具：在 `tools/` 下用 `@tool(...)` 装饰函数即可被自动发现。
- 新增问题族：在 `skills/<name>/` 提供 `metadata.json` + `skill.md` + `examples.md`，并补充对应求解逻辑。

### 可优化方向
- 求解代码生成进一步泛化到任意问题族（当前 MDVRPTW 已参数化，其它族仍为模板）。
- 引入独立策略选择器：按规模/约束密度自动选 exact/heuristic，exact 超时自动降级。
- 打通「执行失败 → 修复 → 重跑」重试环（`core/recovery.py` 目前占位）。
- 沙箱隔离执行生成代码（当前为本机子进程）。
- 向量检索增强 RAG；前端支持历史会话列表、SVG 下载、SSE 流式进度。
