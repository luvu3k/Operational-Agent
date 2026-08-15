# Examples

## 示例 1：论文算例（精确 + Gurobi）

输入：
```
请用精确算法（Gurobi）求解远海岛礁应急补给的多仓库车辆路径问题（MDVRPTW-P），
3 个保障中心、22 个无人机起飞点，带时间窗和优先级约束，目标是最小化总航行时间加优先级惩罚。
使用论文默认算例数据。
```
预期：solver_preference=exact，solver_backend=gurobi，objective≈82.64（最优），8 条路径。

## 示例 2：论文算例（遗传算法）

输入：把上例“精确算法/Gurobi”改为“遗传算法”即可。
预期：solver_preference=heuristic，得到可行解 objective≈86（gap≈4%），并给出路线图与甘特图。

## 示例 3：自定义算例

输入中附带 JSON：
```json
{
  "depots": [{"id": 0, "x": 0, "y": 0}, {"id": 1, "x": 100, "y": 50}],
  "launch_points": [
    {"id": 2, "x": 20, "y": 30, "priority": 10, "latest": 40},
    {"id": 3, "x": 80, "y": 10, "priority": 25, "latest": 30}
  ],
  "params": {"v1": 40, "service_time": 0.5, "max_vehicles_per_depot": 4, "priority_penalty_L": 1.0}
}
```
系统会归一化该实例并按所选方法求解。
