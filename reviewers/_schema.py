"""Shared Pydantic schema for sub-agent structured outputs."""
from typing import List

from pydantic import BaseModel, Field

from models.schemas import Issue


class SubAgentReviewOutput(BaseModel):
    issues: List[Issue] = Field(default_factory=list, description="List of detected issues in the code")
