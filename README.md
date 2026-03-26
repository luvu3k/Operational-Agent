# RescueOptAgent

This directory is the project root for the custom optimization agent.

Main responsibilities:
- Hold the agent's runtime code, knowledge, tools, memory, and storage.
- Separate orchestration, LLM access, and solver execution concerns.
- Keep optimization problem knowledge in Markdown-based skills.

Key design:
- `llm/` handles OpenAI API access.
- `Operational-Agent/` handles the agent workflow and ReAct loop.
- `tools/` exposes callable actions to the agent.
- `solver/` performs code generation, execution, and result parsing.
