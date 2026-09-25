"""Build and installed-command acceptance for the package configuration."""

import os
import re
import shutil
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, Path]:
    root = Path(__file__).resolve().parents[1]
    temporary = tmp_path_factory.mktemp("installed package")
    artifacts = temporary / "artifacts"
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(artifacts), str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    environment = temporary / "environment"
    venv.EnvBuilder(with_pip=True).create(environment)
    bin_directory = environment / ("Scripts" if os.name == "nt" else "bin")
    python = bin_directory / ("python.exe" if os.name == "nt" else "python")
    wheel = next(artifacts.glob("*.whl"))
    subprocess.run(
        [str(python), "-m", "pip", "install", str(wheel)],
        check=True,
        capture_output=True,
        text=True,
    )
    return (
        python,
        bin_directory / ("armarium.exe" if os.name == "nt" else "armarium"),
        artifacts,
    )


@pytest.mark.package
class TestPyproject:
    def test_distribution_contents(self, installed: tuple[Path, Path, Path]) -> None:
        _, _, artifacts = installed
        with zipfile.ZipFile(next(artifacts.glob("*.whl"))) as wheel:
            names = wheel.namelist()
        assert "armarium/cli.py" in names
        assert "armarium/validate.py" in names
        assert not any(name.startswith(("tests/", "vaults/")) for name in names)
        assert not any("__pycache__" in name or ".scratch" in name for name in names)
        with tarfile.open(next(artifacts.glob("*.tar.gz"))) as source:
            names = source.getnames()
        assert any(name.endswith("/pyproject.toml") for name in names)
        assert any(name.endswith("/tests/test_pyproject.py") for name in names)
        assert not any(".scratch" in name or "__pycache__" in name for name in names)

    def test_imports_come_from_installation(
        self, installed: tuple[Path, Path, Path], tmp_path: Path
    ) -> None:
        python, _, _ = installed
        process = subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "from pathlib import Path; import armarium, sys; from importlib.metadata import version; assert Path(armarium.__file__).is_relative_to(Path(sys.prefix)); assert version('armarium') == '0.1.0'",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert process.returncode == 0, process.stderr

    @pytest.mark.parametrize(
        "scenario",
        ["valid", "invalid", "unsupported", "missing", "usage", "broken-link"],
    )
    def test_installed_command(
        self, installed: tuple[Path, Path, Path], tmp_path: Path, scenario: str
    ) -> None:
        _, command, _ = installed
        root = tmp_path / "vault with spaces"
        (root / "reference/types").mkdir(parents=True)
        (root / "reference/schemas").mkdir()
        (root / "campaigns").mkdir()
        (root / "reference/schemas/widget.schema.json").write_text("true")
        (root / "reference/types/Widget.md").write_text('---\ntype: "[[Type]]"\n---\n')
        path = root / "record.md"
        text = (
            "untyped"
            if scenario == "invalid"
            else f'---\ntype: "[[{"Unknown" if scenario == "unsupported" else "Widget"}]]"\n---\n'
        )
        if scenario == "broken-link":
            text += "[[Missing target]]\n"
        path.write_text(text)
        working = tmp_path / "unrelated"
        working.mkdir()
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        arguments = [str(command), "validate"]
        if scenario != "usage":
            arguments.append(
                str(working / "missing.md" if scenario == "missing" else path)
            )
        process = subprocess.run(
            arguments,
            cwd=working,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert (
            process.returncode
            == {
                "valid": 0,
                "invalid": 1,
                "unsupported": 1,
                "missing": 1,
                "usage": 2,
                "broken-link": 1,
            }[scenario]
        ), process.stderr
        assert process.stdout == ""
        if scenario == "broken-link":
            assert "link.missing" in process.stderr
        if scenario == "usage":
            assert "usage: armarium validate" in process.stderr
            assert "error:" in process.stderr
        elif scenario == "missing":
            assert "ValueError:" in process.stderr
        else:
            assert "1 checked" in process.stderr
            assert re.match(
                r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{2} UTC\] (INFO|WARNING|ERROR): ",
                process.stderr,
            )
        assert ("Traceback" in process.stderr) == (
            scenario in {"invalid", "unsupported", "missing", "broken-link"}
        )
        if scenario in {"invalid", "unsupported", "broken-link"}:
            assert process.stderr.rstrip().endswith(
                "ValidationError: 1 file failed validation"
            )
        if scenario == "unsupported":
            assert "1 unsupported" in process.stderr
        assert path.read_text() == text

    @pytest.mark.parametrize("vault", ["starter", "example"])
    @pytest.mark.parametrize("directory", [False, True])
    def test_fresh_vault_copy(
        self,
        installed: tuple[Path, Path, Path],
        tmp_path: Path,
        vault: str,
        directory: bool,
    ) -> None:
        _, command, _ = installed
        source = Path(__file__).resolve().parents[1] / "vaults" / vault
        target = tmp_path / "fresh vault with spaces"
        shutil.copytree(source, target)
        record = target / "reference/types/Type.md"
        before = record.read_bytes()
        process = subprocess.run(
            [str(command), "validate", str(target if directory else record)],
            cwd=tmp_path,
            env={
                key: value
                for key, value in os.environ.items()
                if key not in {"PYTHONPATH", "PYTHONHOME"}
            },
            capture_output=True,
            text=True,
            check=False,
        )
        assert process.returncode == 0, process.stdout + process.stderr
        assert process.stdout == ""
        if directory:
            assert process.stderr.endswith("6 skipped, 0 unsupported\n")
        else:
            assert process.stderr.endswith(
                "INFO: 1 checked, 0 skipped, 0 unsupported\n"
            )
        assert record.read_bytes() == before
