"""Turn a session recording into raw transcript text with whisper.cpp.

Speech-to-text sometimes emits one line, or a pair of lines, dozens of times
in a row in place of the audio underneath. Transcription therefore has two
steps: whisper.cpp writes the raw text, and the repeated runs in it are then
collapsed to one copy and a marker. Neither step creates a Transcript record.
"""

import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from armarium.logging import logger

BACKEND = "whisper-cli"
AUDIO_SUFFIXES = (".flac", ".mp3", ".ogg", ".wav")
TEXT_SUFFIX = ".txt"

DEFAULT_MODEL = "ggml-large-v3-turbo-q8_0.bin"
DEFAULT_VAD_MODEL = "ggml-silero-v6.2.0.bin"
DEFAULT_MODEL_DIR = Path.home() / ".cache" / "whisper-cpp"
DEFAULT_LANGUAGE = "en"
DEFAULT_MIN_REPEATS = 4

WHISPER_MODEL_REPO = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
VAD_MODEL_REPO = "https://huggingface.co/ggml-org/whisper-vad/resolve/main"
VAD_MODEL_PREFIX = "ggml-silero"
DOWNLOAD_CHUNK_BYTES = 1 << 20

# Leading filler words removed, repeatedly, before two lines are compared, so
# "Yeah, we should go." and "We should go." count as the same line.
FILLER_PREFIX = re.compile(
    r"^(yeah|yes|no|um|uh|okay|ok|so|well|right|and)[,.!?\s]+", re.IGNORECASE
)
NON_WORD = re.compile(r"[^a-z0-9 ]+")


@dataclass(frozen=True)
class Transcription:
    """The files one transcription wrote and the loops it collapsed.

    Attributes:
        output: The transcript text with repeated runs collapsed.
        raw: The text as whisper.cpp wrote it, or None when the source was
            already text.
        lines: Number of lines before collapsing.
        kept: Number of lines after collapsing, markers included.
        loops: One description per collapsed run, in order.
    """

    output: Path
    raw: Path | None
    lines: int
    kept: int
    loops: tuple[str, ...]


def model_url(filename: str) -> str:
    """Return the download address of a ggml model.

    Args:
        filename: Model filename, such as ``ggml-base.en.bin``.

    Returns:
        str: Its address in the voice-detection repository for a Silero model,
            and in the whisper.cpp repository otherwise.
    """
    silero = filename.startswith(VAD_MODEL_PREFIX)
    return f"{VAD_MODEL_REPO if silero else WHISPER_MODEL_REPO}/{filename}"


def download(url: str, destination: Path) -> None:
    """Download a file, leaving nothing behind when the download fails.

    Args:
        url: Address to read.
        destination: Path to write; its directory must exist.

    Raises:
        ValueError: The address cannot be read.
        OSError: Writing fails.
        KeyboardInterrupt: The partial file is removed before propagating.
    """
    part = destination.with_name(destination.name + ".part")
    logger.info("Downloading %s to %s", url, destination)
    try:
        with urllib.request.urlopen(url) as response, part.open("wb") as out:
            while chunk := response.read(DOWNLOAD_CHUNK_BYTES):
                out.write(chunk)
    except urllib.error.URLError as exc:
        part.unlink(missing_ok=True)
        raise ValueError(f"cannot download {url}: {exc}") from exc
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    part.rename(destination)


def ensure_model(model: str, model_dir: Path) -> Path:
    """Resolve a model argument to a file, downloading it when it is absent.

    Args:
        model: Path of a model file, or the filename of a ggml model.
        model_dir: Directory holding downloaded models; created when needed.

    Returns:
        Path: The path given when it is a file; otherwise the file of that
            name in ``model_dir``, downloaded first if it is not there.

    Raises:
        ValueError: The model cannot be downloaded.
        OSError: The directory or file cannot be written.
    """
    given = Path(model).expanduser()
    if given.is_file():
        return given
    cached = model_dir.expanduser() / given.name
    if not cached.is_file():
        cached.parent.mkdir(parents=True, exist_ok=True)
        download(model_url(given.name), cached)
    return cached


