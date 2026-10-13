# Speed-to-lead

A Facebook lead ad comes in. A scored, personalised reply is sitting in Discord
**MEASURED_TIME seconds** _(filled in from a real run — see Sample output)_ later.

Blaze's current first response to an inbound lead takes **22 hours**. 58 qualified
property managers produced 12 bookings last quarter — 79% lost, with that 22-hour
delay sitting in the middle of the gap. This is the smallest thing that closes it.

```
POST /webhook/lead
  │  t0
  ├─ validate the payload            name, email, phone, company, doors, message
  ├─ insert row                      Supabase
  ├─ score + draft                   Anthropic, structured output
  │                                    fit_score 1-5 · one-line reason · reply
  ├─ update row                      score, reason, reply
  ├─ post card                       Discord
  └─ t1 — log and return "received → delivered: N.Ns"
```

## What it is not

This is a two-hour build and it is scoped like one. There is no Facebook OAuth —
the payload is fabricated and fired with `curl`. No UI, no queue, no retries, no
auth, no deploy. One happy path, measured.

**Nothing in this project contacts a real business or person.** The lead is
invented: `Northgate Property Group` does not exist, the address is
`@example.com`, and the phone number is in the `555-01xx` range reserved for
fiction. The only outbound message goes to the author's own Discord webhook.
Every Discord card is stamped `SIMULATED LEAD` in its footer. Nothing scrapes.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # then fill in the four values
```

Create the table — paste [`schema.sql`](schema.sql) into the Supabase SQL editor.

```bash
uvicorn app.main:app --port 8000      # terminal 1
./send_test_lead.sh                   # terminal 2
```

### Configuration

Four environment variables, all read from `.env`, which is git-ignored:
`ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `DISCORD_WEBHOOK_URL`.
See [`.env.example`](.env.example). The app logs only whether each one is
**present** — never its value. `.env` was added to `.gitignore` in this
repository's first commit, before any key existed on disk.

## The prompt

[`prompts/qualify_lead.md`](prompts/qualify_lead.md) is the system prompt, read
from disk at runtime by [`app/qualify.py`](app/qualify.py) — it is not duplicated
in a Python string, so the file in this repo is exactly what gets sent.

It encodes the fit rubric: door count is the primary signal (more doors → more
transactions → more reconciliation → more CFO pain), adjusted up for a named
finance pain in the free text and down for an ask Blaze does not serve.

The reply is constrained to reference something specific to the lead. A reply
that would read identically for any other lead has failed the brief.

**Model:** `claude-opus-5-5`, structured output via `client.messages.parse()` with
a Pydantic schema, so a malformed response raises instead of reaching Discord.
Effort is set to `low` deliberately — the task is a rubric lookup plus three
sentences, and latency is the entire point of the project.

## Sample output

_Pending the first live end-to-end run._

## How this was built, and what was wrong with it

Built with Claude Code (Opus 5). Every prompt is in [`prompts/`](prompts/), saved
as it was used rather than reconstructed afterwards.

[`prompts/CHECKED.md`](prompts/CHECKED.md) is the honest part: a running log of
what the model got wrong, how it was caught, and what changed. It includes an
SDK version that was a full major release out of date, two patterns written from
memory that the runtime rejected, and the results of an adversarial code review
by a second agent instructed not to agree by default — including the findings
from that review that turned out to be wrong when checked against a run.

## Known limitations

**Row Level Security is off** on the `leads` table. It is a deliberate demo
choice, not an oversight — Supabase warns about it at creation time and the
warning was read before it was dismissed. RLS on would block the anon key from
inserting, which is the first step of the pipeline. It is safe in this specific
case because the project is a throwaway, the only client is a localhost script,
and no real person's data is ever stored. In production this table would have RLS
on and writes restricted to a service role.

**No refusal fallbacks on the Anthropic call.** The `claude-api` guidance is to
include server-side fallbacks by default on `claude-opus-5-5`. They are omitted
here: they need a beta header and the `client.beta.messages` path, and a safety
refusal while scoring a fabricated property-management lead is close to
impossible. Called out rather than quietly dropped.

**One happy path.** There is no retry, no queue, no dead-letter handling. If
Supabase or Discord is down, the request fails and the lead is lost. A real
version needs the webhook to return 200 immediately and do the work on a queue —
a lead that arrives during an outage must not evaporate.

**The clock stops at Discord's HTTP 2xx**, which is acknowledgement rather than
the notification reaching a phone. The gap is small but it is not zero, and
"delivered" is the looser word for it.

**`received_at` in the database is the Postgres `now()` at insert time**, slightly
after the pipeline's own `t0`. Computing `delivered_at - received_at` from the
table gives a marginally shorter figure than `elapsed_seconds` on the same row.
`elapsed_seconds` is the number to trust.
