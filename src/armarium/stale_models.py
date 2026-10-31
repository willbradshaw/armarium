"""Report repository models newer than transcription's pinned defaults.

A scheduled workflow fetches the Hugging Face listings and passes them in as
files, so nothing here reads the network.
"""

import json
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from armarium.transcribe import DEFAULT_MODEL, DEFAULT_VAD_MODEL

WHISPER_FAMILY = re.compile(r"ggml-large-v(\d+)-turbo-q8_0\.bin")
VAD_FAMILY = re.compile(r"ggml-silero-v(\d+(?:\.\d+)*)\.bin")


def _version(filename: str, family: re.Pattern[str]) -> tuple[int, ...] | None:
    """Return a filename's version, ready to compare with another.

    Args:
        filename: Model filename.
        family: Pattern whose first group captures a dotted version.

    Returns:
        tuple[int, ...] | None: The numbers of the version without trailing
            zeros, so 6.2 equals 6.2.0; None for a file outside the family.
    """
    match = family.fullmatch(filename)
    if match is None:
        return None
    return tuple(int(part) for part in re.sub(r"(\.0+)+$", "", match[1]).split("."))


def newer_models(
    filenames: Iterable[str], pinned: str, family: re.Pattern[str]
) -> list[str]:
    """Find the models of a family with a higher version than the pinned one.

    Args:
        filenames: Filenames in a repository listing.
        pinned: Filename of the pinned default.
        family: Pattern matching the default and the models comparable with it.

    Returns:
        list[str]: The newer filenames, highest version first.

    Raises:
        ValueError: The default is outside the family or not in the listing,
            so the listing cannot show whether the default is current.
    """
    current = _version(pinned, family)
    if current is None:
        raise ValueError(f"{pinned} does not match {family.pattern}")
    names = set(filenames)
    if pinned not in names:
        raise ValueError(f"{pinned} is not in the listing")
    versions = {name: _version(name, family) for name in names}
    newer = [
        (version, name)
        for name, version in versions.items()
        if version is not None and version > current
    ]
    return [name for _, name in sorted(newer, reverse=True)]


def listed_files(path: Path) -> list[str]:
    """Read the filenames from a saved Hugging Face tree listing.

    Args:
        path: JSON file from ``/api/models/REPO/tree/main``.

    Returns:
        list[str]: The paths of the listing's files, without its directories.

    Raises:
        ValueError: The file is not JSON.
        OSError: The file cannot be read.
        KeyError: An entry lacks a listing's fields.
        TypeError: The JSON is not a list of entries.
    """
    entries = json.loads(path.read_text(encoding="utf-8"))
    return [entry["path"] for entry in entries if entry["type"] == "file"]


def report(findings: Sequence[tuple[str, Sequence[str]]]) -> str:
    """Write the text of an issue about newer models.

    Args:
        findings: Each pinned default with the newer models found for it.

    Returns:
        str: Markdown naming every newer model, or nothing when there are none.
    """
    lines = [
        f"- `{name}` is newer than the pinned `{pinned}`"
        for pinned, newer in findings
        for name in newer
    ]
    if not lines:
        return ""
    return "\n".join(
        [
            "Hugging Face lists models newer than the defaults in "
            "`src/armarium/transcribe.py`:",
            "",
            *lines,
            "",
            "Bumping a default is a deliberate change with a CHANGELOG entry. "
            "This issue is updated while it stays open.",
            "",
        ]
    )


def main(argv: Sequence[str]) -> None:
    """Print the report for two saved listings; print nothing when current.

    Args:
        argv: The Whisper listing's path, then the voice-detection listing's.

    Raises:
        ValueError: A listing cannot show whether its default is current.
    """
    whisper, vad = (Path(argument) for argument in argv)
    print(
        report(
            [
                (
                    DEFAULT_MODEL,
                    newer_models(listed_files(whisper), DEFAULT_MODEL, WHISPER_FAMILY),
                ),
                (
                    DEFAULT_VAD_MODEL,
                    newer_models(listed_files(vad), DEFAULT_VAD_MODEL, VAD_FAMILY),
                ),
            ]
        ),
        end="",
    )


if __name__ == "__main__":
    main(sys.argv[1:])
