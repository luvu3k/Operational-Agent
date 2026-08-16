"""
从已保存的 shiyan/results/<case>/<system>/record.json 重新评分与汇总，
无需重复昂贵的 API 调用。修正评分口径：

- min 问题若 objective < 最优 - tol：判为 invalid_below_optimum（说明漏了约束/建错模型，
  给出了"看似更优实则不可行"的解），不计入 optimal，也不算普通 suboptimal。
- max 问题若 objective > 最优 + tol：同理 invalid_above_optimum。
- objective == 最优（容差内）：optimal。
- 有可行解但非最优：feasible_suboptimal。
- 无结果/不可运行：no_result。
- 无 ground truth 的案例(CVRP)：可运行且有目标即 feasible_no_gt。
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def rescore(obj, case, rec=None):
    gt = case.get("ground_truth_objective")
    if obj is None:
        return "no_result"
    if gt is None:
        # 无已知最优(如 CVRP)：要求 feasible==true 且目标为正，才算真正给出可行解；
        # 目标为 0 或空解视为退化/伪解。
        feasible_flag = bool((rec or {}).get("result", {}).get("feasible", False))
        if feasible_flag and isinstance(obj, (int, float)) and obj > 1e-9:
            return "feasible_no_gt"
        return "invalid_degenerate"
    tol = case.get("tol", 1e-6)
    if abs(obj - gt) <= tol:
        return "optimal"
    if case["sense"] == "min":
        return "invalid_below_optimum" if obj < gt - tol else "feasible_suboptimal"
    else:
        return "invalid_above_optimum" if obj > gt + tol else "feasible_suboptimal"


def main():
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))["cases"]
    systems = ["OptAgent", "GPT-4o", "GPT-4o-mini", "Moonshot-v1", "Qwen2.5-72B", "DeepSeek-V3-raw"]

    rows = {}
    for c in cases:
        for s in systems:
            rec_path = RESULTS / c["id"] / s.replace("/", "_") / "record.json"
            if not rec_path.exists():
                continue
            rec = json.loads(rec_path.read_text(encoding="utf-8"))
            rec["verdict"] = rescore(rec.get("objective"), c, rec)
            rec_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            rows[(c["id"], s)] = rec

    # 统计
    def valid_optimal(r):
        return r.get("verdict") == "optimal"

    md = ["# 实验结果汇总（已修正评分口径）\n",
          f"案例数: {len(cases)}，系统数: {len(systems)}。",
          "评分：optimal=命中已知最优；feasible_suboptimal=可行但非最优；",
          "invalid_below/above_optimum=越过最优边界(漏约束/建错模型的伪优解)；no_result=无解/不可运行。\n",
          "## 每系统总体表现\n",
          "| 系统 | 可运行率 | 命中最优率 | 伪优解(建模错误) | 端到端成功率 |",
          "| --- | --- | --- | --- | --- |"]
    stat = {}
    for s in systems:
        rs = [rows[(c["id"], s)] for c in cases if (c["id"], s) in rows]
        n = len(rs) or 1
        runnable = sum(1 for r in rs if r.get("runnable"))
        optimal = sum(1 for r in rs if valid_optimal(r))
        invalid = sum(1 for r in rs if str(r.get("verdict")).startswith("invalid"))
        e2e = sum(1 for r in rs if r.get("runnable") and valid_optimal(r))
        stat[s] = {"n": len(rs), "runnable": runnable, "optimal": optimal, "invalid": invalid, "e2e": e2e}
        md.append(f"| {s} | {runnable}/{len(rs)} ({round(100*runnable/n)}%) | {optimal}/{len(rs)} ({round(100*optimal/n)}%) "
                  f"| {invalid} | {e2e}/{len(rs)} ({round(100*e2e/n)}%) |")

    md.append("\n## 逐案例 objective（对照 ground truth）\n")
    md.append("| 案例 | 类型 | 难度 | GT | " + " | ".join(systems) + " |")
    md.append("|" + " --- |" * (len(systems) + 4))
    for c in cases:
        cells = [c["id"], c["type"], c["difficulty"], str(c.get("ground_truth_objective"))]
        for s in systems:
            r = rows.get((c["id"], s))
            if not r:
                cells.append("-")
            else:
                o = r.get("objective")
                o_str = f"{o:.4g}" if isinstance(o, (int, float)) else str(o)
                cells.append(f"{o_str}({r.get('verdict')})")
        md.append("| " + " | ".join(cells) + " |")

    (RESULTS / "summary.md").write_text("\n".join(md), encoding="utf-8")

    # CSV
    csv = ["case,type,difficulty,system,model,runnable,objective,ground_truth,verdict,elapsed_s"]
    for c in cases:
        for s in systems:
            r = rows.get((c["id"], s))
            if not r:
                continue
            csv.append(f"{c['id']},{c['type']},{c['difficulty']},{s},{r.get('model','')},"
                       f"{r.get('runnable')},{r.get('objective')},{r.get('ground_truth')},"
                       f"{r.get('verdict')},{r.get('elapsed_s','')}")
    (RESULTS / "summary.csv").write_text("\n".join(csv), encoding="utf-8")

    (RESULTS / "stats.json").write_text(json.dumps(stat, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已重评分并写入 summary.md / summary.csv / stats.json")
    print(json.dumps(stat, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
