# What the model got wrong, how it was caught, what changed

A running note, appended while building — not reconstructed afterwards. Required
evidence for "how you checked or improved what it gave you."

Entries are in the order they happened.

---

## 1. Proposed a store the task doesn't allow

**What happened.** Asked why Supabase was needed at all, I checked the task wording
instead of defending the plan. It reads: "Append the lead to a Google Sheet (or
Airtable/Supabase)." That's a closed list of three. A local SQLite file or a JSON
log — both cleaner for a 2-hour build — would have failed the requirement as
written while looking fine to me.

**How it was caught.** Re-read the verbatim task text rather than the summary of it.

**What changed.** Supabase, chosen on friction (GitHub sign-in, one block of SQL)
rather than on taste. Also rejected a "swappable store" abstraction that would have
let the pipeline run against a local file: extra surface, no demo value, and the
demo needs the real table anyway.

## 2. Wrote `requirements.txt` from memory and got the SDK a major version wrong

**What happened.** I pinned `anthropic==0.42.0`. The current SDK is `1.13.0`.
That is not a stale-patch problem: `client.messages.parse()` — the structured-output
helper the whole qualification step is built on — does not exist in the 0.x line,
so the pipeline would have failed at the one call that matters. The other six pins
were wrong too (`fastapi==0.115.6` vs `0.143.0`, `supabase==2.11.0` vs `2.32.0`).

**How it was caught.** Installed the dependencies unpinned and printed the resolved
versions and `hasattr(client.messages, "parse")` instead of trusting the file I had
just written.

**What changed.** `requirements.txt` now carries the versions actually installed and
run. Worth noting the near miss: I had loaded the `claude-api` skill for the API
surface, which is why the *call* was right, but I wrote the dependency pin from
memory anyway — the discipline has to cover the version too, not just the syntax.

## 3. Two more patterns written from memory that the runtime rejected

Both found in the same pass, by importing the app with
`python -W error::DeprecationWarning` instead of assuming it was fine.

**(a) Clients constructed at import time.** `store.py` called `create_client()`
at module scope. Because imports are hoisted, that ran *before*
`config.require_all()`, so a user with no `.env` got
`SupabaseException: supabase_url is required` instead of the clear
"Missing required environment variables: ..." message the config module exists to
produce. `qualify.py` had the same shape. **Changed:** both clients are now built
on first use behind a `_client()` accessor, so the config check is what fails first.

**(b) `@app.on_event("startup")` is deprecated.** FastAPI 0.143 raises a
`DeprecationWarning` for it and points at lifespan handlers. I wrote the old
pattern because it is what I remembered. **Changed:** replaced with an
`asynccontextmanager` lifespan. Import is now clean with warnings as errors.

The theme across entries 2 and 3: the `claude-api` skill kept me honest about the
*Anthropic* call, and every single thing I wrote from memory around it — the
dependency pins, the client lifecycle, the FastAPI startup hook — was wrong.

## 4. Adversarial review by a second agent — five findings, four fixed, one argued with

Prompt: [`01-adversarial-review.md`](01-adversarial-review.md). A fresh sub-agent with
no memory of writing the code, told its default posture was disagreement and that
"this could be more robust" was not a finding. It was not told what I thought was
wrong. **Every finding below was then checked by running something — not by
agreeing with it.** One of its claims was overstated and one of its proposed fixes
was impossible; both are recorded as found.

### F1 — a failed Discord POST printed the webhook token to the terminal. Real, and the worst of the five.

The webhook URL carries the credential in its path, and httpx builds
`HTTPStatusError`'s message from the full URL. Nothing caught it, so it would
surface as an uvicorn traceback — in the terminal being screen-recorded.

*Checked by:* pointing the code at a local server returning 401 with a fake token
in the path and printing the traceback. The token appeared verbatim:
`Client error '400 Bad Request' for url '...webhooks/139.../FAKE-TOKEN-xN4pQ...'`.

*Changed:* both httpx failure modes are re-raised as a `RuntimeError` carrying only
the status code, with `from None` so the chained original cannot leak it either.
*Re-checked:* same reproduction now prints `Discord rejected the card: HTTP 401`,
and the token appears nowhere in the full traceback.

This one mattered most because its consequence is the only unbounded one. A wrong
number gets corrected in the README; a live credential in a Loom means rotating the
key and re-recording.

### F2 — nothing bounded the Anthropic call below 60 seconds. Real.

*Checked by:* computing what the SDK actually does, after my first attempt to verify
imported a symbol that does not exist at module scope — my error, not the reviewer's.
`_calculate_nonstreaming_timeout` is a client method; `claude-opus-5-5` is not in
`MODEL_NONSTREAMING_TOKENS`, so our call gets a **600-second** read timeout, and
`DEFAULT_MAX_RETRIES` is 2. **Worst case 1800 seconds** behind a project whose entire
claim is "under 60". The failure mode is a silent multi-minute stall, not an error.

