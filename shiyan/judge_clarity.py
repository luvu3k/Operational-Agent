"""
用裁判 LLM(GPT-4o) 对各系统在每个案例上的"解释清晰度"按统一 rubric 打分 1-5。
只对有解释文本的记录打分；结果写 shiyan/results/clarity_scores.json 与并入 summary。
LLM-as-judge，附少量人工抽检。
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT))
RESULTS = ROOT / "results"

for line in (PROJECT / ".env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

from llm.client import LLM  # noqa: E402

RUBRIC = """你是运筹优化教学专家。请对下面这段"面向非专业用户的问题解释"按 5 个维度打分(每项1-5)，
并给出总分(1-5 的加权平均，保留一位小数)。只输出 JSON：
{"problem_understanding":x,"modeling_steps":x,"solving_process":x,"result_interpretation":x,"readability_for_nonexpert":x,"overall":x}
维度：问题理解是否准确；建模步骤是否清楚；求解过程是否说明；结果解读是否到位；对非专业读者是否通俗易懂。
若解释为空或与问题无关，overall 记 1。"""


def judge(explanation, nl):
    if not explanation or len(explanation.strip()) < 10:
        return {"overall": 1.0, "note": "empty_or_too_short"}
    llm = LLM(model="gpt-4o", api_key=os.environ.get("CLOSEAI_API_KEY"), base_url=os.environ.get("CLOSEAI_BASE_URL"))
    prompt = f"【问题】{nl}\n\n【待评解释】\n{explanation[:2500]}"
    try:
        r = llm.simple_chat(prompt, system_prompt=RUBRIC, temperature=0, max_tokens=300)
        txt = r.content
        import re
        m = re.search(r"\{[\s\S]*\}", txt)
        return json.loads(m.group(0)) if m else {"overall": None, "raw": txt[:200]}
    except Exception as e:
        return {"overall": None, "error": str(e)[:150]}


def main():
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))["cases"]
    systems = ["OptAgent", "GPT-4o", "GPT-4o-mini", "Moonshot-v1", "Qwen2.5-72B", "DeepSeek-V3-raw"]
    scores = {}
    for c in cases:
        for s in systems:
            rec_path = RESULTS / c["id"] / s.replace("/", "_") / "record.json"
            if not rec_path.exists():
                continue
            rec = json.loads(rec_path.read_text(encoding="utf-8"))
            expl = rec.get("explanation", "")
            sc = judge(expl, c["nl"])
            scores[f"{c['id']}::{s}"] = sc
            print(f"{c['id']} × {s}: overall={sc.get('overall')}", flush=True)
    (RESULTS / "clarity_scores.json").write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8")

    # 每系统平均分
    agg = {}
    for s in systems:
        vals = [v.get("overall") for k, v in scores.items() if k.endswith("::" + s) and isinstance(v.get("overall"), (int, float))]
        agg[s] = round(sum(vals) / len(vals), 2) if vals else None
    (RESULTS / "clarity_avg.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== 各系统解释清晰度平均分 ===")
    print(json.dumps(agg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
