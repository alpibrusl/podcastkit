"""Assemble AGREEABLE Episode 1 into a single MP3.

Two-pass ffmpeg pipeline:
  Pass 1: concat voice lines with prepended silences -> build/voices_track.wav
  Pass 2: mix in ambience, music, SFX overlays -> episode_01.mp3
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT_PATH = HERE / "script.json"
VOICES_DIR = HERE / "voices"
SFX_DIR = HERE / "sfx"
MUSIC_DIR = HERE / "music"
BUILD_DIR = HERE / "build"
VOICES_TRACK = BUILD_DIR / "voices_track.wav"
OUTPUT = HERE / "episode_01.mp3"

TAIL_PAD_SEC = 5.0
SAMPLE_RATE = 44100


# Ordered timeline of voice lines with the silence (seconds) prepended to each.
# Silence before every ARIA line is >=1.0s — non-negotiable per the spec.
TIMELINE = [
    # SCENE 1 — cold open
    ("narr_01",  0.5),
    ("marta_01", 0.6),
    ("narr_02",  0.5),
    ("yusuf_01", 0.5),
    ("marta_02", 0.5),
    ("yusuf_02", 0.4),
    ("marta_03", 0.9),
    ("narr_03",  0.5),
    ("aria_01",  1.2),
    ("narr_04",  0.7),
    ("marta_04", 0.5),
    ("aria_02",  1.0),
    # SCENE 2 — Marta's desk
    ("narr_05",  1.0),
    ("aria_03",  1.0),
    ("narr_06",  0.5),
    ("marta_05", 0.4),
    ("aria_04",  1.0),
    ("marta_06", 0.5),
    ("narr_07",  0.4),
    ("aria_05",  1.5),
    ("narr_08",  0.7),
    # SCENE 3 — Dieter's office
    ("narr_09",  1.2),
    ("dieter_01", 0.4),
    ("dieter_02", 0.5),
    ("marta_07", 0.4),
    ("dieter_03", 0.3),
    ("marta_08", 0.4),
    ("dieter_04", 0.3),
    ("marta_09", 0.4),
    ("dieter_05", 0.3),
    # SCENE 4 — back at Marta's desk
    ("narr_10",  1.2),
    ("aria_06",  1.0),
    ("narr_11",  0.6),
    ("marta_10", 0.5),
    ("aria_07",  1.2),
    ("narr_12",  0.6),
    ("aria_08",  1.0),
    ("marta_11", 0.7),
    ("aria_09",  1.0),
    ("narr_13",  0.5),
    ("narr_14",  0.5),
    # SCENE 5 — Yusuf's desk at night
    ("narr_15",  1.5),
    ("yusuf_03", 0.6),
    ("narr_16",  0.5),
    ("yusuf_04", 0.7),
    ("narr_17",  0.5),
    ("aria_10",  1.2),
    ("yusuf_05", 0.4),
    ("aria_11",  1.0),
    ("narr_18",  0.7),
    ("yusuf_06", 0.7),
    ("aria_12",  1.0),
    ("narr_19",  0.7),
    # SCENE 6 — Marta's apartment
    ("narr_20",  1.5),
    ("narr_21",  0.5),
    ("aria_13",  1.2),
    ("narr_22",  0.6),
    ("aria_14",  1.0),
    ("narr_23",  0.6),
    ("aria_15",  1.5),
    ("narr_24",  0.8),
]


# Volume helpers: dB -> linear gain
def db(x: float) -> float:
    return 10 ** (x / 20.0)


# Background tracks (long, often looped).
# anchor format: (line_id, "start"|"end"), offset is seconds relative to that anchor.
BG_TRACKS = [
    # Office ambience: scene 1 -> end of scene 4
    {
        "file": SFX_DIR / "office_ambience.mp3",
        "start": ("narr_01", "start", 0.0),
        "fade_in": 2.0,
        "fade_out_at": ("narr_14", "end", 0.0),
        "fade_out_dur": 2.0,
        "volume": db(-25),
        "loop": True,
    },
    # Cold-open piano: in at narr_01 start, fade out 1.5s starting at narr_01 end
    {
        "file": MUSIC_DIR / "piano_melancholy.mp3",
        "start": ("narr_01", "start", 0.0),
        "fade_in": 2.0,
        "fade_out_at": ("narr_01", "end", 0.0),
        "fade_out_dur": 1.5,
        "volume": db(-20),
        "loop": False,
    },
    # Scene 5 server hum: fades in as office ambience fades out
    {
        "file": SFX_DIR / "server_hum.mp3",
        "start": ("narr_15", "start", -1.0),
        "fade_in": 2.0,
        "fade_out_at": ("narr_19", "end", 1.0),
        "fade_out_dur": 1.5,
        "volume": db(-22),
        "loop": True,
    },
    # Scene 6 apartment ambience
    {
        "file": SFX_DIR / "apartment_ambience.mp3",
        "start": ("narr_20", "start", -1.0),
        "fade_in": 2.0,
        "fade_out_at": ("narr_24", "end", 1.5),
        "fade_out_dur": 2.0,
        "volume": db(-25),
        "loop": True,
    },
    # Scene 6 piano returns
    {
        "file": MUSIC_DIR / "piano_melancholy.mp3",
        "start": ("narr_20", "start", 0.0),
        "fade_in": 2.0,
        "fade_out_at": ("narr_24", "end", 2.0),
        "fade_out_dur": 3.0,
        "volume": db(-22),
        "loop": False,
    },
    # Final server hum swell after narr_24
    {
        "file": SFX_DIR / "server_hum.mp3",
        "start": ("narr_24", "end", 0.2),
        "fade_in": 0.8,
        "fade_out_at": ("narr_24", "end", 3.5),
        "fade_out_dur": 1.5,
        "volume": db(-15),
        "loop": True,
    },
]


# Short SFX one-shots: anchor + offset, single volume, no looping.
SFX_HITS = [
    {"file": SFX_DIR / "startup_chime.mp3",     "at": ("narr_03", "end", 0.1),   "volume": 0.6},
    {"file": SFX_DIR / "notification_ping.mp3", "at": ("aria_03", "start", -0.2), "volume": 0.6},
    {"file": SFX_DIR / "mouse_click.mp3",       "at": ("marta_05", "end", 0.05), "volume": 0.7},
    {"file": SFX_DIR / "mouse_click.mp3",       "at": ("narr_08", "end", 0.05),  "volume": 0.7},
    {"file": SFX_DIR / "keyboard_typing.mp3",   "at": ("narr_10", "start", 0.5), "volume": 0.5},
    {"file": SFX_DIR / "notification_ping.mp3", "at": ("narr_10", "end", 0.1),   "volume": 0.6},
    {"file": SFX_DIR / "keyboard_typing.mp3",   "at": ("marta_10", "end", 0.1),  "volume": 0.5},
    {"file": SFX_DIR / "phone_buzz.mp3",        "at": ("aria_09", "end", 0.1),   "volume": 0.8},
    {"file": SFX_DIR / "mouse_click.mp3",       "at": ("narr_14", "end", 0.1),   "volume": 0.7},
    {"file": SFX_DIR / "keyboard_typing.mp3",   "at": ("narr_17", "start", 0.5), "volume": 0.5},
    {"file": SFX_DIR / "notification_ping.mp3", "at": ("narr_17", "end", 0.1),   "volume": 0.6},
    {"file": SFX_DIR / "phone_buzz.mp3",        "at": ("narr_20", "end", 0.3),   "volume": 0.8},
]


@dataclass
class Anchor:
    start: float
    end: float


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command, capture output, raise with full stderr on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(f"\nCommand failed: {' '.join(cmd[:6])}...\n")
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result


def ffprobe_duration(path: Path) -> float:
    result = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])
    return float(result.stdout.strip())


def check_prereqs() -> None:
    if shutil.which("ffmpeg") is None:
        sys.exit("ERROR: ffmpeg not on PATH. Install it and retry.")
    if shutil.which("ffprobe") is None:
        sys.exit("ERROR: ffprobe not on PATH. Install it with ffmpeg.")
    if not SCRIPT_PATH.exists():
        sys.exit(f"ERROR: {SCRIPT_PATH} missing. Generate it from the spec.")
    missing = []
    for line_id, _ in TIMELINE:
        voice = VOICES_DIR / f"{line_id}.mp3"
        if not voice.exists():
            missing.append(line_id)
    if missing:
        sys.exit(f"ERROR: missing voice files: {missing}\n       Run generate.py first.")


def build_voices_track() -> dict[str, Anchor]:
    """Pass 1: concat silence+voice pairs (plus tail pad) into voices_track.wav.

    Returns a map of line_id -> Anchor(start, end) in seconds from the start
    of voices_track. The trailing silence pad is appended after the last line.
    """
    print(f"Pass 1: building voice track for {len(TIMELINE)} lines")

    inputs: list[str] = []
    filter_parts: list[str] = []
    concat_labels: list[str] = []
    anchors: dict[str, Anchor] = {}
    cursor = 0.0
    next_in = 0

    for idx, (line_id, pre) in enumerate(TIMELINE):
        voice_path = VOICES_DIR / f"{line_id}.mp3"

        inputs += ["-f", "lavfi", "-t", f"{pre:.3f}", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=stereo"]
        sil_input_idx = next_in; next_in += 1
        inputs += ["-i", str(voice_path)]
        voice_input_idx = next_in; next_in += 1

        sil_lbl = f"s{idx}"
        voice_lbl = f"v{idx}"
        filter_parts.append(
            f"[{sil_input_idx}:a]aresample={SAMPLE_RATE},"
            f"aformat=sample_fmts=s16:channel_layouts=stereo[{sil_lbl}]"
        )
        filter_parts.append(
            f"[{voice_input_idx}:a]aresample={SAMPLE_RATE},"
            f"aformat=sample_fmts=s16:channel_layouts=stereo[{voice_lbl}]"
        )
        concat_labels.append(f"[{sil_lbl}][{voice_lbl}]")

        voice_dur = ffprobe_duration(voice_path)
        start = cursor + pre
        end = start + voice_dur
        anchors[line_id] = Anchor(start=start, end=end)
        cursor = end

    # Trailing pad
    inputs += ["-f", "lavfi", "-t", f"{TAIL_PAD_SEC:.3f}", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=stereo"]
    pad_idx = next_in; next_in += 1
    pad_lbl = "pad"
    filter_parts.append(
        f"[{pad_idx}:a]aresample={SAMPLE_RATE},"
        f"aformat=sample_fmts=s16:channel_layouts=stereo[{pad_lbl}]"
    )
    concat_labels.append(f"[{pad_lbl}]")
    n_streams = sum(c.count("[") for c in concat_labels)

    filter_complex = ";".join(filter_parts) + ";"
    filter_complex += "".join(concat_labels) + f"concat=n={n_streams}:v=0:a=1[out]"

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    cmd += inputs
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "pcm_s16le",
        str(VOICES_TRACK),
    ]
    run(cmd)

    voices_track_dur = ffprobe_duration(VOICES_TRACK)
    print(f"  voices_track.wav  -> {voices_track_dur:6.2f}s  ({len(TIMELINE)} lines + {TAIL_PAD_SEC}s tail pad)")
    return anchors


def resolve_time(spec: tuple[str, str, float], anchors: dict[str, Anchor]) -> float:
    line_id, edge, offset = spec
    a = anchors[line_id]
    base = a.start if edge == "start" else a.end
    return max(0.0, base + offset)


def mix_overlays(anchors: dict[str, Anchor]) -> None:
    """Pass 2: mix bg tracks + SFX hits onto voices_track.wav -> episode_01.mp3."""
    print("Pass 2: mixing ambience, music, and SFX")

    inputs = ["-i", str(VOICES_TRACK)]
    filter_parts = []
    mix_labels = ["[0:a]"]

    available_bg = []
    for bg in BG_TRACKS:
        if not bg["file"].exists():
            print(f"  ! missing optional bg file, skipping: {bg['file'].name}")
            continue
        available_bg.append(bg)

    available_sfx = []
    for sfx in SFX_HITS:
        if not sfx["file"].exists():
            print(f"  ! missing optional SFX, skipping: {sfx['file'].name}")
            continue
        available_sfx.append(sfx)

    next_input = 1
    for bg in available_bg:
        start_t = resolve_time(bg["start"], anchors)
        fade_out_t = resolve_time(bg["fade_out_at"], anchors)
        fade_out_dur = bg["fade_out_dur"]
        fade_in_dur = bg["fade_in"]
        vol = bg["volume"]
        loop = bg.get("loop", False)

        if loop:
            inputs += ["-stream_loop", "-1", "-i", str(bg["file"])]
        else:
            inputs += ["-i", str(bg["file"])]
        idx = next_input
        next_input += 1

        delay_ms = int(round(start_t * 1000))
        lbl = f"bg{idx}"
        chain = (
            f"[{idx}:a]aresample={SAMPLE_RATE},"
            f"aformat=sample_fmts=s16:channel_layouts=stereo,"
            f"volume={vol:.4f},"
            f"adelay={delay_ms}|{delay_ms},"
            f"afade=t=in:st={start_t:.3f}:d={fade_in_dur:.3f},"
            f"afade=t=out:st={fade_out_t:.3f}:d={fade_out_dur:.3f}"
            f"[{lbl}]"
        )
        filter_parts.append(chain)
        mix_labels.append(f"[{lbl}]")

    for sfx in available_sfx:
        at_t = resolve_time(sfx["at"], anchors)
        vol = sfx["volume"]
        inputs += ["-i", str(sfx["file"])]
        idx = next_input
        next_input += 1
        delay_ms = int(round(at_t * 1000))
        lbl = f"fx{idx}"
        chain = (
            f"[{idx}:a]aresample={SAMPLE_RATE},"
            f"aformat=sample_fmts=s16:channel_layouts=stereo,"
            f"volume={vol:.4f},"
            f"adelay={delay_ms}|{delay_ms}"
            f"[{lbl}]"
        )
        filter_parts.append(chain)
        mix_labels.append(f"[{lbl}]")

    n_mix = len(mix_labels)
    filter_complex = ";".join(filter_parts)
    if filter_parts:
        filter_complex += ";"
    filter_complex += "".join(mix_labels) + f"amix=inputs={n_mix}:duration=first:normalize=0[out]"

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    cmd += inputs
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "libmp3lame", "-b:a", "192k", "-ar", str(SAMPLE_RATE), "-ac", "2",
        str(OUTPUT),
    ]
    run(cmd)


def verify() -> None:
    duration = ffprobe_duration(OUTPUT)
    minutes = int(duration // 60)
    seconds = duration - minutes * 60
    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print()
    print(f"Final: {OUTPUT.name}  {minutes}:{seconds:05.2f}  {size_mb:.2f} MB")
    if duration < 420 or duration > 600:
        print(f"  ! WARNING: duration {duration:.1f}s outside 420-600s target window")
    else:
        print("  duration is within 7-10 minute target.")

    # Loudness summary (best-effort, ffmpeg returns numbers in stderr)
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(OUTPUT), "-af", "loudnorm=print_format=summary", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    for line in result.stderr.splitlines():
        if "Input Integrated" in line or "Input True Peak" in line:
            print(f"  {line.strip()}")


def main() -> int:
    check_prereqs()
    anchors = build_voices_track()
    mix_overlays(anchors)
    verify()
    print()
    print(f"Done. Open {OUTPUT} to listen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
