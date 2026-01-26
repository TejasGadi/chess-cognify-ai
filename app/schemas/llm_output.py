"""
Pydantic schemas for LLM structured output.
"""
from pydantic import BaseModel, Field
from typing import List


class ExplanationOutput(BaseModel):
    """Structured output for move explanations."""

    explanation: str = Field(
        ...,
        description="Clear, educational explanation of why the best move is better (max 4 sentences)",
    )


class WeaknessOutput(BaseModel):
    """Structured output for weakness detection."""

    weaknesses: List[str] = Field(
        ...,
        description="List of 3-5 high-level weakness categories (chess concepts, not specific moves)",
        min_length=3,
        max_length=5,
    )
