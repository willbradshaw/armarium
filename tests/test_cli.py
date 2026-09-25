"""Command parsing, diagnostics, exit status and process entry point."""

import os
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from armarium.cli import main, parse_args
from armarium.lib import Diagnostic, Result, ValidationError, VaultNotFoundError
from armarium.logging import logger


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault with spaces"
    (root / "reference/types").mkdir(parents=True)
    (root / "reference/schemas").mkdir()
    (root / "campaigns").mkdir()
    (root / "reference/schemas/widget.schema.json").write_text("true")
    (root / "content").mkdir()
    # Widget records live in content/, and Type records declare their own home.
    for name, directory in (("Widget", "content"), ("Type", "reference/types")):
        (root / f"reference/types/{name}.md").write_text(
            f'---\ntype: "[[Type]]"\ndirectories: {{shared: {directory}}}\n---\n'
        )
    (root / "reference/schemas/type.schema.json").write_text("true")
    return root


@pytest.fixture(autouse=True)
def preserve_logger() -> Iterator[None]:
    handlers, level, propagate = logger.handlers[:], logger.level, logger.propagate
    yield
    logger.handlers, logger.level, logger.propagate = handlers, level, propagate


class TestMain:
    @pytest.mark.parametrize(
        ("text", "name", "status", "diagnostic", "counts"),
        [
            (
                '---\ntype: "[[Widget]]"\n---\n',
                "content/record.md",
                0,
                "",
                "1 checked, 0 skipped, 0 unsupported",
            ),
            (
                '---\ntype: "[[Unknown]]"\n---\n',
                "content/record.md",
                1,
                "ERROR: content/record.md: schema.unsupported",
                "1 checked, 0 skipped, 1 unsupported",
            ),
            (
                "plain Markdown",
                "content/record.md",
                1,
                "ERROR: content/record.md [type]: record.type",
                "1 checked, 0 skipped, 0 unsupported",
            ),
            (
                "---\nx: first\nx: second\n---\n",
                "content/record.md",
                1,
                "ERROR: content/record.md:3: parse.invalid",
                "1 checked, 0 skipped, 0 unsupported",
            ),
            (
                '---\ntype: "[[Widget]]"\n---\n',
                "reference/templates/Widget.md",
                0,
                "INFO: reference/templates/Widget.md: record.template",
                "0 checked, 1 skipped, 0 unsupported",
            ),
        ],
    )
    def test_validation_output(
        self,
        vault: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
        text: str,
        name: str,
        status: int,
        diagnostic: str,
        counts: str,
    ) -> None:
        if "Unknown" in text:
            (vault / "reference/types/Unknown.md").write_text(
                '---\ntype: "[[Type]]"\ndirectories: {shared: content}\n---\n'
            )
        path = vault / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        before = path.read_bytes()
        monkeypatch.setattr(sys, "argv", ["armarium", "validate", str(path)])
        if status:
            with pytest.raises(ValidationError, match="^1 file failed validation$"):
                main()
        else:
            assert main() is None
        output = capsys.readouterr()
        assert output.out == ""
        assert output.err.endswith("INFO: " + counts + "\n")
        headers = re.findall(
            r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{2} UTC\] (INFO|WARNING|ERROR): ",
            output.err,
            re.MULTILINE,
        )
        assert len(headers) == (2 if diagnostic else 1)
        assert diagnostic in output.err
        assert path.read_bytes() == before

    def test_explicit_vault_and_process_arguments(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = tmp_path / "record.md"
        path.write_text('---\ntype: "[[Unknown]]"\n---\n')
        monkeypatch.setattr(
            sys, "argv", ["armarium", "validate", str(path), "--vault", str(tmp_path)]
        )
        with pytest.raises(ValidationError, match="1 file failed validation"):
            main()
        assert "1 unsupported" in capsys.readouterr().err

    @pytest.mark.parametrize(
        "error", [ValueError("bad target"), OSError("cannot read")]
    )
    def test_execution_errors_propagate(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        error: Exception,
    ) -> None:
        from unittest.mock import Mock

        monkeypatch.setattr("armarium.cli.validate", Mock(side_effect=error))
        monkeypatch.setattr(sys, "argv", ["armarium", "validate", "record.md"])
        with pytest.raises(type(error)) as exc:
            main()
        assert exc.value is error
        output = capsys.readouterr()
        assert output.out == output.err == ""

    @pytest.mark.parametrize("files", [1, 2])
    def test_failure_counts_distinct_files(
        self, monkeypatch: pytest.MonkeyPatch, files: int
    ) -> None:
        from unittest.mock import Mock

        findings = [
            Diagnostic(f"{index}.md", rule, "Invalid")
            for index in range(files)
            for rule in ("first", "second")
        ] + [Diagnostic("warning.md", "warning", "Warning", severity="warning")]
        monkeypatch.setattr(
            "armarium.cli.validate",
            Mock(return_value=Result(findings, checked=files + 1)),
        )
        monkeypatch.setattr(sys, "argv", ["armarium", "validate", "record.md"])
        noun = "file" if files == 1 else "files"
        with pytest.raises(
            ValidationError, match=f"^{files} {noun} failed validation$"
        ):
            main()

    @pytest.mark.parametrize("valid", [False, True])
    def test_directory(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        valid: bool,
    ) -> None:
        # A directory inside the vault gets record checks only; see the
        # vault-root test below for infrastructure checks.
        (vault / "content/record.md").write_text(
            '---\ntype: "[[Widget]]"\n---\n' if valid else "Untyped"
        )
        monkeypatch.setattr(
            sys, "argv", ["armarium", "validate", str(vault / "content")]
        )
        if valid:
            assert main() is None
        else:
            with pytest.raises(ValidationError, match="1 file failed validation"):
                main()
        assert "1 checked" in capsys.readouterr().err

    def test_vault_root_reports_infrastructure(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        (vault / "content/record.md").write_text('---\ntype: "[[Widget]]"\n---\n')
        monkeypatch.setattr(sys, "argv", ["armarium", "validate", str(vault)])
        # Every record passes, but the minimal fixture lacks required
        # infrastructure, which is reported against the vault root itself.
        with pytest.raises(ValidationError, match="1 file failed validation"):
            main()
        err = capsys.readouterr().err
        assert "3 checked" in err
        assert ".: vault.required: required directory assets is missing" in err

    @pytest.mark.parametrize("directory", [False, True])
    def test_loose_markdown_requires_context_only_for_file_targets(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        directory: bool,
    ) -> None:
        record = tmp_path / "README.md"
        record.write_text("Repository documentation")
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "validate", str(tmp_path if directory else record)],
        )
        if directory:
            assert main() is None
            assert "0 checked, 0 skipped, 0 unsupported" in capsys.readouterr().err
        else:
            with pytest.raises(VaultNotFoundError):
                main()

    @pytest.mark.parametrize("scenario", ["valid", "invalid", "missing"])
    def test_module_entry_point(
        self, vault: Path, tmp_path: Path, scenario: str
    ) -> None:
        path = vault / "content/record.md"
        if scenario != "missing":
            path.write_text(
                '---\ntype: "[[Widget]]"\n---\n' if scenario == "valid" else "untyped"
            )
        process = subprocess.run(
            [sys.executable, "-m", "armarium.cli", "validate", str(path)],
            cwd=tmp_path,
            env={
                **os.environ,
                "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
            },
            capture_output=True,
            text=True,
            check=False,
        )
        assert process.returncode == (0 if scenario == "valid" else 1)
        if scenario == "missing":
            assert "Traceback" in process.stderr
            assert "ValueError:" in process.stderr
        else:
            assert "INFO: 1 checked, 0 skipped, 0 unsupported" in process.stderr
        if scenario == "invalid":
            assert "Traceback" in process.stderr
            assert process.stderr.rstrip().endswith(
                "ValidationError: 1 file failed validation"
            )
        assert process.stdout == ""


class TestParseArgs:
    @pytest.mark.parametrize("explicit", [False, True])
    def test_paths(self, explicit: bool) -> None:
        argv = ["validate", "record.md"] + (["--vault", "vault"] if explicit else [])
        args = parse_args(argv)
        assert args.command == "validate" and args.path == Path("record.md")
        assert args.vault == (Path("vault") if explicit else None)

    @pytest.mark.parametrize(
        "argv",
        [
            [],
            ["unknown"],
            ["validate"],
            ["validate", "--unknown"],
        ],
    )
    def test_usage_errors(
        self, capsys: pytest.CaptureFixture[str], argv: list[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(argv)
        assert exc.value.code == 2
        output = capsys.readouterr()
        assert output.out == ""
        assert "usage:" in output.err and "error:" in output.err
        assert "Traceback" not in output.err

    @pytest.mark.parametrize("argv", [["--help"], ["validate", "--help"]])
    def test_help(self, capsys: pytest.CaptureFixture[str], argv: list[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(argv)
        assert exc.value.code == 0
        output = capsys.readouterr()
        assert "usage: armarium" in output.out
        assert output.err == ""
