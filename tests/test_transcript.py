"""Transcript selection, local scaffolding, body grammar and safe creation."""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from armarium.add import add_campaign
from armarium.parse import Record
from armarium.session import add_session
from armarium.transcript import add_transcript
from armarium.validate import validate

ROOT = Path(__file__).resolve().parents[1]
BODY = "## Arrival\n\n- [GM] The door opens.\n- [Mira] Who is there?\n\n## Departure\n\n- [GM] Night falls.\n"


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault with spaces"
    shutil.copytree(ROOT / "vaults/starter", root)
    add_session(root, campaign=1)
    return root


@pytest.fixture
def body_file(tmp_path: Path) -> Path:
    path = tmp_path / "recorded speech.md"
    path.write_text(BODY)
    return path


class TestAddTranscript:
    def test_example_vault(self, tmp_path: Path, body_file: Path) -> None:
        root = tmp_path / "example vault"
        shutil.copytree(ROOT / "vaults/example", root)
        session = add_session(root, campaign=1)
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        destination = add_transcript(session.stem, body_file, root)
        assert destination.name == f"{session.stem} Transcript.md"
        assert not validate(root).failed
        assert all(p.read_bytes() == contents for p, contents in before.items())

    @pytest.mark.parametrize(
        "selection",
        [
            "S-1-001",
            "campaigns/campaign_1/sessions/S-1-001.md",
            "[[campaign_1/sessions/S-1-001]]",
        ],
    )
    @pytest.mark.parametrize("explicit", [False, True])
    def test_creation(
        self,
        vault: Path,
        body_file: Path,
        monkeypatch: pytest.MonkeyPatch,
        selection: str,
        explicit: bool,
    ) -> None:
        monkeypatch.chdir(vault / "campaigns/campaign_1/sessions/transcripts")
        before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        destination = add_transcript(selection, body_file, vault if explicit else None)
        assert (
            destination
            == vault / "campaigns/campaign_1/sessions/transcripts/S-1-001 Transcript.md"
        )
        record, _ = Record.parse(destination, vault)
        assert record is not None
        assert (
            record.frontmatter["session"] == "[[campaigns/campaign_1/sessions/S-1-001]]"
        )
        assert record.body.text == BODY
        assert not validate(vault).failed
        assert all(p.read_bytes() == content for p, content in before.items())
        assert body_file.read_text() == BODY

    @pytest.mark.parametrize("explicit", [False, True])
    def test_session_determines_campaign(
        self,
        vault: Path,
        body_file: Path,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        explicit: bool,
    ) -> None:
        add_campaign(vault)
        add_session(vault, campaign=2)
        other = tmp_path / "other vault"
        shutil.copytree(vault, other)
        monkeypatch.chdir(other / "campaigns/campaign_1/sessions")
        destination = add_transcript(
            "S-2-001", body_file, vault, campaign=2 if explicit else None
        )
        assert destination.is_relative_to(vault / "campaigns/campaign_2")
        assert not validate(vault).failed

    def test_qualified_ambiguous_target(self, vault: Path, body_file: Path) -> None:
        session = vault / "campaigns/campaign_1/sessions/S-1-001.md"
        archive = session.parent / "archive"
        archive.mkdir()
        shutil.copyfile(session, archive / session.name)
        with pytest.raises(ValueError, match="uniquely"):
            add_transcript("S-1-001", body_file, vault)
        destination = add_transcript(
            "campaigns/campaign_1/sessions/archive/S-1-001", body_file, vault
        )
        assert not validate(destination).failed

    @pytest.mark.parametrize(
        "selection",
        [
            "Missing",
            "Transcript",
            "reference/templates/Session",
            "Campaign",
            "[[S-1-001|alias]]",
            "[[S-1-001#Heading]]",
            "../S-1-001",
            "",
        ],
    )
    def test_invalid_selection(
        self, vault: Path, body_file: Path, selection: str
    ) -> None:
        with pytest.raises(ValueError):
            add_transcript(selection, body_file, vault)
        assert not list(vault.rglob("* Transcript.md"))

    @pytest.mark.parametrize("campaign", [0, -1, 2])
    def test_campaign_conflict(
        self, vault: Path, body_file: Path, campaign: int
    ) -> None:
        with pytest.raises(ValueError, match="campaign"):
            add_transcript("S-1-001", body_file, vault, campaign=campaign)
        assert not list(vault.rglob("* Transcript.md"))

    @pytest.mark.parametrize(
        "scenario", ["number", "campaign", "malformed", "misplaced", "symlink"]
    )
    def test_invalid_session(self, vault: Path, body_file: Path, scenario: str) -> None:
        path = vault / "campaigns/campaign_1/sessions/S-1-001.md"
        if scenario == "number":
            path.write_text(
                path.read_text().replace("session_number: 1", "session_number: 2")
            )
        elif scenario == "campaign":
            path.write_text(
                path.read_text().replace(
                    "campaign_1/reference/Campaign", "campaign_2/reference/Campaign"
                )
            )
        elif scenario == "malformed":
            path.write_text("---\nbad: [\n---\n")
        elif scenario == "misplaced":
            path.rename(vault / "content/S-1-001.md")
        else:
            moved = path.rename(body_file.parent / "session.md")
            path.symlink_to(moved)
        with pytest.raises(ValueError):
            add_transcript("S-1-001", body_file, vault)
        assert not list(vault.rglob("* Transcript.md"))

    @pytest.mark.parametrize(
        "body",
        [
            "",
            "## Opening\n",
            "# Opening\n- [GM] Hi\n",
            "Preamble\n\n## Opening\n- [GM] Hi\n",
            "## Opening\n- No speaker\n",
            "## Opening\n- [GM] Hi\n\nParagraph\n",
            "## Opening\n- [GM] Hi\n  - nested\n",
            "## Opening\n- [GM] Hi\n[Sam] Bye\n",
            "## Opening\n- [GM] [[Missing]]\n",
            "---\ntype: Other\n---\n## Opening\n- [GM] Hi\n",
        ],
    )
    def test_body_failure_and_retry(
        self, vault: Path, body_file: Path, body: str
    ) -> None:
        body_file.write_text(body)
        with pytest.raises(ValueError, match="generated Transcript"):
            add_transcript("S-1-001", body_file, vault)
        assert not list(vault.rglob("* Transcript.md"))
        assert body_file.read_text() == body
        body_file.write_text(BODY)
        assert add_transcript("S-1-001", body_file, vault).is_file()

    def test_local_customizations(self, vault: Path, body_file: Path) -> None:
        definition = vault / "reference/types/Transcript.md"
        definition.write_text(
            definition.read_text().replace(
                "campaign: sessions/transcripts", "campaign: recorded speech"
            )
        )
        (vault / "campaigns/campaign_1/recorded speech").mkdir()
        template = vault / "reference/templates/Transcript.md"
        template.write_text(
            template.read_text().replace(
                "session:", "custom: Local value\nsession: '[[Missing]]'"
            )
        )
        destination = add_transcript("S-1-001", body_file, vault)
        assert destination.parent.name == "recorded speech"
        record, _ = Record.parse(destination, vault)
        assert record is not None and record.frontmatter["custom"] == "Local value"
        assert record.body.text == BODY
        assert not validate(vault).failed

    @pytest.mark.parametrize(
        "kind", ["file", "directory", "symlink", "dangling", "case"]
    )
    def test_existing_destination(
        self, vault: Path, body_file: Path, kind: str
    ) -> None:
        target = (
            vault
            / "campaigns/campaign_1/sessions/transcripts"
            / ("s-1-001 transcript.MD" if kind == "case" else "S-1-001 Transcript.md")
        )
        if kind in {"file", "case"}:
            target.write_text("Unchanged")
        elif kind == "directory":
            target.mkdir()
        else:
            target.symlink_to(body_file if kind == "symlink" else vault / "missing")
        with pytest.raises(FileExistsError):
            add_transcript("S-1-001", body_file, vault)
        if kind in {"file", "case"}:
            assert target.read_text() == "Unchanged"
        elif kind == "directory":
            assert list(target.iterdir()) == []
        else:
            assert target.is_symlink()
        assert body_file.read_text() == BODY

    @pytest.mark.parametrize(
        "scenario",
        [
            "missing_template",
            "bad_template",
            "wrong_type",
            "missing_type",
            "no_campaign_directory",
            "unsafe_directory",
            "symlink_directory",
            "symlink_template",
            "schema",
            "missing_body",
            "encoding",
            "nested_vault",
        ],
    )
    def test_invalid_scaffolding(
        self, vault: Path, body_file: Path, scenario: str
    ) -> None:
        template = vault / "reference/templates/Transcript.md"
        definition = vault / "reference/types/Transcript.md"
        if scenario == "missing_template":
            template.unlink()
        elif scenario == "bad_template":
            template.write_text("---\nbad: [\n---\n")
        elif scenario == "wrong_type":
            template.write_text("Missing type")
        elif scenario == "missing_type":
            definition.unlink()
        elif scenario in {"no_campaign_directory", "unsafe_directory"}:
            definition.write_text(
                '---\ntype: "[[Type]]"\ndirectories: {'
                + (
                    "shared: content"
                    if scenario == "no_campaign_directory"
                    else "campaign: ../../outside"
                )
                + "}\n---\n"
            )
        elif scenario == "symlink_directory":
            directory = vault / "campaigns/campaign_1/sessions/transcripts"
            moved = directory.rename(vault / "other-transcripts")
            directory.symlink_to(moved)
        elif scenario == "symlink_template":
            template.unlink()
            template.symlink_to(definition)
        elif scenario == "schema":
            schema = vault / "reference/schemas/transcript.schema.json"
            data = json.loads(schema.read_text())
            data["properties"]["frontmatter"]["required"].append("custom_required")
            schema.write_text(json.dumps(data))
        elif scenario == "missing_body":
            body_file.unlink()
        elif scenario == "encoding":
            body_file.write_bytes(b"\xff")
        with pytest.raises((ValueError, OSError)):
            add_transcript(
                "S-1-001",
                body_file,
                vault / "content" if scenario == "nested_vault" else vault,
            )
        assert not list(vault.rglob("* Transcript.md"))

    @pytest.mark.parametrize("error", [OSError("failed"), KeyboardInterrupt()])
    def test_validation_interruption(
        self,
        vault: Path,
        body_file: Path,
        monkeypatch: pytest.MonkeyPatch,
        error: BaseException,
    ) -> None:
        with monkeypatch.context() as patch:
            patch.setattr(
                "armarium.transcript.validate",
                Mock(
                    side_effect=[
                        validate(vault / "campaigns/campaign_1/sessions/S-1-001.md"),
                        error,
                    ]
                ),
            )
            with pytest.raises(type(error)):
                add_transcript("S-1-001", body_file, vault)
        assert not list(vault.rglob("* Transcript.md"))
        assert add_transcript("S-1-001", body_file, vault).is_file()

    @pytest.mark.parametrize("late_collision", [False, True])
    def test_write_failure(
        self,
        vault: Path,
        body_file: Path,
        monkeypatch: pytest.MonkeyPatch,
        late_collision: bool,
    ) -> None:
        destination = (
            vault / "campaigns/campaign_1/sessions/transcripts/S-1-001 Transcript.md"
        )
        original_open = Path.open

        def failing_open(path: Path, *args: object, **kwargs: object) -> object:
            if path == destination and args == ("x",):
                with original_open(path, "x", encoding="utf-8") as stream:
                    stream.write("Late arrival" if late_collision else "")
                if late_collision:
                    return original_open(path, *args, **kwargs)
                failed = MagicMock()
                failed.write.side_effect = OSError("write failed")
                return failed
            return original_open(path, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", failing_open)
            with pytest.raises(OSError):
                add_transcript("S-1-001", body_file, vault)
        if late_collision:
            assert destination.read_text() == "Late arrival"
        else:
            assert not destination.exists()
            assert add_transcript("S-1-001", body_file, vault) == destination
