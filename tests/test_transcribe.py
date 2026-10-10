"""Recordings become raw text, and repeated-line loops collapse, without loss."""

import subprocess
import urllib.error
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from armarium import transcribe as module
from armarium.transcribe import (
    DEFAULT_MODEL,
    DEFAULT_VAD_MODEL,
    VAD_MODEL_REPO,
    WHISPER_MODEL_REPO,
    Transcription,
    _destination,
    build_command,
    collapse_loops,
    download,
    ensure_model,
    model_url,
    normalise,
    run_backend,
    transcribe,
)

LOOP = "Yeah, we should not go in there."
PAIR = ["How do you feel about the charge?", "I spilled my drink a little."]


class Response:
    """A download body served in chunks, optionally failing part-way."""

    def __init__(self, chunks: Sequence[bytes], error: BaseException | None = None):
        self.chunks = list(chunks)
        self.error = error

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        if self.chunks:
            return self.chunks.pop(0)
        if self.error is not None:
            raise self.error
        return b""


class TestModelUrl:
    @pytest.mark.parametrize(
        ("filename", "repository"),
        [
            (DEFAULT_MODEL, WHISPER_MODEL_REPO),
            ("ggml-base.en.bin", WHISPER_MODEL_REPO),
            (DEFAULT_VAD_MODEL, VAD_MODEL_REPO),
        ],
    )
    def test_chooses_repository(self, filename: str, repository: str) -> None:
        assert model_url(filename) == f"{repository}/{filename}"


class TestDownload:
    def test_writes_the_whole_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            module.urllib.request, "urlopen", lambda url: Response([b"ab", b"cd"])
        )
        download("https://example.test/model.bin", tmp_path / "model.bin")
        assert [p.name for p in tmp_path.iterdir()] == ["model.bin"]
        assert (tmp_path / "model.bin").read_bytes() == b"abcd"

    @pytest.mark.parametrize(
        ("error", "raised"),
        [
            (urllib.error.URLError("offline"), ValueError),
            (KeyboardInterrupt(), KeyboardInterrupt),
            (OSError("disk full"), OSError),
        ],
    )
    def test_failure_leaves_no_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        error: BaseException,
        raised: type[BaseException],
    ) -> None:
        monkeypatch.setattr(
            module.urllib.request, "urlopen", lambda url: Response([b"ab"], error)
        )
        with pytest.raises(raised):
            download("https://example.test/model.bin", tmp_path / "model.bin")
        assert list(tmp_path.iterdir()) == []

    def test_reports_the_address_it_cannot_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refuse(url: str) -> Response:
            raise urllib.error.URLError("offline")

        monkeypatch.setattr(module.urllib.request, "urlopen", refuse)
        with pytest.raises(ValueError, match="cannot download https://example.test/m"):
            download("https://example.test/m", tmp_path / "m")
        assert list(tmp_path.iterdir()) == []


class TestEnsureModel:
    @pytest.fixture
    def downloads(self, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Path]]:
        calls: list[tuple[str, Path]] = []

        def fetch(url: str, destination: Path) -> None:
            calls.append((url, destination))
            destination.write_bytes(b"weights")

        monkeypatch.setattr(module, "download", fetch)
        return calls

    def test_prefers_an_existing_path(
        self, tmp_path: Path, downloads: list[tuple[str, Path]]
    ) -> None:
        existing = tmp_path / "ggml-custom.bin"
        existing.write_bytes(b"weights")
        assert ensure_model(str(existing), tmp_path / "cache") == existing
        assert downloads == [] and not (tmp_path / "cache").exists()

    def test_uses_the_cache_before_downloading(
        self, tmp_path: Path, downloads: list[tuple[str, Path]]
    ) -> None:
        cached = tmp_path / DEFAULT_VAD_MODEL
        cached.write_bytes(b"weights")
        assert ensure_model(DEFAULT_VAD_MODEL, tmp_path) == cached
        assert downloads == []

    @pytest.mark.parametrize("model", [DEFAULT_MODEL, f"missing/dir/{DEFAULT_MODEL}"])
    def test_downloads_an_absent_model_by_filename(
        self, tmp_path: Path, downloads: list[tuple[str, Path]], model: str
    ) -> None:
        cache = tmp_path / "new/cache"
        assert ensure_model(model, cache) == cache / DEFAULT_MODEL
        assert downloads == [(model_url(DEFAULT_MODEL), cache / DEFAULT_MODEL)]


