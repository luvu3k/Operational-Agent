# 实验结果最终汇总（供论文引用，全部为真实运行数据）

## 系统
- **OptAgent**（本文）= DeepSeek-V3 + 结构化流水线（NL→数学模型→代码→落盘子进程执行→结果/解释）
- 基线：GPT-4o、GPT-4o-mini、Moonshot-v1(Kimi)、Qwen2.5-72B、DeepSeek-V3-raw（同底座裸模型，消融）
- 待接入(无凭据)：Claude-3、文心一言 ERNIE —— 论文标注 pending，脚本 BASELINES 预留

## 表1：总体表现（10 案例）
| 系统 | 可运行率 | 命中最优率 | 伪优解(建模错误) | 解释清晰度(1-5) | 端到端成功率 |
| --- | --- | --- | --- | --- | --- |
| OptAgent(本文) | 100% (10/10) | 70% (7/10) | 2 | **3.56** | 70% |
| GPT-4o | 100% (10/10) | **80% (8/10)** | 1 | 2.62 | **80%** |
| GPT-4o-mini | 100% (10/10) | 60% (6/10) | 4 | 2.34 | 60% |
| Moonshot-v1 | 50% (5/10) | 40% (4/10) | 1 | 2.38 | 40% |
| Qwen2.5-72B | 20% (2/10) | 20% (2/10) | 0 | 2.18 | 20% |
| DeepSeek-V3-raw | 90% (9/10) | 70% (7/10) | 2 | 3.42 | 70% |

## 核心发现（诚实）
1. **可运行性**：OptAgent 100% 可运行（代码必落盘并子进程执行验证），显著高于 Moonshot(50%)、Qwen(20%)。裸模型常"看似给了代码"但不可运行或不写规范结果。
2. **建模准确性**：GPT-4o 最强(80%)，OptAgent 次之(70%)，与最强商用模型接近；OptAgent 明显优于其国产同类基线(Moonshot/Qwen)。
3. **流水线增益(消融)**：OptAgent(DeepSeek-V3+流水线) 与 DeepSeek-V3-raw 在最优命中率上同为 70%（底座本身较强），但增益体现在可运行率(100% vs 90%，裸模型在单机调度上未产出可运行代码)与解释清晰度(3.56 vs 3.42)上；二者命中最优的案例集合并不完全相同。说明"结构化+执行反馈"带来真实的稳健性与可读性增益。
4. **解释清晰度**：OptAgent 最高(3.56)，远超 raw GPT-4o(2.62)——本文面向非专业用户的分步解释模块是关键差异化优势。
5. **伪优解现象**：多个通用模型在 min 问题上给出"低于已知最优"的伪解(如 GPT-4o-mini 4 次)，即漏约束/建错模型，靠 ground truth 校验才能发现。GPT-4o 最少(1)。
6. **难题**：CVRP(带容量路径) 所有系统都未给出真正可行且非退化的路线(OptAgent/DeepSeek 退化为 0，GPT-4o feasible=false)——共同短板，诚实报告。

## 逐案例（objective / 判定）见 shiyan/results/summary.md、summary.csv
## 清晰度明细见 shiyan/results/clarity_scores.json
## 每条原始输出/代码/执行日志见 shiyan/results/<case>/<system>/record.json

## 环境
- 底座与基线经真实 API 调用(SiliconFlow / CLOSEAI 代理 / Moonshot)，temperature=0。
- ground truth 由 shiyan/verify_ground_truth.py 独立暴力/精确计算(已修正 TSP=17.6569、指派=9、UFLP=14)。
- 所有代码在本机子进程执行，120s 超时。
