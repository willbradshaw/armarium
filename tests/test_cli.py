"""Command parsing, diagnostics, exit status and process entry point."""

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from armarium.cli import _subtype_choices, main, parse_args
from armarium.lib import SUBTYPES, Diagnostic, Result, VaultNotFoundError
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
