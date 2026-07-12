"""The interface plane's contract: the SSE event protocol, in one place, so the
Expo clients and the backend can evolve independently. v1 emits
token/meta/done/error (what ships today); `step` and `verify` are reserved and
additive — old clients ignore unknown events ([[Target-Architecture]] §3).
"""

import json

# Event names — the versioned wire protocol. Do not rename without bumping the
# client contract; only add.
TOKEN = "token"     # a chunk of answer text: {t: str}
META = "meta"       # end-of-answer summary: session_id, thread_id, model, cost, sources
DONE = "done"       # stream finished cleanly
ERROR = "error"     # {code, message}
STEP = "step"       # RESERVED (P5): a delimited solution step
VERIFY = "verify"   # RESERVED (P5): {step_id, verdict}


def format_event(event: str, data: dict) -> str:
    """SSE frame: `event: <name>\\ndata: <json>\\n\\n`."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
