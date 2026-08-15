"""
作用：
- 从用户自然语言中抽取组合优化建模所需的结构化字段，包括背景、集合、参数、决策变量、目标函数、约束、
  求解偏好、求解后端和实例数据。
- 采用“LLM few-shot 主抽取 + 规则兜底 + 归一化”的混合策略：优先让 LLM 返回严格 JSON，
  失败时回退到正则规则抽取，最后统一归一化为 `ExtractedProblem` 结构。

调用关系：
- 被 `core.problem_builder` 调用，将自然语言解析结果合并进 `ProblemSpec`。
- 调用 `llm.client.LLM` 完成 few-shot 结构化抽取（无可用模型时自动降级）。
- 可被未来的 `skills`、`rag`、`memory` 模块复用，用于把技能模板、检索数据和历史经验统一转换为结构化建模信息。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExtractedProblem:
    background: str = ""
    sets: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, str] = field(default_factory=dict)
    decision_variables: Dict[str, str] = field(default_factory=dict)
    objectives: List[str] = field(default_factory=list)
    hard_constraints: List[str] = field(default_factory=list)
    soft_constraints: List[str] = field(default_factory=list)
    solver_preference: str = "auto"
    solver_backend: str = "auto"
    instance_data: Dict[str, Any] = field(default_factory=dict)
    missing_data_hints: List[str] = field(default_factory=list)
    extraction_source: str = "rule"

    def to_dict(self) -> Dict[str, Any]:
        """转换为普通字典，便于合并进 `ProblemSpec`。"""
        return asdict(self)


# ---------------------------------------------------------------------------
# 规则抽取（兜底层）
# ---------------------------------------------------------------------------
def _split_items(text: str) -> List[str]:
    """按中文/英文分隔符拆分同一行里的多个建模条目。"""
    cleaned = text.strip().strip("：:")
    if not cleaned:
        return []
    return [item.strip(" -") for item in re.split(r"[；;\n]", cleaned) if item.strip(" -")]


def _extract_json_block(user_input: str) -> Dict[str, Any]:
    """提取自然语言中的 ```json ... ``` 数据块。"""
    match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", user_input, re.IGNORECASE)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _line_value(line: str) -> str:
    """提取 `字段：内容` 或 `field: content` 中冒号后的内容。"""
    if "：" in line:
        return line.split("：", 1)[1].strip()
    if ":" in line:
        return line.split(":", 1)[1].strip()
    return ""


def _parse_key_value_items(value: str) -> Dict[str, str]:
    """
    将 `x[d,i] 表示运输量；y[i] 表示是否服务` 这类文本解析为字典。
    解析失败时也保留原文，避免信息丢失。
    """
    result: Dict[str, str] = {}
    for item in _split_items(value):
        if "表示" in item:
            key, desc = item.split("表示", 1)
            result[key.strip()] = desc.strip()
        elif "=" in item:
            key, desc = item.split("=", 1)
            result[key.strip()] = desc.strip()
        else:
            result[item] = item
    return result


def detect_solver_preference(user_input: str) -> str:
    """识别用户偏向精确算法还是启发式算法。"""
    text = user_input.lower()
    if any(keyword in text for keyword in ["启发式", "heuristic", "遗传算法", "禁忌搜索", "模拟退火", "局部搜索", "贪心"]):
        return "heuristic"
    if any(keyword in text for keyword in ["精确", "exact", "milp", "mip", "整数规划", "线性规划", "求解器"]):
        return "exact"
    return "auto"


def detect_solver_backend(user_input: str) -> str:
    """识别用户指定的求解器后端。"""
    text = user_input.lower()
    if any(keyword in text for keyword in ["gurobi", "gurobipy", "gorubi"]):
        return "gurobi"
    if "cplex" in text:
        return "cplex"
    if "ortools" in text or "or-tools" in text:
        return "ortools"
    if "pulp" in text or "cbc" in text:
        return "pulp"
    return "auto"


def infer_missing_data_hints(instance_data: Dict[str, Any]) -> List[str]:
    """根据当前岛礁补给模板推断缺失的关键数据。"""
    required_keys = {
        "depots": "仓库数据 depots，至少包含 name 和 supply。",
        "islands": "岛礁需求数据 islands，至少包含 name 和 demand。",
        "routes": "航线数据 routes，至少包含 from、to、cost/time 和 capacity。",
    }
    return [message for key, message in required_keys.items() if not instance_data.get(key)]


def rule_extract_problem(user_input: str) -> ExtractedProblem:
    """纯规则抽取：适用于半结构化输入或 LLM 不可用时的兜底。"""
    extracted = ExtractedProblem(extraction_source="rule")
    extracted.solver_preference = detect_solver_preference(user_input)
    extracted.solver_backend = detect_solver_backend(user_input)
    extracted.instance_data = _extract_json_block(user_input)
    extracted.missing_data_hints = infer_missing_data_hints(extracted.instance_data)

    for raw_line in user_input.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        value = _line_value(line)
        if not value:
            continue
        if line.startswith("背景") or lowered.startswith("background"):
            extracted.background = value
        elif line.startswith("集合") or lowered.startswith("sets"):
            extracted.sets.update(_parse_key_value_items(value))
        elif line.startswith("参数") or lowered.startswith("parameters"):
            extracted.parameters.update(_parse_key_value_items(value))
        elif line.startswith("决策变量") or lowered.startswith("decision"):
            extracted.decision_variables.update(_parse_key_value_items(value))
        elif line.startswith("目标") or lowered.startswith("objective"):
            extracted.objectives.extend(_split_items(value))
        elif line.startswith("硬约束") or line.startswith("约束") or lowered.startswith("constraint"):
            extracted.hard_constraints.extend(_split_items(value))
        elif line.startswith("软约束") or lowered.startswith("soft"):
            extracted.soft_constraints.extend(_split_items(value))

    return extracted


# ---------------------------------------------------------------------------
# LLM few-shot 抽取（主抽取层）
# ---------------------------------------------------------------------------
_EXTRACTION_SYSTEM_PROMPT = """你是组合优化建模信息抽取器。
你的任务不是求解问题，而是从用户输入中提取结构化建模信息，输出给下游求解器使用。

