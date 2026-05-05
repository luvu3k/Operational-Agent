# Operational_Agent

该目录是自定义优化智能体的项目根目录。

主要职责：
- 存放智能体的运行时代码、知识、工具、记忆和存储。
- 分离编排（orchestration）、LLM 访问和求解器执行的关注点。
- 将优化问题的相关知识保留在基于 Markdown 的技能（skills）中。

Key design:
- `llm/` 负责处理 OpenAI API 的访问。
- `Operational-Agent/` 负责处理智能体工作流和 ReAct 循环。
- `tools/` 向智能体暴露可调用的工具（tools）。
- `solver/` 负责执行代码的生成、运行以及结果解析。