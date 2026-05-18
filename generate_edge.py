"""Generate AGREEABLE voice lines using Edge TTS (free, no API key).

Microsoft's neural voices via the edge-tts library — no signup, no API key,
free tier with no published daily cap. Lower expressiveness than ElevenLabs,
but it respects the ellipsis pause trick and the voices fit the cast.

Voice picks (swap freely):
  NARRATOR  en-US-AndrewNeural      warm baritone, documentary feel
  MARTA     en-GB-SoniaNeural       reserved British female (slowed for fatigue)
  DIETER    en-US-DavisNeural       round, friendly, slightly faster
  YUSUF     en-US-BrianNeural       younger US male
  ARIA      en-US-AriaNeural        gentle, calm (and the name fits)
  CHEN      en-SG-WayneNeural       Singapore English — matches Chen's bio

Usage:
    pip install -r requirements-edge.txt
    python3 generate_edge.py --episode 1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_VALID_BYTES = 5 * 1024

VOICES = {
    "NARRATOR": ("en-US-AndrewNeural",  "+0%"),
    "MARTA":    ("en-GB-SoniaNeural",   "-5%"),
    "DIETER":   ("en-US-DavisNeural",   "+5%"),
    "YUSUF":    ("en-US-BrianNeural",   "+0%"),
    "ARIA":     ("en-US-AriaNeural",    "-3%"),
    "CHEN":     ("en-SG-WayneNeural",   "+0%"),
}


async def synthesize(text: str, voice: str, rate: str, dest: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(dest))


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--episode", type=int, required=True, choices=range(1, 7),
                        help="Episode number (1-6)")
    args = parser.parse_args()

    ep_dir = HERE / f"agreeable_ep{args.episode}"
    script_path = ep_dir / "script.json"
    if not script_path.exists():
        print(f"ERROR: {script_path} not found.", file=sys.stderr)
        return 2

    script = json.loads(script_path.read_text(encoding="utf-8"))
    voices_dir = ep_dir / "voices"
    voices_dir.mkdir(parents=True, exist_ok=True)

    total = len(script)
    generated = skipped = 0
    print(f"Episode {args.episode}: {total} lines  ->  {voices_dir}")

    for i, entry in enumerate(script, 1):
        entry_id = entry["id"]
        character = entry["character"]
        text = entry["text"]
        dest = voices_dir / f"{entry_id}.mp3"

        if dest.exists() and dest.stat().st_size >= MIN_VALID_BYTES:
            skipped += 1
            print(f"[{i:02d}/{total}] {entry_id:>10s}  skip ({dest.stat().st_size // 1024} KB)")
            continue

        if character not in VOICES:
            print(f"ERROR: no Edge voice mapped for {character}", file=sys.stderr)
            return 1

        voice, rate = VOICES[character]
        print(f"[{i:02d}/{total}] {entry_id:>10s}  {character:<8s} {voice:<22s} {text[:50]!r}")
        await synthesize(text, voice, rate, dest)
        generated += 1

    print()
    print(f"Generated: {generated}   Skipped: {skipped}")
    missing = [e["id"] for e in script if not (voices_dir / f"{e['id']}.mp3").exists()]
    if missing:
        print(f"MISSING: {missing}", file=sys.stderr)
        return 1
    print(f"All {total} voice lines present. Ready to assemble.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
