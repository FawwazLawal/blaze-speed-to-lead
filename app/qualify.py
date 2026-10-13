"""The LLM step: score the lead, say why, draft the reply.

Uses the Anthropic SDK's structured-output helper, so the response is validated
against the `Qualification` schema before it reaches the rest of the pipeline.
If the model returns anything that does not fit the schema, this raises rather
than quietly delivering a malformed card.

The system prompt is NOT in this file. It is read from prompts/qualify_lead.md
so that the prompt in the repo is literally the prompt that gets sent.
"""

import json
from pathlib import Path

import anthropic

from app.models import Lead, Qualification

MODEL = "claude-opus-5-5"

# Effort is deliberately "low". The task is a rubric lookup plus three sentences
# of drafting — it does not need deep reasoning, and the headline claim of this
# project is end-to-end latency. Raised to "medium" if quality turns out thin.
EFFORT = "low"

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "qualify_lead.md"

_cached: anthropic.Anthropic | None = None


def _client() -> anthropic.Anthropic:
    """Built on first use, not at import — same reason as app/store.py."""
    global _cached
    if _cached is None:
        _cached = anthropic.Anthropic()
    return _cached


def _system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def qualify(lead: Lead) -> Qualification:
    """Score and draft. Raises on refusal or on a schema violation."""
    response = _client().messages.parse(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": EFFORT},
        system=_system_prompt(),
        messages=[
            {
                "role": "user",
                "content": "Qualify this lead.\n\n"
                + json.dumps(lead.model_dump(), indent=2),
            }
        ],
        output_format=Qualification,
    )

    if response.stop_reason == "refusal":
        raise RuntimeError(f"Model declined to answer: {response.stop_details}")

    return response.parsed_output
