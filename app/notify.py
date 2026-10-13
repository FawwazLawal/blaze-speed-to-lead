"""Discord delivery. The operator's phone is the target; this is the only
outbound channel in the project, and it points at the author's own server."""

import httpx

from app import config
from app.models import Lead, Qualification

_SCORE_COLOUR = {
    5: 0x1B9E4B,  # green
    4: 0x5FA832,
    3: 0xC8A415,  # amber
    2: 0xC8691B,
    1: 0x9E3A1B,  # red
}


def _clip(text: str, limit: int = 1024) -> str:
    """Discord rejects an embed field value over 1024 characters with a 400.
    The fabricated payload is well under it, but a longer free-text message
    typed in live would otherwise kill the demo."""
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


def send_card(lead: Lead, q: Qualification, elapsed_seconds: float) -> None:
    """POST the qualified lead to Discord.

    `elapsed_seconds` is the time from receipt to the moment this card was
    composed. It necessarily excludes the Discord round-trip that delivers it —
    a card cannot state how long its own delivery took. The footer is labelled
    "reply drafted" for that reason. The full received-to-delivered figure is
    logged, returned in the HTTP response, and stored on the row.
    """
    embed = {
        "title": f"New lead · fit {q.fit_score}/5 · {lead.company}",
        "description": q.reason,
        "color": _SCORE_COLOUR.get(q.fit_score, 0x808080),
        "fields": [
            {
                "name": "Lead",
                "value": f"{lead.name}\n{lead.email}\n{lead.phone}",
                "inline": True,
            },
            {"name": "Doors", "value": str(lead.doors), "inline": True},
            {"name": "They said", "value": _clip(lead.message), "inline": False},
            {"name": "Suggested reply", "value": _clip(q.reply), "inline": False},
        ],
        "footer": {
            "text": (
                f"received → reply drafted: {elapsed_seconds:.1f}s  ·  "
                "SIMULATED LEAD — fabricated payload, no real business contacted"
            )
        },
    }

    # The webhook URL contains the credential in its path, and httpx puts the
    # full URL into HTTPStatusError's message. Raising it would print the token
    # into the terminal traceback — i.e. onto the screen recording. Every error
    # out of this function is re-raised without the URL, and `from None` drops
    # the original exception so the chained traceback cannot leak it either.
    try:
        response = httpx.post(
            config.DISCORD_WEBHOOK_URL,
            json={"embeds": [embed]},
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Discord rejected the card: HTTP {exc.response.status_code}"
        ) from None
    except httpx.RequestError:
        raise RuntimeError("Could not reach Discord (network error)") from None
