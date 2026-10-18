"""Command parsing, diagnostics, exit status and process entry point."""

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from armarium import cli
from armarium.changes import FileChange, FileChanges
from armarium.cli import (
    _jobs,
    _mark,
    _min_repeats,
    _positive,
    _subtype_choices,
    main,
    parse_args,
    report_plan,
)
from armarium.handout import Handout, Page
from armarium.illustrate import Candidate, Generation
from armarium.lib import SUBTYPES, Diagnostic, Result, VaultNotFoundError
from armarium.logging import configure_logging, logger
from armarium.relink import RelinkChange, RelinkPlan
from armarium.transcribe import (
    DEFAULT_LANGUAGE,
    DEFAULT_MIN_REPEATS,
    DEFAULT_MODEL,
    DEFAULT_MODEL_DIR,
    DEFAULT_VAD_MODEL,
    Transcription,
)


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


@pytest.fixture
def relic_vault(tmp_path: Path) -> Path:
    """A starter vault with a local registration declaring a Relic subtype."""
    root = tmp_path / "relics"
    shutil.copytree(Path(__file__).resolve().parents[1] / "vaults/starter", root)
    (root / "reference/schemas/relic.schema.json").write_text("true")
    (root / "reference/templates/Relic.md").write_text(
        (root / "reference/templates/Content.md")
        .read_text()
        .replace("subtype:\n", "subtype: Relic\n")
    )
    rule = {
        "type": "Content",
        "subtype": "Relic",
        "schema": "schemas/relic.schema.json",
        "template": "templates/Relic.md",
    }
    (root / "reference/extensions.json").write_text(
        json.dumps({"relics": {"subtypes": {"Content": ["Relic"]}, "rules": [rule]}})
    )
    return root


@pytest.fixture(autouse=True)
def preserve_logger() -> Iterator[None]:
    handlers, level, propagate = logger.handlers[:], logger.level, logger.propagate
    yield
    logger.handlers, logger.level, logger.propagate = handlers, level, propagate


