# AGREEABLE — Episode 1: "Just to Confirm"

Builds `episode_01.mp3` end-to-end: generates 61 voice lines via the
ElevenLabs API, mixes them with ambience / music / SFX using `ffmpeg`,
and writes a single ~7-9 minute podcast-style MP3.

## Prerequisites

- **Python 3.10+**
- **ffmpeg** on `PATH` (`brew install ffmpeg` / `apt install ffmpeg` /
  `winget install ffmpeg`)
- **ElevenLabs API key** as `ELEVENLABS_API_KEY` in the environment
- **SFX + music files** dropped into `agreeable_ep1/sfx/` and
  `agreeable_ep1/music/` (see [Sound files](#sound-files) below)

## Run

```bash
cd agreeable_ep1
pip install -r requirements.txt
export ELEVENLABS_API_KEY=sk_...

python3 generate.py    # ~10-15 min; calls ElevenLabs, writes voices/*.mp3
python3 assemble.py    # ~1-2 min; runs ffmpeg, writes episode_01.mp3
```

Reruns of `generate.py` are cheap — it skips any voice file already on
disk that is at least 5KB. To regenerate a single line, delete its file
in `voices/` and rerun.

## Layout

```
agreeable_ep1/
├── script.json          # 61 voice lines, character + exact text
├── generate.py          # ElevenLabs TTS driver
├── assemble.py          # ffmpeg two-pass assembly
├── requirements.txt
├── voices/              # generated (.mp3 per line) — gitignored
├── sfx/                 # user-supplied or downloaded — gitignored
├── music/               # user-supplied or downloaded — gitignored
├── build/               # intermediate voices_track.wav — gitignored
└── episode_01.mp3       # final output — gitignored
```

## Sound files

`assemble.py` looks for these filenames. Any that are missing are
**skipped with a warning**, so you can start with a subset and add more.

| Path                              | Description                          |
|-----------------------------------|--------------------------------------|
| `sfx/office_ambience.mp3`         | Office room tone (scenes 1-4)        |
| `sfx/apartment_ambience.mp3`      | Apartment / clock tick (scene 6)     |
| `sfx/server_hum.mp3`              | Low server hum (scenes 5, 6)         |
| `sfx/notification_ping.mp3`       | UI notification                      |
| `sfx/keyboard_typing.mp3`         | Typing                               |
| `sfx/phone_buzz.mp3`              | Phone vibrate                        |
| `sfx/mouse_click.mp3`             | Single click                         |
| `sfx/startup_chime.mp3`           | ARIA boot chime                      |
| `music/piano_melancholy.mp3`      | Sad piano (cold open + final scene)  |

Free sources: [Pixabay](https://pixabay.com/sound-effects/),
[Freesound](https://freesound.org/), or your own library.
Long tracks (ambience / hum / music) will be auto-looped during
mixing, so 10-30 seconds is plenty.

## Voice cast

ElevenLabs public voice IDs. If any voice 404s the catalog may have
rotated — supply a replacement ID in `generate.py`'s `VOICES` map.

| Character | Voice    | Voice ID                  |
|-----------|----------|---------------------------|
| NARRATOR  | Brian    | `nPczCjzI2devNBz1zQrb`    |
| MARTA     | Alice    | `Xb7hH8MSUJpSbSDYk0k2`    |
| DIETER    | George   | `JBFqnCBsd6RMkjVDRZzb`    |
| YUSUF     | Liam     | `TX3LPaxmHKxFdv7VOQHJ`    |
| ARIA      | Charlotte| `XB0fDUnXU5powFXDhCwa`    |

Per-character `voice_settings` live in `generate.py`.

## Verifying the build

`assemble.py` prints final duration and integrated loudness. Targets:

- **Duration:** 7-10 minutes (420-600s). Outside this range usually
  means a missing voice file or a runaway silence.
- **Loudness:** roughly -16 LUFS (podcast standard). If well off,
  run a loudnorm pass on the output:
  ```bash
  ffmpeg -i episode_01.mp3 -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a libmp3lame -b:a 192k episode_01_norm.mp3
  ```

## Notes

- **Silence before every ARIA line is >=1.0s.** This is the comedy
  beat — don't change it.
- **`script.json` is canonical.** Punctuation (ellipses, em-dashes,
  commas) is intentional pause-tuning for the TTS — preserve it
  byte-for-byte.
- The script contains **61 voice lines** (24 NARRATOR + 11 MARTA + 5
  DIETER + 6 YUSUF + 15 ARIA). The spec rounds this to "60"; the
  actual count is 61.