def build_command(
    model: Path,
    vad_model: Path,
    audio: Path,
    output_base: Path,
    language: str,
    extra_args: Sequence[str] = (),
) -> list[str]:
    """Assemble the whisper.cpp invocation for one recording.

    The fixed options are those that limit repeated-line loops: no text carried
    between windows, voice-activity detection and beam search.

    Args:
        model: Whisper model file.
        vad_model: Voice-activity-detection model file.
        audio: Recording to transcribe.
        output_base: Output path without ``.txt``, which whisper.cpp appends.
        language: Spoken language code.
        extra_args: Further whisper.cpp arguments, placed last.

    Returns:
        list[str]: The command and its arguments.
    """
    return [
        BACKEND,
        "-m",
        str(model),
        "-f",
        str(audio),
        "--language",
        language,
        "-otxt",
        "-of",
        str(output_base),
        "--max-context",
        "0",
        "--vad",
        "--vad-model",
        str(vad_model),
        "--beam-size",
        "5",
        *extra_args,
    ]


def run_backend(command: Sequence[str], output: Path) -> None:
    """Run whisper.cpp and confirm that it wrote its text file.

    whisper.cpp prints the text as it goes; that is sent to standard error, so
    standard output stays free for the caller.

    Args:
        command: The invocation from build_command.
        output: The text file the command should write.

    Raises:
        ValueError: The command fails, or succeeds without writing the file.
        OSError: The command cannot be started.
        KeyboardInterrupt: A partial text file is removed before propagating.
    """
    logger.info("Running %s", " ".join(command))
    try:
        result = subprocess.run(command, stdout=sys.stderr, check=False)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    if result.returncode != 0:
        output.unlink(missing_ok=True)
        raise ValueError(f"{BACKEND} exited with status {result.returncode}")
    if not output.is_file():
        raise ValueError(f"{BACKEND} wrote no {output}; see its messages above")


def normalise(line: str) -> str:
    """Return the form of a transcript line used to compare it with others.

    Args:
        line: One line of raw transcript text.

    Returns:
        str: The line in lower case without leading filler words, punctuation
            or extra spaces; empty for a line of nothing else.
    """
    text = line.strip().lower()
    while (stripped := FILLER_PREFIX.sub("", text)) != text:
        text = stripped
    return " ".join(NON_WORD.sub("", text).split())


def collapse_loops(
    lines: Sequence[str], min_repeats: int = DEFAULT_MIN_REPEATS
) -> tuple[list[str], list[str]]:
    """Collapse runs of one repeated line, or one repeated pair of lines.

    A run is the same line, or the same two lines in turn, at least
    ``min_repeats`` times in a row once each is normalised. It is replaced by
    its first copy and a marker line giving the count and the lines replaced.
    Blank lines and lines of filler words alone never form a run.

    Args:
        lines: Raw transcript lines without line endings.
        min_repeats: Fewest consecutive copies that count as a run.

    Returns:
        tuple[list[str], list[str]]: The collapsed lines, and one description
            per run with its line numbers in the input, counted from 1.
    """
    keys = [normalise(line) for line in lines]
    out: list[str] = []
    report: list[str] = []
    i = 0
    while i < len(lines):
        for period in (1, 2):
            cycle = keys[i : i + period]
            if len(cycle) < period or not all(cycle) or len(set(cycle)) < period:
                continue
            j = i + period
            while keys[j : j + period] == cycle:
                j += period
            repeats = (j - i) // period
            if repeats >= min_repeats:
                unit = "line" if period == 1 else "2-line cycle"
                out.extend(lines[i : i + period])
                out.append(
                    f"[ASR loop: previous {unit} repeated {repeats} times; "
                    f"raw lines {i + 1}-{j}]"
                )
                report.append(
                    f"lines {i + 1}-{j}: {unit} x{repeats}: {lines[i].strip()[:60]!r}"
                )
                i = j
                break
        else:
            out.append(lines[i])
            i += 1
    return out, report


