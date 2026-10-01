"""Content creation, subtype requirements, local scaffolding and safe failure."""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from armarium.add import add_campaign
from armarium.content import SUBTYPES, _content_body, _content_frontmatter, add_content
from armarium.parse import Record
from armarium.validate import validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "my-vault"
    shutil.copytree(ROOT / "vaults/starter", root)
    (root / "campaigns/campaign_1/reference/players/Alex.md").write_text(
        '---\ntype: "[[types/Player]]"\nplays: []\n---\n'
    )
    return root


@pytest.fixture
def calendar(vault: Path) -> None:
    add_content("Calendar", "Lore", vault)


class TestContentFrontmatter:
    @pytest.mark.parametrize("subtype", SUBTYPES)
    @pytest.mark.parametrize("campaign", [None, 2])
    def test_stub_fields(self, vault: Path, subtype: str, campaign: int | None) -> None:
        template, _ = Record.parse(vault / "reference/templates/Content.md", vault)
        assert template is not None
        metadata = _content_frontmatter(
            template,
            subtype,
            campaign,
            frontmatter={
                k: v
                for k, v in {
                    "player": "[[Alex]]" if subtype == "PC" else None,
                    "reckoning": "[[Calendar]]" if subtype == "Date" else None,
                    "scale": "month" if subtype == "Date" else None,
                }.items()
                if v is not None
            },
        )
        assert metadata["subtype"] == subtype and metadata["summary"] is None
        assert "campaign_1" not in metadata
        if campaign is not None:
            assert metadata["campaign_2"]["first_session"] is None
            if subtype in {"Object", "Gear"}:
                assert metadata["campaign_2"]["held_by"] is None
        if subtype in {"NPC", "Location", "Faction", "Gear"}:
            field = {
                "NPC": "stats",
                "Location": "parent_location",
                "Faction": "members",
                "Gear": "source",
            }[subtype]
            assert field in metadata and metadata[field] is None

    def test_invalid_campaign_state(self, vault: Path) -> None:
        path = vault / "reference/templates/Content.md"
        path.write_text('---\ntype: "[[types/Content]]"\ncampaign_1: invalid\n---\n')
        template, _ = Record.parse(path, vault)
        assert template is not None
        with pytest.raises(ValueError, match="campaign_1 must be a mapping"):
            _content_frontmatter(template, "Lore", 1)


class TestContentBody:
    @pytest.mark.parametrize("subtype", ["Gear", "Object", "Lore"])
    @pytest.mark.parametrize("callout", ["", "> [!rules]\n> Local rules.\n\n"])
    def test_preserves_template(self, subtype: str, callout: str) -> None:
        body = callout + "## Notes\nKeep this text.\n"
        result = _content_body(body, subtype)
        assert result.endswith(body)
        if subtype == "Gear":
            assert result.count("> [!rules]") == 1
            assert result.startswith("> [!rules]")
        else:
            assert result == body


