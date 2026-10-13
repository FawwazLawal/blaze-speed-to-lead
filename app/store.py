"""Supabase persistence. Two calls: insert the raw lead, update it with the
qualification once the LLM returns."""

from datetime import datetime, timezone

from supabase import Client, create_client

from app import config
from app.models import Lead, Qualification

_cached: Client | None = None


def _client() -> Client:
    """Built on first use, not at import. Import-time construction made a
    missing env var surface as an opaque library error before config's own
    check could run."""
    global _cached
    if _cached is None:
        _cached = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _cached


def insert_lead(lead: Lead) -> int:
    """Store the lead exactly as received. Returns the new row id."""
    result = _client().table("leads").insert(lead.model_dump()).execute()
    return result.data[0]["id"]


def attach_qualification(row_id: int, q: Qualification) -> None:
    _client().table("leads").update(
        {"fit_score": q.fit_score, "reason": q.reason, "reply": q.reply}
    ).eq("id", row_id).execute()


def mark_delivered(row_id: int, elapsed_seconds: float) -> None:
    _client().table("leads").update(
        {
            "delivered_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed_seconds, 2),
        }
    ).eq("id", row_id).execute()
