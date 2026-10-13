# Speed-to-lead

A Facebook lead ad comes in. A scored, personalised reply is sitting in Discord
**4.7 seconds** later.

Blaze's inbound first response takes **22 hours**. The lead has moved on by then —
the useful window is while they still have the tab open. This is the smallest
thing that closes it.

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

This is a deliberately small build. There is no Facebook OAuth — the payload is
fabricated and fired with `curl`. No UI, no queue, no auth, no
deploy, and no application-level retries. One happy path, measured.

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

Three consecutive live runs of the fabricated lead, measured end to end —
request received to Discord acknowledging the card:

| Run | Row | Fit | Elapsed |
|---|---|---|---|
| 1 | 2 | 4/5 | **6.76s** |
| 2 | 3 | 4/5 | **3.95s** |
| 3 | 4 | 4/5 | **4.71s** |

Run 1 is slowest because the API clients are built lazily on first use, inside
that request's window. The Anthropic call dominates all three (~4–5s); Supabase
and Discord are sub-second once the clients exist. Against a 22-hour baseline,
4.7 seconds is roughly **17,000x faster** — but the honest framing is that the
useful threshold is "while the lead still has the tab open", and anything in
single-digit seconds clears it.

The reply from run 1, verbatim:

> Hi Dana, managing 420 doors across three markets with a nine-day month-end
> close and August rent still outstanding is a heavy load, especially without a
> bookkeeper since September. Blaze handles rent reconciliation, owner
> statements, payables and month-end close for property-management companies,
> which is the work that has been piling up for you. Would you have 20 minutes
> this week for a short call so we can look at how your books are set up today?

It names the door count, the nine-day close, the August arrears and the missing
bookkeeper — all four from the lead's own free text. It would not read the same
for any other lead, which was the bar set in the prompt.

**On the score:** 4, not 5, on all three runs. The rubric puts 420 doors in the
200–499 band (baseline 3) and adds one for a named finance pain. A 5 would need
1500+ doors. Getting a consistent, rubric-correct 4 rather than a flattering 5 is
the evidence that the scoring is doing something.

Full artifacts: [`samples/run_output.json`](samples/run_output.json),
[`samples/server_log.txt`](samples/server_log.txt),
[`samples/supabase_rows.json`](samples/supabase_rows.json).

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

**Row Level Security is on, with permissive policies.** The `leads` table has
explicit `anon` insert/select/update policies (see [`schema.sql`](schema.sql)).
They allow everything, which is appropriate for a throwaway project whose only
client is a localhost script and whose only row is a fabricated lead — but it is
a demo posture, not a production one. A real version would drop these policies
and write through a service role. This was not the original design: the first
live run failed on an RLS violation and the fix went this way rather than
switching RLS off. See [`prompts/CHECKED.md`](prompts/CHECKED.md) entry 5.

**No refusal fallbacks on the Anthropic call.** The `claude-api` guidance is to
include server-side fallbacks by default on `claude-opus-5-5`. They are omitted
here: they need a beta header and the `client.beta.messages` path, and a safety
refusal while scoring a fabricated property-management lead is close to
impossible. Called out rather than quietly dropped.

**One happy path.** No queue, no dead-letter handling, and no application-level
retry (the Anthropic call retries once at the SDK level; nothing else does). If
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
