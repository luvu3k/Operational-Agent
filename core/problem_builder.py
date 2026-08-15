"""
作用：
- 将用户输入、匹配到的 skill 基础知识、RAG 资源/经验以及当前求解偏好合并成统一的 `ProblemSpec`。
- 在进入 ReAct 循环前形成稳定的问题对象，供确认、校验和工具调用复用。

调用关系：
- 被 `core.agent` 调用，构造最小可执行问题状态。
- 调用 `core.problem_extractor` 完成自然语言结构化抽取（LLM few-shot + 规则兜底）。
- 调用 `skills.loader` 读取 skill 内容，调用 `rag.retrievers` 补齐资源与经验。
- 调用 `schemas.problem` 输出标准问题结构。
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.problem_extractor import extract_problem_from_text
from schemas.problem import ProblemSpec
from skills.loader import load_skill


def _extract_markdown_bullets(markdown_text: str) -> List[str]:
    bullets: List[str] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def _retrieve_resource_instance(user_input: str, skill_name: str) -> Dict[str, Any]:
    """当用户未在 prompt 内附带数据时，尝试从 RAG 资源索引检索实例数据。"""
    try:
        from rag.retrievers.resource_retriever import retrieve_resource_context

        context = retrieve_resource_context(user_input, skill_name=skill_name)
        resources = context.get("resources", {})
        return resources if isinstance(resources, dict) else {}
    except Exception:
        return {}


def _retrieve_experience_hints(user_input: str, skill_name: str) -> List[str]:
    """从长期记忆检索历史经验提示，失败时返回空列表。"""
    try:
        from rag.retrievers.experience_retriever import retrieve_experience_context

        records = retrieve_experience_context(user_input, skill_name=skill_name, limit=3)
        return [str(record.get("summary", "")) for record in records if record.get("summary")]
    except Exception:
        return []


def build_problem_spec(user_input: str, intent_result: Dict[str, object], *, use_llm: bool = True) -> Dict[str, object]:
    """构建结构化问题对象，并附带 skill 基础信息、RAG 资源与历史经验。"""
    matched_skill = str(intent_result.get("matched_skill", "emergency_island_supply"))
    skill = load_skill(matched_skill)

    skill_markdown = skill.get("skill_markdown", "")
    metadata = skill.get("metadata", {})
    bullets = _extract_markdown_bullets(skill_markdown)
    extracted = extract_problem_from_text(user_input, use_llm=use_llm, skill_hint=matched_skill)

    # 实例数据优先来自用户 prompt，其次来自 RAG 资源检索。
    instance_data = extracted.get("instance_data", {})
    if not instance_data:
        instance_data = _retrieve_resource_instance(user_input, matched_skill)

    objective_list = list(extracted.get("objectives", [])) or bullets[:2] or ["以用户输入与基础 skill 为准构建目标函数。"]
    hard_constraint_list = list(extracted.get("hard_constraints", [])) or bullets[2:] or ["需满足 skill 中基础约束以及用户新增约束。"]
    background = str(extracted.get("background", "")) or skill_markdown
    experience_hints = _retrieve_experience_hints(user_input, matched_skill)

    problem = ProblemSpec(
        skill_name=matched_skill,
        problem_type=str(metadata.get("description", matched_skill)),
        description=f"基于 skill `{matched_skill}` 构建的优化问题。",
        user_input=user_input,
        background=background,
        sets=dict(extracted.get("sets", {})),
        parameters=dict(extracted.get("parameters", {})),
        decision_variables=dict(extracted.get("decision_variables", {})),
        objectives=objective_list,
        hard_constraints=hard_constraint_list,
        soft_constraints=list(extracted.get("soft_constraints", [])),
        assumptions=["默认以本地可用资源和 skill 基础设定构建模型。"],
        resources={"instance_data": instance_data} if instance_data else {},
        experience_hints=experience_hints,
        extra_requirements=[user_input],
        missing_data_hints=list(extracted.get("missing_data_hints", [])),
        solver_preference=str(intent_result.get("solver_preference", "auto") or extracted.get("solver_preference", "auto")),
        solver_backend=str(extracted.get("solver_backend", "auto")),
        confirmed=False,
    )
    return problem.to_dict()


if __name__ == "__main__":
    print("=== problem_builder.py 本地测试 ===")
    sample_input = "请帮我求解一个岛礁应急物资补给问题，优先使用精确算法。"
    sample_intent = {
        "intent": "solve_problem",
        "matched_skill": "emergency_island_supply",
        "solver_preference": "exact",
    }
    print(build_problem_spec(sample_input, sample_intent))
