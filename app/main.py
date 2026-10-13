"""Speed-to-lead webhook.

A simulated Facebook lead-ad POST arrives here; a qualified, personalised reply
lands in Discord. The clock starts when the request is received and stops when
Discord acknowledges the card.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import config, notify, qualify, store
from app.models import Lead

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger("speed-to-lead")

config.require_all()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Presence only. A key's value is never logged.
    log.info("config: %s", config.presence_report())
    yield


app = FastAPI(title="Blaze speed-to-lead", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/webhook/lead")
def receive_lead(lead: Lead) -> dict:
    t0 = time.monotonic()
    log.info("lead received: %s · %s · %s doors", lead.name, lead.company, lead.doors)

    row_id = store.insert_lead(lead)
    log.info("supabase row %s inserted (+%.1fs)", row_id, time.monotonic() - t0)

    q = qualify.qualify(lead)
    log.info(
        "qualified: fit %s/5 — %s (+%.1fs)", q.fit_score, q.reason, time.monotonic() - t0
    )

    store.attach_qualification(row_id, q)

    notify.send_card(lead, q, elapsed_seconds=time.monotonic() - t0)
    elapsed = time.monotonic() - t0
    store.mark_delivered(row_id, elapsed)

    log.info("received → delivered: %.1fs", elapsed)

    return {
        "row_id": row_id,
        "fit_score": q.fit_score,
        "reason": q.reason,
        "reply": q.reply,
        "elapsed_seconds": round(elapsed, 2),
        "delivered_under_60s": elapsed < 60,
    }
