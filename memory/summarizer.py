"""
Role:
- Compress session history into reusable lessons and experience records.

Called by:
- `Operational-Agent.recovery`
- Future session-finalization flows.

Calls:
- `llm.responder`
- `memory.long_term`
- `knowledge.ingestors.experience_ingestor`
"""


def summarize_session(session_messages: list) -> str:
    """Placeholder memory summarizer."""
    return "SESSION_SUMMARY_PLACEHOLDER"
