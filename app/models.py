"""Payload and result shapes.

`Lead` mirrors the six fields a Facebook lead-ad form would deliver.
`Qualification` is the schema the LLM is required to return.
"""

from pydantic import BaseModel, Field


class Lead(BaseModel):
    """A lead as it arrives from the (simulated) Facebook lead-ad webhook."""

    name: str
    email: str
    phone: str
    company: str
    doors: int = Field(ge=0, description="Units under management")
    message: str


class Qualification(BaseModel):
    """What the LLM must return. Enforced as a structured-output schema."""

    fit_score: int = Field(ge=1, le=5)
    reason: str
    reply: str
