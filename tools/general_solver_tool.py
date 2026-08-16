"""
作用：
- 通用组合优化求解工具：面向任意自然语言描述的组合优化问题（TSP/背包/指派/调度/VRP 等），
  由 LLM 依据结构化流程产出 (1) 数学模型 (2) 可运行 Python 求解代码 (3) 分步解释，
  然后把代码落盘、子进程执行、解析结果，形成"建模→代码→执行→解释"的完整闭环。
- 这是本项目从"单一 MDVRPTW 模板"升级为"通用问题族"的核心工具，也是论文实验的被测系统。

调用关系：
- 被 `tools.tool_registry` 通过 `@tool` 自动扫描注册。
- 被 `core.react_agent`、实验脚本 `shiyan/` 调用。
- 复用 `llm.client.LLM`（默认 DeepSeek-V3）与 `solver.artifact_store` 落盘执行能力。
"""

from __future__ import annotations

import re
from typing import Dict

from solver.artifact_store import (
    create_run_artifact,
    read_json,
    run_python_file,
    save_execution_logs,
    write_json,
    write_text,
)
from tools.tool_registry import tool

# 让 LLM 输出严格分区的三段：MODEL / CODE / EXPLANATION。
_SYSTEM_PROMPT = """你是一名运筹优化专家兼 Python 工程师。用户会用自然语言描述一个组合优化问题。
你的任务是把它转化为可执行的求解方案，严格输出三个部分，用如下标记分隔：

===MODEL===
（用简洁文字给出数学模型：决策变量、目标函数、约束。可用 LaTeX 风格但保持纯文本。）

===CODE===
```python
# 完整、自包含、可直接运行的 Python 代码。
# 硬性要求：
# 1. 若问题规模小，优先用精确方法（如 pulp / 暴力 / 动态规划 / 匈牙利算法）确保最优；
#    大规模可用启发式，但必须给出可行解。
# 2. 只能使用 Python 标准库，或以下已安装库：pulp、numpy。不要使用 gurobi、ortools 等未必安装的库。
# 3. 必须在最后把结果写入 result.json，路径由环境变量 RESULT_PATH 指定（若无则用 "result.json"）。
#    result.json 至少包含：{"objective": <数值>, "solution": <可读的解>, "feasible": true/false}。
# 4. 同时用 print 输出关键结果，便于日志查看。
# 5. 代码不得依赖任何外部输入文件，所有数据内联在代码里。
```

===EXPLANATION===
（面向非运筹专业读者的分步解释：这个问题是什么、模型怎么建、代码怎么解、结果如何解读。用中文，通俗清晰。）

务必输出这三个标记段，不要有多余内容。"""


def _split_sections(text: str) -> Dict[str, str]:
    """把 LLM 输出按 ===MODEL===/===CODE===/===EXPLANATION=== 切分。"""
    sections = {"model": "", "code": "", "explanation": ""}
    model_m = re.search(r"===MODEL===(.*?)(?:===CODE===|$)", text, re.DOTALL)
    code_m = re.search(r"===CODE===(.*?)(?:===EXPLANATION===|$)", text, re.DOTALL)
    expl_m = re.search(r"===EXPLANATION===(.*)$", text, re.DOTALL)
    if model_m:
        sections["model"] = model_m.group(1).strip()
    if code_m:
        raw = code_m.group(1).strip()
        fence = re.search(r"```(?:python)?\s*([\s\S]*?)```", raw)
        sections["code"] = (fence.group(1) if fence else raw).strip()
    if expl_m:
        sections["explanation"] = expl_m.group(1).strip()
    # 兜底：整段找 python 代码块
    if not sections["code"]:
        fence = re.search(r"```(?:python)?\s*([\s\S]*?)```", text)
        if fence:
            sections["code"] = fence.group(1).strip()
    return sections


def _inject_result_path(code: str, result_path: str) -> str:
    """在代码顶部注入 RESULT_PATH 环境变量，确保 result.json 落到本次运行目录。"""
    header = (
        "import os as _os\n"
        f"_os.environ.setdefault('RESULT_PATH', {result_path!r})\n"
    )
    return header + code


