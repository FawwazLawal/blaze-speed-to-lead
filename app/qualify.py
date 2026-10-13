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

# The SDK would otherwise pick a 600s read timeout for this max_tokens and retry
# it twice — a 30-minute worst case behind a project whose entire claim is "under
# 60 seconds". Bounded so the slowest possible qualification is 2 x 18 = 36s,
# leaving headroom for the Supabase and Discord legs inside the 60s budget.
TIMEOUT_SECONDS = 18.0
MAX_RETRIES = 1

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
    """Score and draft.

    Raises rather than returning something malformed. Note that a refusal
    carrying prose is caught by the SDK's own schema validation *inside*
    `parse()` — it raises a pydantic ValidationError before the stop_reason
    check below is reached. That check only fires for a refusal with no text
    block at all, which is also the case where `parsed_output` is None.
    """
    response = _client().with_options(max_retries=MAX_RETRIES).messages.parse(
        model=MODEL,
        timeout=TIMEOUT_SECONDS,
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

    # parsed_output is Optional: it returns None when no text block carries a
    # parsed result. Guarded so a None can never reach the caller as a
    # Qualification and fail later with an opaque AttributeError.
    if response.parsed_output is None:
        raise RuntimeError(
            f"No parsed qualification in the response (stop_reason="
            f"{response.stop_reason})"
        )

    return response.parsed_output
