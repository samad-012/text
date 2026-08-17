from app.agent.agent import SYSTEM_PROMPT

_sessions: dict[str, list[dict]] = {}


def get_history(session_id: str) -> list[dict]:
    if session_id not in _sessions:
        _sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return _sessions[session_id]


def reset(session_id: str) -> None:
    _sessions.pop(session_id, None)