class TestAddContent:
    def test_gear_template_fields_and_rules(self, vault: Path) -> None:
        template = vault / "reference/templates/Content.md"
        original = (
            template.read_text()
            .replace("subtype:\n", "subtype:\nsource: Homebrew\nrarity: Common\n")
            .replace("## Notes", "> [!rules]\n> Supports one passenger.\n\n## Notes", 1)
        )
        template.write_text(original)
        path = add_content("Harness", "Gear", vault, campaign=1)
        record, _ = Record.parse(path, vault)
        assert record is not None
        assert record.frontmatter["source"] == "Homebrew"
        assert record.frontmatter["rarity"] == "Common"
        assert record.frontmatter["campaign_1"]["held_by"] is None
        assert record.body.text.count("> [!rules]") == 1
        assert "Supports one passenger." in record.body.text
        assert template.read_text() == original

    @pytest.mark.parametrize(
        "holder,valid", [("[[Mira]]", True), ("[[Calendar]]", False)]
    )
    def test_gear_possession(
        self, vault: Path, calendar: None, holder: str, valid: bool
    ) -> None:
        from armarium.session import add_session

        add_content("Mira", "PC", vault, campaign=1, frontmatter={"player": "[[Alex]]"})
        add_session(vault, campaign=1)
        path = add_content("Harness", "Gear", vault, campaign=1)
        path.write_text(
            path.read_text()
            .replace("first_session: null", 'first_session: "[[S-1-001]]"')
            .replace("last_session: null", 'last_session: "[[S-1-001]]"')
            .replace("held_by: null", f'held_by: "{holder}"')
            .replace(
                "## Appearances\n- N/A",
                "## Appearances\n- [[S-1-001]]: Acquired the harness.",
            )
        )
        assert validate(path).failed != valid

    @pytest.mark.parametrize("subtype", ["NPC", "Date"])
    def test_reckoning_requires_lore(
        self, vault: Path, calendar: None, subtype: str
    ) -> None:
        add_content(
            "Not a calendar",
            subtype,
            vault,
            frontmatter={
                k: v
                for k, v in {
                    "reckoning": "[[Calendar]]" if subtype == "Date" else None,
                    "scale": "year" if subtype == "Date" else None,
                }.items()
                if v is not None
            },
        )
        with pytest.raises(ValueError):
            add_content(
                "Invalid date",
                "Date",
                vault,
                frontmatter={"reckoning": "[[Not a calendar]]", "scale": "day"},
            )
        assert not (vault / "content/Invalid date.md").exists()

    def test_date_history_and_clue_subject(self, vault: Path, calendar: None) -> None:
        from armarium.clue import add_clue
        from armarium.session import add_session

        add_session(vault, campaign=1)
        path = add_content(
            "Year 42",
            "Date",
            vault,
            frontmatter={"reckoning": "[[Calendar]]", "scale": "year"},
        )
        path.write_text(
            path.read_text()
            .replace(
                "scale: year",
                'scale: year\ncampaign_1:\n  first_session: "[[S-1-001]]"\n  last_session: "[[S-1-001]]"',
            )
            .replace(
                "## Appearances\n- N/A",
                "## Appearances\n- [[S-1-001]]: The party arrived during this year.",
            )
        )
        add_clue(
            vault, campaign=1, frontmatter={"text": "The charter dates to [[Year 42]]."}
        )
        assert not validate(vault).failed
        path.write_text(
            path.read_text().replace(
                "## Appearances\n- [[S-1-001]]: The party arrived during this year.",
                "## Appearances\n- N/A",
            )
        )
        assert validate(path).failed

    @pytest.mark.parametrize(
        "reckoning", ["Calendar", "[[Calendar]]", "content/Calendar.md"]
    )
    def test_date_reckoning_resolution(
        self, vault: Path, reckoning: str, calendar: None
    ) -> None:
        path = add_content(
            "Year 42",
            "Date",
            vault,
            frontmatter={
                k: v
                for k, v in {
                    "reckoning": reckoning
                    if reckoning is None or reckoning.startswith("[[")
                    else f"[[{reckoning}]]",
                    "scale": "year",
                }.items()
                if v is not None
            },
        )
        record, _ = Record.parse(path, vault)
        assert record is not None
        assert record.frontmatter["reckoning"] == (
            reckoning if reckoning.startswith("[[") else f"[[{reckoning}]]"
        )
        assert record.frontmatter["scale"] == "year"
        assert not validate(vault).failed

    @pytest.mark.parametrize("override", [False, True])
    def test_date_template_defaults(
        self, vault: Path, override: bool, calendar: None
    ) -> None:
        template = vault / "reference/templates/Content.md"
        template.write_text(
            template.read_text().replace(
                "subtype:\n",
                'subtype:\nreckoning: "[[Calendar]]"\nscale: year\nspan: 2\n',
            )
        )
        path = add_content(
            "Period",
            "Date",
            vault,
            frontmatter={
                k: v
                for k, v in {"scale": "month" if override else None}.items()
                if v is not None
            },
        )
        record, _ = Record.parse(path, vault)
        assert record is not None
        assert record.frontmatter["scale"] == ("month" if override else "year")
        assert record.frontmatter["span"] == 2

    @pytest.mark.parametrize(
        "reckoning,scale",
        [
            (None, "day"),
            ("Calendar", None),
            ("Calendar", " "),
            ("Missing", "day"),
            ("Alex", "day"),
            ("[[Calendar|alias]]", "day"),
        ],
    )
    def test_invalid_date(
        self, vault: Path, reckoning: str | None, scale: str | None, calendar: None
    ) -> None:
        before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        with pytest.raises(ValueError):
            add_content(
                "Invalid",
                "Date",
                vault,
                frontmatter={
                    k: v
                    for k, v in {
                        "reckoning": reckoning
                        if reckoning is None or reckoning.startswith("[[")
                        else f"[[{reckoning}]]",
                        "scale": scale,
                    }.items()
                    if v is not None
                },
            )
        assert {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()} == before

    def test_template_player_default(self, vault: Path) -> None:
        template = vault / "reference/templates/Content.md"
        template.write_text(
            template.read_text().replace("subtype:\n", 'subtype:\nplayer: "[[Alex]]"\n')
        )
        assert add_content("Mira", "PC", vault, campaign=1).is_file()

    def test_write_failure_cleanup(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        destination = vault / "content/Entity.md"
        original_open = Path.open

        def failing_open(path: Path, *args: object, **kwargs: object) -> object:
            if path == destination and args == ("x",):
                stream = original_open(path, "x", encoding="utf-8")
                stream.close()
                mock = MagicMock()
                mock.write.side_effect = OSError("write failed")
                return mock
            return original_open(path, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", failing_open)
            with pytest.raises(OSError, match="write failed"):
                add_content("Entity", "Lore", vault)
        assert not destination.exists()
        assert add_content("Entity", "Lore", vault).is_file()

    @pytest.mark.parametrize("subtype", SUBTYPES)
    @pytest.mark.parametrize("campaign", [None, 1])
    def test_valid_stub(self, vault: Path, subtype: str, campaign: int | None) -> None:
        if subtype == "Date":
            add_content("Calendar", "Lore", vault)
        before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        destination = add_content(
            "New Entity",
            subtype,
            vault,
            campaign=campaign,
            frontmatter={
                k: v
                for k, v in {
                    "player": "[[Alex]]" if subtype == "PC" else None,
                    "reckoning": "[[Calendar]]" if subtype == "Date" else None,
                    "scale": "month" if subtype == "Date" else None,
                }.items()
                if v is not None
            },
        )
        expected = (
            vault
            / ("content" if campaign is None else "campaigns/campaign_1/content")
            / "New Entity.md"
        )
        assert destination == expected
        result = validate(vault)
        assert not result.failed, result.diagnostics
        assert all(p.read_bytes() == contents for p, contents in before.items())
        record, _ = Record.parse(destination, vault)
        assert record is not None
        assert record.frontmatter.get("summary") is None
        if subtype == "PC":
            assert record.frontmatter["player"] == "[[Alex]]"

    def test_campaign_two_and_discovery(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        add_campaign(vault)
        monkeypatch.chdir(vault / "campaigns/campaign_2/content")
        destination = add_content("The Compass", "Object", campaign=2)
        record, _ = Record.parse(destination, vault)
        assert record is not None and set(record.frontmatter.campaigns) == {
            "campaign_2"
        }
        assert record.frontmatter["campaign_2"]["held_by"] is None
        assert (
            add_content("The Coast", "Location").parent
            == vault / "campaigns/campaign_2/content"
        )
        assert not validate(vault).failed

    @pytest.mark.parametrize(
        "relative", ["campaigns/campaign_1", "campaigns/campaign_1/reference/players"]
    )
    @pytest.mark.parametrize("explicit_vault", [False, True])
    def test_infers_current_campaign(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        relative: str,
        explicit_vault: bool,
    ) -> None:
        monkeypatch.chdir(vault / relative)
        destination = add_content(
            "Mira",
            "PC",
            vault if explicit_vault else None,
            frontmatter={"player": "[[Alex]]"},
        )
        assert destination.parent == vault / "campaigns/campaign_1/content"
        record, _ = Record.parse(destination, vault)
        assert record is not None and set(record.frontmatter.campaigns) == {
            "campaign_1"
        }

    def test_explicit_campaign_overrides_working_directory(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        add_campaign(vault)
        monkeypatch.chdir(vault / "campaigns/campaign_1")
        assert (
            add_content("Harbour", "Location", campaign=2).parent
            == vault / "campaigns/campaign_2/content"
        )

    def test_does_not_infer_from_another_vault(
        self, vault: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        other = tmp_path / "another-vault"
        shutil.copytree(vault, other)
        monkeypatch.chdir(other / "campaigns/campaign_1")
        assert add_content("Harbour", "Location", vault).parent == vault / "content"

    def test_customized_template_and_directory(self, vault: Path) -> None:
        definition = vault / "reference/types/Content.md"
        definition.write_text(
            definition.read_text().replace(
                "shared: content", "shared: content/entities"
            )
        )
        (vault / "content/entities").mkdir()
        template = vault / "reference/templates/Content.md"
        template.write_text(
            template.read_text()
            .replace("summary:\n", "summary: Local default\ncustom: Keep me\n")
            .replace("## Notes\n- N/A", "## Notes\nLocal guidance.")
        )
        destination = add_content("Harbour", "Location", vault)
        record, _ = Record.parse(destination, vault)
        assert record is not None
        assert destination.parent == vault / "content/entities"
        assert record.frontmatter["custom"] == "Keep me"
        assert record.frontmatter["summary"] == "Local default"
        original, _ = Record.parse(template, vault)
        assert original is not None and record.body.text == original.body.text
        assert not validate(vault).failed

    @pytest.mark.parametrize(
        "player", ["Alex", "[[Alex]]", "campaigns/campaign_1/reference/players/Alex.md"]
    )
    def test_player_resolution(self, vault: Path, player: str) -> None:
        path = add_content(
            "Mira",
            "PC",
            vault,
            campaign=1,
            frontmatter={
                k: v
                for k, v in {
                    "player": player
                    if player is None or player.startswith("[[")
                    else f"[[{player}]]"
                }.items()
                if v is not None
            },
        )
        record, _ = Record.parse(path, vault)
        assert record is not None and record.frontmatter["summary"] is None
        assert not validate(path).failed

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
            "A#B",
            "A|B",
            "A[B]",
            "end.",
        ],
    )
    def test_invalid_name(self, vault: Path, name: str) -> None:
        with pytest.raises(ValueError, match="name must"):
            add_content(name, "Lore", vault)
        assert not list((vault / "content").glob("*.md"))

    @pytest.mark.parametrize(
        "kind", ["file", "directory", "symlink", "dangling", "case"]
    )
    def test_collision(self, vault: Path, kind: str) -> None:
        target = vault / "content" / ("NAME.md" if kind == "case" else "Name.md")
        if kind in {"file", "case"}:
            target.write_text("Unchanged")
        elif kind == "directory":
            target.mkdir()
        else:
            target.symlink_to(
                vault
                / ("reference/types/Content.md" if kind == "symlink" else "missing")
            )
        with pytest.raises(FileExistsError):
            add_content("Name", "Lore", vault)
        if kind in {"file", "case"}:
            assert target.read_text() == "Unchanged"
        elif kind == "directory":
            assert list(target.iterdir()) == []
        else:
            assert target.is_symlink()

    @pytest.mark.parametrize(
        "scenario", ["missing", "wrong_type", "ambiguous", "wrong_campaign"]
    )
    def test_invalid_player(self, vault: Path, scenario: str) -> None:
        player = "Missing" if scenario == "missing" else "Alex"
        if scenario == "wrong_type":
            player = "types/Content"
        if scenario in {"ambiguous", "wrong_campaign"}:
            add_campaign(vault)
        if scenario == "ambiguous":
            shutil.copyfile(
                vault / "campaigns/campaign_1/reference/players/Alex.md",
                vault / "campaigns/campaign_2/reference/players/Alex.md",
            )
        with pytest.raises(ValueError):
            add_content(
                "Mira",
                "PC",
                vault,
                campaign=2 if scenario == "wrong_campaign" else 1,
                frontmatter={
                    k: v
                    for k, v in {
                        "player": player
                        if player is None or player.startswith("[[")
                        else f"[[{player}]]"
                    }.items()
                    if v is not None
                },
            )
        assert not list(vault.rglob("Mira.md"))

    @pytest.mark.parametrize(
        "scenario",
        [
            "subtype",
            "campaign_zero",
            "campaign_missing",
            "no_player",
            "outside",
            "nested_vault",
        ],
    )
    def test_invalid_arguments(
        self, vault: Path, tmp_path: Path, scenario: str
    ) -> None:
        with pytest.raises(ValueError):
            add_content(
                "Entity",
                "Unknown"
                if scenario == "subtype"
                else "PC"
                if scenario == "no_player"
                else "Lore",
                tmp_path
                if scenario == "outside"
                else vault / "content"
                if scenario == "nested_vault"
                else vault,
                campaign=0
                if scenario == "campaign_zero"
                else 9
                if scenario == "campaign_missing"
                else None,
            )
        assert not list(vault.rglob("Entity.md"))

    @pytest.mark.parametrize(
        "scenario",
        [
            "missing_template",
            "bad_template",
            "wrong_template_type",
            "missing_definition",
            "no_shared",
            "symlink_directory",
            "symlink_template",
            "schema",
        ],
    )
    def test_invalid_scaffolding(self, vault: Path, scenario: str) -> None:
        template = vault / "reference/templates/Content.md"
        definition = vault / "reference/types/Content.md"
        if scenario == "missing_template":
            template.unlink()
        elif scenario == "bad_template":
            template.write_text("---\nbad: [\n---\n")
        elif scenario == "wrong_template_type":
            template.write_text("No frontmatter")
        elif scenario == "missing_definition":
            definition.unlink()
        elif scenario == "no_shared":
            definition.write_text(
                '---\ntype: "[[Type]]"\ndirectories: {campaign: content}\n---\n'
            )
        elif scenario == "symlink_directory":
            directory = vault / "content"
            moved = directory.rename(vault / "other-content")
            directory.symlink_to(moved)
        elif scenario == "symlink_template":
            template.unlink()
            template.symlink_to(definition)
        else:
            schema = vault / "reference/schemas/content.schema.json"
            data = json.loads(schema.read_text())
            data["properties"]["frontmatter"]["required"].append("custom_required")
            schema.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            add_content("Entity", "Lore", vault)
        assert not list(vault.rglob("Entity.md"))

    @pytest.mark.parametrize(
        "error", [OSError("validation read failed"), KeyboardInterrupt()]
    )
    def test_interrupted_validation_cleanup(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException
    ) -> None:
        with monkeypatch.context() as patch:
            patch.setattr("armarium.add.validate", Mock(side_effect=error))
            with pytest.raises(type(error)):
                add_content("Entity", "Lore", vault)
        assert not (vault / "content/Entity.md").exists()
        assert add_content("Entity", "Lore", vault).is_file()


class TestExtensionContent:
    @pytest.mark.parametrize("campaign", [None, 1])
    def test_local_template_and_core_checks(
        self, vault: Path, campaign: int | None
    ) -> None:
        from armarium.extensions import enable_extension, load_extensions

        enable_extension("example", vault)
        (rule,) = load_extensions(vault)
        assert rule.template is not None
        rule.template.write_text(
            rule.template.read_text()
            .replace("climate:", "climate: Temperate")
            .replace("- N/A", "- Local notes", 1)
        )
        path = add_content("Harbor", "Location", vault, campaign=campaign)
        record, _ = Record.parse(path, vault)
        assert record is not None
        assert record.frontmatter["climate"] == "Temperate"
        assert record.frontmatter["parent_location"] is None
        assert "Local notes" in record.body.text
        if campaign:
            assert record.frontmatter["campaign_1"]["first_session"] is None
        assert not validate(path, vault).failed
        path.write_text(path.read_text().replace("## Notes", "## Missing"))
        assert validate(path, vault).failed

    def test_nested_frontmatter(self, vault: Path) -> None:
        add_campaign(vault, number=2)
        path = add_content(
            "Harness",
            "Gear",
            vault,
            campaign=2,
            frontmatter={"campaign_2": {"custom": {"rating": 3}}, "source": "Homebrew"},
        )
        record, _ = Record.parse(path, vault)
        assert record is not None
        assert record.frontmatter["campaign_2"] == {
            "first_session": None,
            "last_session": None,
            "held_by": None,
            "custom": {"rating": 3},
        }
        assert "campaign_1" not in record.frontmatter
        assert record.frontmatter["source"] == "Homebrew"
