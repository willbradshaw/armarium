"""Command parsing, diagnostics, exit status and process entry point."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from armarium.cli import main


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault with spaces"
    (root / "reference/types").mkdir(parents=True)
    (root / "reference/schemas").mkdir()
    (root / "campaigns").mkdir()
    (root / "reference/schemas/widget.schema.json").write_text("true")
    return root


class TestMain:
    @pytest.mark.parametrize(
        ("text", "name", "status", "diagnostic", "counts"),
        [
            (
                '---\ntype: "[[Widget]]"\n---\n',
                "note.md",
                0,
                "",
                "1 checked, 0 skipped, 0 unsupported",
            ),
            (
                '---\ntype: "[[Unknown]]"\n---\n',
                "note.md",
                0,
                "warning schema.unsupported",
                "1 checked, 0 skipped, 1 unsupported",
            ),
            (
                "plain Markdown",
                "note.md",
                1,
                "note.md [type]: error record.type",
                "1 checked, 0 skipped, 0 unsupported",
            ),
            (
                "---\nx: first\nx: second\n---\n",
                "note.md",
                1,
                "note.md:3: error parse.invalid",
                "1 checked, 0 skipped, 0 unsupported",
            ),
            (
                '---\ntype: "[[Widget]]"\n---\n',
                "reference/templates/Widget.md",
                0,
                "info record.template",
                "0 checked, 1 skipped, 0 unsupported",
            ),
        ],
    )
    def test_validation_output(
        self,
        vault: Path,
        capsys: pytest.CaptureFixture[str],
        text: str,
        name: str,
        status: int,
        diagnostic: str,
        counts: str,
    ) -> None:
        path = vault / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        before = path.read_bytes()
        assert main(["validate", str(path)]) == status
        output = capsys.readouterr()
        assert output.err == ""
        assert output.out.endswith(counts + "\n")
        if diagnostic:
            assert diagnostic in output.out
        else:
            assert output.out == counts + "\n"
        assert path.read_bytes() == before

    def test_explicit_vault_and_process_arguments(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = tmp_path / "note.md"
        path.write_text('---\ntype: "[[Unknown]]"\n---\n')
        monkeypatch.setattr(
            sys, "argv", ["armarium", "validate", str(path), "--vault", str(tmp_path)]
        )
        assert main() == 0
        assert "1 unsupported" in capsys.readouterr().out

    @pytest.mark.parametrize(
        "argv",
        [
            [],
            ["unknown"],
            ["validate"],
            ["validate", "--unknown"],
            ["validate", "missing.md"],
        ],
    )
    def test_usage_errors(
        self, capsys: pytest.CaptureFixture[str], argv: list[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            main(argv)
        assert exc.value.code == 2
        output = capsys.readouterr()
        assert output.out == ""
        assert "usage:" in output.err and "error:" in output.err
        assert "Traceback" not in output.err

    @pytest.mark.parametrize("argv", [["--help"], ["validate", "--help"]])
    def test_help(self, capsys: pytest.CaptureFixture[str], argv: list[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            main(argv)
        assert exc.value.code == 0
        output = capsys.readouterr()
        assert "usage: armarium" in output.out
        assert output.err == ""

    @pytest.mark.parametrize(
        "error", [ValueError("bad target"), OSError("cannot read")]
    )
    def test_invocation_failure_is_usage_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        error: Exception,
    ) -> None:
        from unittest.mock import Mock

        monkeypatch.setattr("armarium.cli.validate_markdown", Mock(side_effect=error))
        with pytest.raises(SystemExit) as exc:
            main(["validate", "note.md"])
        assert exc.value.code == 2
        assert str(error) in capsys.readouterr().err

    @pytest.mark.parametrize("valid", [False, True])
    def test_module_entry_point(self, vault: Path, tmp_path: Path, valid: bool) -> None:
        path = vault / "note.md"
        path.write_text('---\ntype: "[[Widget]]"\n---\n' if valid else "untyped")
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
        assert process.returncode == (0 if valid else 1)
        assert "1 checked, 0 skipped, 0 unsupported" in process.stdout
        assert process.stderr == ""
