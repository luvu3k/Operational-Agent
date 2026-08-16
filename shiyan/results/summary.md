# 实验结果汇总（已修正评分口径）

案例数: 10，系统数: 6。
评分：optimal=命中已知最优；feasible_suboptimal=可行但非最优；
invalid_below/above_optimum=越过最优边界(漏约束/建错模型的伪优解)；no_result=无解/不可运行。

## 每系统总体表现

| 系统 | 可运行率 | 命中最优率 | 伪优解(建模错误) | 端到端成功率 |
| --- | --- | --- | --- | --- |
| OptAgent | 10/10 (100%) | 7/10 (70%) | 2 | 7/10 (70%) |
| GPT-4o | 10/10 (100%) | 8/10 (80%) | 1 | 8/10 (80%) |
| GPT-4o-mini | 10/10 (100%) | 6/10 (60%) | 4 | 6/10 (60%) |
| Moonshot-v1 | 5/10 (50%) | 4/10 (40%) | 1 | 4/10 (40%) |
| Qwen2.5-72B | 2/10 (20%) | 2/10 (20%) | 0 | 2/10 (20%) |
| DeepSeek-V3-raw | 9/10 (90%) | 7/10 (70%) | 2 | 7/10 (70%) |

## 逐案例 objective（对照 ground truth）

| 案例 | 类型 | 难度 | GT | OptAgent | GPT-4o | GPT-4o-mini | Moonshot-v1 | Qwen2.5-72B | DeepSeek-V3-raw |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_knapsack | knapsack | easy | 26 | 26(optimal) | 26(optimal) | 26(optimal) | 26(optimal) | None(no_result) | 26(optimal) |
| C02_tsp | tsp | medium | 17.6569 | 0(invalid_below_optimum) | 17.66(optimal) | 17.66(optimal) | None(no_result) | None(no_result) | 17.66(optimal) |
| C03_assignment | assignment | easy | 9 | 9(optimal) | 9(optimal) | 9(optimal) | 9(optimal) | None(no_result) | 9(optimal) |
| C04_bin_packing | bin_packing | medium | 2 | 2(optimal) | 2(optimal) | 1(invalid_below_optimum) | 2(optimal) | None(no_result) | 2(optimal) |
| C05_set_cover | set_cover | medium | 2 | 2(optimal) | 2(optimal) | 2(optimal) | 2(optimal) | 2(optimal) | 2(optimal) |
| C06_job_scheduling | scheduling | medium | 2 | 20(feasible_suboptimal) | 3(feasible_suboptimal) | 2(optimal) | None(no_result) | None(no_result) | None(no_result) |
| C07_cvrp | vrp | hard | None | 0(invalid_degenerate) | 20.47(invalid_degenerate) | 0(invalid_degenerate) | None(no_result) | None(no_result) | 0(invalid_degenerate) |
| C08_graph_coloring | graph_coloring | medium | 3 | 3(optimal) | 3(optimal) | 1(invalid_below_optimum) | None(no_result) | None(no_result) | 0(invalid_below_optimum) |
| C09_max_flow | max_flow | medium | 15 | 15(optimal) | 15(optimal) | 20(invalid_above_optimum) | 20(invalid_above_optimum) | None(no_result) | 15(optimal) |
| C10_facility_location | facility_location | hard | 14 | 14(optimal) | 14(optimal) | 14(optimal) | None(no_result) | 14(optimal) | 14(optimal) |