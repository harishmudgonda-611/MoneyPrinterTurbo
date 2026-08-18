from typing import Literal

from pydantic import BaseModel, Field


class ReferenceVideoAnalysis(BaseModel):
    reference_id: str
    duration_seconds: float = Field(ge=0)
    width: int = Field(ge=0)
    height: int = Field(ge=0)
    fps: float = Field(ge=0)
    has_audio: bool
    shot_count: int = Field(ge=0)
    average_shot_seconds: float = Field(ge=0)
    pacing: Literal["slow", "medium", "fast", "very_fast"]
    hook_window_seconds: float = Field(ge=0)
    structure: list[str]
    creative_principles: list[str]
    originality_rules: list[str]
