"""
Role:
- Wrap the official OpenAI client used by the project.
- Provide a single construction point for model access.

Called by:
- `llm.responder`
- `Operational-Agent.agent`

Calls:
- `config.settings`
"""


class OpenAIClientWrapper:
    """Placeholder wrapper around the OpenAI official client."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