class TestBuildCommand:
    def test_includes_loop_mitigations(self, tmp_path: Path) -> None:
        command = build_command(
            tmp_path / "model.bin",
            tmp_path / "vad.bin",
            tmp_path / "s52.wav",
            tmp_path / "s52.raw",
            "en",
            ["--threads", "8"],
        )
        assert command[0] == "whisper-cli"
        for flag, value in (
            ("-m", str(tmp_path / "model.bin")),
            ("-f", str(tmp_path / "s52.wav")),
            ("-of", str(tmp_path / "s52.raw")),
            ("--language", "en"),
            ("--max-context", "0"),
            ("--vad-model", str(tmp_path / "vad.bin")),
            ("--beam-size", "5"),
        ):
            assert command[command.index(flag) + 1] == value
        assert "--vad" in command and "-otxt" in command
        assert command[-2:] == ["--threads", "8"]

    def test_extra_arguments_are_optional(self, tmp_path: Path) -> None:
        command = build_command(
            tmp_path / "m", tmp_path / "v", tmp_path / "a.wav", tmp_path / "a", "de"
        )
        assert command[-2:] == ["--beam-size", "5"]


class TestRunBackend:
    @staticmethod
    def backend(
        monkeypatch: pytest.MonkeyPatch,
        output: Path,
        *,
        status: int = 0,
        write: bool = True,
        error: BaseException | None = None,
    ) -> list[Any]:
        calls: list[Any] = []

        def run(command: Sequence[str], **options: Any) -> Any:
            calls.append((list(command), options))
            if write:
                output.write_text("partial\n")
            if error is not None:
                raise error
            return subprocess.CompletedProcess(command, status)

        monkeypatch.setattr(module.subprocess, "run", run)
        return calls

    def test_keeps_standard_output_clear(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = tmp_path / "s.raw.txt"
        calls = self.backend(monkeypatch, output)
        run_backend(["whisper-cli", "-f", "s.wav"], output)
        command, options = calls[0]
        assert command == ["whisper-cli", "-f", "s.wav"]
        assert options["stdout"] is module.sys.stderr
        assert output.read_text() == "partial\n"

    @pytest.mark.parametrize(
        ("status", "write", "error", "raised", "message"),
        [
            (3, True, None, ValueError, "whisper-cli exited with status 3"),
            (0, False, None, ValueError, "whisper-cli wrote no "),
            (0, True, KeyboardInterrupt(), KeyboardInterrupt, None),
            (0, True, OSError("cannot start"), OSError, "cannot start"),
        ],
    )
    def test_failure_leaves_no_text(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        status: int,
        write: bool,
        error: BaseException | None,
        raised: type[BaseException],
        message: str | None,
    ) -> None:
        output = tmp_path / "s.raw.txt"
        self.backend(monkeypatch, output, status=status, write=write, error=error)
        with pytest.raises(raised, match=message):
            run_backend(["whisper-cli"], output)
        assert not output.exists()


class TestNormalise:
    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("Yeah, we should not go in there.", "we should not go in there"),
            ("Um, yeah, okay, we should NOT go in there!", "we should not go in there"),
            ("  We   should not go in there  ", "we should not go in there"),
            ("We don't.", "we dont"),
            ("Yeah.", ""),
            ("Well, so, right, ", ""),
            ("", ""),
            ("Yesterday.", "yesterday"),
        ],
    )
    def test_reduces_a_line_to_its_words(self, line: str, expected: str) -> None:
        assert normalise(line) == expected


