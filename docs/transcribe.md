# Transcribing a recording

```sh
armarium transcribe recordings/s52.wav
```

`armarium transcribe SOURCE` turns a recording of a session into raw transcript
text, using [whisper.cpp](https://github.com/ggml-org/whisper.cpp) on your own
machine. It writes plain text files beside the recording. It needs no
[vault](vault.md), changes no record and creates no
[Transcript](type.md#transcript): the raw text still has to be cleaned and
attributed before [`armarium add transcript`](add.md#transcripts) can take it.

## What it needs

- **whisper.cpp**, which provides the `whisper-cli` program. Armarium does not
  install it. Install it yourself, for example with `brew install whisper-cpp`
  on macOS, and check that `whisper-cli` is on your `PATH`. Without it the
  command stops with a message before it downloads anything. Only this command
  uses it.
- **Two models**, which the command downloads from Hugging Face the first time
  it needs them and keeps in `~/.cache/whisper-cpp`: a Whisper model,
  `ggml-large-v3-turbo-q8_0.bin` (about 900 MB), and a voice-detection model,
  `ggml-silero-v6.2.0.bin` (under 1 MB). Nothing else is sent or fetched; the
  recording stays on your machine.

`SOURCE` is a FLAC, MP3, Ogg or WAV file. Convert other formats first, for
example with `ffmpeg -i session.m4a session.wav`.

## What it writes

For `recordings/s52.wav`:

| File | Holds |
| --- | --- |
| `recordings/s52.raw.txt` | the text exactly as whisper.cpp wrote it |
| `recordings/s52.txt` | the same text with [repeated runs collapsed](#repeated-lines) |

The command prints the second path on standard output and reports its progress
on standard error. It never changes the recording, and it replaces no file: if
either output exists it stops before transcribing. Move the old file or name
another with `--output`.

`--output PATH` names the collapsed file, which must end in `.txt`; the raw text
goes beside it, as `NAME.raw.txt`. Missing directories are created. Keep
recordings and raw text out of Git: a new vault ignores `.scratch/`, which suits
them.

## Repeated lines

Speech-to-text sometimes writes one line, or one pair of lines, dozens of times
in a row in place of what was said. The command replaces each such run with its
first copy and a marker:

```text
We should not go in there.
[ASR loop: previous line repeated 37 times; raw lines 212-248]
```

A run is four or more copies in a row, comparing lines without case, punctuation
or leading words such as "yeah" and "okay". Set the threshold with
`--min-repeats N`, of at least 2. Fewer copies than the threshold are kept, so a
line that was truly said three times stays. The marker names the lines of the
raw file it replaced, and whatever was said during them is lost to the
transcript: listen to that stretch of the recording if it matters.

## Text from another tool

```sh
armarium transcribe notes/s52-export.txt
```

Given a `.txt` file of raw transcript text, the command only collapses repeated
runs, into `notes/s52-export.collapsed.txt` or `--output PATH`. This needs
neither whisper.cpp nor a model.

## Options

| Option | Does |
| --- | --- |
| `-o`, `--output PATH` | names the collapsed `.txt` file |
| `--model MODEL` | Whisper model: a file, or a ggml filename to download, such as `ggml-base.en.bin` |
| `--vad-model MODEL` | voice-detection model, given the same way |
| `--model-dir DIR` | where downloaded models are kept |
| `--language CODE` | spoken language, `en` unless given; `auto` detects it |
| `--min-repeats N` | fewest copies in a row collapsed as a run |

Arguments after `--` are passed to `whisper-cli` unchanged, after the command's
own:

```sh
armarium transcribe recordings/s52.wav -- --threads 8
```

The command always runs whisper.cpp with voice detection, beam search and no
text carried from one window to the next, which makes repeated runs rarer.

It exits with `0` when the text is written and `2` for a usage error. It exits
with `1`, with a one-line message, when `SOURCE` is missing or of another kind,
an output exists, `whisper-cli` is missing or fails, or a model cannot be
downloaded. A failed or interrupted run leaves no partial model or text behind.
