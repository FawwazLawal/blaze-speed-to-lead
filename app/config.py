"""Environment configuration.

Every secret comes from an environment variable. Nothing in this module ever
logs, prints or returns a secret's value — only whether it is present.
"""

import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED = (
    "ANTHROPIC_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "DISCORD_WEBHOOK_URL",
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


def missing() -> list[str]:
    """Names of required variables that are unset or empty."""
    return [name for name in REQUIRED if not os.environ.get(name)]


def presence_report() -> str:
    """A one-line startup summary. Presence only, never values."""
    absent = set(missing())
    return "  ".join(
        f"{name}={'MISSING' if name in absent else 'present'}" for name in REQUIRED
    )


def require_all() -> None:
    """Fail loudly at startup rather than halfway through a lead."""
    absent = missing()
    if absent:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(absent)
            + ". Copy .env.example to .env and fill them in."
        )
