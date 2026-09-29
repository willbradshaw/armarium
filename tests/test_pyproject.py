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
    source = temporary / "source"
    source.mkdir()
    for folder in ("src", "tests", "vaults", "docs"):
        shutil.copytree(
            root / folder, source / folder, ignore=shutil.ignore_patterns("__pycache__")
        )
    for name in ("pyproject.toml", "README.md", "AGENTS.md", "ruff.toml", ".gitignore"):
        shutil.copyfile(root / name, source / name)
    # Build from a used checkout, not just a pristine tree. Local vault state
    # must not leak into either distribution or a newly initialized vault.
    for name in (
        ".scratch/private.md",
        ".obsidian/workspace.json",
        ".obsidian/workspace-mobile.json",
        ".env",
        ".env.local",
        "session.cookie",
        ".DS_Store",
        "__pycache__/generated.pyc",
    ):
        path = source / "vaults/starter" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Local-only data")
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(artifacts), str(source)],
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
    def test_installed_record_workflow(
        self, installed: tuple[Path, Path, Path], tmp_path: Path
    ) -> None:
        """Create linked records through the installed commands in one vault."""
        _, command, _ = installed
        root = tmp_path / "workflow-vault"
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        steps = [
            ["init", str(root)],
            ["add", "player", "Alex", "--campaign", "1", "--vault", str(root)],
            [
                "add",
                "content",
                "Mira",
                "--subtype",
                "PC",
                "--player",
                "Alex",
                "--campaign",
                "1",
                "--vault",
                str(root),
            ],
            ["add", "note", "Mira notes", "--campaign", "1", "--vault", str(root)],
            [
                "add",
                "clue",
                "--campaign",
                "1",
                "--vault",
                str(root),
                "--text",
                "[[Mira]] knows the route; [[Mira]] drew the map.",
            ],
            ["validate", str(root)],
        ]
        for arguments in steps:
            result = subprocess.run(
                [str(command), *arguments],
                cwd=tmp_path,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr
        assert (root / "campaigns/campaign_1/notes/Mira notes.md").is_file()
        pc = root / "campaigns/campaign_1/content/Mira.md"
        assert "reference/players/Alex" in pc.read_text()
        clue = root / "campaigns/campaign_1/clues/C-1-0001.md"
        assert clue.read_text().count("[[campaigns/campaign_1/content/Mira]]") == 1
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        refused = subprocess.run(
            [
                str(command),
                "add",
                "clue",
                "--campaign",
                "1",
                "--vault",
                str(root),
                "--text",
                "[[Mira notes]] contains the route.",
            ],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert refused.returncode == 1 and "must target Content" in refused.stderr
        assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before

    @pytest.mark.parametrize("scope", ["shared", "inferred", "explicit"])
    def test_installed_add_note(
        self,
        installed: tuple[Path, Path, Path],
        tmp_path: Path,
        scope: str,
    ) -> None:
        import json

        _, command, _ = installed
        root = tmp_path / "vault with spaces"
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        initialized = subprocess.run(
            [str(command), "init", str(root)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert initialized.returncode == 0, initialized.stderr
        template = root / "reference/templates/Note.md"
        template.write_text(
            '---\ntype: "[[types/Note]]"\ncustom: Local value\n---\n\n## Ideas\nLocal guidance.\n'
        )
        definition = root / "reference/types/Note.md"
        definition.write_text(
            definition.read_text()
            .replace("shared: notes", "shared: notes/working")
            .replace("campaign: notes", "campaign: notes/working")
        )
        for directory in ("notes/working", "campaigns/campaign_1/notes/working"):
            (root / directory).mkdir()
        schema = root / "reference/schemas/note.schema.json"
        data = json.loads(schema.read_text())
        data["properties"]["frontmatter"]["required"].append("custom")
        schema.write_text(json.dumps(data))
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        args = [str(command), "add", "note", "Working ideas"]
        if scope != "inferred":
            args += ["--vault", str(root)]
        if scope == "explicit":
            args += ["--campaign", "1"]
        cwd = (
            root / "campaigns/campaign_1/reference/players"
            if scope == "inferred"
            else tmp_path
        )
        result = subprocess.run(
            args, cwd=cwd, env=environment, capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout == ""
        assert result.stderr.rstrip().endswith("Validation completed successfully")
        destination = (
            root
            / (
                "notes/working"
                if scope == "shared"
                else "campaigns/campaign_1/notes/working"
            )
            / "Working ideas.md"
        )
        assert destination.read_bytes() == template.read_bytes()
        assert all(p.read_bytes() == contents for p, contents in before.items())
        refused = subprocess.run(
            args, cwd=cwd, env=environment, capture_output=True, text=True, check=False
        )
        assert refused.returncode == 1
        assert "already exists" in refused.stderr and "Traceback" not in refused.stderr
        assert destination.read_bytes() == template.read_bytes()
        validated = subprocess.run(
            [str(command), "validate", str(root)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert validated.returncode == 0, validated.stderr

    @pytest.mark.parametrize("explicit", [False, True])
    def test_installed_add_player(
        self, installed: tuple[Path, Path, Path], tmp_path: Path, explicit: bool
    ) -> None:
        _, command, _ = installed
        root = tmp_path / "vault with spaces"
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        initialized = subprocess.run(
            [str(command), "init", str(root)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert initialized.returncode == 0, initialized.stderr
        definition = root / "reference/types/Player.md"
        definition.write_text(
            definition.read_text().replace(
                "campaign: reference/players", "campaign: reference/people"
            )
        )
        (root / "campaigns/campaign_1/reference/people").mkdir()
        template = root / "reference/templates/Player.md"
        template.write_text(template.read_text() + "\nLocal player guidance.\n")
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        args = [str(command), "add", "player", "New Player"]
        if explicit:
            args += ["--vault", str(root), "--campaign", "1"]
        working = tmp_path if explicit else root / "campaigns/campaign_1/reference"
        for expected in (0, 1):
            result = subprocess.run(
                args,
                cwd=working,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == expected, result.stderr
            assert "Traceback" not in result.stderr
            assert ("Validation completed successfully" in result.stderr) == (
                expected == 0
            )
        destination = root / "campaigns/campaign_1/reference/people/New Player.md"
        assert "Local player guidance." in destination.read_text()
        assert all(p.read_bytes() == data for p, data in before.items())
        player_before = destination.read_bytes()
        created = subprocess.run(
            [
                str(command),
                "add",
                "content",
                "New PC",
                "--subtype",
                "PC",
                "--player",
                "New Player",
                "--campaign",
                "1",
                "--vault",
                str(root),
            ],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert created.returncode == 0, created.stderr
        assert destination.read_bytes() == player_before

    @pytest.mark.parametrize("explicit", [False, True])
    def test_installed_add_clue(
        self, installed: tuple[Path, Path, Path], tmp_path: Path, explicit: bool
    ) -> None:
        _, command, _ = installed
        root = tmp_path / "my-vault"
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        initialized = subprocess.run(
            [str(command), "init", str(root)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert initialized.returncode == 0, initialized.stderr
        template = root / "reference/templates/Clue.md"
        template.write_text(
            template.read_text().replace('text: ""', 'text: "Local fact."')
        )
        help_result = subprocess.run(
            [str(command), "add", "clue", "--help", "--vault", str(root)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert help_result.returncode == 0, help_result.stderr
        assert '(default: "Local fact.")' in " ".join(help_result.stdout.split())
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        arguments = [str(command), "add", "clue"]
        if explicit:
            arguments += ["--vault", str(root), "--campaign", "1"]
        working_directory = (
            tmp_path if explicit else root / "campaigns/campaign_1/clues"
        )
        for options, expected in (([], 1), (["--number", "7"], 7), ([], 8)):
            result = subprocess.run(
                [*arguments, *options],
                cwd=working_directory,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr
            assert result.stdout == ""
            assert result.stderr.rstrip().endswith("Validation completed successfully")
            destination = root / "campaigns/campaign_1/clues" / f"C-1-{expected:04}.md"
            assert "Local fact." in destination.read_text()
        assert all(p.read_bytes() == text for p, text in before.items())
        original = root / "campaigns/campaign_1/clues/C-1-0001.md"
        contents = original.read_bytes()
        refused = subprocess.run(
            [*arguments, "--number", "1"],
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert refused.returncode == 1
        assert "already exists" in refused.stderr and "Traceback" not in refused.stderr
        assert original.read_bytes() == contents

    @pytest.mark.parametrize("explicit", [False, True])
    def test_installed_add_session(
        self, installed: tuple[Path, Path, Path], tmp_path: Path, explicit: bool
    ) -> None:
        _, command, _ = installed
        root = tmp_path / "my-vault"
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        initialized = subprocess.run(
            [str(command), "init", str(root)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert initialized.returncode == 0, initialized.stderr
        template = root / "reference/templates/Session.md"
        template.write_text(
            template.read_text().replace(
                "## Starting scene\n- N/A", "## Starting scene\nLocal instructions."
            )
        )
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        arguments = [str(command), "add", "session"]
        if explicit:
            arguments += ["--vault", str(root), "--campaign", "1"]
        working_directory = (
            tmp_path if explicit else root / "campaigns/campaign_1/sessions"
        )
        for options, expected in (([], 1), (["--number", "7"], 7), ([], 8)):
            result = subprocess.run(
                [*arguments, *options],
                cwd=working_directory,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr
            assert result.stdout == ""
            assert result.stderr.rstrip().endswith("Validation completed successfully")
            destination = (
                root / "campaigns/campaign_1/sessions" / f"S-1-{expected:03}.md"
            )
            assert "Local instructions." in destination.read_text()
        assert all(p.read_bytes() == text for p, text in before.items())
        original = root / "campaigns/campaign_1/sessions/S-1-001.md"
        contents = original.read_bytes()
        refused = subprocess.run(
            [*arguments, "--number", "1"],
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert refused.returncode == 1
        assert "already exists" in refused.stderr and "Traceback" not in refused.stderr
        assert original.read_bytes() == contents

    @pytest.mark.parametrize("subtype", ["Location", "PC"])
    def test_installed_add_content(
        self, installed: tuple[Path, Path, Path], tmp_path: Path, subtype: str
    ) -> None:
        _, command, _ = installed
        root = tmp_path / "my-vault"
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        initialized = subprocess.run(
            [str(command), "init", str(root)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert initialized.returncode == 0, initialized.stderr
        (root / "campaigns/campaign_1/reference/players/Alex.md").write_text(
            '---\ntype: "[[types/Player]]"\nplays: []\n---\n'
        )
        template = root / "reference/templates/Content.md"
        template.write_text(
            template.read_text().replace("## Notes\n- N/A", "## Notes\nLocal guidance.")
        )
        args = [
            str(command),
            "add",
            "content",
            "New Entity",
            "--subtype",
            subtype,
            "--vault",
            str(root),
        ]
        if subtype == "PC":
            args += ["--player", "Alex"]
        working_directory = (
            root / "campaigns/campaign_1" if subtype == "PC" else tmp_path
        )
        created = subprocess.run(
            args,
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert created.returncode == 0, created.stderr
        assert created.stderr.rstrip().endswith("Validation completed successfully")
        directory = root / (
            "campaigns/campaign_1/content" if subtype == "PC" else "content"
        )
        destination = directory / "New Entity.md"
        assert "Local guidance." in destination.read_text()
        before = destination.read_bytes()
        refused = subprocess.run(
            args,
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert refused.returncode == 1 and "already exists" in refused.stderr
        assert "Traceback" not in refused.stderr
        assert destination.read_bytes() == before

    @pytest.mark.parametrize("explicit", [False, True])
    def test_installed_add_campaign(
        self, installed: tuple[Path, Path, Path], tmp_path: Path, explicit: bool
    ) -> None:
        _, command, _ = installed
        root = tmp_path / "my-vault"
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        initialized = subprocess.run(
            [str(command), "init", str(root)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert initialized.returncode == 0, initialized.stderr
        template = root / "reference/templates/Campaign.md"
        template.write_text(template.read_text() + "\nLocal campaign guidance.\n")
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        arguments = ["add", "campaign"]
        if explicit:
            arguments += ["--vault", str(root), "--number", "12"]
        result = subprocess.run(
            [str(command), *arguments],
            cwd=tmp_path if explicit else root / "content",
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout == ""
        assert result.stderr.rstrip().endswith("Validation completed successfully")
        destination = root / "campaigns" / ("campaign_12" if explicit else "campaign_2")
        assert (
            destination / "reference/Campaign.md"
        ).read_bytes() == template.read_bytes()
        assert all(p.read_bytes() == contents for p, contents in before.items())
        refused = subprocess.run(
            [str(command), "add", "campaign", "--vault", str(root), "--number", "1"],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert refused.returncode == 1
        assert "already exists" in refused.stderr
        assert "Traceback" not in refused.stderr

    def test_distribution_contents(self, installed: tuple[Path, Path, Path]) -> None:
        _, _, artifacts = installed
        with zipfile.ZipFile(next(artifacts.glob("*.whl"))) as wheel:
            names = wheel.namelist()
        assert "armarium/cli.py" in names
        assert "armarium/validate.py" in names
        assert not any(name.startswith(("tests/", "vaults/")) for name in names)
        assert not any("__pycache__" in name for name in names)
        starter = Path(__file__).resolve().parents[1] / "vaults/starter"
        expected = {
            p.relative_to(starter).as_posix() for p in starter.rglob("*") if p.is_file()
        }
        assert {
            name.removeprefix("armarium/starter/")
            for name in names
            if name.startswith("armarium/starter/")
        } == expected
        with zipfile.ZipFile(next(artifacts.glob("*.whl"))) as wheel:
            for name in expected:
                assert (
                    wheel.read("armarium/starter/" + name)
                    == (starter / name).read_bytes()
                )
        with tarfile.open(next(artifacts.glob("*.tar.gz"))) as source:
            names = source.getnames()
        assert any(name.endswith("/pyproject.toml") for name in names)
        assert any(name.endswith("/tests/test_pyproject.py") for name in names)
        assert not any("__pycache__" in name for name in names)
        assert not any(
            ".scratch" in name and not name.endswith(".scratch/.gitkeep")
            for name in names
        )
        assert not any(
            name.endswith(("workspace.json", ".env", ".DS_Store")) for name in names
        )

    def test_installed_init(
        self, installed: tuple[Path, Path, Path], tmp_path: Path
    ) -> None:
        _, command, _ = installed
        target = tmp_path / "new-parent/my-vault"
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        created = subprocess.run(
            [str(command), "init", str(target)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert created.returncode == 0, created.stderr
        assert [line.split("INFO: ", 1)[1] for line in created.stderr.splitlines()] == [
            f"Initializing new vault at {target}",
            "New vault successfully initialized; validating",
            "Validation completed successfully",
        ]
        assert created.stdout == ""
        source = Path(__file__).resolve().parents[1] / "vaults/starter"
        expected = {
            p.relative_to(source): p.read_bytes()
            for p in source.rglob("*")
            if p.is_file()
        }
        assert {
            p.relative_to(target): p.read_bytes()
            for p in target.rglob("*")
            if p.is_file()
        } == expected
        # Independent after creation: moving it does not break resources or links.
        relocated = target.rename(tmp_path / "Moved setting")
        checked = subprocess.run(
            [str(command), "validate", str(relocated)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert checked.returncode == 0, checked.stderr
        assert "8 skipped, 0 unsupported" in checked.stderr
        customized = relocated / "campaigns/campaign_1/reference/Campaign.md"
        customized.write_text(customized.read_text() + "\nMy campaign.\n")
        before = {
            p.relative_to(relocated): p.read_bytes()
            for p in relocated.rglob("*")
            if p.is_file()
        }
        refused = subprocess.run(
            [str(command), "init", str(relocated)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert refused.returncode == 1
        assert "Cannot create vault" in refused.stderr
        assert "Traceback" not in refused.stderr
        assert {
            p.relative_to(relocated): p.read_bytes()
            for p in relocated.rglob("*")
            if p.is_file()
        } == before
        forced = subprocess.run(
            [str(command), "init", "--force", str(relocated)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert forced.returncode == 0, forced.stderr
        assert forced.stderr.splitlines()[1].endswith(
            "WARNING: Directory already exists; overwriting"
        )
        assert forced.stderr.rstrip().endswith("Validation completed successfully")
        assert {
            p.relative_to(relocated): p.read_bytes()
            for p in relocated.rglob("*")
            if p.is_file()
        } == expected

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
        (root / "content").mkdir()
        for name, directory in (("Widget", "content"), ("Type", "reference/types")):
            (root / f"reference/types/{name}.md").write_text(
                f'---\ntype: "[[Type]]"\ndirectories: {{shared: {directory}}}\n---\n'
            )
        path = root / "content/record.md"
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
        assert ("Traceback" in process.stderr) == (scenario == "missing")
        if scenario in {"invalid", "unsupported", "broken-link"}:
            assert process.stderr.rstrip().endswith("ERROR: 1 file failed validation")
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
            assert process.stderr.endswith("8 skipped, 0 unsupported\n")
        else:
            assert process.stderr.endswith(
                "INFO: 1 checked, 0 skipped, 0 unsupported\n"
            )
        assert record.read_bytes() == before
