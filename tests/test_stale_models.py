"""Canned listings show which repository models outrank the pinned defaults."""

import json
import re
from pathlib import Path

import pytest

from armarium.stale_models import (
    VAD_FAMILY,
    WHISPER_FAMILY,
    _version,
    listed_files,
    main,
    newer_models,
    report,
)
from armarium.transcribe import DEFAULT_MODEL, DEFAULT_VAD_MODEL

WHISPER_PIN = "ggml-large-v3-turbo-q8_0.bin"
VAD_PIN = "ggml-silero-v6.2.0.bin"
NEWER_WHISPER = "ggml-large-v99-turbo-q8_0.bin"
NEWER_VAD = "ggml-silero-v99.0.0.bin"


def listing(path: Path, *names: str) -> Path:
    """Save a Hugging Face tree listing of the named files and one directory."""
    entries = [{"type": "directory", "path": "ggml-silero-v99.1.0.bin"}]
    entries += [{"type": "file", "path": name} for name in names]
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


class TestVersion:
    @pytest.mark.parametrize(
        ("filename", "family", "expected"),
        [
            ("ggml-large-v3-turbo-q8_0.bin", WHISPER_FAMILY, (3,)),
            ("ggml-large-v10-turbo-q8_0.bin", WHISPER_FAMILY, (10,)),
            ("ggml-silero-v6.2.0.bin", VAD_FAMILY, (6, 2)),
            ("ggml-silero-v6.2.bin", VAD_FAMILY, (6, 2)),
            ("ggml-silero-v6.10.0.bin", VAD_FAMILY, (6, 10)),
            ("ggml-silero-v7.0.0.bin", VAD_FAMILY, (7,)),
            ("ggml-silero-v10.0.bin", VAD_FAMILY, (10,)),
            ("ggml-silero-v0.bin", VAD_FAMILY, (0,)),
            ("ggml-large-v3-turbo-q5_0.bin", WHISPER_FAMILY, None),
            ("ggml-large-v3-turbo.bin", WHISPER_FAMILY, None),
            ("ggml-large-v3-q8_0.bin", WHISPER_FAMILY, None),
            ("ggml-large-v3-turbo-q8_0.bin.zip", WHISPER_FAMILY, None),
            ("for-tests-ggml-large-v3-turbo-q8_0.bin", WHISPER_FAMILY, None),
            ("ggml-silero-latest.bin", VAD_FAMILY, None),
        ],
    )
    def test_reads_the_family(
        self,
        filename: str,
        family: re.Pattern[str],
        expected: tuple[int, ...] | None,
    ) -> None:
        assert _version(filename, family) == expected

    @pytest.mark.parametrize(
        ("filename", "family"),
        [(DEFAULT_MODEL, WHISPER_FAMILY), (DEFAULT_VAD_MODEL, VAD_FAMILY)],
    )
    def test_covers_the_pinned_defaults(
        self, filename: str, family: re.Pattern[str]
    ) -> None:
        assert _version(filename, family) is not None


