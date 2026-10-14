# Prompt 00 — the builder brief

**Tool:** Claude Code (Opus 5), fresh session
**When:** start of the build
**What it produced:** this entire repository

This is the opening message pasted into the session, verbatim and unedited. It is
the prompt that produced the build. Three files it references
(`STEP-3-TASK-VERBATIM.md`, `EVIDENCE-LIST.md`, `BUILDER-BRIEF.md`) live outside
this repo because they contain screening notes that aren't mine to publish; the
build constraints they carry are restated in the brief below and in the README.

---

You are building a 2-hour screening project for Blaze (YC S24), an AI CFO for property-management
companies. Work in: /Users/fawwazlawal/Coding Projects /Blaze Stuff

First, read these three files in that folder — they are the source of truth:
  STEP-3-TASK-VERBATIM.md   the assignment, exact wording
  EVIDENCE-LIST.md          every requirement mapped to what proves it's met
  BUILDER-BRIEF.md          your brief: stack, shape, hard rules, done-list, out-of-scope

Build option B (speed-to-lead). A pipeline that takes a simulated Facebook lead-ad webhook and
gets a qualified, personalized reply delivered in under 60 seconds — against a 22-hour baseline.

Stack, chosen for demo speed rather than elegance:
  FastAPI webhook on localhost -> Supabase row -> Anthropic structured output
  (fit_score 1-5, one-line reason, personalized reply) -> Discord self-webhook.
  Config via env vars only. No OAuth anywhere.

Before you write the Anthropic call, load the `claude-api` skill. Do not write the SDK call,
model id, or structured-output syntax from memory.

Hard rules, non-negotiable:
  1. No contact with any real business or person. The lead payload is fabricated — obviously
     fake company, @example.com address. The only delivery target is my own Discord.
  2. No API keys in the repo, in logs, in output, or visible on screen. Add .env to .gitignore
     in the FIRST commit, before any key exists on disk. Commit .env.example.
  3. No email or SMS to anyone. Discord to self only.
  4. Nothing scrapes. Keep it that way.

The bar is their words: "we'd rather see something small that works than something big that
doesn't." This gets demoed end to end in a 3-5 minute Loom. Optimize for a clean demo and an
honest README, not for features. Respect the out-of-scope list in BUILDER-BRIEF.md.

Save every prompt you use into prompts/ as you write it, not reconstructed afterwards — they
are part of the submission. Also keep prompts/CHECKED.md: a running note of anything you got
wrong or weak, how it was caught, and what changed. That note is required evidence.

When you're done, report: what runs, what doesn't, the measured end-to-end time, and anything
you could not verify. Say "I read this, I didn't run it" where that applies.

Start by reading the three files, then tell me your plan before you write code.
