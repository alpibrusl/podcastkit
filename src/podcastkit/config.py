from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel


class VoiceConfig(BaseModel):
    backend: Literal["chatterbox", "elevenlabs", "kokoro", "openai"]
    voice_id: str                       # ElevenLabs voice_id, Kokoro voice name, or OpenAI voice name
    model_id: str = ""                  # ElevenLabs model_id; unused for others
    settings: dict[str, Any] = {}      # ElevenLabs voice_settings; unused for others


class TimelineEntry(BaseModel):
    id: str
    pre_silence: float = 0.5


# anchor: [line_id, "start"|"end", offset_seconds]
Anchor = tuple[str, Literal["start", "end"], float]


class BgTrack(BaseModel):
    file: str
    start: Anchor
    fade_in: float = 2.0
    fade_out_at: Anchor
    fade_out_dur: float = 2.0
    volume_db: float = -25.0
    loop: bool = True


class SfxHit(BaseModel):
    file: str
    at: Anchor
    volume: float = 0.6


class EpisodeConfig(BaseModel):
    title: str = ""
    output: str = "episode.mp3"
    voices: dict[str, VoiceConfig]
    timeline: list[TimelineEntry]
    bg_tracks: list[BgTrack] = []
    sfx_hits: list[SfxHit] = []