class TestNewerModels:
    @pytest.mark.parametrize(
        ("names", "pinned", "family", "expected"),
        [
            ([WHISPER_PIN, "ggml-large-v2-q8_0.bin"], WHISPER_PIN, WHISPER_FAMILY, []),
            (
                [WHISPER_PIN, "ggml-large-v4-turbo-q8_0.bin"],
                WHISPER_PIN,
                WHISPER_FAMILY,
                ["ggml-large-v4-turbo-q8_0.bin"],
            ),
            (
                [
                    WHISPER_PIN,
                    "ggml-large-v4-turbo-q5_0.bin",
                    "ggml-large-v4-turbo.bin",
                    "ggml-large-v4-turbo-encoder.mlmodelc.zip",
                    "ggml-large-v4.bin",
                ],
                WHISPER_PIN,
                WHISPER_FAMILY,
                [],
            ),
            (
                [
                    WHISPER_PIN,
                    "ggml-large-v4-turbo-q8_0.bin",
                    "ggml-large-v10-turbo-q8_0.bin",
                ],
                WHISPER_PIN,
                WHISPER_FAMILY,
                ["ggml-large-v10-turbo-q8_0.bin", "ggml-large-v4-turbo-q8_0.bin"],
            ),
            ([VAD_PIN, "ggml-silero-v5.1.2.bin"], VAD_PIN, VAD_FAMILY, []),
            ([VAD_PIN, "ggml-silero-v6.2.bin"], VAD_PIN, VAD_FAMILY, []),
            (
                [VAD_PIN, "ggml-silero-v6.2.1.bin"],
                VAD_PIN,
                VAD_FAMILY,
                ["ggml-silero-v6.2.1.bin"],
            ),
            (
                [VAD_PIN, "ggml-silero-v6.10.0.bin"],
                VAD_PIN,
                VAD_FAMILY,
                ["ggml-silero-v6.10.0.bin"],
            ),
        ],
    )
    def test_finds_only_higher_versions_of_the_family(
        self,
        names: list[str],
        pinned: str,
        family: re.Pattern[str],
        expected: list[str],
    ) -> None:
        assert newer_models(names, pinned, family) == expected

    @pytest.mark.parametrize(
        ("names", "pinned", "message"),
        [
            ([], VAD_PIN, "is not in the listing"),
            (["ggml-silero-v5.1.2.bin"], VAD_PIN, "is not in the listing"),
            ([WHISPER_PIN], WHISPER_PIN, "does not match"),
        ],
    )
    def test_refuses_what_cannot_show_the_default_is_current(
        self, names: list[str], pinned: str, message: str
    ) -> None:
        with pytest.raises(ValueError, match=message):
            newer_models(names, pinned, VAD_FAMILY)


class TestListedFiles:
    def test_reads_files_and_not_directories(self, tmp_path: Path) -> None:
        path = listing(tmp_path / "listing.json", "README.md", VAD_PIN)
        assert listed_files(path) == ["README.md", VAD_PIN]

    @pytest.mark.parametrize(
        ("text", "error"),
        [
            ("not json", ValueError),
            ('{"error": "Repository not found"}', TypeError),
            ('[{"type": "file"}]', KeyError),
        ],
    )
    def test_refuses_what_is_not_a_listing(
        self, tmp_path: Path, text: str, error: type[Exception]
    ) -> None:
        path = tmp_path / "listing.json"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(error):
            listed_files(path)


class TestReport:
    @pytest.mark.parametrize(
        "findings", [[], [(WHISPER_PIN, []), (VAD_PIN, [])]], ids=["empty", "current"]
    )
    def test_is_empty_with_nothing_newer(
        self, findings: list[tuple[str, list[str]]]
    ) -> None:
        assert report(findings) == ""

    def test_names_every_newer_model(self) -> None:
        text = report([(WHISPER_PIN, [NEWER_WHISPER, "b.bin"]), (VAD_PIN, [NEWER_VAD])])
        assert f"- `{NEWER_WHISPER}` is newer than the pinned `{WHISPER_PIN}`" in text
        assert f"- `b.bin` is newer than the pinned `{WHISPER_PIN}`" in text
        assert f"- `{NEWER_VAD}` is newer than the pinned `{VAD_PIN}`" in text


class TestMain:
    @pytest.mark.parametrize(
        ("whisper", "vad", "expected"),
        [
            ([], [], []),
            ([NEWER_WHISPER], [], [NEWER_WHISPER]),
            ([], [NEWER_VAD], [NEWER_VAD]),
            ([NEWER_WHISPER], [NEWER_VAD], [NEWER_WHISPER, NEWER_VAD]),
        ],
    )
    def test_compares_each_listing_with_its_default(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        whisper: list[str],
        vad: list[str],
        expected: list[str],
    ) -> None:
        main(
            [
                str(listing(tmp_path / "w.json", DEFAULT_MODEL, *whisper)),
                str(listing(tmp_path / "v.json", DEFAULT_VAD_MODEL, *vad)),
            ]
        )
        output = capsys.readouterr().out
        assert (output != "") == bool(expected)
        assert [name for name in (NEWER_WHISPER, NEWER_VAD) if name in output] == (
            expected
        )

    def test_a_listing_without_its_default_stops_the_check(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(ValueError, match="is not in the listing"):
            main(
                [
                    str(listing(tmp_path / "w.json", NEWER_WHISPER)),
                    str(listing(tmp_path / "v.json", DEFAULT_VAD_MODEL)),
                ]
            )
        assert capsys.readouterr().out == ""
