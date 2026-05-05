"""
将输入转换成问题规格，然后根据问题规格生成 prompt，包括但不限于：
- system prompt
- skills 内容
- RAG 检索结果
- memory 内容
- 当前问题规格
这些拼成不同阶段的 prompt。
"""