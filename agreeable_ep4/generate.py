"""Generate all voice lines for AGREEABLE Episode 4 via ElevenLabs.

Reads script.json, POSTs each line to ElevenLabs, saves MP3s to voices/.
Skips files that already exist. Retries with exponential backoff.

CHEN is a new character introduced in Episode 4. Pick an ElevenLabs voice for
him (the bible suggests slightly formal, English-as-second-language precise —
e.g., Bill or Daniel with higher stability) and paste the voice_id below.

Run:
    export ELEVENLABS_API_KEY=sk_...
    python3 generate.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
SCRIPT_PATH = HERE / "script.json"
VOICES_DIR = HERE / "voices"

VOICES = {
    "NARRATOR": {"voice_id": "nPczCjzI2devNBz1zQrb", "model_id": "eleven_multilingual_v2"},
    "MARTA":    {"voice_id": "Xb7hH8MSUJpSbSDYk0k2", "model_id": "eleven_multilingual_v2"},
    "DIETER":   {"voice_id": "JBFqnCBsd6RMkjVDRZzb", "model_id": "eleven_multilingual_v2"},
    "YUSUF":    {"voice_id": "TX3LPaxmHKxFdv7VOQHJ", "model_id": "eleven_multilingual_v2"},
    "ARIA":     {"voice_id": "XB0fDUnXU5powFXDhCwa", "model_id": "eleven_multilingual_v2"},
    # TODO: pick an ElevenLabs voice for CHEN and paste the ID here.
    "CHEN":     {"voice_id": "REPLACE_ME_CHEN_VOICE_ID", "model_id": "eleven_multilingual_v2"},
}

VOICE_SETTINGS = {
    "NARRATOR": {"stability": 0.70, "similarity_boost": 0.70, "style": 0.0,  "use_speaker_boost": True},
    "MARTA":    {"stability": 0.65, "similarity_boost": 0.70, "style": 0.0,  "use_speaker_boost": True},
    "DIETER":   {"stability": 0.40, "similarity_boost": 0.75, "style": 0.30, "use_speaker_boost": True},
    "YUSUF":    {"stability": 0.55, "similarity_boost": 0.75, "style": 0.10, "use_speaker_boost": True},
    "ARIA":     {"stability": 0.50, "similarity_boost": 0.75, "style": 0.0,  "use_speaker_boost": True},
    "CHEN":     {"stability": 0.75, "similarity_boost": 0.70, "style": 0.0,  "use_speaker_boost": True},
}

API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"
MIN_VALID_BYTES = 5 * 1024
MAX_RETRIES = 3
POLITE_SLEEP = 1.0


def synthesize(api_key: str, character: str, text: str, dest: Path) -> None:
    voice = VOICES[character]
    url = f"{API_BASE}/{voice['voice_id']}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": text,
        "model_id": voice["model_id"],
        "voice_settings": VOICE_SETTINGS[character],
    }

    backoff = 2
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(url, headers=headers, json=body, timeout=60)
        if resp.status_code == 200:
            dest.write_bytes(resp.content)
            if dest.stat().st_size < MIN_VALID_BYTES:
                raise RuntimeError(f"response too small ({dest.stat().st_size} bytes) — likely silent failure")
            return
        if resp.status_code == 401:
            raise RuntimeError("401 unauthorized — check ELEVENLABS_API_KEY")
        if resp.status_code == 404:
            raise RuntimeError(
                f"404 on voice_id {voice['voice_id']} for {character} — "
                f"ElevenLabs may have rotated the public catalog. Provide a replacement voice ID."
            )
        if resp.status_code == 429:
            wait = 30
            print(f"  ! 429 rate-limited, sleeping {wait}s")
            time.sleep(wait)
            continue
        print(f"  ! attempt {attempt} got {resp.status_code}: {resp.text[:200]}")
        if attempt == MAX_RETRIES:
            raise RuntimeError(f"failed after {MAX_RETRIES} attempts for {character}")
        time.sleep(backoff)
        backoff *= 2


def main() -> int:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY is not set in environment.", file=sys.stderr)
        print("       export ELEVENLABS_API_KEY=sk_... and retry.", file=sys.stderr)
        return 2

    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    VOICES_DIR.mkdir(parents=True, exist_ok=True)

    total = len(script)
    skipped = generated = 0
    print(f"Loaded {total} lines from {SCRIPT_PATH.name}")

    for i, entry in enumerate(script, 1):
        entry_id = entry["id"]
        character = entry["character"]
        text = entry["text"]
        dest = VOICES_DIR / f"{entry_id}.mp3"

        if dest.exists() and dest.stat().st_size >= MIN_VALID_BYTES:
            skipped += 1
            print(f"[{i:02d}/{total}] {entry_id:>10s}  skip (exists, {dest.stat().st_size // 1024} KB)")
            continue

        print(f"[{i:02d}/{total}] {entry_id:>10s}  {character:<8s}  {text[:60]!r}")
        synthesize(api_key, character, text, dest)
        generated += 1
        time.sleep(POLITE_SLEEP)

    missing = [e["id"] for e in script if not (VOICES_DIR / f"{e['id']}.mp3").exists()]
    small = [
        e["id"] for e in script
        if (VOICES_DIR / f"{e['id']}.mp3").exists()
        and (VOICES_DIR / f"{e['id']}.mp3").stat().st_size < MIN_VALID_BYTES
    ]

    total_bytes = sum(
        (VOICES_DIR / f"{e['id']}.mp3").stat().st_size
        for e in script
        if (VOICES_DIR / f"{e['id']}.mp3").exists()
    )
    print()
    print(f"Generated: {generated}   Skipped (already present): {skipped}")
    print(f"Total voices size: {total_bytes / 1024 / 1024:.2f} MB")

    if missing:
        print(f"MISSING: {missing}", file=sys.stderr)
        return 1
    if small:
        print(f"TOO SMALL (likely partial response, delete and rerun): {small}", file=sys.stderr)
        return 1

    print(f"All {total} voice lines present and >5KB. Ready to assemble.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
