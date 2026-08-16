"""
实验运行器：对 10 个组合优化案例，对比"本文智能体(OptAgent)"与多个通用大模型基线在
建模准确性 / 代码可运行性 / 端到端成功率上的表现。

设计要点（保证公平与真实）：
- 统一 prompt 模板、统一代码执行 harness、统一 result.json 口径、temperature=0。
- 所有模型（含基线）产出的代码都被真实抽取并在子进程中执行；不臆测任何数值。
- OptAgent 走本项目 general_solver_tool（结构化流水线+执行）。
- 基线走 raw：同一 prompt 直接问模型，抽取代码执行。
- 每个案例 × 系统的原始输出、代码、执行日志、评分逐一落盘到 shiyan/results/。

用法：
    PYTHONPATH=. python3 shiyan/run_experiments.py                # 跑全部
    PYTHONPATH=. python3 shiyan/run_experiments.py --systems OptAgent GPT-4o
    PYTHONPATH=. python3 shiyan/run_experiments.py --cases C01_knapsack C02_tsp
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT))

from llm.client import LLM  # noqa: E402
from tools.general_solver_tool import _split_sections, run_general_solver  # noqa: E402

RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


def _load_env():
    for line in (PROJECT / ".env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip().strip('"'))


_load_env()

# 基线系统定义：(名称, model, api_key_env, base_url_env)。key/url 为 None 表示用默认 LLM_* 环境。
BASELINES = {
    "GPT-4o": ("gpt-4o", "CLOSEAI_API_KEY", "CLOSEAI_BASE_URL"),
    "GPT-4o-mini": ("gpt-4o-mini", "CLOSEAI_API_KEY", "CLOSEAI_BASE_URL"),
    "Moonshot-v1": ("moonshot-v1-8k", "MOONSHOT_API_KEY", "MOONSHOT_BASE_URL"),
    "Qwen2.5-72B": ("Qwen/Qwen2.5-72B-Instruct", "SILICON_API_KEY", "SILICON_BASE_URL"),
    "DeepSeek-V3-raw": ("deepseek-ai/DeepSeek-V3", "SILICON_API_KEY", "SILICON_BASE_URL"),
    # 待接入（无可用凭据时留空，脚本会跳过并在报告中标注 pending）：
    # "Claude-3": ("claude-3-5-sonnet", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"),
    # "ERNIE-4.0": ("ernie-4.0", "WENXIN_API_KEY", "WENXIN_BASE_URL"),
}

# 与 general_solver_tool 一致的 raw prompt（让基线也产出 模型/代码/解释 三段）。
RAW_SYSTEM_PROMPT = (
    "你是一名运筹优化专家兼 Python 工程师。用户会用自然语言描述一个组合优化问题。"
    "请严格输出三段，用 ===MODEL===、===CODE===、===EXPLANATION=== 分隔。"
    "MODEL 给数学模型；CODE 给完整可直接运行的 Python 代码(仅用标准库或 pulp/numpy，"
    "把结果写入 result.json，路径取环境变量 RESULT_PATH，至少含 objective/solution/feasible)；"
    "EXPLANATION 面向非专业读者分步解释。"
)


def extract_number(sol: dict, key="objective"):
    v = sol.get(key)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def score_objective(obj, case):
    gt = case.get("ground_truth_objective")
    if obj is None:
        return "no_result"
    if gt is None:
        return "feasible_no_gt"  # 如 CVRP 只判可行
    tol = case.get("tol", 1e-6)
    if abs(obj - gt) <= tol:
        return "optimal"
    if case["sense"] == "min" and obj > gt + tol:
        return "feasible_suboptimal"
    if case["sense"] == "max" and obj < gt - tol:
        return "feasible_suboptimal"
    return "feasible_suboptimal"


def run_code(code: str, workdir: Path, timeout=120):
    """把代码落盘并执行，返回 (returncode, stdout, stderr, result_dict)。"""
    workdir.mkdir(parents=True, exist_ok=True)
    result_path = workdir / "result.json"
    if result_path.exists():
        result_path.unlink()
    header = f"import os as _os\n_os.environ.setdefault('RESULT_PATH', {str(result_path)!r})\n"
    code_path = workdir / "generated.py"
    code_path.write_text(header + code, encoding="utf-8")
    try:
        proc = subprocess.run([sys.executable, str(code_path)], cwd=str(workdir),
                              capture_output=True, text=True, timeout=timeout)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        rc, out, err = -1, "", "TIMEOUT"
    result = {}
    if result_path.exists():
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception:
            result = {}
    return rc, out, err, result


def run_baseline(system, model_cfg, case, outdir):
    model, key_env, url_env = model_cfg
    key = os.environ.get(key_env) if key_env else None
    url = os.environ.get(url_env) if url_env else None
    t0 = time.time()
    try:
        llm = LLM(model=model, api_key=key, base_url=url)
        resp = llm.simple_chat(case["nl"], system_prompt=RAW_SYSTEM_PROMPT, temperature=0, max_tokens=2400)
        raw = resp.content
        err_msg = ""
    except Exception as e:
        raw, err_msg = "", f"{type(e).__name__}: {e}"
    elapsed = round(time.time() - t0, 2)

    sections = _split_sections(raw) if raw else {"model": "", "code": "", "explanation": ""}
    rc, out, err, result = (-1, "", err_msg or "no_code", {})
    if sections["code"]:
        rc, out, err, result = run_code(sections["code"], outdir / "run")
    runnable = (rc == 0 and "objective" in result)
    obj = extract_number(result)
    verdict = score_objective(obj, case)
    return {
        "system": system, "model": model, "case": case["id"], "nl": case["nl"],
        "math_model": sections["model"], "code": sections["code"], "explanation": sections["explanation"],
        "raw_output": raw, "elapsed_s": elapsed, "returncode": rc,
        "stdout": out[:800], "stderr": err[:800], "result": result,
        "objective": obj, "ground_truth": case.get("ground_truth_objective"),
        "runnable": runnable, "verdict": verdict,
    }


def run_optagent(case):
    t0 = time.time()
    spec = {"skill_name": case["type"], "user_input": case["nl"], "description": case["name"]}
    res = run_general_solver(spec)
    elapsed = round(time.time() - t0, 2)
    sol = res.get("solution", {})
    obj = extract_number(sol)
    runnable = res.get("status") == "success"
    verdict = score_objective(obj, case)
    return {
        "system": "OptAgent", "model": res.get("model_name"), "case": case["id"], "nl": case["nl"],
        "math_model": res.get("math_model", ""), "code": res.get("generated_code", ""),
        "explanation": res.get("explanation", ""), "raw_output": res.get("raw_output", ""),
        "elapsed_s": elapsed, "returncode": res.get("execution", {}).get("returncode"),
        "stdout": str(res.get("execution", {}).get("stdout", ""))[:800], "stderr": "",
        "result": sol, "objective": obj, "ground_truth": case.get("ground_truth_objective"),
        "runnable": runnable, "verdict": verdict,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", nargs="*", default=["OptAgent"] + list(BASELINES.keys()))
    ap.add_argument("--cases", nargs="*", default=None)
    args = ap.parse_args()

    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))["cases"]
    if args.cases:
        cases = [c for c in cases if c["id"] in args.cases]

    rows = []
    for case in cases:
        cdir = RESULTS / case["id"]
        cdir.mkdir(parents=True, exist_ok=True)
        for system in args.systems:
            print(f"[RUN] {case['id']} × {system} ...", flush=True)
            outdir = cdir / system.replace("/", "_")
            outdir.mkdir(parents=True, exist_ok=True)
            try:
                if system == "OptAgent":
                    rec = run_optagent(case)
                else:
                    rec = run_baseline(system, BASELINES[system], case, outdir)
            except Exception as e:
                rec = {"system": system, "case": case["id"], "runnable": False,
                       "verdict": "error", "objective": None, "stderr": str(e)[:400],
                       "ground_truth": case.get("ground_truth_objective")}
            (outdir / "record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            rows.append(rec)
            print(f"      -> runnable={rec.get('runnable')} obj={rec.get('objective')} "
                  f"gt={rec.get('ground_truth')} verdict={rec.get('verdict')}", flush=True)

    # 汇总
    write_summary(rows, cases, args.systems)


def write_summary(rows, cases, systems):
    by = {(r["case"], r["system"]): r for r in rows}
    # CSV
    lines = ["case,system,model,runnable,objective,ground_truth,verdict,elapsed_s"]
    for c in cases:
        for s in systems:
            r = by.get((c["id"], s))
            if not r:
                continue
            lines.append(f"{c['id']},{s},{r.get('model','')},{r.get('runnable')},{r.get('objective')},"
                         f"{r.get('ground_truth')},{r.get('verdict')},{r.get('elapsed_s','')}")
    (RESULTS / "summary.csv").write_text("\n".join(lines), encoding="utf-8")

    # Markdown 汇总 + 每系统统计
    md = ["# 实验结果汇总\n", f"案例数: {len(cases)}，系统数: {len(systems)}\n"]
    md.append("## 每系统总体表现\n")
    md.append("| 系统 | 可运行率 | 命中最优率 | 端到端成功(可运行且最优) |")
    md.append("| --- | --- | --- | --- |")
    for s in systems:
        rs = [by[(c["id"], s)] for c in cases if (c["id"], s) in by]
        n = len(rs) or 1
        runnable = sum(1 for r in rs if r.get("runnable"))
        optimal = sum(1 for r in rs if r.get("verdict") == "optimal")
        e2e = sum(1 for r in rs if r.get("runnable") and r.get("verdict") == "optimal")
        md.append(f"| {s} | {runnable}/{len(rs)} ({100*runnable//n}%) | {optimal}/{len(rs)} ({100*optimal//n}%) | {e2e}/{len(rs)} ({100*e2e//n}%) |")
    md.append("\n## 逐案例 objective（对照 ground truth）\n")
    header = "| 案例 | GT | " + " | ".join(systems) + " |"
    md.append(header)
    md.append("| " + " --- |" * (len(systems) + 2))
    for c in cases:
        cells = [c["id"], str(c.get("ground_truth_objective"))]
        for s in systems:
            r = by.get((c["id"], s))
            cells.append(f"{r.get('objective')}({r.get('verdict','-')})" if r else "-")
        md.append("| " + " | ".join(cells) + " |")
    (RESULTS / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n=== 汇总已写入 shiyan/results/summary.md 与 summary.csv ===")
    print("\n".join(md[:12]))


if __name__ == "__main__":
    main()
