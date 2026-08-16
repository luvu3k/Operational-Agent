# shiyan/ —— 实验数据与对比结果

本文实验的全部资料，按案例分类整理。所有数字均来自\*\*真实运行\*\*（真实 API 调用 + 真实代码执行），无编造。

## 目录结构
```
shiyan/
├── cases.json              10 个组合优化案例定义（自然语言 + 类型/难度 + 独立校验的参考最优值）
├── PROTOCOL.md             实验设计与评估协议（被测系统、基线、指标、公平性）
├── verify_ground_truth.py  独立暴力/精确算法校验各案例最优值（用于纠正真值）
├── run_experiments.py      主实验：每案例 × 每系统 调模型→抽代码→统一执行→评分
├── rescore.py              从已存记录重评分（修正"伪优解/退化解"判定），无需重跑
├── judge_clarity.py        GPT-4o 裁判对"解释清晰度"打分(1-5)
├── FINAL_RESULTS.md        论文引用的最终汇总与核心发现（诚实）
├── logs/                   运行日志（full_run.log / clarity.log）
└── results/
    ├── summary.md          总体表现表 + 逐案例目标值对照表
    ├── summary.csv          机器可读汇总
    ├── stats.json           每系统统计
    ├── clarity_avg.json     每系统解释清晰度平均分
    ├── clarity_scores.json  逐条清晰度评分明细
    └── C01_knapsack/ ... C10_facility_location/     ← 按案例分类
        └── <系统名>/record.json    每个系统在该案例上的完整记录
              （含 自然语言输入 / 数学模型 / 生成代码 / 执行日志 / 目标值 / 判定）
```

## 被测系统
- **OptAgent（本文）**：DeepSeek-V3 + 结构化流水线（建模→代码→落盘执行→解释）。
- 基线：GPT-4o、GPT-4o-mini、Moonshot-v1(Kimi)、Qwen2.5-72B、DeepSeek-V3-raw（同底座裸模型，消融）。
- 待接入：Claude-3、文心一言（无可用凭据；`run_experiments.py` 的 `BASELINES` 已预留接口，补 key 即可跑）。

## 如何复现
```bash
cd /Applications/yhy/Operational_Agent
export PYTHONPATH=$PWD
python3 shiyan/verify_ground_truth.py      # 校验真值
python3 shiyan/run_experiments.py          # 全量对比实验（真实 API + 执行，约 10-20 分钟）
python3 shiyan/rescore.py                  # 重评分并生成 summary
python3 shiyan/judge_clarity.py            # 解释清晰度评分
# 也可只跑部分：python3 shiyan/run_experiments.py --cases C01_knapsack --systems OptAgent GPT-4o
```

## 核心结论（详见 FINAL_RESULTS.md）
- 可运行率：OptAgent 100%，与 GPT-4o 并列最高。
- 最优命中率：GPT-4o 80% ＞ OptAgent 70% ＞ 其余基线；OptAgent 明显优于国产同类基线。
- 解释清晰度：OptAgent 3.56（最高），高于裸 GPT-4o（2.62）。
- 消融：OptAgent(DeepSeek-V3+流水线) 70% ＞ DeepSeek-V3-raw 60%，验证流水线增益。
- 共同短板：CVRP 等强约束路径问题所有系统均未给出真正可行非退化解，诚实报告。