class TestMain:
    @pytest.mark.parametrize("campaign", [False, True])
    def test_add_note(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        campaign: bool,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "vault with spaces")
        monkeypatch.chdir(root / "notes")
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "add", "note", "Working ideas"]
            + (["--vault", str(root), "--campaign", "1"] if campaign else []),
        )
        main()
        destination = (
            root
            / ("campaigns/campaign_1/notes" if campaign else "notes")
            / "Working ideas.md"
        )
        assert destination.is_file()
        output = capsys.readouterr()
        assert output.out == ""
        assert [line.split("INFO: ", 1)[1] for line in output.err.splitlines()] == [
            f"Adding new Note record at {destination}",
            "New note successfully created; validating",
            "Validation completed successfully",
        ]

    @pytest.mark.parametrize(
        "scenario", ["missing_campaign", "schema", "unrelated_error", "collision"]
    )
    def test_add_note_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        scenario: str,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "vault with spaces")
        monkeypatch.chdir(root)
        destination = root / "notes/Ideas.md"
        if scenario == "schema":
            (root / "reference/schemas/note.schema.json").write_text("false")
        elif scenario == "unrelated_error":
            (root / "content/Broken.md").write_text("No type")
        elif scenario == "collision":
            destination.write_text("Unchanged")
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "add", "note", "Ideas"]
            + (["--campaign", "9"] if scenario == "missing_campaign" else []),
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert "Traceback" not in output.err
        assert "Validation completed successfully" not in output.err
        if scenario == "unrelated_error":
            assert destination.is_file()
            assert f"Note retained at {destination}" in output.err
            assert "record.type" in output.err
        elif scenario == "collision":
            assert destination.read_text() == "Unchanged"
        else:
            assert not destination.exists()
            assert "Cannot add note" in output.err
            if scenario == "schema":
                assert "schema" in output.err

    @pytest.mark.parametrize("explicit", [False, True])
    def test_add_player(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        explicit: bool,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "my-vault")
        monkeypatch.chdir(tmp_path if explicit else root / "campaigns/campaign_1")
        arguments = ["armarium", "add", "player", "New Player"]
        if explicit:
            arguments += ["--vault", str(root), "--campaign", "1"]
        monkeypatch.setattr(sys, "argv", arguments)
        main()
        destination = root / "campaigns/campaign_1/reference/players/New Player.md"
        assert destination.is_file()
        output = capsys.readouterr()
        assert output.out == ""
        assert [line.split("INFO: ", 1)[1] for line in output.err.splitlines()] == [
            f"Adding new Player record at {destination}",
            "New player successfully created; validating",
            "Validation completed successfully",
        ]

    @pytest.mark.parametrize(
        "scenario", ["missing_campaign", "invalid_template", "unrelated_error"]
    )
    def test_add_player_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        scenario: str,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "my-vault")
        monkeypatch.chdir(root)
        if scenario == "invalid_template":
            template = root / "reference/templates/Player.md"
            template.write_text(
                template.read_text().replace("plays: []", "plays: null")
            )
        elif scenario == "unrelated_error":
            (root / "content/Broken.md").write_text("No type")
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "add", "player", "New Player"]
            + ([] if scenario == "missing_campaign" else ["--campaign", "1"]),
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert "Traceback" not in output.err
        assert "Validation completed successfully" not in output.err
        destination = root / "campaigns/campaign_1/reference/players/New Player.md"
        if scenario == "unrelated_error":
            assert destination.is_file()
            assert "Player retained at" in output.err
        else:
            assert not destination.exists()
            assert "Cannot add player" in output.err

    @pytest.mark.parametrize("explicit", [False, True])
    def test_add_clue(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        explicit: bool,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "my-vault")
        monkeypatch.chdir(tmp_path if explicit else root / "campaigns/campaign_1")
        arguments = [
            "armarium",
            "add",
            "clue",
            "--frontmatter",
            json.dumps({"text": "A fact."}),
        ]
        if explicit:
            arguments += ["--vault", str(root), "--campaign", "1", "--number", "12"]
        monkeypatch.setattr(sys, "argv", arguments)
        main()
        destination = (
            root
            / "campaigns/campaign_1/clues"
            / ("C-1-0012.md" if explicit else "C-1-0001.md")
        )
        assert destination.is_file()
        output = capsys.readouterr()
        assert output.out == ""
        assert [line.split("INFO: ", 1)[1] for line in output.err.splitlines()] == [
            f"Adding new Clue record at {destination}",
            "New clue successfully created; validating",
            "Validation completed successfully",
        ]

    @pytest.mark.parametrize(
        "scenario", ["missing_campaign", "invalid_template", "unrelated_error"]
    )
    def test_add_clue_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        scenario: str,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "my-vault")
        monkeypatch.chdir(root)
        if scenario == "invalid_template":
            template = root / "reference/templates/Clue.md"
            template.write_text(
                template.read_text().replace("## Sessions", "## Wrong heading")
            )
        elif scenario == "unrelated_error":
            (root / "content/Broken.md").write_text("No type")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "armarium",
                "add",
                "clue",
                "--frontmatter",
                json.dumps({"text": "A fact."}),
            ]
            + ([] if scenario == "missing_campaign" else ["--campaign", "1"]),
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert "Traceback" not in output.err
        assert "Validation completed successfully" not in output.err
        destination = root / "campaigns/campaign_1/clues/C-1-0001.md"
        if scenario == "unrelated_error":
            assert destination.is_file()
            assert "Clue retained at" in output.err
        else:
            assert not destination.exists()
            assert "Cannot add clue" in output.err

    @pytest.mark.parametrize("scenario", ["valid", "body", "missing", "unrelated"])
    def test_add_transcript(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        scenario: str,
    ) -> None:
        from armarium.init import init_vault
        from armarium.session import add_session

        root = init_vault(tmp_path / "my vault")
        add_session(root, campaign=1)
        body = tmp_path / "speech.md"
        body.write_text(
            "Invalid" if scenario == "body" else "## Opening\n- [GM] Hello.\n"
        )
        if scenario == "unrelated":
            (root / "content/Broken.md").write_text("No type")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "armarium",
                "add",
                "transcript",
                "Missing" if scenario == "missing" else "S-1-001",
                "--body-file",
                str(body),
                "--vault",
                str(root),
            ],
        )
        if scenario == "valid":
            main()
        else:
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
        output = capsys.readouterr()
        destination = (
            root / "campaigns/campaign_1/sessions/transcripts/S-1-001 Transcript.md"
        )
        assert destination.exists() == (scenario in {"valid", "unrelated"})
        assert output.out == "" and "Traceback" not in output.err
        assert ("Validation completed successfully" in output.err) == (
            scenario == "valid"
        )
        if scenario == "valid":
            assert [line.split("INFO: ", 1)[1] for line in output.err.splitlines()] == [
                f"Adding new Transcript record at {destination}",
                "New transcript successfully created; validating",
                "Validation completed successfully",
            ]
        elif scenario == "unrelated":
            assert "Transcript retained at" in output.err
        else:
            assert "Cannot add transcript" in output.err

    @pytest.mark.parametrize("explicit", [False, True])
    def test_add_session(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        explicit: bool,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "my-vault")
        monkeypatch.chdir(tmp_path if explicit else root / "campaigns/campaign_1")
        arguments = ["armarium", "add", "session"]
        if explicit:
            arguments += ["--vault", str(root), "--campaign", "1", "--number", "12"]
        monkeypatch.setattr(sys, "argv", arguments)
        main()
        destination = (
            root
            / "campaigns/campaign_1/sessions"
            / ("S-1-012.md" if explicit else "S-1-001.md")
        )
        assert destination.is_file()
        output = capsys.readouterr()
        assert output.out == ""
        assert [line.split("INFO: ", 1)[1] for line in output.err.splitlines()] == [
            f"Adding new Session record at {destination}",
            "New session successfully created; validating",
            "Validation completed successfully",
        ]

    @pytest.mark.parametrize(
        "scenario", ["missing_campaign", "invalid_template", "unrelated_error"]
    )
    def test_add_session_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        scenario: str,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "my-vault")
        monkeypatch.chdir(root)
        if scenario == "invalid_template":
            template = root / "reference/templates/Session.md"
            template.write_text(
                template.read_text().replace("## Starting scene", "## Wrong heading")
            )
        elif scenario == "unrelated_error":
            (root / "content/Broken.md").write_text("No type")
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "add", "session"]
            + ([] if scenario == "missing_campaign" else ["--campaign", "1"]),
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert "Traceback" not in output.err
        assert "Validation completed successfully" not in output.err
        destination = root / "campaigns/campaign_1/sessions/S-1-001.md"
        if scenario == "unrelated_error":
            assert destination.is_file()
            assert "Session retained at" in output.err
        else:
            assert not destination.exists()
            assert "Cannot add session" in output.err

    @pytest.mark.parametrize("campaign", [False, True])
    def test_add_content(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        campaign: bool,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "my-vault")
        monkeypatch.chdir(root / "content")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "armarium",
                "add",
                "content",
                "Port Briselle",
                "--subtype",
                "Location",
            ]
            + (["--vault", str(root), "--campaign", "1"] if campaign else []),
        )
        main()
        directory = root / ("campaigns/campaign_1/content" if campaign else "content")
        destination = directory / "Port Briselle.md"
        assert destination.is_file()
        output = capsys.readouterr()
        assert output.out == ""
        assert [line.split("INFO: ", 1)[1] for line in output.err.splitlines()] == [
            f"Adding new Content record at {destination}",
            "New content successfully created; validating",
            "Validation completed successfully",
        ]

    def test_add_date_content(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from armarium.content import add_content
        from armarium.init import init_vault
        from armarium.parse import Record

        root = init_vault(tmp_path / "my-vault")
        add_content("Calendar", "Lore", root)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "armarium",
                "add",
                "content",
                "Year 42",
                "--subtype",
                "Date",
                "--vault",
                str(root),
                "--frontmatter",
                json.dumps({"reckoning": "[[" + "Calendar" + "]]", "scale": "year"}),
            ],
        )
        main()
        record, _ = Record.parse(root / "content/Year 42.md", root)
        assert record is not None
        assert record.frontmatter["reckoning"] == "[[Calendar]]"
        assert record.frontmatter["scale"] == "year"

    def test_add_content_missing_player(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "my-vault")
        monkeypatch.chdir(root)
        monkeypatch.setattr(
            sys, "argv", ["armarium", "add", "content", "Mira", "--subtype", "PC"]
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert "Cannot add content" in output.err and "player" in output.err
        assert "Traceback" not in output.err
        assert not (root / "content/Mira.md").exists()

    @pytest.mark.parametrize("explicit", [False, True])
    def test_add_campaign(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        explicit: bool,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "my-vault")
        monkeypatch.chdir(tmp_path if explicit else root / "content")
        argv = ["armarium", "add", "campaign"]
        if explicit:
            argv += ["--vault", str(root), "--number", "7"]
        monkeypatch.setattr(sys, "argv", argv)
        main()
        destination = root / "campaigns" / ("campaign_7" if explicit else "campaign_2")
        assert (destination / "reference/Campaign.md").is_file()
        output = capsys.readouterr()
        assert output.out == ""
        assert [line.split("INFO: ", 1)[1] for line in output.err.splitlines()] == [
            f"Adding new campaign at {destination}",
            "New campaign successfully created; validating",
            "Validation completed successfully",
        ]

    @pytest.mark.parametrize(
        "scenario", ["outside", "existing", "missing_template", "invalid_record"]
    )
    def test_add_campaign_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        scenario: str,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "my-vault")
        template = root / "reference/templates/Campaign.md"
        if scenario == "missing_template":
            template.unlink()
        elif scenario == "invalid_record":
            template.write_text("Missing frontmatter")
        monkeypatch.chdir(tmp_path if scenario == "outside" else root)
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "add", "campaign"]
            + (["--number", "1"] if scenario == "existing" else []),
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert "Traceback" not in output.err
        assert "Validation completed successfully" not in output.err
        destination = root / "campaigns/campaign_2"
        if scenario == "invalid_record":
            assert "record.type" in output.err
            assert f"Campaign retained at {destination}" in output.err
            assert destination.is_dir()
        else:
            assert "Cannot add campaign" in output.err
            assert not destination.exists()

    @pytest.mark.parametrize("existing", [False, True])
    def test_force_warning(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        existing: bool,
    ) -> None:
        destination = tmp_path / "my-vault"
        if existing:
            destination.mkdir()
        monkeypatch.setattr(
            sys, "argv", ["armarium", "init", "--force", str(destination)]
        )
        main()
        lines = capsys.readouterr().err.splitlines()
        warning = "WARNING: Directory already exists; overwriting"
        if existing:
            assert len(lines) == 4
            assert lines[1].endswith(warning)
            assert lines[2].endswith("New vault successfully initialized; validating")
        else:
            assert len(lines) == 3
            assert all(warning not in line for line in lines)

    @pytest.mark.parametrize("existing", [False, True])
    def test_init(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        existing: bool,
    ) -> None:
        destination = tmp_path / "My Setting"
        working_directory = tmp_path / "checkout"
        working_directory.mkdir()
        monkeypatch.chdir(working_directory)
        if existing:
            destination.mkdir()
        monkeypatch.setattr(sys, "argv", ["armarium", "init", "../My Setting"])
        if existing:
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
            assert list(destination.iterdir()) == []
        else:
            assert main() is None
            assert (destination / ".obsidian/app.json").is_file()
        output = capsys.readouterr()
        assert output.out == ""
        assert (
            "Cannot create vault" if existing else "successfully initialized"
        ) in output.err
        assert "Traceback" not in output.err
        if not existing:
            assert [line.split("INFO: ", 1)[1] for line in output.err.splitlines()] == [
                f"Initializing new vault at {destination}",
                "New vault successfully initialized; validating",
                "Validation completed successfully",
            ]
        else:
            assert "successfully initialized" not in output.err
            assert "Validation completed successfully" not in output.err

    def test_init_validation_warning(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from unittest.mock import Mock

        destination = tmp_path / "my-vault"
        monkeypatch.setattr(
            "armarium.cli.validate",
            Mock(
                return_value=Result(
                    [
                        Diagnostic(
                            "record.md",
                            "example.warning",
                            "Check this",
                            severity="warning",
                        ),
                        Diagnostic(
                            "template.md", "record.template", "Skipped", severity="info"
                        ),
                    ]
                )
            ),
        )
        monkeypatch.setattr(sys, "argv", ["armarium", "init", str(destination)])
        main()
        output = capsys.readouterr()
        assert output.out == ""
        assert len(output.err.splitlines()) == 4
        assert "WARNING: record.md:: - example.warning - Check this" in output.err
        assert output.err.rstrip().endswith("Validation completed successfully")

    def test_init_validation_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        import shutil

        starter = tmp_path / "starter"
        shutil.copytree(Path(__file__).resolve().parents[1] / "vaults/starter", starter)
        (starter / "content/Broken.md").write_text("Missing frontmatter")
        monkeypatch.setattr("armarium.init._starter", lambda: starter)
        destination = tmp_path / "New vault"
        monkeypatch.setattr(sys, "argv", ["armarium", "init", str(destination)])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert "content/Broken.md:type: - record.type" in output.err
        assert "1 file failed validation" in output.err
        assert f"Vault retained at {destination} for inspection" in output.err
        assert "New vault successfully initialized; validating" in output.err
        assert "Validation completed successfully" not in output.err
        assert "Traceback" not in output.err
        assert (destination / "content/Broken.md").read_text() == "Missing frontmatter"

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
                "ERROR: content/record.md:: - schema.unsupported",
                "1 checked, 0 skipped, 1 unsupported",
            ),
            (
                "plain Markdown",
                "content/record.md",
                1,
                "ERROR: content/record.md:type: - record.type",
                "1 checked, 0 skipped, 0 unsupported",
            ),
            (
                "---\nx: first\nx: second\n---\n",
                "content/record.md",
                1,
                "ERROR: content/record.md::3 - parse.invalid",
                "1 checked, 0 skipped, 0 unsupported",
            ),
            (
                '---\ntype: "[[Widget]]"\n---\n',
                "reference/templates/Widget.md",
                0,
                "INFO: reference/templates/Widget.md:: - record.template",
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
            with pytest.raises(SystemExit) as exit_status:
                main()
            assert exit_status.value.code == 1
        else:
            assert main() is None
        output = capsys.readouterr()
        assert output.out == ""
        lines = output.err.splitlines()
        if status:
            assert lines[-1].endswith("ERROR: 1 file failed validation")
            lines.pop()
        assert lines[-1].endswith("INFO: " + counts)
        headers = re.findall(
            r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{2} UTC\] (INFO|WARNING|ERROR): ",
            output.err,
            re.MULTILINE,
        )
        assert len(headers) == (2 if diagnostic else 1) + (1 if status else 0)
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
        with pytest.raises(SystemExit) as exit_status:
            main()
        assert exit_status.value.code == 1
        err = capsys.readouterr().err
        assert "1 unsupported" in err
        assert err.rstrip().endswith("ERROR: 1 file failed validation")

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

    @pytest.mark.parametrize(("options", "jobs"), [([], None), (["--jobs", "3"], 3)])
    def test_validate_receives_jobs(
        self, monkeypatch: pytest.MonkeyPatch, options: list[str], jobs: int | None
    ) -> None:
        from unittest.mock import Mock

        run = Mock(return_value=Result(checked=1))
        monkeypatch.setattr("armarium.cli.validate", run)
        monkeypatch.setattr(sys, "argv", ["armarium", "validate", "vault", *options])
        main()
        run.assert_called_once_with(Path("vault"), None, jobs=jobs)

    @pytest.mark.parametrize("files", [1, 2])
    def test_failure_counts_distinct_files(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        files: int,
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
        with pytest.raises(SystemExit) as exit_status:
            main()
        assert exit_status.value.code == 1
        assert (
            capsys.readouterr()
            .err.rstrip()
            .endswith(f"ERROR: {files} {noun} failed validation")
        )

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
            with pytest.raises(SystemExit) as exit_status:
                main()
            assert exit_status.value.code == 1
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
        with pytest.raises(SystemExit) as exit_status:
            main()
        assert exit_status.value.code == 1
        err = capsys.readouterr().err
        assert "3 checked" in err
        assert ".:: - vault.required - required directory assets is missing" in err

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
            assert "Traceback" not in process.stderr
            assert process.stderr.rstrip().endswith("ERROR: 1 file failed validation")
        assert process.stdout == ""


class TestParseArgs:
    @pytest.mark.parametrize(
        "selection", ["inferred", "explicit_before", "explicit_after", "equals"]
    )
    def test_clue_help(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        selection: str,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "selected vault")
        template = root / "reference/templates/Clue.md"
        template.write_text(
            template.read_text().replace('text: ""', 'text: "100% local fact."')
        )
        monkeypatch.chdir(
            root / "campaigns/campaign_1/clues" if selection == "inferred" else tmp_path
        )
        options = {
            "inferred": ["--help"],
            "explicit_before": ["--vault", str(root), "--help"],
            "explicit_after": ["-h", "--vault", str(root)],
            "equals": [f"--vault={root}", "--help"],
        }
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        with pytest.raises(SystemExit) as exc:
            parse_args(["add", "clue", *options[selection]])
        assert exc.value.code == 0
        output = capsys.readouterr()
        assert "--frontmatter" in output.out
        assert output.err == ""
        assert all(p.read_bytes() == content for p, content in before.items())

    @pytest.mark.parametrize("explicit", [False, True])
    def test_add_player_options(self, explicit: bool) -> None:
        args = parse_args(
            ["add", "player", "New Player"]
            + (["--vault", "/tmp/vault", "--campaign", "2"] if explicit else [])
        )
        assert args.addition == "player" and args.name == "New Player"
        assert args.campaign == (2 if explicit else None)
        assert args.vault == (Path("/tmp/vault") if explicit else None)

    @pytest.mark.parametrize("explicit", [False, True])
    def test_add_note_options(self, explicit: bool) -> None:
        args = parse_args(
            ["add", "note", "Working ideas"]
            + (["--vault", "my-vault", "--campaign", "2"] if explicit else [])
        )
        assert args.addition == "note" and args.name == "Working ideas"
        assert args.vault == (Path("my-vault") if explicit else None)
        assert args.campaign == (2 if explicit else None)

    def test_note_help_defaults(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(["add", "note", "--help"])
        assert exc.value.code == 0
        help_text = " ".join(capsys.readouterr().out.split())
        assert "(default: discovered from the current directory)" in help_text
        assert (
            "campaign number within vault (default: current campaign directory, or shared notes)"
            in help_text
        )

    @pytest.mark.parametrize("explicit", [False, True])
    def test_add_clue_options(self, explicit: bool) -> None:
        args = parse_args(
            ["add", "clue"]
            + (
                ["--vault", "my-vault", "--campaign", "2", "--number", "7"]
                if explicit
                else []
            )
        )
        assert args.addition == "clue"
        assert args.vault == (Path("my-vault") if explicit else None)
        assert args.campaign == (2 if explicit else None)
        assert args.number == (7 if explicit else None)

    def test_add_transcript_options(self) -> None:
        args = parse_args(
            [
                "add",
                "transcript",
                "S-2-001",
                "--body-file",
                "speech.md",
                "--vault",
                "my vault",
            ]
        )
        assert args.addition == "transcript"
        assert args.session == "S-2-001"
        assert args.body_file == Path("speech.md")
        assert args.vault == Path("my vault")
        assert not hasattr(args, "campaign")

    @pytest.mark.parametrize(
        "arguments",
        [
            [],
            ["S-1-001"],
            ["--body-file", "speech.md"],
            ["S-1-001", "--body-file", "speech.md", "--campaign", "1"],
            ["S-1-001", "--body-file", "speech.md", "--force"],
        ],
    )
    def test_add_transcript_usage(self, arguments: list[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(["add", "transcript", *arguments])
        assert exc.value.code == 2

    def test_add_transcript_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(["add", "transcript", "--help"])
        assert exc.value.code == 0
        output = capsys.readouterr().out
        assert "--body-file" in output and "(default:" in output
        assert "UTF-8 Markdown file containing transcript body" in output
        assert "--campaign" not in output

    @pytest.mark.parametrize("explicit", [False, True])
    def test_add_session_options(self, explicit: bool) -> None:
        args = parse_args(
            ["add", "session"]
            + (
                ["--vault", "my-vault", "--campaign", "2", "--number", "7"]
                if explicit
                else []
            )
        )
        assert args.addition == "session"
        assert args.vault == (Path("my-vault") if explicit else None)
        assert args.campaign == (2 if explicit else None)
        assert args.number == (7 if explicit else None)

    def test_add_content_options(self) -> None:
        args = parse_args(
            [
                "add",
                "content",
                "Mira",
                "--subtype",
                "PC",
                "--campaign",
                "2",
                "--vault",
                "my-vault",
                "--frontmatter",
                json.dumps({"player": "[[Alex]]"}),
            ]
        )
        assert args.addition == "content" and args.name == "Mira"
        assert args.subtype == "PC" and args.campaign == 2
        assert args.frontmatter == {"player": "[[Alex]]"}
        assert args.vault == Path("my-vault")

    @pytest.mark.parametrize("explicit", [False, True])
    def test_add_content_declared_subtype(
        self,
        relic_vault: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        explicit: bool,
    ) -> None:
        monkeypatch.chdir(tmp_path if explicit else relic_vault / "content")
        vault = ["--vault", str(relic_vault)] if explicit else []
        args = parse_args(["add", "content", "Crown", "--subtype", "Relic", *vault])
        assert args.subtype == "Relic"
        with pytest.raises(SystemExit) as exc:
            parse_args(["add", "content", "--help", *vault])
        assert exc.value.code == 0
        assert ",Gear,Relic}" in capsys.readouterr().out

    def test_add_content_undeclared_subtype(
        self, relic_vault: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (relic_vault / "reference/extensions.json").unlink()
        with pytest.raises(SystemExit) as exc:
            parse_args(
                [
                    "add",
                    "content",
                    "Crown",
                    "--subtype",
                    "Relic",
                    "--vault",
                    str(relic_vault),
                ]
            )
        assert exc.value.code == 2
        assert "invalid choice: 'Relic'" in capsys.readouterr().err

    @pytest.mark.parametrize("explicit", [False, True])
    def test_add_campaign_options(self, explicit: bool) -> None:
        args = parse_args(
            ["add", "campaign"]
            + (["--vault", "my-vault", "--number", "12"] if explicit else [])
        )
        assert args.command == "add" and args.addition == "campaign"
        assert args.number == (12 if explicit else None)
        assert args.vault == (Path("my-vault") if explicit else None)

    @pytest.mark.parametrize("force", [False, True])
    def test_init_path(self, force: bool) -> None:
        args = parse_args(["init", "A new setting"] + (["--force"] if force else []))
        assert args.command == "init"
        assert args.path == Path("A new setting")
        assert args.force is force

    @pytest.mark.parametrize("explicit", [False, True])
    def test_paths(self, explicit: bool) -> None:
        argv = ["validate", "record.md"] + (["--vault", "vault"] if explicit else [])
        args = parse_args(argv)
        assert args.command == "validate" and args.path == Path("record.md")
        assert args.vault == (Path("vault") if explicit else None)
        assert args.jobs is None

    def test_jobs(self) -> None:
        assert parse_args(["validate", ".", "--jobs", "4"]).jobs == 4

    @pytest.mark.parametrize("value", ["0", "-1", "1.5", "many"])
    def test_invalid_jobs(self, capsys: pytest.CaptureFixture[str], value: str) -> None:
        with pytest.raises(SystemExit) as exit_status:
            parse_args(["validate", ".", f"--jobs={value}"])
        assert exit_status.value.code == 2
        assert "jobs must be a whole number of at least 1" in capsys.readouterr().err

    @pytest.mark.parametrize(
        "argv",
        [
            [],
            ["unknown"],
            ["validate"],
            ["validate", "--unknown"],
            ["init"],
            ["init", "setting", "--vault", "other"],
            ["add"],
            ["add", "unknown"],
            ["add", "note"],
            ["add", "note", "Name", "--campaign", "0"],
            ["add", "note", "Name", "--campaign", "text"],
            ["add", "note", "Name", "--force"],
            ["add", "note", "Name", "--body", "text"],
            ["add", "campaign", "--number", "0"],
            ["add", "campaign", "--number", "-1"],
            ["add", "campaign", "--number", "text"],
            ["add", "campaign", "--force"],
            ["add", "content"],
            ["add", "content", "Name"],
            ["add", "content", "Name", "--subtype", "Unknown"],
            ["add", "content", "Name", "--subtype", "Lore", "--campaign", "0"],
            ["add", "content", "Name", "--subtype", "Lore", "--force"],
            ["add", "session", "--campaign", "0"],
            ["add", "session", "--number", "0"],
            ["add", "session", "--number", "1000"],
            ["add", "session", "--number", "text"],
            ["add", "session", "--force"],
            ["add", "player"],
            ["add", "player", "Name", "--campaign", "0"],
            ["add", "player", "Name", "--campaign", "text"],
            ["add", "player", "Name", "--force"],
            ["add", "clue", "--number", "0"],
            ["add", "clue", "--number", "10000"],
            ["add", "clue", "--campaign", "0"],
            ["add", "clue", "--number", "text"],
            ["add", "clue", "--force"],
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

    @pytest.mark.parametrize(
        "argv",
        [
            ["--help"],
            ["validate", "--help"],
            ["init", "--help"],
            ["add", "--help"],
            ["add", "campaign", "--help"],
            ["add", "content", "--help"],
            ["add", "session", "--help"],
            ["add", "player", "--help"],
            ["add", "note", "--help"],
            ["add", "clue", "--help"],
        ],
    )
    def test_help(self, capsys: pytest.CaptureFixture[str], argv: list[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(argv)
        assert exc.value.code == 0
        output = capsys.readouterr()
        assert "usage: armarium" in output.out
        assert output.err == ""


class TestSubtypeChoices:
    @pytest.mark.parametrize(
        "argv",
        [
            ["validate", "."],
            ["add", "note", "Name"],
            ["add", "content", "Name", "--vault"],
            ["add", "content", "Name", "--vault", "missing"],
        ],
    )
    def test_core(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        choices, origin = _subtype_choices(argv)
        assert choices == SUBTYPES
        assert origin == (
            ""
            if argv[:2] != ["add", "content"]
            else "; enabled extensions may add others"
        )

    @pytest.mark.parametrize("explicit", [False, True])
    @pytest.mark.parametrize("from_sys_argv", [False, True])
    def test_vault_extensions(
        self,
        relic_vault: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        explicit: bool,
        from_sys_argv: bool,
    ) -> None:
        monkeypatch.chdir(tmp_path if explicit else relic_vault)
        argv = ["add", "content", "Name"] + (
            [f"--vault={relic_vault}"] if explicit else []
        )
        if from_sys_argv:
            monkeypatch.setattr(sys, "argv", ["armarium", *argv])
        choices, origin = _subtype_choices(None if from_sys_argv else argv)
        assert choices == (*SUBTYPES, "Relic")
        assert origin == " (core subtypes and enabled extensions)"

    def test_unreadable_extensions(self, relic_vault: Path) -> None:
        (relic_vault / "reference/templates/Relic.md").unlink()
        choices, origin = _subtype_choices(
            ["add", "content", "Name", "--vault", str(relic_vault)]
        )
        assert choices is None
        assert origin.startswith("; cannot read the vault's extensions: ")


class TestExtensionCommand:
    @pytest.mark.parametrize("explicit", [False, True])
    def test_enable(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        explicit: bool,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "vault")
        monkeypatch.chdir(root / "content")
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "extension", "enable", "example"]
            + (["--vault", str(root)] if explicit else []),
        )
        main()
        assert (root / "reference/extensions.json").exists()
        assert "Validation completed successfully" in capsys.readouterr().err

    @pytest.mark.parametrize("scenario", ["unknown", "migration", "invalid-schema"])
    def test_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        scenario: str,
    ) -> None:
        from armarium.content import add_content
        from armarium.extensions import enable_extension
        from armarium.init import init_vault

        root = init_vault(tmp_path / "vault")
        if scenario == "migration":
            add_content("Harbor", "Location", root)
        elif scenario == "invalid-schema":
            enable_extension("example", root)
            (
                root / "reference/extensions/example/schemas/location.schema.json"
            ).write_text('{"type": "bad"}')
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "armarium",
                "extension",
                "enable",
                "absent" if scenario == "unknown" else "example",
                "--vault",
                str(root),
            ],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr().err
        assert "Validation completed successfully" not in output
        if scenario == "migration":
            assert "Extension change retained" in output
            assert (root / "reference/extensions.json").exists()


class TestInitExtensionCommand:
    @pytest.mark.parametrize("name,success", [("example", True), ("missing", False)])
    def test_init(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        name: str,
        success: bool,
    ) -> None:
        root = tmp_path / "vault"
        monkeypatch.setattr(
            sys, "argv", ["armarium", "init", str(root), "--extension", name]
        )
        if success:
            main()
            assert (root / "reference/extensions.json").exists()
        else:
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
            assert not root.exists()
        assert (
            "Validation completed successfully" in capsys.readouterr().err
        ) == success


class TestRemoveExtensionCommand:
    @pytest.mark.parametrize("scenario", ["valid", "missing", "edited"])
    def test_remove(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        scenario: str,
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(
            tmp_path / "vault", extensions=[] if scenario == "missing" else ["example"]
        )
        if scenario == "edited":
            path = root / "reference/extensions/example/README.md"
            path.write_text(path.read_text() + "Local notes.\n")
        monkeypatch.chdir(root / "content")
        monkeypatch.setattr(sys, "argv", ["armarium", "extension", "remove", "example"])
        if scenario != "missing":
            main()
            assert not (root / "reference/extensions/example/README.md").exists()
        else:
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
        assert ("Validation completed successfully" in capsys.readouterr().err) == (
            scenario != "missing"
        )


class TestRepeatedExtensionOptions:
    def test_accumulates(self) -> None:
        args = parse_args(
            ["init", "new-vault", "--extension", "example", "--extension", "extra"]
        )
        assert args.extension == ["example", "extra"]
        assert parse_args(["init", "new-vault"]).extension == []


class TestUpdateExtensionCommand:
    @pytest.mark.parametrize("requires_migration", [False, True])
    def test_update(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        requires_migration: bool,
    ) -> None:
        import json
        import shutil

        import armarium.extensions as extensions
        from armarium.content import add_content
        from armarium.init import init_vault

        root = init_vault(tmp_path / "vault", extensions=["example"])
        record = add_content("Harbor", "Location", root)
        original = record.read_bytes()
        replacement = tmp_path / "replacement"
        shutil.copytree(
            Path(__file__).resolve().parents[1] / "extensions/example", replacement
        )
        if requires_migration:
            schema = replacement / "schemas/location.schema.json"
            data = json.loads(schema.read_text())
            data["properties"]["frontmatter"]["required"].append("region")
            schema.write_text(json.dumps(data))
        monkeypatch.setattr(extensions, "_extension", lambda name: replacement)
        monkeypatch.setattr(extensions, "_armarium_version", lambda: "2.0.0")
        monkeypatch.chdir(root / "content")
        monkeypatch.setattr(sys, "argv", ["armarium", "extension", "update", "example"])
        if requires_migration:
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
        else:
            main()
        output = capsys.readouterr().err
        assert ("Validation completed successfully" in output) != requires_migration
        assert "updated; validating" in output
        assert record.read_bytes() == original
        assert (
            json.loads((root / extensions.CONFIG).read_text())["example"][
                "armarium_version"
            ]
            == "2.0.0"
        )

    def test_not_installed(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from armarium.init import init_vault

        root = init_vault(tmp_path / "vault")
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "extension", "update", "example", "--vault", str(root)],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        assert "not installed" in capsys.readouterr().err


class TestDowngradeOption:
    @pytest.mark.parametrize("allow", [False, True])
    def test_update(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        allow: bool,
    ) -> None:
        import json

        import armarium.extensions as extensions
        from armarium.init import init_vault

        root = init_vault(tmp_path / "vault", extensions=["example"])
        config = root / extensions.CONFIG
        data = json.loads(config.read_text())
        data["example"]["armarium_version"] = "2.0.0"
        config.write_text(json.dumps(data))
        monkeypatch.setattr(extensions, "_armarium_version", lambda: "1.0.0")
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "extension", "update", "example", "--vault", str(root)]
            + (["--allow-downgrade"] if allow else []),
        )
        if allow:
            main()
        else:
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
        output = capsys.readouterr().err
        assert ("Validation completed successfully" in output) == allow
        if not allow:
            assert "--allow-downgrade" in output
        assert json.loads(config.read_text())["example"]["armarium_version"] == (
            "1.0.0" if allow else "2.0.0"
        )


class TestFindCommand:
    @pytest.fixture
    def records(self, vault: Path) -> Path:
        (vault / "content/Mara.md").write_text(
            '---\ntype: "[[Widget]]"\nsummary: Harbour pilot.\n---\n'
        )
        (vault / "content/Quay Nine.md").write_text(
            '---\ntype: "[[Widget]]"\nsubtype: Location\naliases: [Mara]\n---\n'
        )
        return vault

    @pytest.mark.parametrize(
        ("arguments", "expected"),
        [
            (
                ["mara"],
                [
                    "content/Mara.md\tWidget\tname\tHarbour pilot.",
                    "content/Quay Nine.md\tWidget/Location\talias\t",
                ],
            ),
            (
                ["quay nine"],
                ["content/Quay Nine.md\tWidget/Location\tname\t"],
            ),
        ],
    )
    @pytest.mark.parametrize("explicit", [False, True])
    def test_lists_matches(
        self,
        records: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        arguments: list[str],
        expected: list[str],
        explicit: bool,
    ) -> None:
        monkeypatch.chdir(records.parent if explicit else records / "content")
        vault_option = ["--vault", str(records)] if explicit else []
        monkeypatch.setattr(
            sys, "argv", ["armarium", "find", *arguments, *vault_option]
        )
        before = {p: p.read_bytes() for p in records.rglob("*") if p.is_file()}
        main()
        output = capsys.readouterr()
        assert output.out.splitlines() == expected
        assert output.err == ""
        assert all(p.read_bytes() == content for p, content in before.items())

    @pytest.mark.parametrize(
        ("arguments", "inside", "message"),
        [
            (["gull"], True, "INFO: No records match gull"),
            (["quay"], True, "INFO: No records match quay"),
            ([" "], True, "ERROR: Cannot find  : name must not be blank"),
            (["mara"], False, "ERROR: Cannot find mara: "),
            (
                ["mara", "--campaign", "7"],
                True,
                "ERROR: Cannot find mara: campaign 7 does not exist",
            ),
        ],
    )
    def test_exits_with_one(
        self,
        records: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        arguments: list[str],
        inside: bool,
        message: str,
    ) -> None:
        monkeypatch.chdir(records if inside else records.parent)
        monkeypatch.setattr(sys, "argv", ["armarium", "find", *arguments])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert message in output.err

    @pytest.mark.parametrize(
        "arguments",
        [
            [],
            ["mara", "vey"],
            ["mara", "--type", "Content"],
            ["mara", "--subtype", "NPC"],
            ["mara", "--campaign"],
            ["mara", "--campaign", "one"],
        ],
    )
    def test_usage_errors(
        self, arguments: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(["find", *arguments])
        assert exc.value.code == 2
        assert "usage: armarium" in capsys.readouterr().err

    def test_options(self, tmp_path: Path) -> None:
        args = parse_args(["find", "Mara Vey"])
        assert (args.name, args.vault, args.campaign) == ("Mara Vey", None, None)
        args = parse_args(["find", "Mara", "--vault", str(tmp_path), "--campaign", "2"])
        assert (args.vault, args.campaign) == (tmp_path, 2)

    def test_campaign_limits_the_listing(
        self,
        records: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        for number in (1, 2):
            directory = records / f"campaigns/campaign_{number}/content"
            directory.mkdir(parents=True)
            (directory / "Mara.md").write_text("---\nsummary: Local.\n---\n")
        monkeypatch.chdir(records)
        monkeypatch.setattr(
            sys, "argv", ["armarium", "find", "mara", "--campaign", "2"]
        )
        main()
        assert capsys.readouterr().out.splitlines() == [
            "campaigns/campaign_2/content/Mara.md\t\tname\tLocal.",
            "content/Mara.md\tWidget\tname\tHarbour pilot.",
            "content/Quay Nine.md\tWidget/Location\talias\t",
        ]


class TestTraceCommand:
    LINES = [
        "content/Quay Nine.md\tkeeper\t",
        "content/Quay Nine.md\tNotes > Events\t6",
    ]

    @pytest.mark.parametrize("explicit", [False, True])
    def test_outbound_lists_the_files_linked_to(
        self,
        records: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        explicit: bool,
    ) -> None:
        (records / "content/Quay Nine.md").write_text(
            '---\nkeeper: "[[Mara]]"\n---\n# Notes\n[[Mara]] and [[Gull]].\n'
        )
        monkeypatch.chdir(records.parent if explicit else records / "content")
        path = "content/Quay Nine.md" if explicit else "Quay Nine.md"
        vault_option = ["--vault", str(records)] if explicit else []
        monkeypatch.setattr(
            sys, "argv", ["armarium", "trace", path, "--outbound", *vault_option]
        )
        before = {p: p.read_bytes() for p in records.rglob("*") if p.is_file()}
        main()
        output = capsys.readouterr()
        assert output.out.splitlines() == [
            "content/Mara.md\tkeeper\t",
            "content/Mara.md\tNotes\t5",
        ]
        assert (
            "WARNING: content/Quay Nine.md: line 5: [[Gull]] names no file"
            in output.err
        )
        assert "INFO: 2 links from content/Quay Nine.md" in output.err
        assert all(p.read_bytes() == content for p, content in before.items())

    def test_outbound_rejects_what_is_not_a_record(
        self,
        records: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        (records / "assets").mkdir()
        (records / "assets/Map.png").write_text("image")
        monkeypatch.chdir(records)
        monkeypatch.setattr(
            sys, "argv", ["armarium", "trace", "assets/Map.png", "--outbound"]
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert "is not a Markdown record" in output.err

    def test_outbound_option(self) -> None:
        assert parse_args(["trace", "a.md"]).outbound is False
        assert parse_args(["trace", "a.md", "--outbound"]).outbound is True

    @pytest.fixture
    def records(self, vault: Path) -> Path:
        (vault / "content/Mara.md").write_text("---\naliases: [The Pilot]\n---\n")
        (vault / "content/Quay Nine.md").write_text(
            '---\nkeeper: "[[Mara]]"\n---\n# Notes\n## Events\n[[Mara]] waits.\n'
        )
        return vault

    @pytest.mark.parametrize(
        ("directory", "path", "explicit", "lines", "message"),
        [
            ("..", "content/Mara.md", True, LINES, "2 links to content/Mara.md"),
            ("content", "content/Mara.md", True, LINES, "2 links to content/Mara.md"),
            ("content", "Mara.md", False, LINES, "2 links to content/Mara.md"),
            ("", "content/Mara.md", False, LINES, "2 links to content/Mara.md"),
            (
                "..",
                "{vault}/content/Mara.md",
                False,
                LINES,
                "2 links to content/Mara.md",
            ),
            (
                "..",
                "{vault}/content/Mara.md",
                True,
                LINES,
                "2 links to content/Mara.md",
            ),
            ("", "content/Quay Nine.md", False, [], "0 links to content/Quay Nine.md"),
            (
                "..",
                "reference/types/Widget.md",
                True,
                [],
                "0 links to reference/types/Widget.md",
            ),
        ],
    )
    def test_lists_links(
        self,
        records: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        directory: str,
        path: str,
        explicit: bool,
        lines: list[str],
        message: str,
    ) -> None:
        monkeypatch.chdir(records / directory)
        arguments = [path.format(vault=records)]
        arguments += ["--vault", str(records)] if explicit else []
        monkeypatch.setattr(sys, "argv", ["armarium", "trace", *arguments])
        before = {p: p.read_bytes() for p in records.rglob("*") if p.is_file()}
        main()
        output = capsys.readouterr()
        assert output.out.splitlines() == lines
        assert output.err.strip().endswith(f"INFO: {message}")
        assert len(output.err.splitlines()) == 1
        assert all(p.read_bytes() == content for p, content in before.items())

    def test_counts_one_link(
        self,
        records: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        (records / "content/Quay Nine.md").write_text("[[Mara]]\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "trace", "content/Mara.md", "--vault", str(records)],
        )
        main()
        assert (
            capsys.readouterr().err.strip().endswith("INFO: 1 link to content/Mara.md")
        )

    @pytest.mark.parametrize(
        ("path", "explicit", "message"),
        [
            ("content/Gull.md", True, "content/Gull.md does not exist"),
            ("content/Gull.md", False, "content/Gull.md does not exist"),
            ("Mara", False, "Mara does not exist"),
            ("content", True, "content is a directory, not a file"),
            ("content/.Hidden.md", True, "is not part of the vault: hidden entries"),
            ("content/Linked.md", False, "content/Linked.md is a symlink"),
            ("../Loose.md", False, "cannot infer vault; supply --vault PATH"),
            ("../Loose.md", True, "target must be inside the selected vault directory"),
        ],
    )
    def test_exits_with_one(
        self,
        records: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        path: str,
        explicit: bool,
        message: str,
    ) -> None:
        (records / "content/.Hidden.md").write_text("")
        (records / "content/Linked.md").symlink_to(records / "content/Mara.md")
        (records.parent / "Loose.md").write_text("")
        monkeypatch.chdir(records)
        arguments = [path, *(["--vault", str(records)] if explicit else [])]
        monkeypatch.setattr(sys, "argv", ["armarium", "trace", *arguments])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert len(output.err.splitlines()) == 1
        assert f"ERROR: Cannot trace {path}: " in output.err and message in output.err

    @pytest.mark.parametrize(
        "arguments",
        [
            [],
            ["content/Mara.md", "content/Quay Nine.md"],
            ["content/Mara.md", "--jobs", "2"],
        ],
    )
    def test_usage_errors(
        self, arguments: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(["trace", *arguments])
        assert exc.value.code == 2
        assert "usage: armarium" in capsys.readouterr().err

    def test_options(self, tmp_path: Path) -> None:
        args = parse_args(["trace", "content/Mara Vey.md"])
        assert (args.path, args.vault) == (Path("content/Mara Vey.md"), None)
        args = parse_args(["trace", "content/Mara.md", "--vault", str(tmp_path)])
        assert args.vault == tmp_path


class TestTranscribeCommand:
    LOOP = "lines 2-6: line x5: 'Agreed.'"

    @pytest.mark.parametrize(
        ("loops", "summary"),
        [
            ((), "0 loops collapsed; 3 of 3 lines kept"),
            ((LOOP,), "1 loop collapsed; 3 of 3 lines kept"),
            ((LOOP, LOOP), "2 loops collapsed; 3 of 3 lines kept"),
        ],
    )
    @pytest.mark.parametrize("raw", [None, Path("s52.raw.txt")])
    def test_prints_the_output_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        loops: tuple[str, ...],
        summary: str,
        raw: Path | None,
    ) -> None:
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def transcribe(*args: object, **options: object) -> Transcription:
            calls.append((args, options))
            return Transcription(Path("out/s52.txt"), raw, 3, 3, loops)

        monkeypatch.setattr(cli, "transcribe", transcribe)
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "transcribe", "s52.wav", "-o", "out/s52.txt", "--", "-t", "8"],
        )
        main()
        output = capsys.readouterr()
        assert output.out == "out/s52.txt\n"
        messages = [line.split("] ", 1)[1] for line in output.err.splitlines()]
        assert messages == [
            *(["INFO: Raw transcript written to s52.raw.txt"] if raw else []),
            *(f"INFO: Collapsed {loop}" for loop in loops),
            f"INFO: {summary}",
        ]
        assert calls == [
            (
                (Path("s52.wav"), Path("out/s52.txt")),
                {
                    "model": DEFAULT_MODEL,
                    "vad_model": DEFAULT_VAD_MODEL,
                    "model_dir": DEFAULT_MODEL_DIR,
                    "language": DEFAULT_LANGUAGE,
                    "min_repeats": DEFAULT_MIN_REPEATS,
                    "extra_args": ["-t", "8"],
                    "loose": False,
                },
            )
        ]

    def test_collapses_a_text_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        source = tmp_path / "raw.txt"
        source.write_text("before\n" + "Agreed.\n" * 5 + "after\n")
        monkeypatch.setattr(sys, "argv", ["armarium", "transcribe", str(source)])
        main()
        output = capsys.readouterr()
        assert output.out == f"{tmp_path / 'raw.collapsed.txt'}\n"
        assert (tmp_path / "raw.collapsed.txt").read_text() == (
            "before\nAgreed.\n"
            "[ASR loop: previous line repeated 5 times; raw lines 2-6]\nafter\n"
        )
        assert f"INFO: Collapsed {self.LOOP}" in output.err
        assert "INFO: 1 loop collapsed; 4 of 7 lines kept" in output.err

    @pytest.mark.parametrize(
        ("name", "message"),
        [
            ("absent.wav", "absent.wav is not a file"),
            ("notes.md", "unsupported input notes.md"),
            ("raw.txt", "raw.collapsed.txt already exists"),
            ("s52.wav", "whisper-cli is not on PATH; install whisper.cpp"),
        ],
    )
    def test_exits_with_one(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        name: str,
        message: str,
    ) -> None:
        for existing in ("notes.md", "raw.txt", "raw.collapsed.txt", "s52.wav"):
            (tmp_path / existing).write_text("kept")
        monkeypatch.setenv("PATH", str(tmp_path))
        path = str(tmp_path / name)
        monkeypatch.setattr(sys, "argv", ["armarium", "transcribe", path])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert len(output.err.splitlines()) == 1
        assert f"ERROR: Cannot transcribe {path}: " in output.err
        assert message in output.err
        assert (tmp_path / "raw.collapsed.txt").read_text() == "kept"
        assert len(list(tmp_path.iterdir())) == 4

    def test_options(self, tmp_path: Path) -> None:
        args = parse_args(
            [
                "transcribe",
                "s52.wav",
                "--model",
                "ggml-base.en.bin",
                "--vad-model",
                "vad.bin",
                "--model-dir",
                str(tmp_path),
                "--language",
                "de",
                "--min-repeats",
                "6",
                "--loose",
            ]
        )
        assert (args.source, args.output) == (Path("s52.wav"), None)
        assert (args.model, args.vad_model) == ("ggml-base.en.bin", "vad.bin")
        assert (args.model_dir, args.language) == (tmp_path, "de")
        assert (args.min_repeats, args.whisper_args) == (6, [])
        assert args.loose
        assert not parse_args(["transcribe", "s52.wav"]).loose

    @pytest.mark.parametrize(
        ("arguments", "source", "whisper_args"),
        [
            (["s.wav", "--"], "s.wav", []),
            (["s.wav", "--", "--threads", "8"], "s.wav", ["--threads", "8"]),
            (["--language", "de", "s.wav", "--", "-o", "--"], "s.wav", ["-o", "--"]),
        ],
    )
    def test_passes_arguments_after_the_separator_to_the_backend(
        self, arguments: list[str], source: str, whisper_args: list[str]
    ) -> None:
        args = parse_args(["transcribe", *arguments])
        assert (args.source, args.output) == (Path(source), None)
        assert args.whisper_args == whisper_args

    def test_other_commands_keep_the_separator(self) -> None:
        args = parse_args(["find", "--", "--name"])
        assert args.name == "--name" and not hasattr(args, "whisper_args")

    @pytest.mark.parametrize(
        "arguments",
        [
            [],
            ["a.wav", "b.wav"],
            ["a.wav", "--threads", "8"],
            ["a.wav", "--min-repeats", "1"],
            ["--", "a.wav"],
        ],
    )
    def test_usage_errors(
        self, arguments: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(["transcribe", *arguments])
        assert exc.value.code == 2
        assert "usage: armarium" in capsys.readouterr().err


class TestIllustrateCommand:
    RECORD = "campaigns/campaign_1/content/Harness.md"

    @pytest.fixture
    def starter(self, tmp_path: Path) -> Path:
        from armarium.content import add_content

        root = tmp_path / "vault"
        shutil.copytree(Path(__file__).resolve().parents[1] / "vaults/starter", root)
        add_content("Harness", "Gear", root, campaign=1)
        return root

    @pytest.fixture
    def source(self, tmp_path: Path) -> Path:
        from PIL import Image

        Image.new("RGB", (30, 20), "red").save(tmp_path / "harness.png")
        return tmp_path / "harness.png"

    def test_prints_the_image_path(
        self,
        starter: Path,
        source: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        image = "assets/art/gear/Harness.webp"
        argv = ["armarium", "illustrate", "ingest", self.RECORD, str(source)]
        monkeypatch.setattr(sys, "argv", [*argv, "--vault", str(starter)])
        main()
        output = capsys.readouterr()
        assert output.out == f"{image}\n"
        messages = [line.split("] ", 1)[1] for line in output.err.splitlines()]
        size = (starter / image).stat().st_size
        assert messages == [
            "INFO: Used style Gear",
            f"INFO: Wrote {image}: 30 px on its long edge, {size} bytes",
            f"INFO: Set image in {self.RECORD}; validating",
            "INFO: Validation completed successfully",
        ]
        assert f"image: {image}\n" in (starter / self.RECORD).read_text()

    def test_reports_the_image_it_replaces(
        self,
        starter: Path,
        source: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = starter / self.RECORD
        path.write_text(path.read_text().replace("source:", "image: old.png\nsource:"))
        argv = ["armarium", "illustrate", "ingest", self.RECORD, str(source)]
        monkeypatch.setattr(sys, "argv", [*argv, "--vault", str(starter)])
        main()
        assert "INFO: The record's image was old.png, left in place" in (
            capsys.readouterr().err
        )

    def test_exits_with_one_when_it_cannot_ingest(
        self,
        starter: Path,
        source: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        argv = ["armarium", "illustrate", "ingest", self.RECORD, str(source)]
        monkeypatch.setattr(
            sys, "argv", [*argv, "--vault", str(starter), "-o", "a.webp"]
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert output.err.splitlines()[0].endswith(
            f"ERROR: Cannot illustrate {self.RECORD}: a.webp is not a .webp path "
            "inside the vault's assets/"
        )

    def test_exits_with_one_when_the_record_fails_validation(
        self,
        starter: Path,
        source: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = starter / self.RECORD
        path.write_text(path.read_text().replace("source: null", "source: 3"))
        argv = ["armarium", "illustrate", "ingest", self.RECORD, str(source)]
        monkeypatch.setattr(sys, "argv", [*argv, "--vault", str(starter)])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "ERROR: 1 file failed validation" in err
        assert "ERROR: Image and record change retained for inspection" in err
        assert (starter / "assets/art/gear/Harness.webp").is_file()

    def test_options(self) -> None:
        args = parse_args(
            [
                "illustrate",
                "ingest",
                "a.md",
                "a.png",
                "-o",
                "assets/a.webp",
                "--max-bytes",
                "5000",
                "--max-edge",
                "600",
                "--no-opacity",
                "--overwrite",
                "--style",
                "Ink",
            ]
        )
        assert (args.stage, args.record, args.picture) == (
            "ingest",
            Path("a.md"),
            Path("a.png"),
        )
        assert (args.output, args.max_bytes, args.max_edge) == (
            "assets/a.webp",
            5000,
            600,
        )
        assert (args.opacity, args.overwrite, args.vault) == (False, True, None)
        assert (args.style, args.directory) == ("Ink", None)

    def test_directory(self) -> None:
        args = parse_args(
            ["illustrate", "ingest", "a.md", "a.png", "--directory", "assets/ink"]
        )
        assert (args.directory, args.output) == ("assets/ink", None)

    def test_directory_and_output_exclude_each_other(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        argv = ["illustrate", "ingest", "a.md", "a.png", "--directory", "assets/x"]
        with pytest.raises(SystemExit):
            parse_args([*argv, "-o", "assets/a.webp"])
        assert "not allowed with argument" in capsys.readouterr().err

    def test_defaults(self) -> None:
        args = parse_args(["illustrate", "ingest", "a.md", "a.png"])
        assert (args.style, args.directory, args.output) == (None, None, None)
        assert (args.max_bytes, args.max_edge) == (None, None)
        assert (args.opacity, args.overwrite) == (None, False)

    def test_passes_the_options_to_ingest(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        calls: list[dict[str, object]] = []

        def ingest(*args: object, **options: object) -> object:
            calls.append(options)
            raise ValueError("stop")

        monkeypatch.setattr(cli, "ingest", ingest)
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "illustrate", "ingest", "a.md", "a.png", "--opacity"],
        )
        with pytest.raises(SystemExit):
            main()
        assert calls == [
            {
                "style": None,
                "directory": None,
                "output": None,
                "max_bytes": None,
                "max_edge": None,
                "opacity": True,
                "overwrite": False,
            }
        ]

    @pytest.mark.parametrize(
        "arguments",
        [
            [],
            ["ingest"],
            ["ingest", "a.md"],
            ["ingest", "a.md", "a.png", "--max-edge", "0"],
        ],
    )
    def test_usage_errors(
        self, arguments: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(["illustrate", *arguments])
        assert exc.value.code == 2
        assert "usage: armarium" in capsys.readouterr().err


class TestIllustratePromptCommand:
    def test_prints_the_prompt(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        calls: list[tuple[object, ...]] = []

        def prompt(*args: object, **options: object) -> str:
            calls.append((*args, options))
            return "Paint it.\n\n<subject>Harness</subject>"

        monkeypatch.setattr(cli, "prompt", prompt)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "armarium",
                "illustrate",
                "prompt",
                "a.md",
                "--style",
                "Ink",
                "--vault",
                "v",
                "--visual",
                "Laid flat.",
            ],
        )
        main()
        output = capsys.readouterr()
        assert output.out == "Paint it.\n\n<subject>Harness</subject>\n"
        assert output.err == ""
        assert calls == [
            (
                Path("a.md"),
                Path("v"),
                {"style": "Ink", "preamble": None, "visual": "Laid flat."},
            )
        ]

    def test_exits_with_one_when_it_cannot_build_the_prompt(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        missing = str(tmp_path / "missing.md")
        monkeypatch.setattr(sys, "argv", ["armarium", "illustrate", "prompt", missing])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert f"ERROR: Cannot illustrate {missing}: " in output.err

    def test_defaults(self) -> None:
        args = parse_args(["illustrate", "prompt", "a.md"])
        assert (args.stage, args.record, args.style, args.vault) == (
            "prompt",
            Path("a.md"),
            None,
            None,
        )
        assert (args.preamble, args.visual) == (None, None)

    def test_preamble(self) -> None:
        args = parse_args(["illustrate", "prompt", "a.md", "--preamble", "p.txt"])
        assert (args.preamble, args.style) == (Path("p.txt"), None)

    @pytest.mark.parametrize(
        "arguments",
        [
            [],
            ["a.md", "b.md"],
            ["a.md", "--opacity"],
            ["a.md", "--style", "Ink", "--preamble", "p.txt"],
        ],
    )
    def test_usage_errors(
        self, arguments: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(["illustrate", "prompt", *arguments])
        assert exc.value.code == 2
        assert "usage: armarium" in capsys.readouterr().err


class TestIllustrateGenerateCommand:
    GENERATION = Generation(
        Path("/v/content/Harness.md"),
        "gpt-image-2.5-flare",
        "Gear",
        (
            Candidate(Path("/v/.scratch/illustrate/Harness-1.png"), ("a.png",)),
            Candidate(Path("/v/.scratch/illustrate/Harness-2.png"), ()),
        ),
        ("[[Hook]] has no image file in the vault",),
    )

    @pytest.fixture
    def calls(self, monkeypatch: pytest.MonkeyPatch) -> list[tuple[object, ...]]:
        recorded: list[tuple[object, ...]] = []

        def generate(*args: object, **options: object) -> Generation:
            recorded.append((*args, options))
            return self.GENERATION

        monkeypatch.setattr(cli, "generate", generate)
        return recorded

    def test_paints_from_a_prompt_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        calls: list[tuple[object, ...]],
    ) -> None:
        text = tmp_path / "prompt.txt"
        text.write_text("\ufeffPaint it.\n", encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "armarium",
                "illustrate",
                "generate",
                "a.md",
                "--prompt",
                str(text),
                "--style",
                "Gear",
                "--reference",
                "x.png",
                "--reference",
                "y.png",
                "--sample",
                "1",
                "--count",
                "3",
                "--model",
                "gpt-image-2.5-flare",
                "--overwrite",
                "--vault",
                "v",
            ],
        )
        main()
        assert calls == [
            (
                Path("a.md"),
                "Paint it.\n",
                Path("v"),
                {
                    "style": "Gear",
                    "references": [Path("x.png"), Path("y.png")],
                    "sample": 1,
                    "count": 3,
                    "model": "gpt-image-2.5-flare",
                    "overwrite": True,
                },
            )
        ]
        output = capsys.readouterr()
        assert output.out == (
            "/v/.scratch/illustrate/Harness-1.png\n/v/.scratch/illustrate/Harness-2.png\n"
        )
        for line in (
            "INFO: Used style Gear",
            "WARNING: Left out reference [[Hook]] has no image file in the vault",
            "INFO: Painted with gpt-image-2.5-flare",
            "INFO: Harness-1.png: painted from a.png",
        ):
            assert line in output.err
        assert "Harness-2.png: painted" not in output.err

    def test_reads_the_prompt_from_standard_input(
        self,
        monkeypatch: pytest.MonkeyPatch,
        calls: list[tuple[object, ...]],
    ) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO("Paint it."))
        monkeypatch.setattr(
            sys, "argv", ["armarium", "illustrate", "generate", "a.md", "--prompt", "-"]
        )
        main()
        assert calls == [
            (
                Path("a.md"),
                "Paint it.",
                None,
                {
                    "style": None,
                    "references": None,
                    "sample": None,
                    "count": 3,
                    "model": None,
                    "overwrite": False,
                },
            )
        ]

    @pytest.mark.parametrize("missing", [True, False])
    def test_exits_with_one_when_it_cannot_paint(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        missing: bool,
    ) -> None:
        text = tmp_path / "prompt.txt"
        if not missing:
            text.write_text("Paint it.")

            def generate(*args: object, **options: object) -> Generation:
                raise ValueError("OPENAI_API_KEY is not set")

            monkeypatch.setattr(cli, "generate", generate)
        monkeypatch.setattr(
            sys,
            "argv",
            ["armarium", "illustrate", "generate", "a.md", "--prompt", str(text)],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert "ERROR: Cannot illustrate a.md: " in output.err
        if not missing:
            assert "OPENAI_API_KEY is not set" in output.err

    @pytest.mark.parametrize(
        "arguments",
        [
            ["a.md"],
            ["a.md", "--prompt", "p", "--count", "0"],
            ["a.md", "--prompt", "p", "--sample", "-1"],
            ["a.md", "--prompt", "p", "--preamble", "x"],
        ],
    )
    def test_usage_errors(
        self, arguments: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(["illustrate", "generate", *arguments])
        assert exc.value.code == 2
        assert "usage: armarium" in capsys.readouterr().err


class TestHandoutCommand:
    def test_prints_the_pdf_and_logs_each_page(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        calls: list[tuple[object, ...]] = []

        def handout(*args: object, **options: object) -> Handout:
            calls.append((*args, options))
            return Handout(
                Path("v"),
                Path("loot.pdf"),
                (
                    Page("content/Ring.md", "Gear", 22.5, 4.1),
                    Page("content/Rope.md", "", 12, None, ("its text overflows",)),
                ),
            )

        monkeypatch.setattr(cli, "handout", handout)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "armarium",
                "handout",
                "content/Ring.md",
                "content/Rope.md",
                "-o",
                "loot.pdf",
                "--layout",
                "Gear",
                "--overwrite",
                "--vault",
                "v",
                "--no-title",
                "--max-text-size",
                "18",
            ],
        )
        main()
        output = capsys.readouterr()
        assert output.out == "loot.pdf\n"
        assert (
            "INFO: content/Ring.md: layout Gear, text 22.5pt, picture 4.1in"
            in output.err
        )
        assert (
            "INFO: content/Rope.md: layout defaults, text 12pt, no picture"
            in output.err
        )
        assert "WARNING: content/Rope.md: its text overflows" in output.err
        assert calls == [
            (
                [Path("content/Ring.md"), Path("content/Rope.md")],
                Path("loot.pdf"),
                Path("v"),
                {
                    "layout": "Gear",
                    "overrides": {"title": False, "max_text_size": 18.0},
                    "overwrite": True,
                },
            )
        ]

    def test_exits_with_one_when_it_cannot_print(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        missing = str(tmp_path / "missing.md")
        monkeypatch.setattr(
            sys, "argv", ["armarium", "handout", missing, "-o", "loot.pdf"]
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert "ERROR: Cannot print the handout: " in output.err

    def test_defaults(self) -> None:
        args = parse_args(["handout", "a.md", "-o", "out.pdf"])
        assert (args.records, args.output, args.layout) == (
            [Path("a.md")],
            Path("out.pdf"),
            None,
        )
        assert (args.overwrite, args.vault) == (False, None)

    def test_sets_no_layout_field_unless_asked(self) -> None:
        args = parse_args(["handout", "a.md", "-o", "out.pdf"])
        assert not [name for name in vars(args) if name.startswith("override_")]

    @pytest.mark.parametrize(
        ("arguments", "expected"),
        [
            (["--callout", "handout"], {"callout": "handout"}),
            (["--title"], {"title": True}),
            (["--no-title"], {"title": False}),
            (["--page", "a4", "--margin", "18mm"], {"page": "a4", "margin": "18mm"}),
            (["--font", "Helvetica"], {"font": "Helvetica"}),
            (
                ["--title-size", "40", "--min-text-size", "10"],
                {"title_size": 40.0, "min_text_size": 10.0},
            ),
            (
                ["--max-text-size", "20.5", "--line-spacing", "1.5"],
                {"max_text_size": 20.5, "line_spacing": 1.5},
            ),
            (["--image-share", "0.3"], {"image_share": 0.3}),
            (
                ["--mark", "attunement=A"],
                {"mark": {"field": "attunement", "text": "A"}},
            ),
            (["--mark", "magic=A=B"], {"mark": {"field": "magic", "text": "A=B"}}),
            (["--no-mark"], {"mark": None}),
            (
                ["--underline-links", "--no-lowercase-links"],
                {"underline_links": True, "lowercase_links": False},
            ),
        ],
    )
    def test_sets_layout_fields(
        self, arguments: list[str], expected: dict[str, object]
    ) -> None:
        args = parse_args(["handout", "a.md", "-o", "out.pdf", *arguments])
        assert {
            name.removeprefix("override_"): value
            for name, value in vars(args).items()
            if name.startswith("override_")
        } == expected

    @pytest.mark.parametrize(
        "arguments",
        [
            [],
            ["a.md"],
            ["-o", "out.pdf"],
            ["a.md", "-o", "out.pdf", "--mark", "attunement"],
            ["a.md", "-o", "out.pdf", "--max-text-size", "big"],
        ],
    )
    def test_usage_errors(
        self, arguments: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(["handout", *arguments])
        assert exc.value.code == 2
        assert "usage: armarium" in capsys.readouterr().err


class TestMark:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("attunement=A", {"field": "attunement", "text": "A"}),
            ("magic=A=B", {"field": "magic", "text": "A=B"}),
            ("=", {"field": "", "text": ""}),
        ],
    )
    def test_splits_at_the_first_equals(
        self, value: str, expected: dict[str, str]
    ) -> None:
        assert _mark(value) == expected

    def test_refuses_a_value_without_an_equals(self) -> None:
        with pytest.raises(argparse.ArgumentTypeError, match="is not FIELD=TEXT"):
            _mark("attunement")


class TestPositive:
    @pytest.mark.parametrize(("value", "expected"), [("1", 1), ("98000", 98000)])
    def test_size(self, value: str, expected: int) -> None:
        assert _positive(value) == expected

    @pytest.mark.parametrize("value", ["0", "-3", "2.0", "", "all"])
    def test_invalid_size(self, value: str) -> None:
        with pytest.raises(argparse.ArgumentTypeError, match="at least 1"):
            _positive(value)


class TestMinRepeats:
    @pytest.mark.parametrize(("value", "expected"), [("2", 2), ("12", 12)])
    def test_count(self, value: str, expected: int) -> None:
        assert _min_repeats(value) == expected

    @pytest.mark.parametrize("value", ["1", "0", "-3", "2.0", "", "all"])
    def test_invalid_count(self, value: str) -> None:
        with pytest.raises(argparse.ArgumentTypeError, match="at least 2"):
            _min_repeats(value)


class TestJobs:
    @pytest.mark.parametrize(("value", "expected"), [("1", 1), ("12", 12)])
    def test_count(self, value: str, expected: int) -> None:
        assert _jobs(value) == expected

    @pytest.mark.parametrize("value", ["0", "-3", "2.0", "", "all"])
    def test_invalid_count(self, value: str) -> None:
        with pytest.raises(argparse.ArgumentTypeError, match="at least 1"):
            _jobs(value)


class TestFrontmatterJson:
    @pytest.mark.parametrize(
        "raw",
        [
            "[]",
            "null",
            '"text"',
            "42",
            "{",
            '{"a":1,"a":2}',
            '{"nested":{"a":1,"a":2}}',
            '{"x":NaN}',
            '{"x":Infinity}',
            '{"x":1e999}',
        ],
    )
    def test_invalid(self, raw: str) -> None:
        import argparse

        from armarium.cli import _frontmatter_json

        with pytest.raises(argparse.ArgumentTypeError):
            _frontmatter_json(raw)

    def test_values(self) -> None:
        from armarium.cli import _frontmatter_json

        value = {
            "link": "[[Alex]]",
            "true": True,
            "false": False,
            "empty": None,
            "number": 3,
            "list": [1, "two"],
            "nested": {"field": "café"},
        }
        assert _frontmatter_json(json.dumps(value)) == value


class TestFrontmatterInput:
    @pytest.mark.parametrize("file", [False, True])
    @pytest.mark.parametrize(
        "kind", ["content", "player", "note", "session", "clue", "transcript"]
    )
    def test_record_creation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file: bool, kind: str
    ) -> None:
        from armarium.init import init_vault
        from armarium.parse import Record
        from armarium.session import add_session

        root = init_vault(tmp_path / "vault")
        monkeypatch.chdir(root / "campaigns/campaign_1")
        fields = {"custom": {"enabled": True, "tags": ["one", "two"], "empty": None}}
        args = ["armarium", "add", kind]
        if kind in {"content", "player", "note"}:
            args += ["New record"]
        if kind == "content":
            args += ["--subtype", "Lore"]
        if kind == "clue":
            fields["text"] = "A fact."
        if kind == "transcript":
            add_session(root, campaign=1)
            body = tmp_path / "speech.md"
            body.write_text("## Arrival\n\n- [GM] Welcome.\n")
            args += ["S-1-001", "--body-file", str(body)]
        if file:
            source = Path("../../../fields.json")
            source.write_text(json.dumps(fields), encoding="utf-8")
            args += ["--frontmatter-file", str(source)]
        else:
            args += ["--frontmatter", json.dumps(fields)]
        before = set(root.rglob("*.md"))
        monkeypatch.setattr(sys, "argv", args)
        main()
        [created] = set(root.rglob("*.md")) - before
        record, _ = Record.parse(created, root)
        assert record is not None
        assert record.frontmatter["custom"] == fields["custom"]

    @pytest.mark.parametrize(
        "scenario", ["missing", "directory", "encoding", "syntax", "both"]
    )
    def test_invalid_file(self, tmp_path: Path, scenario: str) -> None:
        path = tmp_path / "fields.json"
        if scenario == "directory":
            path.mkdir()
        elif scenario == "encoding":
            path.write_bytes(b"\xff")
        elif scenario in {"syntax", "both"}:
            path.write_text("{")
        args = ["add", "note", "Idea", "--frontmatter-file", str(path)]
        if scenario == "both":
            args += ["--frontmatter", "{}"]
        with pytest.raises(SystemExit) as exc:
            parse_args(args)
        assert exc.value.code == 2

    @pytest.mark.parametrize("option", ["--player", "--reckoning", "--scale", "--text"])
    def test_removed_options(self, option: str) -> None:
        args = (
            ["add", "clue"]
            if option == "--text"
            else ["add", "content", "Name", "--subtype", "PC"]
        )
        with pytest.raises(SystemExit) as exc:
            parse_args([*args, option, "value"])
        assert exc.value.code == 2

    @pytest.mark.parametrize(
        "kind,fields",
        [
            ("note", {"type": "[[Content]]"}),
            ("player", {"type": None}),
            ("content", {"subtype": "NPC"}),
            ("session", {"session_number": 9}),
            ("session", {"campaign": "[[Another Campaign]]"}),
            ("clue", {"text": "A fact.", "subjects": ["[[Wrong]]"]}),
            ("transcript", {"session": "[[S-1-002]]"}),
        ],
    )
    def test_conflicting_identity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, fields: dict
    ) -> None:
        from armarium.init import init_vault
        from armarium.session import add_session

        root = init_vault(tmp_path / "vault")
        monkeypatch.chdir(root / "campaigns/campaign_1")
        args = ["armarium", "add", kind]
        if kind in {"content", "note", "player"}:
            args += ["Name"]
        if kind == "content":
            args += ["--subtype", "Lore"]
        if kind == "transcript":
            add_session(root, campaign=1)
            body = tmp_path / "speech.md"
            body.write_text("## Arrival\n\n- [GM] Welcome.\n")
            args += ["S-1-001", "--body-file", str(body)]
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        monkeypatch.setattr(sys, "argv", [*args, "--frontmatter", json.dumps(fields)])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before

    @pytest.mark.parametrize("value,valid", [("Temperate", True), (42, False)])
    def test_extension_fields(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        value: object,
        valid: bool,
    ) -> None:
        from armarium.init import init_vault
        from armarium.parse import Record

        root = init_vault(tmp_path / "vault", extensions=["example"])
        monkeypatch.chdir(root)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "armarium",
                "add",
                "content",
                "Harbor",
                "--subtype",
                "Location",
                "--frontmatter",
                json.dumps({"climate": value}),
            ],
        )
        destination = root / "content/Harbor.md"
        if valid:
            main()
            record, _ = Record.parse(destination, root)
            assert record is not None and record.frontmatter["climate"] == value
        else:
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
            assert not destination.exists()


@pytest.fixture
def example(tmp_path: Path) -> Path:
    root = tmp_path.resolve() / "example"
    shutil.copytree(Path(__file__).resolve().parents[1] / "vaults/example", root)
    return root


class TestRenameCommand:
    @pytest.mark.parametrize("dry_run", [False, True])
    def test_renames(
        self,
        example: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        dry_run: bool,
    ) -> None:
        arguments = ["content/Wake-lark.md", "Lark", "--vault", str(example)]
        arguments += ["--dry-run"] if dry_run else []
        monkeypatch.setattr(sys, "argv", ["armarium", "rename", *arguments])
        main()
        output = capsys.readouterr()
        lines = output.out.splitlines()
        assert lines[0] == "content/Wake-lark.md\t\t\trenamed to content/Lark.md"
        assert (
            "content/Captain Mara Vey.md\tsummary\t\t[[Wake-lark]] → [[Lark]]" in lines
        )
        assert (example / "content/Lark.md").exists() is not dry_run
        assert (example / "content/Wake-lark.md").exists() is dry_run
        moved = "would be moved" if dry_run else "moved"
        assert f"content/Wake-lark.md: {moved} to content/Lark.md" in output.err

    def test_exits_with_one(
        self,
        example: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        arguments = ["content/Wake-lark.md", "Port Briselle", "--vault", str(example)]
        monkeypatch.setattr(sys, "argv", ["armarium", "rename", *arguments])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert "ERROR: Cannot rename content/Wake-lark.md: " in output.err
        assert "content/Port Briselle.md already exists" in output.err

    @pytest.mark.parametrize(
        "arguments", [[], ["content/Mara.md"], ["a.md", "b", "c"], ["a.md", "b", "-j"]]
    )
    def test_usage_errors(
        self, arguments: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            parse_args(["rename", *arguments])
        assert exc.value.code == 2
        assert "usage: armarium" in capsys.readouterr().err

    def test_options(self, tmp_path: Path) -> None:
        args = parse_args(["rename", "content/Mara.md", "Mara Vey"])
        assert (args.path, args.name, args.dry_run, args.vault) == (
            Path("content/Mara.md"),
            "Mara Vey",
            False,
            None,
        )
        args = parse_args(
            ["rename", "a.md", "b", "--dry-run", "--vault", str(tmp_path)]
        )
        assert (args.dry_run, args.vault) == (True, tmp_path)


class TestReportPlan:
    PLAN = RelinkPlan(
        FileChanges(Path("vault")),
        changes=[
            RelinkChange("content/Lark.md", "", 0, "renamed"),
            RelinkChange("content/Wake-lark.md", "Notes", 3, "[[A]] → [[B]]"),
        ],
        notes=["docs/a.md:1: [[A]] not changed: not a record"],
    )

    @pytest.mark.parametrize(
        ("dry_run", "summary"),
        [
            (True, "content/Lark.md: would be replaced"),
            (False, "content/Lark.md: replaced"),
        ],
    )
    def test_reports(
        self, capsys: pytest.CaptureFixture[str], dry_run: bool, summary: str
    ) -> None:
        configure_logging()
        files = [FileChange("replace", "content/Lark.md")]
        report_plan(self.PLAN, files, dry_run=dry_run)
        output = capsys.readouterr()
        assert output.out.splitlines() == [
            "content/Lark.md\t\t\trenamed",
            "content/Wake-lark.md\tNotes\t3\t[[A]] → [[B]]",
        ]
        assert "WARNING: docs/a.md:1: [[A]] not changed" in output.err
        assert f"INFO: {summary}" in output.err
