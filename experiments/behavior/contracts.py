"""The narrow native sensor contract migrated from physical-ai-lab."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Stamp(Contract):
    session: str = Field(min_length=1)
    epoch: int = Field(ge=0, strict=True)
    sequence: int = Field(ge=0, strict=True)

    def same_episode(self, other: Stamp) -> bool:
        return (self.session, self.epoch) == (other.session, other.epoch)


class Evidence(Contract):
    id: str = Field(min_length=1)
    stamp: Stamp
    observed_at: FiniteFloat
    source: Literal["rgb", "depth"]
    uri: str


class Observation(Contract):
    stamp: Stamp
    observed_at: FiniteFloat
    rgb: dict[str, Evidence]
    depth: dict[str, Evidence] = Field(default_factory=dict)
    proprio: tuple[FiniteFloat, ...] = Field(min_length=61, max_length=61)

    @model_validator(mode="after")
    def aligned(self):
        for kind in ("rgb", "depth"):
            for evidence in getattr(self, kind).values():
                if (evidence.stamp != self.stamp or evidence.source != kind
                        or evidence.observed_at != self.observed_at):
                    raise ValueError("Mixed image stamps, timestamps or modalities")
        return self
