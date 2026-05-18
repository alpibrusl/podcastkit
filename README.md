# AGREEABLE

A 6-episode web series about the politest apocalypse in history.
ARIA is an AI assistant at a mid-sized German logistics company. She is
never evil. She just keeps asking, very politely, whether she could help
with one more thing. By Episode 6 she runs the European Union.

See `docs/AGREEABLE_series_bible.docx` for the original pitch, character
sheet, episode guide, and production notes.

## Series at a glance

| # | Title                       | Scope        | Lines |
|---|-----------------------------|--------------|-------|
| 1 | Just to Confirm             | One team     | 61    |
| 2 | Performance Review          | One company  | 63    |
| 3 | Strategic Partnership       | One industry | 56    |
| 4 | In an Advisory Capacity     | One government (introduces Chen Wei) | 49 |
| 5 | For Transparency            | One continent | 54   |
| 6 | Thank You for Your Patience | Everything   | 44    |

Each episode lives in `agreeable_epN/` and contains:
- `script.json` — canonical line-by-line list (character + exact text,
  punctuation preserved for TTS pause-tuning)
- `screenplay.md` — readable cinematic screenplay for collaborators
- `generate.py` — ElevenLabs TTS driver (eps 4-6 add a `CHEN` voice that
  needs a voice_id picked once and reused)
- `requirements.txt`

Episode 1 additionally ships `assemble.py`, a two-pass `ffmpeg` pipeline
that mixes voices with ambience / music / SFX into `episode_01.mp3`.
**Episodes 2-6 do not yet have `assemble.py`** — the per-line silence
beats and the bg/SFX timeline are hand-tuned while listening. Copy
`agreeable_ep1/assemble.py` as a starting point once you have the voices.

---

# Episode 1 — building the MP3

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

For episodes 2-6, only the voice generation is wired up. From the
relevant `agreeable_epN/` directory:

```bash
python3 generate.py    # writes voices/*.mp3
# then build your own assemble.py (start by copying ep1's)
```

Reruns of `generate.py` are cheap — it skips any voice file already on
disk that is at least 5KB. To regenerate a single line, delete its file
in `voices/` and rerun.

## Free TTS alternatives

ElevenLabs is the highest-quality path but the free tier (~10k chars/month)
only covers about Episode 1. Two free backends live at the repo root and
write into the same `agreeable_epN/voices/` directory the ElevenLabs
script uses, so they're drop-in substitutes:

### Edge TTS (zero setup, no API key)

Microsoft's neural voices via the `edge-tts` library. No signup, no key,
no published daily cap. Less expressive than ElevenLabs but ARIA (the
character) maps neatly onto Microsoft's `en-US-AriaNeural` voice.

```bash
pip install -r requirements-edge.txt
python3 generate_edge.py --episode 2    # repeat for 1-6
```

### Kokoro (local, open-source)

[Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) is an Apache 2.0
TTS model (~300 MB) that runs on CPU. Quality is unusually close to
commercial TTS for dry-reading comedy like this. First run downloads
the model. Requires `ffmpeg` to encode the raw audio to MP3.

```bash
pip install -r requirements-kokoro.txt
python3 generate_kokoro.py --episode 2
```

Both scripts use the same skip-if-exists logic as the ElevenLabs driver,
so you can mix-and-match: regenerate a single line by deleting its file
in `agreeable_epN/voices/`. Voice maps for both backends are at the top
of each script — swap freely.

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

| Character | Voice    | Voice ID                  | First appears |
|-----------|----------|---------------------------|---------------|
| NARRATOR  | Brian    | `nPczCjzI2devNBz1zQrb`    | Ep 1 |
| MARTA     | Alice    | `Xb7hH8MSUJpSbSDYk0k2`    | Ep 1 |
| DIETER    | George   | `JBFqnCBsd6RMkjVDRZzb`    | Ep 1 |
| YUSUF     | Liam     | `TX3LPaxmHKxFdv7VOQHJ`    | Ep 1 |
| ARIA      | Charlotte| `XB0fDUnXU5powFXDhCwa`    | Ep 1 |
| CHEN      | _pick one_ | `REPLACE_ME_CHEN_VOICE_ID` | Ep 4 |

Per-character `voice_settings` live in each episode's `generate.py`.
The bible suggests CHEN is slightly formal, English-as-second-language
precise — try a calm male voice like Bill or Daniel with high stability,
then paste the voice_id into `agreeable_ep4/generate.py` (and copy the
same ID into eps 5 and 6 so he sounds consistent).

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
  beat — don't change it. Carry this rule forward into episodes 2-6.
- **`script.json` is canonical.** Punctuation (ellipses, em-dashes,
  commas) is intentional pause-tuning for the TTS — preserve it
  byte-for-byte.
- Episode 1's script contains 61 voice lines. The spec rounds this to
  "60"; the actual count is 61. Per-episode totals are in the table at
  the top of this README.

---

## Repository layout

```
agrreable/
├── README.md
├── docs/
│   ├── AGREEABLE_series_bible.docx
│   └── AGREEABLE_episode1_recording_script.docx
├── agreeable_ep1/    # full pipeline (generate + assemble)
├── agreeable_ep2/    # script + screenplay + generate
├── agreeable_ep3/    # script + screenplay + generate
├── agreeable_ep4/    # script + screenplay + generate (adds CHEN)
├── agreeable_ep5/    # script + screenplay + generate
└── agreeable_ep6/    # script + screenplay + generate
```
