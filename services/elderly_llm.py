"""campus-qwen calls for Elderly Safety (UC-01 steps 3 and 6).

Two untrusted proposals, both validated by domain rules before use:

    propose_fall_risk(view, config)        risk_level + rationale for a suspected fall
    interpret_resident_reply(payload, cfg) verdict (safe / help / unclear) for a reply

Privacy (NFR-03): `view` is `FallContext.for_llm()` (room category, timing and
sensor values only) and `payload` is the reply text plus attempt number. No
resident identity, address, contacts, event ID or API key is ever placed in
a prompt; the key only travels in the Authorization header.

Kept separate from `services/campus_proxy.py` so domain prompts do not
conflict with other members' edits to the shared client; it reuses that
module's `CampusProxyConfig`.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping
from urllib.request import Request, urlopen

from services.campus_proxy import CampusProxyConfig

FALL_SYSTEM_PROMPT = (
    "You assess a possible fall of an older adult at home from de-identified smart-home sensor data. "
    "Reply with one JSON object only: {\"risk_level\": \"LOW\" | \"MEDIUM\" | \"HIGH\", \"rationale\": \"one short sentence\"}. "
    "HIGH means help is likely needed now; MEDIUM means the resident should be asked; LOW means normal activity. "
    "Null values are unknown, not normal. Do not diagnose, do not suggest calling emergency services, "
    "and do not claim anyone was contacted or any device was operated."
)

REPLY_SYSTEM_PROMPT = (
    "An older adult was asked after a possible fall. Attempt 1 asked 'Are you okay? Please reply.'; "
    "attempt 2 asked 'Do you need me to contact your family? Please answer yes or no.'. "
    "Classify the reply. Reply with one JSON object only: {\"verdict\": \"safe\" | \"help\" | \"unclear\", "
    "\"rationale\": \"one short sentence\"}. Any mention of pain, injury, being unable to get up, "
    "or asking for help is 'help'. If unsure, use 'unclear'. Do not invent details."
)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _chat_json(config: CampusProxyConfig, system: str, user: Mapping[str, Any], max_tokens: int = 1024) -> dict[str, Any]:
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(dict(user), ensure_ascii=False)},
        ],
        "max_completion_tokens": max_tokens,
        "stream": False,
    }
    # Opt-in for OpenAI-compatible providers whose models think before answering
    # (e.g. DashScope Qwen3): otherwise the token budget can be spent on reasoning
    # and the answer text is empty. Not sent to the course proxy by default.
    if os.getenv("ELEC5620_DISABLE_THINKING", "").strip() == "1":
        payload["enable_thinking"] = False
    request = Request(
        config.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + config.api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=config.timeout_seconds) as response:
        data = json.load(response)
    choice = data["choices"][0]
    content = choice["message"].get("content")
    if not isinstance(content, str):
        raise ValueError("campus proxy returned non-text model content")
    if not content.strip():
        raise ValueError(f"model returned no answer text (finish_reason={choice.get('finish_reason')}); "
                         "for thinking models set ELEC5620_DISABLE_THINKING=1")
    text = _FENCE.sub("", content.strip())
    proposal = json.loads(text)
    if not isinstance(proposal, dict):
        raise ValueError("campus proxy proposal must be a JSON object")
    return proposal


def propose_fall_risk(view: Mapping[str, Any], config: CampusProxyConfig) -> dict[str, Any]:
    """`view` must be `FallContext.for_llm()`; the caller validates the result with rules."""
    return _chat_json(config, FALL_SYSTEM_PROMPT, view)


def interpret_resident_reply(payload: Mapping[str, Any], config: CampusProxyConfig) -> dict[str, Any]:
    """`payload` is {"reply": str, "attempt": int}; the caller keeps help requests as help."""
    return _chat_json(config, REPLY_SYSTEM_PROMPT, {"reply": payload.get("reply"), "attempt": payload.get("attempt")}, 512)


def campus_providers(config: CampusProxyConfig | None = None):
    """(fall proposal provider, reply interpreter) bound to the campus model.

    Raises ValueError when no key is configured, so callers can fall back to
    rule-only mode and say so.
    """
    config = config or CampusProxyConfig.from_environment()
    return (lambda view: propose_fall_risk(view, config), lambda payload: interpret_resident_reply(payload, config))
