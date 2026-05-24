"""
作用：
- 提供本地命令行最小交互入口，用于手动体验“问题输入 -> 用户确认 -> ReAct 执行”的完整流程。
- 便于在不引入 Web 框架的前提下快速验证当前智能体主链路。

调用关系：
- 被 `main.py` 调用作为启动入口。
- 调用 `app.session` 生成会话上下文。
- 调用 `core.agent` 执行顶层智能体流程。
"""

from __future__ import annotations

from app.session import create_session
from core.agent import run_agent


def run_cli() -> None:
    """启动一个最小可交互 CLI。"""
    session = create_session()
    print(f"当前会话已启动: {session.session_id}")
    user_input = input("请输入优化问题描述：").strip()
    if not user_input:
        print("未输入问题描述，程序结束。")
        return

    first_round = run_agent(user_input)
    print("\n=== 待确认问题定义 ===")
    print(first_round["confirmation_message"])

    confirm = input("\n请确认是否继续求解？(y/n)：").strip().lower()
    if confirm not in {"y", "yes"}:
        print("已取消求解。")
        return

    second_round = run_agent(
        user_input,
        confirmed=True,
        problem_spec=first_round["problem_spec"],
    )
    print("\n=== ReAct 执行结果 ===")
    print(second_round["final_answer"])
