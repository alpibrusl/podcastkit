"""Generate AGREEABLE voice lines using Kokoro (free, open-source, runs locally).

Kokoro-82M is an Apache 2.0 TTS model (~300 MB) that runs on CPU. Quality is
unusually close to commercial TTS for this kind of dry-reading comedy. First
run downloads the model from Hugging Face.

Voice picks (swap freely — Kokoro ships a few dozen):
  NARRATOR  bm_george       British male, dry documentary
  MARTA     bf_emma         British female, reserved
  DIETER    am_michael      US male, warm and hearty
  YUSUF     am_adam         US male, younger
  ARIA      af_bella        US female, warm and calm
  CHEN      bm_daniel       British male, formal

Requires ffmpeg on PATH (used to encode the model's raw audio to MP3).

Usage:
    pip install -r requirements-kokoro.txt
    python3 generate_kokoro.py --episode 1
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MIN_VALID_BYTES = 5 * 1024
KOKORO_SAMPLE_RATE = 24000

VOICES = {
    "NARRATOR": "bm_george",
    "MARTA":    "bf_emma",
    "DIETER":   "am_michael",
    "YUSUF":    "am_adam",
    "ARIA":     "af_bella",
    "CHEN":     "bm_daniel",
}

_pipelines: dict[str, object] = {}


def get_pipeline(voice_name: str):
    """Cache one KPipeline per language code. Kokoro's American (a) and
    British (b) phonemizers differ — pick the one matching the voice prefix."""
    from kokoro import KPipeline
    lang = voice_name[0]  # 'a' for af_/am_, 'b' for bf_/bm_
    if lang not in _pipelines:
        _pipelines[lang] = KPipeline(lang_code=lang)
    return _pipelines[lang]


def write_mp3(audio: np.ndarray, sample_rate: int, dest: Path) -> None:
    if shutil.which("ffmpeg") is None:
        sys.exit("ERROR: ffmpeg not on PATH. Install it and retry.")
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "s16le", "-ar", str(sample_rate), "-ac", "1", "-i", "pipe:0",
        "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        str(dest),
    ]
    subprocess.run(cmd, input=pcm, check=True)


def synthesize(text: str, voice: str, dest: Path) -> None:
    pipeline = get_pipeline(voice)
    chunks = []
    for _, _, audio in pipeline(text, voice=voice):
        # Kokoro returns torch tensors; convert to numpy.
        chunks.append(audio.cpu().numpy() if hasattr(audio, "cpu") else np.asarray(audio))
    if not chunks:
        raise RuntimeError(f"Kokoro produced no audio for: {text[:60]!r}")
    write_mp3(np.concatenate(chunks), KOKORO_SAMPLE_RATE, dest)


def main() -> int:
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
    print("(first run: downloading Kokoro model from Hugging Face — ~300 MB)")

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
            print(f"ERROR: no Kokoro voice mapped for {character}", file=sys.stderr)
            return 1

        voice = VOICES[character]
        print(f"[{i:02d}/{total}] {entry_id:>10s}  {character:<8s} {voice:<14s} {text[:50]!r}")
        synthesize(text, voice, dest)
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
    sys.exit(main())
