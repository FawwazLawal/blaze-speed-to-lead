# Prompt 01 — adversarial self-review

**Tool:** Claude Code (Opus 5), fresh sub-agent with no memory of writing the code
**When:** after the pipeline imported cleanly and the Discord card shape verified,
before the first live end-to-end run
**Why a fresh agent:** a reviewer that just wrote the code will defend it. This one
was given the files and the task, and explicitly *not* given my opinion of them.

Every finding it returned was then checked by running the code. The outcome —
including the findings that turned out to be wrong — is in `CHECKED.md`.

---

You are reviewing a small Python project adversarially. Your default posture is
disagreement: assume the code is wrong until the code itself proves otherwise.
Do not be agreeable. Do not praise anything. Do not suggest features.

The project is a 2-hour screening build: a webhook receives a fabricated
Facebook lead-ad payload, stores it in Supabase, calls the Anthropic API for a
1-5 fit score plus a drafted reply, and posts a card to a Discord webhook. The
single headline claim is that received -> delivered takes under 60 seconds.

Read every file in the repository at the path given below. Then report, in order
of how badly it would hurt a live end-to-end demo:

1. Anything that will throw, hang, or silently produce a wrong result at runtime.
   Name the exact line and the exact input or condition that triggers it.
2. Anywhere the stated constraints are actually violated, not just unfashionable:
   a secret that could reach the repo, a log line or output or Discord card that
   could print a key's value, any outbound contact with a real person or business,
   anything that scrapes.
3. Any place the elapsed-time number is measured or reported in a way that
   overstates how fast the pipeline is. Be specific about what the number
   includes and excludes.
4. Anything in the README or comments that claims something the code does not do.

Rules for your report:
- A finding needs a concrete failure path: the input, the line, the result. "This
  could be more robust" is not a finding and you should not write it.
- If you cannot find a real problem in one of the categories above, say so for
  that category rather than inventing something to fill it.
- Do not propose refactors, abstractions, tests, or error handling that the
  demo does not need. The brief explicitly rules those out.
- Rank your findings. Say which single one you would fix first and why.
