"""Extension registration, local customization, confinement and installation."""

import json
import shutil
from pathlib import Path

import pytest
from jsonschema.exceptions import SchemaError

from armarium.content import add_content
from armarium.extensions import (
    CONFIG,
    ExtensionRule,
    _declarations,
    _extension,
    _local_path,
    enable_extension,
    load_extensions,
)
from armarium.parse import Record
from armarium.validate import validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    shutil.copytree(ROOT / "vaults/starter", root)
    return root


@pytest.fixture
def enabled(vault: Path) -> Path:
    enable_extension("dnd-5-5", vault)
    return vault


class TestExtensionRule:
    @pytest.mark.parametrize("selector", [None, "Gear"])
    @pytest.mark.parametrize(
        "kind,subtype", [("Content", "Gear"), ("Content", "Lore"), ("Note", None)]
    )
    def test_matches(
        self, enabled: Path, selector: str | None, kind: str, subtype: str | None
    ) -> None:
        rule = load_extensions(enabled)[0]
        rule = ExtensionRule(
            rule.extension, "Content", selector, rule.schema, rule.template
        )
        assert rule.matches(kind, subtype) == (
            kind == "Content" and (selector is None or selector == subtype)
        )


class TestLocalPath:
    def test_relative(self, vault: Path) -> None:
        assert (
            _local_path(vault, "reference/schemas", "custom/a.json")
            == vault / "reference/schemas/custom/a.json"
        )

    @pytest.mark.parametrize("name", ["/tmp/outside", "../outside", "a/../../outside"])
    def test_escape(self, vault: Path, name: str) -> None:
        with pytest.raises(ValueError, match="stay inside"):
            _local_path(vault, "reference/schemas", name)

    @pytest.mark.parametrize("nested", [False, True])
    def test_symlink(self, vault: Path, tmp_path: Path, nested: bool) -> None:
        link = vault / "reference/schemas/link"
        link.symlink_to(tmp_path / "missing")
        with pytest.raises(ValueError, match="symlinks"):
            _local_path(
                vault, "reference/schemas", "link/file.json" if nested else "link"
            )


class TestDeclarations:
    def test_valid(self) -> None:
        assert (
            _declarations(ROOT / "extensions/dnd-5-5/extension.json")["dnd-5-5"][0][
                "subtype"
            ]
            == "Gear"
        )

    @pytest.mark.parametrize(
        "data",
        [
            None,
            [],
            {"../bad": []},
            {"custom": []},
            {"custom": [{"type": "Content"}]},
            {"custom": [{"type": "Content", "schema": "x", "typo": True}]},
        ],
    )
    def test_invalid(self, tmp_path: Path, data: object) -> None:
        path = tmp_path / "extension.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="invalid extension declaration"):
            _declarations(path)


class TestLoadExtensions:
    def test_absent(self, vault: Path) -> None:
        assert load_extensions(vault) == []

    def test_loads_local_files(self, enabled: Path) -> None:
        (rule,) = load_extensions(enabled)
        assert (
            rule.extension == "dnd-5-5"
            and rule.kind == "Content"
            and rule.subtype == "Gear"
        )
        assert rule.schema.path.is_relative_to(enabled / "reference/schemas")
        assert rule.template is not None and rule.template.is_relative_to(
            enabled / "reference/templates"
        )

    @pytest.mark.parametrize(
        "scenario",
        [
            "schema-missing",
            "schema-invalid",
            "template-missing",
            "template-type",
            "template-subtype",
            "conflict",
            "broad-conflict",
            "config-invalid",
            "config-symlink",
        ],
    )
    def test_invalid_configuration(self, enabled: Path, scenario: str) -> None:
        (rule,) = load_extensions(enabled)
        assert rule.template is not None
        config = enabled / CONFIG
        if scenario == "schema-missing":
            rule.schema.path.unlink()
        elif scenario == "schema-invalid":
            rule.schema.path.write_text('{"type": "nonsense"}')
        elif scenario == "template-missing":
            rule.template.unlink()
        elif scenario.startswith("template-"):
            text = rule.template.read_text()
            rule.template.write_text(
                text.replace("types/Content", "types/Note")
                if scenario == "template-type"
                else text.replace("subtype: Gear", "subtype: Lore")
            )
        elif scenario in {"conflict", "broad-conflict"}:
            data = json.loads(config.read_text())
            other = dict(data["dnd-5-5"][0])
            if scenario == "broad-conflict":
                other.pop("subtype")
            data["custom"] = [other]
            config.write_text(json.dumps(data))
        elif scenario == "config-invalid":
            config.write_text("{")
        else:
            config.unlink()
            config.symlink_to(enabled / "missing")
        with pytest.raises((OSError, ValueError, SchemaError)):
            load_extensions(enabled)
        assert validate(enabled).failed

    def test_additional_local_constraints(self, enabled: Path) -> None:
        config = enabled / CONFIG
        data = json.loads(config.read_text())
        data["house-rules"] = [
            {"type": "Content", "subtype": "Gear", "schema": "house.schema.json"}
        ]
        (enabled / "reference/schemas/house.schema.json").write_text(
            json.dumps({"properties": {"frontmatter": {"required": ["rating"]}}})
        )
        config.write_text(json.dumps(data))
        assert len(load_extensions(enabled)) == 2
        with pytest.raises(ValueError):
            add_content("Harness", "Gear", enabled)
        assert not (enabled / "content/Harness.md").exists()


