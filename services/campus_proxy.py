"""Small OpenAI-compatible client for the ELEC5620 course proxy.

The course guide also shows a LangChain ChatOpenAI setup. This standard-library
adapter follows its documented chat-completions request and remains usable
until the team's shared LangGraph/LLM integration is ready.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any
from urllib.request import Request, urlopen

from models import Event

DEFAULT_BASE_URL = "http://10.167.60.148:8000/v1"
DEFAULT_MODEL = "campus-qwen"


@dataclass(frozen=True)
class CampusProxyConfig:
    api_key: str = field(repr=False)
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_seconds: int = 15

    @classmethod
    def from_environment(cls) -> "CampusProxyConfig":
        key = os.getenv("ELEC5620_API_KEY", "").strip()
        if not key:
            raise ValueError("Set ELEC5620_API_KEY in your local environment before using the campus proxy")
        return cls(
            api_key=key,
            base_url=os.getenv("ELEC5620_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            model=os.getenv("ELEC5620_MODEL", DEFAULT_MODEL),
        )


def request_json_chat(messages: list[dict[str, str]], config: CampusProxyConfig) -> dict[str, Any]:
    """Send one JSON chat request through the shared course proxy client.

    The caller owns the domain prompt and must validate the untrusted reply.
    """
    payload = {
        "model": config.model,
        "messages": messages,
        "max_completion_tokens": 1024,
        "stream": False,
    }
    request = Request(
        config.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + config.api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=config.timeout_seconds) as response:
        data = json.load(response)
    content = data["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("campus proxy returned non-text model content")
    proposal = json.loads(content)
    if not isinstance(proposal, dict):
        raise ValueError("campus proxy proposal must be a JSON object")
    return proposal


def propose_pet_risk(event: Event, config: CampusProxyConfig) -> dict[str, Any]:
    """Ask campus-qwen to interpret only minimal pet sensor observations.

    No pet ID, resident details, location, owner contact or API key is included
    in the prompt. The caller must validate this untrusted result with rules.
    """

    observations = [
        {"type": item.reading_type, "value": item.value, "unit": item.unit}
        for item in event.readings
    ]
    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Assess a pet sensor observation. Reply with one JSON object containing "
                    "risk_level (LOW, MEDIUM, or HIGH) and a short rationale. "
                    "Do not suggest or execute feeding or claim an owner was notified."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"event_type": event.event_type, "readings": observations}),
            },
        ],
        "max_completion_tokens": 1024,
        "stream": False,
    }
    request = Request(
        config.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + config.api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=config.timeout_seconds) as response:
        data = json.load(response)
    content = data["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("campus proxy returned non-text model content")
    proposal = json.loads(content)
    if not isinstance(proposal, dict):
        raise ValueError("campus proxy proposal must be a JSON object")
    return proposal


def propose_smart_home_goal(event: Event, config: CampusProxyConfig) -> dict[str, Any]:
    """Request a structured UC-02 goal without giving the model device authority."""

    text = event.context.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("user goal text is required")
    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Classify a smart-home request. Reply with one JSON object only. "
                    "Use domain 'smart_home_control'. Use intent night_mode, away_mode, "
                    "relax_mode, direct_control, unlock_door, or clarify. Mode parameters may "
                    "contain temperature_c from 18 to 28. For direct_control, parameters may "
                    "contain only light_power, light_brightness, curtain_position, door_locked, "
                    "ac_power, ac_mode, and temperature_c. light_power and ac_power must be the "
                    "strings 'on' or 'off'; curtain_position must be 'open' or 'closed'; "
                    "door_locked must be a JSON boolean; and ac_mode must be 'sleep', 'eco', or "
                    "'comfort'. For clarify, include clarification_question. "
                    "Do not create device IDs, commands, approvals, or claims of execution."
                ),
            },
            {"role": "user", "content": json.dumps({"request": text}, ensure_ascii=False)},
        ],
        "max_completion_tokens": 512,
        "stream": False,
    }
    request = Request(
        config.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + config.api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=config.timeout_seconds) as response:
        data = json.load(response)
    content = data["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("campus proxy returned non-text model content")
    proposal = json.loads(content)
    if not isinstance(proposal, dict):
        raise ValueError("campus proxy proposal must be a JSON object")
    return proposal
