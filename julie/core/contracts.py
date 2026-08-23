"""
Julie-Core Type Contracts & State Schemas
=========================================
Strict domain contracts and state representations for Julie voice agent.
"""

from dataclasses import dataclass
from typing import Literal

JulieState = Literal["idle", "listening", "thinking", "speaking", "executing"]


@dataclass(frozen=True, slots=True)
class VoiceIntentPayload:
    raw_transcript: str
    target_job: str
    requires_quant_telemetry: bool