class TestExtension:
    def test_checkout(self) -> None:
        assert _extension("dnd-5-5").joinpath("extension.json").is_file()

    @pytest.mark.parametrize("name", ["absent", "../dnd-5-5", "/dnd-5-5", "DND", ""])
    def test_unknown(self, name: str) -> None:
        with pytest.raises(ValueError):
            _extension(name)


class TestEnableExtension:
    def test_install_preserves_core(self, vault: Path) -> None:
        original = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        assert enable_extension("dnd-5-5", vault) == vault
        assert all(p.read_bytes() == contents for p, contents in original.items())
        assert not validate(vault).failed

    def test_reenable_preserves_edits(self, enabled: Path) -> None:
        (rule,) = load_extensions(enabled)
        assert rule.template is not None
        rule.template.write_text(
            rule.template.read_text().replace("source:", "source: Homebrew")
        )
        before = {p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()}
        with pytest.raises(ValueError, match="already enabled"):
            enable_extension("dnd-5-5", enabled)
        assert before == {p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()}

    @pytest.mark.parametrize(
        "collision",
        [
            "reference/dnd-5-5.md",
            "reference/schemas/extensions/dnd-5-5/gear.schema.json",
        ],
    )
    def test_collision(self, vault: Path, collision: str) -> None:
        path = vault / collision
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Keep me")
        before = set(vault.rglob("*"))
        with pytest.raises(FileExistsError):
            enable_extension("dnd-5-5", vault)
        assert set(vault.rglob("*")) == before
        assert path.read_text() == "Keep me"

    @pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
    @pytest.mark.parametrize("existing_config", [False, True])
    def test_rollback(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        failure: type[BaseException],
        existing_config: bool,
    ) -> None:
        if existing_config:
            (vault / CONFIG).write_text("{}\n")
        original = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        original_entries = set(vault.rglob("*"))
        real = Path.read_bytes

        def read(path: Path) -> bytes:
            if path.name == "Gear.md" and path.is_relative_to(ROOT / "extensions"):
                raise failure("interrupted copy")
            return real(path)

        monkeypatch.setattr(Path, "read_bytes", read)
        with pytest.raises(failure):
            enable_extension("dnd-5-5", vault)
        assert set(vault.rglob("*")) == original_entries
        assert all(p.read_bytes() == content for p, content in original.items())

    @pytest.mark.parametrize("existing_config", [False, True])
    def test_registration_failure_restores_configuration(
        self,
        vault: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        existing_config: bool,
    ) -> None:
        import armarium.extensions as extensions

        source = tmp_path / "extension"
        shutil.copytree(ROOT / "extensions/dnd-5-5", source)
        (source / "reference/templates/extensions/dnd-5-5/Gear.md").write_text(
            "invalid"
        )
        monkeypatch.setattr(extensions, "_extension", lambda name: source)
        if existing_config:
            (vault / CONFIG).write_text("{}\n")
        before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        entries = set(vault.rglob("*"))
        with pytest.raises(ValueError):
            enable_extension("dnd-5-5", vault)
        assert set(vault.rglob("*")) == entries
        assert before == {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}

    def test_existing_records_require_migration(self, vault: Path) -> None:
        gear = add_content("Harness", "Gear", vault)
        original = gear.read_bytes()
        enable_extension("dnd-5-5", vault)
        assert gear.read_bytes() == original
        assert validate(gear, vault).failed
        lore = add_content("Legend", "Lore", vault)
        assert not validate(lore, vault).failed

    def test_portable(self, enabled: Path, tmp_path: Path) -> None:
        moved = enabled.rename(tmp_path / "moved")
        add_content("Harness", "Gear", moved)
        assert not validate(moved).failed


class TestDndGearSchema:
    @pytest.mark.parametrize(
        "field,value,valid",
        [
            ("rarity", "Rare", True),
            ("rarity", "Varies", True),
            ("rarity", "rare", False),
            ("item_type", "Shield", False),
            ("item_type", "Rope", False),
            ("item_type", " ", False),
            ("item_type", "Armor", True),
            ("attunement", True, True),
            ("attunement", "true", False),
            ("consumable", False, True),
            ("consumable", 0, False),
            ("cursed", True, True),
            ("cursed", "unknown", False),
            ("sentient", None, True),
            ("sentient", "false", False),
            ("item_tags", [], True),
            ("item_tags", ["Weapon", "Homebrew"], True),
            ("item_tags", ["Weapon", "Weapon"], False),
            ("item_tags", [" "], False),
            ("attunement_restrictions", "Wizard", False),
            ("joke_score", 5, True),
            ("ddb_id", 123, True),
        ],
    )
    def test_fields(
        self, enabled: Path, field: str, value: object, valid: bool
    ) -> None:
        path = add_content("Harness", "Gear", enabled)
        record, _ = Record.parse(path, enabled)
        assert record is not None
        from armarium.add import record_text

        data = dict(record.frontmatter)
        data[field] = value
        path.write_text(record_text(data, record.body.text))
        assert validate(path, enabled).failed != valid

    @pytest.mark.parametrize(
        "field", ["item_type", "rarity", "attunement", "consumable", "cursed", "source"]
    )
    def test_required_fields(self, enabled: Path, field: str) -> None:
        path = add_content("Harness", "Gear", enabled)
        path.write_text(path.read_text().replace(f"{field}: null\n", ""))
        assert validate(path, enabled).failed