*Changed:* `timeout=18.0` and `max_retries=1` on the call — worst case 36s, leaving
headroom for the Supabase and Discord legs. Note this needed *both*: an 18s timeout
with the default 2 retries is still 54s, and 25s with 2 retries would have been 75s.

### F3 — the card's elapsed number excluded the POST carrying it. Real; its proposed fix was not.

The value handed to `send_card` is sampled on the line before `httpx.post` runs, so
the footer could not include the Discord round-trip. The reviewer called this "a
one-line reorder."

**It is not reorderable, and I disagree with that part.** A card cannot state how
long its own delivery took — the number has to be sampled before the POST that
carries it. The defect is real but it is a labelling defect, not an ordering one.

*Changed:* the footer now reads `received → reply drafted`, which is true of what it
measures, and `send_card`'s docstring says why. The full received-to-delivered figure
— which does include the POST — is logged, returned in the HTTP response, and stored
on the row. Two numbers, both honest, neither mislabelled.

### F4 — `parsed_output` can be None. Real. "The refusal guard is unreachable" — overstated.

*Checked by:* reading the installed SDK. `parsed_output` is genuinely
`Optional[ResponseFormatT]` and returns None when no text block carries a parsed
result — that would have hit `q.fit_score` as an opaque `AttributeError`.

But the claim that the `stop_reason == "refusal"` branch is "never reached" is too
strong. `parse_text` runs `validate_json` inside `parse()`, so a refusal carrying
*prose* does raise first — correct. A refusal with **no text block at all** raises
nothing there and reaches the guard normally. The branch is narrow, not dead.

*Changed:* added the None guard; rewrote the docstring to state the actual split
rather than the reviewer's version of it.

### F5 — two files pointed at a README that was a placeholder. Real.

`schema.sql` claimed the RLS decision was "noted in the README as well"; the builder
brief said the constraints were restated there. Neither was true — the README was
three lines. *Changed:* README written.

### What it found nothing on

