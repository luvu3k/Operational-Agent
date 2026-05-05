# Operational-Agent

This folder contains the agent workflow layer.

Main responsibilities:
- Implement the ReAct-style control loop.
- Route the conversation through intent parsing, retrieval, confirmation, tool use, and repair.
- Act as the core agent implementation layer.

Important note:
- The folder name follows the requested naming, but the hyphen makes normal Python package imports awkward.
- If this becomes a real import package, consider renaming it to `operational_agent` later.