@tool(
    name="general_optimization_solver",
    description="面向任意自然语言描述的组合优化问题(TSP/背包/指派/调度/VRP等)，由LLM生成数学模型、可运行求解代码与分步解释，并落盘执行返回结果。",
    input_schema={
        "type": "object",
        "properties": {
            "problem_spec": {"type": "object", "description": "结构化问题定义，至少含 user_input/description。"}
        },
        "required": ["problem_spec"],
    },
    aliases=["@general", "@gen"],
    tags=["solver", "general", "codegen"],
)
def run_general_solver(problem_spec: dict) -> dict:
    """LLM 建模+生成代码+解释 -> 落盘执行 -> 解析结果。"""
    from llm.client import LLM

    user_input = str(problem_spec.get("user_input") or problem_spec.get("description") or "")
    task_name = str(problem_spec.get("skill_name") or "general_opt")

    if not user_input.strip():
        return {"status": "error", "selected_solver": "general_optimization_solver",
                "message": "缺少问题描述 user_input。", "solution": {"feasible": False}}

    # 1) 调 LLM 产出三段。
    try:
        llm = LLM()
        model_name = llm.model
        resp = llm.simple_chat(user_input, system_prompt=_SYSTEM_PROMPT, temperature=0, max_tokens=2400)
        raw_output = resp.content
    except Exception as exc:
        return {"status": "error", "selected_solver": "general_optimization_solver",
                "message": f"LLM 调用失败: {exc}", "solution": {"feasible": False}}

    sections = _split_sections(raw_output)
    if not sections["code"]:
        return {"status": "error", "selected_solver": "general_optimization_solver",
                "message": "LLM 未产出可执行代码。", "raw_output": raw_output,
                "math_model": sections["model"], "solution": {"feasible": False}}

    # 2) 落盘并执行。
    artifact = create_run_artifact(task_name, "general_llm")
    runnable = _inject_result_path(sections["code"], str(artifact.result_path))
    write_json(artifact.problem_spec_path, {"problem_spec": problem_spec, "model_name": model_name})
    write_text(artifact.code_path, runnable)
    write_text(artifact.run_dir / "math_model.md", sections["model"])
    write_text(artifact.answer_path, sections["explanation"])

    execution = run_python_file(artifact.code_path, cwd=artifact.run_dir, timeout=120)
    save_execution_logs(artifact, execution)
    solution = read_json(artifact.result_path)

    ran_ok = execution.get("returncode") == 0
    has_result = isinstance(solution, dict) and "objective" in solution
    status = "success" if (ran_ok and has_result) else "error"

    if status != "success" and "message" not in solution:
        solution = {"feasible": False, "message": "生成代码执行失败或未写出 result.json。",
                    "stderr": execution.get("stderr", "")[:1000]}

    return {
        "mode": "general_llm",
        "status": status,
        "selected_solver": "general_optimization_solver",
        "message": (f"已完成通用求解：目标值 {solution.get('objective')}。" if status == "success"
                    else "通用求解未成功，详见 stderr。"),
        "model_name": model_name,
        "problem_spec": problem_spec,
        "math_model": sections["model"],
        "explanation": sections["explanation"],
        "generated_code": runnable,
        "raw_output": raw_output,
        "artifact": artifact.to_dict(),
        "code_path": str(artifact.code_path),
        "result_path": str(artifact.result_path),
        "answer_path": str(artifact.answer_path),
        "execution": {"returncode": execution.get("returncode"), "stdout": execution.get("stdout", "")[:500]},
        "solution": solution,
    }


if __name__ == "__main__":
    print("=== general_solver_tool.py 本地测试 ===")
    spec = {
        "skill_name": "knapsack",
        "user_input": "有3件物品，重量分别是2、3、4，价值分别是3、4、5，背包容量是5，求能装入的最大总价值。",
        "description": "0/1 背包问题",
    }
    result = run_general_solver(spec)
    print(f"status={result['status']} | model={result.get('model_name')}")
    print(f"objective={result['solution'].get('objective')} | feasible={result['solution'].get('feasible')}")
    print(f"code_path={result.get('code_path')}")
