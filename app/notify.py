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
    """POST the qualified lead to Discord. Raises on a non-2xx response."""
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
                f"lead received → card sent: {elapsed_seconds:.1f}s  ·  "
                "SIMULATED LEAD — fabricated payload, no real business contacted"
            )
        },
    }

    response = httpx.post(
        config.DISCORD_WEBHOOK_URL,
        json={"embeds": [embed]},
        timeout=10.0,
    )
    response.raise_for_status()
