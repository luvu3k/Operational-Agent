"""
MDVRPTW-P 求解包（带时间窗与优先级约束的多仓库车辆路径问题）。

来源：从论文《基于知识引导的多智能体DRL求解远海岛礁应急物资补给规划》抽象而来，
经 experiments/mdvrptw 验证：Gurobi 精确解与遗传算法解口径一致、GA gap≈4%。

对外接口：
- presets.paper_instance() / normalize_instance(dict)：构建/归一化实例。
- model.evaluate_solution：唯一目标评估口径。
- exact.solve_exact：Gurobi 精确求解。
- genetic.solve_genetic：记忆式遗传算法求解。
- viz.build_visualizations：路线图 + 甘特图 SVG。
- codegen.build_standalone_script：生成可独立运行的完整求解脚本。
"""
