# 实验设计与评估协议（shiyan/）

## 1. 被测系统与基线

| 角色 | 系统 | 说明 |
| --- | --- | --- |
| 本文智能体 | **OptAgent** = DeepSeek-V3 + 结构化流水线（NL→数学模型→代码→**落盘子进程执行**→结果/解释） | 通过 `tools/general_solver_tool.py` 实现，代码真实运行并写 result.json |
| 基线1 | GPT-4o（CLOSEAI 代理） | 通用大模型，raw 直接回答 |
| 基线2 | GPT-4o-mini | 通用大模型 |
| 基线3 | Moonshot-v1-8k（Kimi，月之暗面/国产） | 通用大模型 |
| 基线4 | Qwen2.5-72B-Instruct（SiliconFlow） | 通用大模型（国产） |
| 基线5 | DeepSeek-V3（raw） | 与本文同底座但**不带流水线/不执行代码**，用于消融：验证"结构化+执行"带来的增益 |

> 说明：市面主流商用模型中 GPT-4o、Kimi、Qwen、DeepSeek 均已通过真实 API 跑通；Claude 3 / 文心一言当前无可用凭据，本文以**可复现脚本**形式给出接入方式（`shiyan/run_experiments.py` 中 `BASELINES` 增加条目即可），标注为"待执行"，不编造其数值。

## 2. 两种评测条件

- **Raw 条件**（对所有基线 + 对本文智能体的底座 DeepSeek-V3）：把自然语言问题直接给模型，要求它给出数学模型、可运行代码与解释；**代码由统一 harness 抽取并真实执行**（同样落盘子进程执行）。衡量"通用大模型直接产物"的质量。
- **Agent 条件**（仅本文系统）：走完整流水线（结构化抽取→建模→codegen→执行→解释），带执行反馈。

统一执行是关键：所有模型产出的代码都用同一个沙箱式 harness 跑，用同一 result.json 口径评判，保证公平。

## 3. 评估指标

1. **建模准确性 Modeling Accuracy**：模型/代码求得的 objective 是否等于（min 取≤、由验证器确认最优）ground truth。
   - `optimal`：objective 命中已知最优（在容差内）。
   - `feasible_suboptimal`：给出可行解但非最优。
   - `wrong/infeasible`：无解/不可行/错误。
2. **代码可运行性 Code Runnability**：抽取的代码能否在 120s 内无异常运行并写出规范 result.json（returncode==0 且含 objective）。二值。
3. **解释清晰度 Explanation Clarity**：由裁判 LLM(GPT-4o) 依据统一 rubric 对"问题理解/建模步骤/求解过程/结果解读/面向非专业读者可读性"打分 1–5（LLM-as-judge，附人工抽检）。
4. **端到端成功率**：可运行 且 命中最优。

## 4. 案例集（10 个，已独立暴力/精确验证 ground truth）

见 `shiyan/cases.json`。覆盖：背包、TSP、指派、装箱、集合覆盖、单机调度、CVRP、图着色、最大流、设施选址；难度 easy/medium/hard。
ground truth 由 `shiyan/verify_ground_truth.py` 独立计算（已修正 3 个手算错误：TSP=17.6569、指派=9、UFLP=14）。

## 5. 流程与产物

`shiyan/run_experiments.py`：
- 对每个案例 × 每个系统：调用模型 → 抽取代码 → 统一执行 → 记录 objective/runnable/耗时/原始输出。
- 逐案例产物存 `shiyan/results/<case_id>/<system>.json`（含 nl、raw_output、code、exec 日志、objective、评分）。
- 汇总 `shiyan/results/summary.csv` 与 `shiyan/results/summary.md`。
- 解释清晰度评分 `shiyan/results/clarity_scores.json`（裁判 LLM）。

## 6. 公平性与可复现
- 所有系统同一 prompt 模板、同一执行 harness、同一评判口径、temperature=0。
- 随机性来源仅模型采样；temperature=0 降低方差；每案例可重复 N 次（默认 1，脚本支持 --repeat）。
- 全部原始输出与代码落盘，可复核。