def _destination(path: Path) -> Path:
    """Return an output path, refusing one that exists or is not a text file.

    Args:
        path: Proposed output file.

    Returns:
        Path: The path with a leading ``~`` expanded.

    Raises:
        ValueError: The path does not end in ``.txt``.
        OSError: A file or directory is already there.
    """
    path = path.expanduser()
    if path.suffix != TEXT_SUFFIX:
        raise ValueError(f"output must end in {TEXT_SUFFIX}: {path}")
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"{path} already exists; move it or choose --output")
    return path


def transcribe(
    source: Path,
    output: Path | None = None,
    *,
    model: str = DEFAULT_MODEL,
    vad_model: str = DEFAULT_VAD_MODEL,
    model_dir: Path = DEFAULT_MODEL_DIR,
    language: str = DEFAULT_LANGUAGE,
    min_repeats: int = DEFAULT_MIN_REPEATS,
    extra_args: Sequence[str] = (),
) -> Transcription:
    """Transcribe a recording, or collapse the loops in existing raw text.

    A recording is transcribed by whisper.cpp to ``NAME.raw.txt`` and collapsed
    to ``NAME.txt``, beside the recording unless ``output`` names ``NAME.txt``
    elsewhere. A ``.txt`` source is only collapsed, to ``NAME.collapsed.txt``
    or ``output``. The source is never changed and no existing file is
    replaced.

    Args:
        source: Recording (FLAC, MP3, Ogg or WAV) or raw transcript text.
        output: Collapsed text file to write, ending in ``.txt``.
        model: Whisper model file, or ggml filename to fetch into ``model_dir``.
        vad_model: Voice-activity-detection model, given the same way.
        model_dir: Directory for downloaded models.
        language: Spoken language code.
        min_repeats: Fewest consecutive copies collapsed as a loop.
        extra_args: Further whisper.cpp arguments.

    Returns:
        Transcription: The files written and the loops collapsed.

    Raises:
        ValueError: The source is missing or of an unsupported kind, the output
            is not a ``.txt`` path, whisper.cpp is not installed or fails, or a
            model cannot be downloaded.
        OSError: An output exists, or reading or writing fails.
        KeyboardInterrupt: Partial outputs are removed before propagating.
    """
    source = source.expanduser()
    if not source.is_file():
        raise ValueError(f"{source} is not a file")
    suffix = source.suffix.lower()
    if suffix != TEXT_SUFFIX and suffix not in AUDIO_SUFFIXES:
        kinds = ", ".join((*AUDIO_SUFFIXES, TEXT_SUFFIX))
        raise ValueError(f"unsupported input {source.name}; expected one of {kinds}")
    raw: Path | None = None
    if suffix == TEXT_SUFFIX:
        text = source
        destination = _destination(
            output or source.with_name(f"{source.stem}.collapsed{TEXT_SUFFIX}")
        )
    else:
        destination = _destination(output or source.with_suffix(TEXT_SUFFIX))
        raw = text = _destination(
            destination.with_name(f"{destination.stem}.raw{TEXT_SUFFIX}")
        )
        if shutil.which(BACKEND) is None:
            raise ValueError(
                f"{BACKEND} is not on PATH; install whisper.cpp to transcribe "
                "recordings"
            )
        command = build_command(
            ensure_model(model, model_dir),
            ensure_model(vad_model, model_dir),
            source,
            raw.with_suffix(""),
            language,
            extra_args,
        )
        raw.parent.mkdir(parents=True, exist_ok=True)
        run_backend(command, raw)
    lines = text.read_text(encoding="utf-8", errors="replace").splitlines()
    collapsed, loops = collapse_loops(lines, min_repeats)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("x", encoding="utf-8") as out:
            out.write("".join(f"{line}\n" for line in collapsed))
    except FileExistsError:
        raise
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return Transcription(destination, raw, len(lines), len(collapsed), tuple(loops))