Secrets reaching the repo (`.env` ignored in the first commit, `git ls-files` clean),
outbound contact with anyone real (one `httpx.post`, to the author's own Discord),
and scraping (no fetcher or parser anywhere). It also independently confirmed the
Anthropic call surface against the installed SDK — model id, every argument, the
`output_config` shape — which is the part the `claude-api` skill was loaded for.

## 5. I assumed RLS was off. The first live run proved it wasn't.

**What happened.** `schema.sql` was written with a comment explaining that Row
Level Security was "intentionally left OFF for this demo", and I told Fawwaz the
pipeline would work as long as he didn't enable it. The first real end-to-end run
failed at the first step:

```
postgrest.exceptions.APIError: {'message': 'new row violates row-level security
policy for table "leads"', 'code': '42501'}
```

RLS was on. My belief about the state of the database was simply wrong, and every
piece of reasoning downstream of it — including a paragraph in the README's known
limitations explaining *why* RLS was off — was confidently describing something
that was not the case.

**How it was caught.** By running the pipeline against the real database. Nothing
in the code, the schema file, or the review would have caught it: the whole class
of error lives in the gap between what I believed about an external system and
what was true of it. Worth noting the adversarial review in entry 4 did not catch
this either — it reviewed the source, and the source was self-consistent.

**What changed.** Rather than switching RLS off to match the comment, the fix went
the other way: RLS stays on and `schema.sql` now grants the anon role explicit
insert/select/update policies on this one table. That is better than what I
originally wrote — it is scoped, it is visible in the schema, it keeps Supabase's
security linter clean, and it does not require clicking past a security warning on
camera. The file is also now idempotent so it can be re-run over the existing table.

**The general lesson, which is the one worth saying in the Loom:** entries 2, 3 and
4 were all caught by reading code or SDK source. This one could only be caught by
running the thing against the real world. An assumption about an external system
is not checkable by review, however adversarial.

## 6. The README published the client's own funnel numbers to a public repo

**What happened.** The opening paragraph carried Blaze's internal figures from a
separate exercise — qualified-lead and booking counts, and a loss percentage —
as colour for why speed matters. The repository is public. Those numbers went to
the open internet under my author's name, in a repo built for a company whose
product is finance software.

**How it was caught.** Re-reading the README as a published artifact rather than
as a document, and asking a different question than "is this accurate?" — namely
"should this be legible to everyone, forever?" Accuracy was never the problem.
Every one of those figures was correct.

**What changed.** The specific figures are gone; the 22-hour baseline stays,
because that one comes from the assignment's own wording and is the premise of
the build rather than someone's internal data. `git ls-files | xargs grep` over
the whole tree confirms nothing else carried them.

**Worth recording because it is a different failure mode from the other five.**
Entries 2-4 were caught by reading code, entry 5 by running it. This one was only
visible by asking who the audience is. No test, no reviewer and no amount of
running would have surfaced it, because nothing was broken.

## 7. "The seam is the sender, and nothing else" — confidently wrong

**What happened.** Asked how this would connect to a real Facebook lead ad, I
wrote a line into the README saying `app/main.py` cannot tell a `curl` POST from
a Facebook POST, so the only difference is who sends it. It reads well and it is
false.

**How it was caught.** Looking it up instead of writing Meta's API from memory —
the same rule that applied to the Anthropic SDK. Meta's `leadgen` webhook does
**not** contain the lead. It carries a `leadgen_id` and no name, email or answers
at all; the server has to make a second authenticated Graph API call to fetch
`field_data`, whose keys vary per form. So the real adapter is a verification
handshake, a Graph call, an explicit per-form field mapping, and a queue — not a
change of sender.

**What changed.** The README paragraph now says the seam is the sender *and the
payload shape*, and a new section sets out what the real integration actually
requires, labelled as researched and not built. Where sources disagreed on the
App Review permission list, the README says they disagree rather than picking one.

**Third time the same lesson.** Entry 2 was a dependency version written from
memory. Entry 3 was a framework pattern written from memory. This was a
third-party API written from memory — in the README rather than in code, where
nothing would ever have failed to flag it. Prose is the easiest place to be
confidently wrong, because it does not run.

## 8. The drafted reply was correct and unusable

**What happened.** The first prompt produced replies that passed every rule I had
written — specific to the lead, no filler openers, a concrete next step — and
still read like a brochure:

> Hi Dana, managing 420 doors across three markets with a nine-day month-end
> close and August rent still outstanding is a heavy load, especially without a
> bookkeeper since September. Blaze handles rent reconciliation, owner
> statements, payables and month-end close for property-management companies,
> which is the work that has been piling up for you. Would you have 20 minutes
> this week for a short call so we can look at how your books are set up today?

70 words. Two specific faults, neither of which my rules caught:

1. **It mirrors back all four details the lead gave.** I had written "must
   reference something specific", and the model satisfied it by referencing
   *everything* specific. Repeating a person's message back to them is what a
   machine does to prove it parsed the input.
2. **It lists four product features.** "Rent reconciliation, owner statements,
   payables and month-end close" is a brochure line, and it sits between the hook
   and the ask — exactly where attention is leaking.

**How it was caught.** Not by me, and not by the adversarial reviewer. Fawwaz read
a delivered card and said it was too long and not human enough. The output was
correct against its spec; the spec was wrong. That is invisible to any check that
asks "does this meet the requirements?"

**What changed.** `qualify_lead.md` now caps the reply at 55 words, says to pick
**one** detail rather than all of them, requires Blaze's offering in a single
clause rather than a list, bans a specific set of sales words, and carries a
worked example to set economy rather than wording.

**Measured, not assumed.** Three runs before: ~70 words. Three runs after: 36, 43,
36 words, with the fit score unchanged at 4 and latency unchanged. The specificity
survived — every new reply still names the lost bookkeeper and the nine-day close.

**The lesson that is not in the other seven entries.** Everything else here was
caught by reading code, running code, or looking something up. This one needed a
human to look at the output and say "I wouldn't send that." A prompt can satisfy
every constraint you wrote and still be wrong, because the constraints were the
thing that was wrong.

## 9. The predicted failure actually happened, and the fix held

**What happened.** During a rehearsal run, Discord returned **HTTP 503**. This is
precisely the failure path entry 4 (finding F1) was about: a non-2xx from the
Discord webhook, which before the fix would have printed the full webhook URL —
and therefore the credential in its path — into an uvicorn traceback.

**What appeared on screen instead:**

```
File ".../app/notify.py", line 69, in send_card
  raise RuntimeError(
    f"Discord rejected the card: HTTP {exc.response.status_code}"
  ) from None
RuntimeError: Discord rejected the card: HTTP 503
```

Status code surfaced, token absent, and `from None` kept the original httpx
exception — the one carrying the URL — out of the chained traceback.

**Why this entry exists.** Entry 4 recorded a fix verified against a reproduction
I built myself with a fake token. This is the same failure arriving unprompted,
from Discord's real infrastructure, on a real credential. A reproduction proves a
fix works against your model of the failure. This proves it works against the
failure.

**Not fixed, deliberately.** 503 is transient and the pipeline has no retry — the
lead is lost and the request errors. That is the documented behaviour, not a
regression: the README's "one happy path" limitation says exactly this, and the
remedy is the queue described there, not a retry bolted on to make a demo
smoother. Adding one now would also hide the failure mode that just demonstrated
the sanitising works.

