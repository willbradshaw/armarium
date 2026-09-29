"""Note scope, local scaffolding, preservation and safe creation failures."""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from armarium.add import add_campaign
from armarium.note import add_note
from armarium.parse import Record
from armarium.validate import validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault with spaces"
    shutil.copytree(ROOT / "vaults/starter", root)
    return root


class TestAddNote:
    @pytest.mark.parametrize("source", ["starter", "example"])
    @pytest.mark.parametrize("campaign", [None, 1])
    def test_valid_addition(
        self, tmp_path: Path, source: str, campaign: int | None
    ) -> None:
        root = tmp_path / "vault with spaces"
        shutil.copytree(ROOT / "vaults" / source, root)
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        destination = add_note("Working ideas", root, campaign=campaign)
        assert (
            destination
            == root
            / ("notes" if campaign is None else "campaigns/campaign_1/notes")
            / "Working ideas.md"
        )
        record, _ = Record.parse(destination, root)
        assert record is not None and record.frontmatter.type == "Note"
        assert not record.body.text.strip()
        assert not validate(destination, root).failed
        result = validate(root)
        assert not result.failed, result.diagnostics
        assert all(p.read_bytes() == text for p, text in before.items())

    @pytest.mark.parametrize(
        "relative",
        ["", "notes", "campaigns/campaign_1", "campaigns/campaign_1/reference/players"],
    )
    @pytest.mark.parametrize("explicit_vault", [False, True])
    def test_scope_inference(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        relative: str,
        explicit_vault: bool,
    ) -> None:
        monkeypatch.chdir(vault / relative)
        destination = add_note("Working ideas", vault if explicit_vault else None)
        expected = (
            "campaigns/campaign_1/notes"
            if relative.startswith("campaigns/")
            else "notes"
        )
        assert destination.parent == vault / expected

    def test_explicit_override(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        add_campaign(vault)
        monkeypatch.chdir(vault / "campaigns/campaign_1/notes")
        assert (
            add_note("Working ideas", campaign=2).parent
            == vault / "campaigns/campaign_2/notes"
        )

    def test_selecting_other_vault(
        self, vault: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        other = tmp_path / "other vault"
        shutil.copytree(vault, other)
        monkeypatch.chdir(other / "campaigns/campaign_1/notes")
        assert add_note("Working ideas", vault).parent == vault / "notes"

    @pytest.mark.parametrize("campaign", [None, 1])
    def test_local_customizations(self, vault: Path, campaign: int | None) -> None:
        definition = vault / "reference/types/Note.md"
        definition.write_text(
            definition.read_text()
            .replace("shared: notes", "shared: notes/working")
            .replace("campaign: notes", "campaign: notes/working")
        )
        for directory in ("notes/working", "campaigns/campaign_1/notes/working"):
            (vault / directory).mkdir()
        template = vault / "reference/templates/Note.md"
        text = '---\ntype: "[[types/Note]]"\n# Keep the formatting too.\ncustom: [Local, values]\n---\n\n## Ideas\n\nFreeform **Markdown**.\n'
        template.write_text(text)
        schema = vault / "reference/schemas/note.schema.json"
        data = json.loads(schema.read_text())
        data["properties"]["frontmatter"]["required"].append("custom")
        data["properties"]["frontmatter"]["properties"]["custom"] = {
            "const": ["Local", "values"]
        }
        data["properties"]["body"]["minLength"] = 10
        schema.write_text(json.dumps(data))
        before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        destination = add_note("Working ideas", vault, campaign=campaign)
        assert destination.parent.name == "working"
        assert destination.read_text() == text
        assert not validate(vault).failed
        assert all(p.read_bytes() == value for p, value in before.items())

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "../outside",
            "sub/name",
            "sub\\name",
            ".hidden",
            " Name",
            "Name ",
            "Two  Spaces",
            "Name.md",
            "Name.MD",
            "A#B",
            "A|B",
            "A[B]",
            "end.",
            "bad\x00name",
            "bad\x1fname",
            "A:B",
            "A?B",
            "A*B",
            'A"B',
            "A<B>",
        ],
    )
    def test_invalid_name(self, vault: Path, name: str) -> None:
        with pytest.raises(ValueError, match="name must"):
            add_note(name, vault)
        assert not list((vault / "notes").glob("*.md"))

    @pytest.mark.parametrize(
        "kind", ["file", "directory", "symlink", "dangling", "case", "unicode"]
    )
    def test_collision(self, vault: Path, kind: str) -> None:
        name = "Café" if kind == "unicode" else "Name"
        existing = (
            "Cafe\u0301.md"
            if kind == "unicode"
            else "NAME.md"
            if kind == "case"
            else "Name.md"
        )
        target = vault / "notes" / existing
        if kind == "directory":
            target.mkdir()
        elif kind in {"symlink", "dangling"}:
            target.symlink_to(
                vault / ("missing" if kind == "dangling" else "reference/types/Note.md")
            )
        else:
            target.write_text("Unchanged")
        with pytest.raises(FileExistsError):
            add_note(name, vault)
        if kind == "directory":
            assert list(target.iterdir()) == []
        elif kind in {"symlink", "dangling"}:
            assert target.is_symlink()
        else:
            assert target.read_text() == "Unchanged"

    @pytest.mark.parametrize(
        "scenario", ["zero", "missing_campaign", "outside", "nested_vault"]
    )
    def test_invalid_scope(self, vault: Path, tmp_path: Path, scenario: str) -> None:
        with pytest.raises(ValueError):
            add_note(
                "Ideas",
                tmp_path
                if scenario == "outside"
                else vault / "notes"
                if scenario == "nested_vault"
                else vault,
                campaign=0
                if scenario == "zero"
                else 9
                if scenario == "missing_campaign"
                else None,
            )
        assert not list(vault.rglob("Ideas.md"))

    @pytest.mark.parametrize(
        "scenario",
        [
            "missing_template",
            "bad_template",
            "wrong_type",
            "missing_definition",
            "missing_scope",
            "traversal",
            "absolute",
            "missing_directory",
        ],
    )
    def test_invalid_scaffolding(self, vault: Path, scenario: str) -> None:
        template = vault / "reference/templates/Note.md"
        definition = vault / "reference/types/Note.md"
        if scenario == "missing_template":
            template.unlink()
        elif scenario == "bad_template":
            template.write_text("---\nbad: [\n---\n")
        elif scenario == "wrong_type":
            template.write_text('---\ntype: "[[types/Content]]"\n---\n')
        elif scenario == "missing_definition":
            definition.unlink()
        elif scenario == "missing_directory":
            shutil.rmtree(vault / "notes")
        else:
            declaration = {
                "missing_scope": "{campaign: notes}",
                "traversal": "{shared: ../outside}",
                "absolute": "{shared: /tmp}",
            }[scenario]
            definition.write_text(
                f'---\ntype: "[[Type]]"\ndirectories: {declaration}\n---\n'
            )
        with pytest.raises(ValueError):
            add_note("Ideas", vault)
        assert not list(vault.rglob("Ideas.md"))

    @pytest.mark.parametrize(
        "relative",
        [
            "notes",
            "campaigns",
            "campaigns/campaign_1",
            "campaigns/campaign_1/notes",
            "reference/templates/Note.md",
            "reference/templates",
            "reference",
        ],
    )
    def test_symlink_paths(self, vault: Path, tmp_path: Path, relative: str) -> None:
        target = vault / relative
        moved = target.rename(tmp_path / "moved")
        target.symlink_to(moved, target_is_directory=moved.is_dir())
        with pytest.raises(ValueError):
            add_note(
                "Ideas", vault, campaign=1 if relative.startswith("campaigns") else None
            )
        assert not list(tmp_path.rglob("Ideas.md"))

    @pytest.mark.parametrize("constraint", ["metadata", "body"])
    def test_schema_failure_cleanup_retry(self, vault: Path, constraint: str) -> None:
        schema = vault / "reference/schemas/note.schema.json"
        data = json.loads(schema.read_text())
        if constraint == "metadata":
            data["properties"]["frontmatter"]["required"].append("custom")
        else:
            data["properties"]["body"]["minLength"] = 10
        schema.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="failed validation"):
            add_note("Ideas", vault)
        assert not (vault / "notes/Ideas.md").exists()
        (vault / "reference/templates/Note.md").write_text(
            '---\ntype: "[[types/Note]]"\ncustom: supplied\n---\nEnough body text.\n'
        )
        assert add_note("Ideas", vault).is_file()
        assert not validate(vault).failed

    @pytest.mark.parametrize("location", ["metadata", "body"])
    def test_context_failure_cleanup_retry(self, vault: Path, location: str) -> None:
        template = vault / "reference/templates/Note.md"
        text = (
            '---\ntype: "[[types/Note]]"\nrelated: "[[Missing]]"\n---\n'
            if location == "metadata"
            else '---\ntype: "[[types/Note]]"\n---\nSee [[Missing]].\n'
        )
        template.write_text(text)
        with pytest.raises(ValueError, match="failed validation"):
            add_note("Ideas", vault)
        assert not (vault / "notes/Ideas.md").exists()
        assert template.read_text() == text
        template.write_text(text.replace("[[Missing]]", "[[types/Note]]"))
        assert add_note("Ideas", vault).is_file()
        assert not validate(vault).failed

    @pytest.mark.parametrize("error", [OSError("read failed"), KeyboardInterrupt()])
    def test_validation_failure_cleanup_retry(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException
    ) -> None:
        with monkeypatch.context() as patch:
            patch.setattr("armarium.note.validate", Mock(side_effect=error))
            with pytest.raises(type(error)):
                add_note("Ideas", vault)
        assert not (vault / "notes/Ideas.md").exists()
        assert add_note("Ideas", vault).is_file()

    @pytest.mark.parametrize("error", [OSError("disk full"), KeyboardInterrupt()])
    def test_write_failure_cleanup_retry(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException
    ) -> None:
        original = Path.open
        destination = vault / "notes/Ideas.md"

        def failing_open(
            path: Path, mode: str = "r", *args: object, **kwargs: object
        ) -> object:
            if path == destination and mode == "x":
                destination.touch()
                stream = MagicMock()
                stream.__enter__.return_value = stream
                stream.write.side_effect = error
                return stream
            return original(path, mode, *args, **kwargs)  # type: ignore[call-overload]

        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", failing_open)
            with pytest.raises(type(error)):
                add_note("Ideas", vault)
        assert not destination.exists()
        assert add_note("Ideas", vault).is_file()

    def test_late_collision(self, vault: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        destination = vault / "notes/Ideas.md"
        original = Path.open

        def racing_open(
            path: Path, mode: str = "r", *args: object, **kwargs: object
        ) -> object:
            if path == destination and mode == "x":
                destination.write_text("Concurrent writer")
            return original(path, mode, *args, **kwargs)  # type: ignore[call-overload]

        monkeypatch.setattr(Path, "open", racing_open)
        with pytest.raises(FileExistsError):
            add_note("Ideas", vault)
        assert destination.read_text() == "Concurrent writer"
