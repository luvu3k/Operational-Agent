"""
作用：
- 提供“多轮对话 + 问题分解纠正”的会话编排引擎，是全栈后端调用的核心。
- 单用户简化设计：会话状态存内存字典（按 session_id），对话历史另落 SQLite 短期记忆。
- 支持完整闭环：分析(analyze) -> 展示数学模型 -> 用户纠正(refine，可多次) -> 确认(confirm) -> 求解(solve)。

调用关系：
- 被 `app.api`（FastAPI）与 `app.cli` 调用。
- 调用 `core.intent_parser`、`core.problem_builder` 完成问题分解，`core.react_agent` 完成求解。
- 复用 `core.problem_extractor` 解析纠正指令，`memory.short_term` 记录对话。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from core.confirmation import build_confirmation_message
from core.intent_parser import parse_intent
from core.problem_builder import build_problem_spec
from core.problem_extractor import _extract_json_block, detect_solver_backend, detect_solver_preference
from core.react_agent import run_react_loop


class ConversationState:
    """单个会话的可变状态。"""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.phase = "idle"  # idle -> awaiting_confirmation -> solved
        self.problem_spec: Optional[Dict[str, Any]] = None
        self.intent_result: Dict[str, Any] = {}
        self.messages: List[Dict[str, str]] = []
        self.last_result: Optional[Dict[str, Any]] = None
        self.revision = 0  # 分解纠正次数

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})


class ConversationManager:
    """管理多会话状态并驱动分析/纠正/确认/求解流程。"""

    def __init__(self) -> None:
        self._sessions: Dict[str, ConversationState] = {}

    # ---- 会话管理 ----
    def get_or_create(self, session_id: str) -> ConversationState:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationState(session_id)
        return self._sessions[session_id]

    def reset(self, session_id: str) -> None:
        self._sessions[session_id] = ConversationState(session_id)

    def history(self, session_id: str) -> List[Dict[str, str]]:
        return self.get_or_create(session_id).messages

    # ---- 记忆写入（尽力而为） ----
    def _record(self, session_id: str, role: str, content: str) -> None:
        try:
            from memory.short_term import append_short_term_message

            append_short_term_message(session_id, content, role=role)
        except Exception:
            pass

    # ---- 核心：分析（首轮分解问题） ----
    def analyze(self, session_id: str, user_input: str) -> Dict[str, Any]:
        """把自然语言分解为结构化数学模型（ProblemSpec），进入待确认阶段。"""
        state = self.get_or_create(session_id)
        state.add_message("user", user_input)
        self._record(session_id, "user", user_input)

        intent_result = parse_intent(user_input)
        problem_spec = build_problem_spec(user_input, intent_result)

        state.intent_result = intent_result
        state.problem_spec = problem_spec
        state.phase = "awaiting_confirmation"
        state.revision = 0

        return self._model_payload(state, note="已完成问题分解，请确认数学模型。如需修改，请直接输入纠正指令。")

    # ---- 核心：纠正（多轮 refine） ----
    def refine(self, session_id: str, correction: str) -> Dict[str, Any]:
        """
        根据用户纠正指令重新分析问题，在已有 ProblemSpec 上做定向覆盖。
        可反复调用，直到用户确认。
        """
        state = self.get_or_create(session_id)
        if state.problem_spec is None:
            # 尚未分析，退化为首轮分析。
            return self.analyze(session_id, correction)

        state.add_message("user", correction)
        self._record(session_id, "user", correction)

        spec = dict(state.problem_spec)
        applied: List[str] = []

        # 1) 求解偏好 / 后端纠正。
        pref = detect_solver_preference(correction)
        if pref != "auto":
            spec["solver_preference"] = pref
            applied.append(f"求解偏好 -> {pref}")
        backend = detect_solver_backend(correction)
        if backend != "auto":
            spec["solver_backend"] = backend
            applied.append(f"求解后端 -> {backend}")
        if any(k in correction.lower() for k in ["遗传", "genetic", "ga"]):
            spec["solver_preference"] = "heuristic"
            spec["solver_backend"] = "genetic"
            applied.append("求解方式 -> 遗传算法")

        # 2) 数值参数纠正（如惩罚系数、航速、服务时长）。
        instance_data = dict((spec.get("resources") or {}).get("instance_data", {}) or {})
        params = dict(instance_data.get("params", {}) or {})
        for pattern, key, label in [
            (r"惩罚(?:系数|权重)?\s*(?:改?为|=|:|设为)?\s*([0-9.]+)", "priority_penalty_L", "优先级惩罚系数"),
            (r"(?:航速|速度|v1)\s*(?:改?为|=|:|设为)?\s*([0-9.]+)", "v1", "补给舰航速"),
            (r"服务(?:时长|时间)\s*(?:改?为|=|:|设为)?\s*([0-9.]+)", "service_time", "服务时长"),
            (r"(?:每仓库|每中心)?(?:补给舰|车辆|船)(?:数|数量)\s*(?:改?为|=|:|设为)?\s*([0-9]+)", "max_vehicles_per_depot", "每中心车辆上限"),
        ]:
            match = re.search(pattern, correction)
            if match:
                params[key] = float(match.group(1))
                applied.append(f"{label} -> {match.group(1)}")
        if params:
            instance_data["params"] = params

        # 3) 显式 JSON 实例数据纠正。
        raw_block = _extract_json_block(correction)
        if raw_block:
            instance_data.update(raw_block)
            applied.append("实例数据已按提供的 JSON 更新")
        if instance_data:
            spec.setdefault("resources", {})
            spec["resources"]["instance_data"] = instance_data

        # 4) 目标 / 约束的自然语言追加（非空则并入）。
        try:
            fresh = build_problem_spec(correction, {"matched_skill": spec.get("skill_name", ""), "solver_preference": spec.get("solver_preference", "auto")})
            for field in ["objectives", "hard_constraints", "soft_constraints"]:
                new_items = [item for item in fresh.get(field, []) if item and item not in spec.get(field, [])]
                # 仅当纠正文本确实提到目标/约束关键词时才追加，避免误并入 skill 默认值。
                if new_items and any(kw in correction for kw in ["目标", "约束", "最小化", "最大化", "限制", "要求"]):
                    spec[field] = list(spec.get(field, [])) + new_items
                    applied.append(f"{field} 追加 {len(new_items)} 项")
        except Exception:
            pass

        spec["extra_requirements"] = list(spec.get("extra_requirements", [])) + [correction]
        state.problem_spec = spec
        state.phase = "awaiting_confirmation"
        state.revision += 1

        note = "已根据纠正指令重新分析。" + ("本次调整：" + "；".join(applied) if applied else "未识别到明确的结构化修改，已记录为附加需求。")
        return self._model_payload(state, note=note)

    # ---- 核心：确认并求解 ----
    def solve(self, session_id: str) -> Dict[str, Any]:
        """确认当前数学模型并进入 ReAct 求解，返回结果、路径、可视化与完整代码。"""
        state = self.get_or_create(session_id)
        if state.problem_spec is None:
            return {"type": "error", "message": "尚无可求解的问题，请先描述问题。"}

        spec = dict(state.problem_spec)
        spec["confirmed"] = True
        react_result = run_react_loop({
            "user_input": spec.get("user_input", ""),
            "intent_result": state.intent_result,
            "problem_spec": spec,
        })
        state.phase = "solved"
        state.last_result = react_result

        payload = self._result_payload(react_result)
        summary = payload.get("assistant_summary", "求解完成。")
        state.add_message("assistant", summary)
        self._record(session_id, "assistant", summary)
        return payload

    # ---- 结果/模型的展示载荷构造 ----
    def _model_payload(self, state: ConversationState, *, note: str) -> Dict[str, Any]:
        spec = state.problem_spec or {}
        confirmation = build_confirmation_message(spec)
        return {
            "type": "model_proposal",
            "session_id": state.session_id,
            "phase": state.phase,
            "revision": state.revision,
            "note": note,
            "problem_spec": spec,
            "math_model": self._render_math_model(spec),
            "confirmation_message": confirmation,
        }

    def _result_payload(self, react_result: Dict[str, Any]) -> Dict[str, Any]:
        tool_payload = react_result.get("tool_result", {}).get("payload", {})
        solution = tool_payload.get("solution", {})
        routes = solution.get("routes", [])
        route_lines = [f"中心{r['depot']} · 船{i + 1}: {' -> '.join(map(str, r['sequence']))}" for i, r in enumerate(routes)]
        summary = react_result.get("final_answer") or tool_payload.get("message", "求解完成。")
        return {
            "type": "solution",
            "phase": "solved",
            "status": react_result.get("status"),
            "selected_tool": react_result.get("selected_tool"),
            "assistant_summary": summary,
            "objective": solution.get("objective"),
            "travel_time": solution.get("travel_time"),
            "priority_penalty": solution.get("priority_penalty"),
            "feasible": solution.get("feasible"),
            "num_routes": solution.get("num_routes"),
            "routes": routes,
            "route_text": route_lines,
            "arrival_times": solution.get("arrival_times", {}),
            "route_map_svg": tool_payload.get("route_map_svg", ""),
            "gantt_svg": tool_payload.get("gantt_svg", ""),
            "generated_code": tool_payload.get("generated_code", ""),
            "code_path": tool_payload.get("code_path", ""),
            "result_path": tool_payload.get("result_path", ""),
            "instance_summary": tool_payload.get("instance_summary", {}),
        }

    def _render_math_model(self, spec: Dict[str, Any]) -> str:
        """把 ProblemSpec 渲染成便于用户核对的数学模型文本。"""
        lines: List[str] = []
        lines.append(f"问题族: {spec.get('skill_name', 'unknown')}")
        if spec.get("sets"):
            lines.append("集合: " + "; ".join(f"{k}={v}" for k, v in spec["sets"].items()))
        if spec.get("parameters"):
            lines.append("参数: " + "; ".join(f"{k}={v}" for k, v in spec["parameters"].items()))
        if spec.get("decision_variables"):
            lines.append("决策变量: " + "; ".join(f"{k}={v}" for k, v in spec["decision_variables"].items()))
        if spec.get("objectives"):
            lines.append("目标函数: " + "; ".join(spec["objectives"]))
        if spec.get("hard_constraints"):
            lines.append("硬约束: " + "; ".join(spec["hard_constraints"]))
        if spec.get("soft_constraints"):
            lines.append("软约束: " + "; ".join(spec["soft_constraints"]))
        lines.append(f"求解偏好: {spec.get('solver_preference', 'auto')} | 后端: {spec.get('solver_backend', 'auto')}")
        return "\n".join(lines)


# 单用户场景使用模块级单例。
_MANAGER = ConversationManager()


def get_conversation_manager() -> ConversationManager:
    return _MANAGER


if __name__ == "__main__":
    print("=== conversation.py 本地测试 ===")
    mgr = get_conversation_manager()
    sid = "demo-conv"
    step1 = mgr.analyze(sid, "求解远海岛礁多保障中心补给舰路径规划 MDVRPTW，带时间窗和优先级，用精确算法")
    print("① analyze:", step1["type"], "| pref=", step1["problem_spec"]["solver_preference"], "| rev=", step1["revision"])
    step2 = mgr.refine(sid, "改用遗传算法，优先级惩罚系数设为2")
    print("② refine:", step2["note"])
    print("   pref=", step2["problem_spec"]["solver_preference"], "| backend=", step2["problem_spec"]["solver_backend"])
    print("   params=", step2["problem_spec"]["resources"]["instance_data"]["params"])
    step3 = mgr.solve(sid)
    print("③ solve:", step3["type"], "| obj=", step3["objective"], "| routes=", step3["num_routes"], "| feasible=", step3["feasible"])
    print("   history turns:", len(mgr.history(sid)))