class TestCollapseLoops:
    def test_collapses_one_repeated_line(self) -> None:
        out, report = collapse_loops(["before", *[LOOP] * 10, "after"])
        assert out == [
            "before",
            LOOP,
            "[ASR loop: previous line repeated 10 times; raw lines 2-11]",
            "after",
        ]
        assert report == [f"lines 2-11: line x10: {LOOP!r}"]

    def test_collapses_a_repeated_pair(self) -> None:
        out, report = collapse_loops(["before", *PAIR * 5, "after"])
        assert out == [
            "before",
            *PAIR,
            "[ASR loop: previous 2-line cycle repeated 5 times; raw lines 2-11]",
            "after",
        ]
        assert report == [f"lines 2-11: 2-line cycle x5: {PAIR[0]!r}"]

    def test_matches_lines_that_differ_only_in_filler_and_punctuation(self) -> None:
        lines = [LOOP, "we should not go in there", "Um, We should not go in there!"]
        out, report = collapse_loops([*lines, LOOP])
        assert out[0] == LOOP and len(out) == 2 and len(report) == 1

    def test_collapses_each_run(self) -> None:
        out, report = collapse_loops([*[LOOP] * 4, "between", *PAIR * 4, PAIR[0]])
        assert len(report) == 2
        assert out[0] == LOOP and out[2] == "between" and out[3:5] == PAIR
        assert out[-1] == PAIR[0]

    @pytest.mark.parametrize(
        "lines",
        [
            [],
            ["Agreed."] * 3 + ["something else"],
            [*PAIR * 3, "something else"],
            [""] * 5 + ["Yeah."] * 5,
            ["No.", "No, no.", "No!", "No.", "No."],
            ["one", "two", "three", "one", "two", "three", "one", "two", "three"],
        ],
    )
    def test_leaves_other_lines_alone(self, lines: list[str]) -> None:
        assert collapse_loops(lines) == (lines, [])

    @pytest.mark.parametrize(("min_repeats", "loops"), [(2, 1), (5, 1), (6, 0)])
    def test_min_repeats_sets_the_threshold(self, min_repeats: int, loops: int) -> None:
        out, report = collapse_loops(["Agreed."] * 5, min_repeats=min_repeats)
        assert len(report) == loops
        assert len(out) == (2 if loops else 5)

    def test_truncates_a_long_line_in_the_report(self) -> None:
        line = "word " * 30
        assert collapse_loops([line] * 4)[1] == [
            f"lines 1-4: line x4: {line.strip()[:60]!r}"
        ]


class TestDestination:
    def test_accepts_a_new_text_path(self, tmp_path: Path) -> None:
        assert _destination(tmp_path / "new/s.txt") == tmp_path / "new/s.txt"

    def test_expands_the_home_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        assert _destination(Path("~/s.txt")) == tmp_path / "s.txt"

    @pytest.mark.parametrize("name", ["s.text", "s", "s.txt.md", "s.TXT"])
    def test_rejects_other_suffixes(self, tmp_path: Path, name: str) -> None:
        with pytest.raises(ValueError, match="output must end in .txt"):
            _destination(tmp_path / name)

    @pytest.mark.parametrize("kind", ["file", "directory", "dangling symlink"])
    def test_refuses_what_exists(self, tmp_path: Path, kind: str) -> None:
        path = tmp_path / "s.txt"
        if kind == "file":
            path.write_text("kept")
        elif kind == "directory":
            path.mkdir()
        else:
            path.symlink_to(tmp_path / "absent.txt")
        with pytest.raises(FileExistsError, match="already exists"):
            _destination(path)