严格要求：
1. 只能输出一个 JSON 对象，不要输出任何解释文字或 Markdown 代码块标记。
2. 如果某类信息缺失，返回空字符串、空对象或空数组，绝对不要编造数值。
3. 如果用户提供了具体数据（仓库、需求、航线等），把它放进 instance_data；否则 instance_data 为空对象。
4. solver_preference 只能取 "exact"、"heuristic" 或 "auto"。
5. solver_backend 只能取 "gurobi"、"pulp"、"ortools"、"cplex" 或 "auto"。

输出 JSON 字段：
{
  "background": "问题背景一句话",
  "sets": {"集合符号": "集合含义"},
  "parameters": {"参数符号": "参数含义"},
  "decision_variables": {"变量符号": "变量含义"},
  "objectives": ["目标函数自然语言或表达式"],
  "hard_constraints": ["硬约束"],
  "soft_constraints": ["软约束"],
  "solver_preference": "exact|heuristic|auto",
  "solver_backend": "gurobi|pulp|ortools|cplex|auto",
  "instance_data": {},
  "missing_data_hints": ["还需要补充的数据"]
}"""

_FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": "帮我用精确算法和gurobi求解岛礁补给问题，两个仓库给三个岛礁送物资，目标是最小化总运输成本，要满足每个岛礁需求且不超过航线容量。",
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "background": "两个仓库向三个岛礁进行应急物资补给。",
                "sets": {"D": "仓库集合", "I": "岛礁集合", "R": "可用航线集合"},
                "parameters": {
                    "supply[d]": "仓库 d 的库存",
                    "demand[i]": "岛礁 i 的需求",
                    "cost[d,i]": "航线 d->i 的单位运输成本",
                    "capacity[d,i]": "航线 d->i 的最大运输量",
                },
                "decision_variables": {"x[d,i]": "从仓库 d 运往岛礁 i 的物资数量"},
                "objectives": ["minimize sum(cost[d,i] * x[d,i] for (d,i) in R)"],
                "hard_constraints": [
                    "每个仓库发出量不超过库存",
                    "每个岛礁收到量满足需求",
                    "每条航线运输量不超过容量",
                ],
                "soft_constraints": [],
                "solver_preference": "exact",
                "solver_backend": "gurobi",
                "instance_data": {},
                "missing_data_hints": ["仓库库存", "岛礁需求", "航线成本与容量"],
            },
            ensure_ascii=False,
        ),
    },
    {
        "role": "user",
        "content": "用启发式算法解一个车辆路径问题，让车辆从仓库出发服务所有客户点再回到仓库，最小化总行驶距离。",
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "background": "车辆从仓库出发服务全部客户点后返回仓库的路径优化问题。",
                "sets": {"V": "节点集合(含仓库与客户)", "K": "车辆集合"},
                "parameters": {"dist[i,j]": "节点 i 到 j 的距离", "demand[i]": "客户 i 的需求", "cap[k]": "车辆 k 容量"},
                "decision_variables": {"x[i,j,k]": "车辆 k 是否经过弧 (i,j)"},
                "objectives": ["minimize sum(dist[i,j] * x[i,j,k])"],
                "hard_constraints": ["每个客户被服务一次", "车辆载重不超过容量", "路径连续且回到仓库"],
                "soft_constraints": [],
                "solver_preference": "heuristic",
                "solver_backend": "auto",
                "instance_data": {},
                "missing_data_hints": ["客户坐标或距离矩阵", "客户需求", "车辆数量与容量"],
            },
            ensure_ascii=False,
        ),
    },
]


def _extract_json_from_llm_text(text: str) -> Optional[Dict[str, Any]]:
    """从 LLM 返回文本中稳健解析 JSON，兼容 ```json``` 包裹和多余文字。"""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
    if candidate is None:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def llm_extract_problem(user_input: str, *, skill_hint: str = "") -> ExtractedProblem:
    """使用 LLM few-shot 抽取结构化建模信息，失败时抛出异常由上层兜底。"""
    from llm.client import LLM  # 延迟导入，避免无 LLM 环境下 import 失败

    llm = LLM()
    messages = [{"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT}]
    messages.extend(_FEW_SHOT_EXAMPLES)
    user_content = user_input
    if skill_hint:
        user_content = f"[已匹配问题族: {skill_hint}]\n{user_input}"
    messages.append({"role": "user", "content": user_content})

    response = llm.chat(messages, temperature=0)
    parsed = _extract_json_from_llm_text(response.content)
    if parsed is None:
        raise ValueError("LLM 未返回可解析的 JSON。")

    extracted = _dict_to_extracted(parsed)
    extracted.extraction_source = "llm"
    # 实例数据优先信任用户原文里的 JSON 块，避免 LLM 篡改数值。
    raw_block = _extract_json_block(user_input)
    if raw_block:
        extracted.instance_data = raw_block
    extracted.missing_data_hints = extracted.missing_data_hints or infer_missing_data_hints(extracted.instance_data)
    return extracted


def _as_str_dict(value: Any) -> Dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(val) for key, val in value.items()}


def _as_str_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dict_to_extracted(payload: Dict[str, Any]) -> ExtractedProblem:
    """把 LLM 或外部 JSON 归一化为 `ExtractedProblem`。"""
    preference = str(payload.get("solver_preference", "auto") or "auto").lower()
    if preference not in {"exact", "heuristic", "auto"}:
        preference = "auto"
    backend = str(payload.get("solver_backend", "auto") or "auto").lower()
    if backend not in {"gurobi", "pulp", "ortools", "cplex", "auto"}:
        backend = "auto"
    instance_data = payload.get("instance_data", {})
    if not isinstance(instance_data, dict):
        instance_data = {}
    return ExtractedProblem(
        background=str(payload.get("background", "")),
        sets=_as_str_dict(payload.get("sets", {})),
        parameters=_as_str_dict(payload.get("parameters", {})),
        decision_variables=_as_str_dict(payload.get("decision_variables", {})),
        objectives=_as_str_list(payload.get("objectives", [])),
        hard_constraints=_as_str_list(payload.get("hard_constraints", [])),
        soft_constraints=_as_str_list(payload.get("soft_constraints", [])),
        solver_preference=preference,
        solver_backend=backend,
        instance_data=instance_data,
        missing_data_hints=_as_str_list(payload.get("missing_data_hints", [])),
    )


def _merge_extractions(primary: ExtractedProblem, fallback: ExtractedProblem) -> ExtractedProblem:
    """用规则抽取补齐 LLM 抽取中缺失的字段，避免信息丢失。"""
    primary.background = primary.background or fallback.background
    primary.sets = primary.sets or fallback.sets
    primary.parameters = primary.parameters or fallback.parameters
    primary.decision_variables = primary.decision_variables or fallback.decision_variables
    primary.objectives = primary.objectives or fallback.objectives
    primary.hard_constraints = primary.hard_constraints or fallback.hard_constraints
    primary.soft_constraints = primary.soft_constraints or fallback.soft_constraints
    if primary.solver_preference == "auto" and fallback.solver_preference != "auto":
        primary.solver_preference = fallback.solver_preference
    if primary.solver_backend == "auto" and fallback.solver_backend != "auto":
        primary.solver_backend = fallback.solver_backend
    primary.instance_data = primary.instance_data or fallback.instance_data
    return primary


def extract_problem_from_text(
    user_input: str,
    *,
    use_llm: bool = True,
    skill_hint: str = "",
) -> Dict[str, Any]:
    """
    从自然语言中抽取可用于构建 `ProblemSpec` 的建模字段。

    策略：
    1. 先跑规则抽取，作为稳定兜底和字段补全来源。
    2. 若允许且 LLM 可用，用 LLM few-shot 覆盖并补全结构化字段。
    3. 归一化并返回统一字典。
    """
    rule_result = rule_extract_problem(user_input)
    if not use_llm:
        return rule_result.to_dict()

    try:
        llm_result = llm_extract_problem(user_input, skill_hint=skill_hint)
    except Exception:
        # LLM 不可用、无网络、无 API Key、返回非法 JSON 等，全部安全回退到规则结果。
        return rule_result.to_dict()

    merged = _merge_extractions(llm_result, rule_result)
    merged.missing_data_hints = merged.missing_data_hints or infer_missing_data_hints(merged.instance_data)
    return merged.to_dict()


if __name__ == "__main__":
    print("=== problem_extractor.py 本地测试 ===")
    sample = """
    背景：2个仓库为3个岛礁补给。
    决策变量：x[d,i] 表示从仓库 d 到岛礁 i 的补给量。
    参数：supply[d] 表示仓库库存；demand[i] 表示岛礁需求；cost[d,i] 表示运输成本。
    目标：最小化总运输成本。
    约束：每个仓库发出量不超过库存；每个岛礁收到量满足需求；每条航线不超过容量。
    使用 Gurobi 求解器。
    """
    print("[规则抽取]")
    print(json.dumps(extract_problem_from_text(sample, use_llm=False), ensure_ascii=False, indent=2))
    print("\n[混合抽取(若无可用 LLM 会自动回退规则)]")
    print(json.dumps(extract_problem_from_text(sample, use_llm=True), ensure_ascii=False, indent=2))