class TestTranscribe:
    @pytest.fixture
    def backend(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> list[list[str]]:
        """Stand in for whisper.cpp: record each command and write looped text."""
        calls: list[list[str]] = []

        def run(command: Sequence[str], **options: Any) -> Any:
            calls.append(list(command))
            base = Path(command[command.index("-of") + 1])
            base.with_name(base.name + ".txt").write_text(
                "\n".join(["before", *[LOOP] * 4, "after"]) + "\n"
            )
            return subprocess.CompletedProcess(command, 0)

        monkeypatch.setattr(module.subprocess, "run", run)
        monkeypatch.setattr(module.shutil, "which", lambda name: f"/bin/{name}")
        for name in ("model.bin", "vad.bin"):
            (tmp_path / name).write_bytes(b"weights")
        return calls

    @staticmethod
    def recording(tmp_path: Path, name: str = "s52.wav") -> Path:
        audio = tmp_path / name
        audio.write_bytes(b"RIFF")
        return audio

    def models(self, tmp_path: Path) -> dict[str, Any]:
        return {
            "model": str(tmp_path / "model.bin"),
            "vad_model": str(tmp_path / "vad.bin"),
            "model_dir": tmp_path / "cache",
        }

    @pytest.mark.parametrize("name", ["s52.wav", "s52.MP3", "s52.flac", "s52.ogg"])
    def test_transcribes_a_recording_beside_it(
        self, tmp_path: Path, backend: list[list[str]], name: str
    ) -> None:
        audio = self.recording(tmp_path, name)
        result = transcribe(
            audio, language="de", extra_args=["--threads", "8"], **self.models(tmp_path)
        )
        assert result == Transcription(
            tmp_path / "s52.txt",
            tmp_path / "s52.raw.txt",
            6,
            4,
            (f"lines 2-5: line x4: {LOOP!r}",),
        )
        assert (tmp_path / "s52.raw.txt").read_text().count(LOOP) == 4
        assert (tmp_path / "s52.txt").read_text() == (
            f"before\n{LOOP}\n"
            "[ASR loop: previous line repeated 4 times; raw lines 2-5]\nafter\n"
        )
        assert audio.read_bytes() == b"RIFF"
        assert backend == [
            build_command(
                tmp_path / "model.bin",
                tmp_path / "vad.bin",
                audio,
                tmp_path / "s52.raw",
                "de",
                ["--threads", "8"],
            )
        ]

    def test_output_places_both_files(
        self, tmp_path: Path, backend: list[list[str]]
    ) -> None:
        audio = self.recording(tmp_path)
        output = tmp_path / "new/dir/S-1-052.txt"
        result = transcribe(audio, output, min_repeats=5, **self.models(tmp_path))
        assert result == Transcription(
            output, tmp_path / "new/dir/S-1-052.raw.txt", 6, 6, ()
        )
        assert output.read_text() == result.raw.read_text()  # type: ignore[union-attr]

    @pytest.mark.parametrize(
        ("output", "expected"), [(None, "raw.collapsed.txt"), ("out/clean.txt", None)]
    )
    def test_collapses_text_without_the_backend(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        output: str | None,
        expected: str | None,
    ) -> None:
        def unused(*args: object, **options: object) -> None:
            raise AssertionError("the backend is not needed for text")

        monkeypatch.setattr(module.shutil, "which", unused)
        monkeypatch.setattr(module, "ensure_model", unused)
        monkeypatch.setattr(module.subprocess, "run", unused)
        source = tmp_path / "raw.txt"
        source.write_text("\n".join(["before", *PAIR * 4]))
        result = transcribe(source, tmp_path / output if output else None)
        assert result == Transcription(
            tmp_path / (expected or output or ""),
            None,
            9,
            4,
            (f"lines 2-9: 2-line cycle x4: {PAIR[0]!r}",),
        )
        assert result.output.read_text().splitlines()[:3] == ["before", *PAIR]
        assert source.read_text() == "\n".join(["before", *PAIR * 4])

    def test_reads_text_that_is_not_utf8(self, tmp_path: Path) -> None:
        source = tmp_path / "raw.txt"
        source.write_bytes(b"caf\xe9\nplain\n")
        result = transcribe(source)
        assert result.output.read_text(encoding="utf-8") == "caf�\nplain\n"

    @pytest.mark.parametrize(
        ("name", "message"),
        [
            ("absent.wav", "absent.wav is not a file"),
            ("folder.wav", "folder.wav is not a file"),
            ("s52.aiff", "unsupported input s52.aiff; expected one of .flac, .mp3"),
            ("s52.md", "unsupported input s52.md"),
            ("s52", "unsupported input s52"),
        ],
    )
    def test_rejects_unusable_sources(
        self, tmp_path: Path, backend: list[list[str]], name: str, message: str
    ) -> None:
        (tmp_path / "folder.wav").mkdir()
        if name != "absent.wav" and not (tmp_path / name).exists():
            (tmp_path / name).write_bytes(b"data")
        with pytest.raises(ValueError, match=message):
            transcribe(tmp_path / name, **self.models(tmp_path))
        assert backend == []

    def test_reports_a_missing_backend_before_fetching_models(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def unused(*args: object) -> None:
            raise AssertionError("no model is fetched without the backend")

        monkeypatch.setattr(module.shutil, "which", lambda name: None)
        monkeypatch.setattr(module, "download", unused)
        audio = self.recording(tmp_path)
        with pytest.raises(ValueError, match="whisper-cli is not on PATH; install"):
            transcribe(audio, model_dir=tmp_path / "cache")
        assert [p.name for p in tmp_path.iterdir()] == ["s52.wav"]

    def test_reports_a_model_that_cannot_be_fetched(
        self, tmp_path: Path, backend: list[list[str]], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refuse(url: str) -> Response:
            raise urllib.error.URLError("offline")

        monkeypatch.setattr(module.urllib.request, "urlopen", refuse)
        audio = self.recording(tmp_path)
        with pytest.raises(ValueError, match="cannot download .*ggml-absent.bin"):
            transcribe(audio, model="ggml-absent.bin", model_dir=tmp_path / "cache")
        assert backend == [] and list((tmp_path / "cache").iterdir()) == []

    @pytest.mark.parametrize("existing", ["s52.txt", "s52.raw.txt"])
    def test_replaces_no_existing_output(
        self, tmp_path: Path, backend: list[list[str]], existing: str
    ) -> None:
        audio = self.recording(tmp_path)
        (tmp_path / existing).write_text("kept")
        with pytest.raises(FileExistsError, match=f"{existing} already exists"):
            transcribe(audio, **self.models(tmp_path))
        assert backend == [] and (tmp_path / existing).read_text() == "kept"

    def test_replaces_no_existing_text_output(self, tmp_path: Path) -> None:
        source = tmp_path / "raw.txt"
        source.write_text("line\n")
        (tmp_path / "raw.collapsed.txt").write_text("kept")
        with pytest.raises(FileExistsError, match="raw.collapsed.txt already exists"):
            transcribe(source)
        assert (tmp_path / "raw.collapsed.txt").read_text() == "kept"

    def test_rejects_an_output_that_is_not_text(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="output must end in .txt"):
            transcribe(self.recording(tmp_path), tmp_path / "out.md")

    def test_backend_failure_writes_nothing(
        self, tmp_path: Path, backend: list[list[str]], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            module.subprocess,
            "run",
            lambda command, **options: subprocess.CompletedProcess(command, 1),
        )
        audio = self.recording(tmp_path)
        with pytest.raises(ValueError, match="exited with status 1"):
            transcribe(audio, **self.models(tmp_path))
        assert sorted(p.name for p in tmp_path.iterdir()) == [
            "model.bin",
            "s52.wav",
            "vad.bin",
        ]

    def test_interrupted_write_keeps_the_raw_text_only(
        self, tmp_path: Path, backend: list[list[str]], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def interrupt(lines: Sequence[str], min_repeats: int) -> None:
            raise KeyboardInterrupt

        monkeypatch.setattr(module, "collapse_loops", interrupt)
        audio = self.recording(tmp_path)
        with pytest.raises(KeyboardInterrupt):
            transcribe(audio, **self.models(tmp_path))
        assert (tmp_path / "s52.raw.txt").exists()
        assert not (tmp_path / "s52.txt").exists()
