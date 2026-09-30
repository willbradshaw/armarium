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
    _write_config,
    enable_extension,
    is_template,
    load_extensions,
    remove_extension,
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
    enable_extension("example", vault)
    return vault


class TestExtensionRule:
    @pytest.mark.parametrize("selector", [None, "Location"])
    @pytest.mark.parametrize(
        "kind,subtype", [("Content", "Location"), ("Content", "Lore"), ("Note", None)]
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
            _declarations(ROOT / "extensions/example/extension.json")["example"][
                "rules"
            ][0]["subtype"]
            == "Location"
        )

    @pytest.mark.parametrize(
        "data",
        [
            None,
            [],
            {"../bad": []},
            {"custom": []},
            {"custom": {"rules": []}},
            {"custom": {"rules": [{"type": "Content"}]}},
            {
                "custom": {
                    "rules": [{"type": "Content", "schema": "x"}],
                    "installed": "yes",
                }
            },
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
            rule.extension == "example"
            and rule.kind == "Content"
            and rule.subtype == "Location"
        )
        assert rule.schema.path.is_relative_to(
            enabled / "reference/extensions/example/schemas"
        )
        assert rule.template is not None and rule.template.is_relative_to(
            enabled / "reference/extensions/example/templates"
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
                else text.replace("subtype: Location", "subtype: Lore")
            )
        elif scenario in {"conflict", "broad-conflict"}:
            data = json.loads(config.read_text())
            other = dict(data["example"]["rules"][0])
            if scenario == "broad-conflict":
                other.pop("subtype")
            data["custom"] = {"rules": [other]}
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
        data["house-rules"] = {
            "rules": [
                {
                    "type": "Content",
                    "subtype": "Location",
                    "schema": "schemas/house.schema.json",
                }
            ]
        }
        (enabled / "reference/schemas/house.schema.json").write_text(
            json.dumps({"properties": {"frontmatter": {"required": ["rating"]}}})
        )
        config.write_text(json.dumps(data))
        assert len(load_extensions(enabled)) == 2
        with pytest.raises(ValueError):
            add_content("Harbor", "Location", enabled)
        assert not (enabled / "content/Harbor.md").exists()


class TestExtension:
    def test_checkout(self) -> None:
        assert _extension("example").joinpath("extension.json").is_file()

    @pytest.mark.parametrize(
        "name", ["absent", "../example", "/example", "INVALID", ""]
    )
    def test_unknown(self, name: str) -> None:
        with pytest.raises(ValueError):
            _extension(name)


class TestEnableExtension:
    def test_install_preserves_core(self, vault: Path) -> None:
        original = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        assert enable_extension("example", vault) == vault
        assert all(p.read_bytes() == contents for p, contents in original.items())
        assert not validate(vault).failed

    def test_reenable_preserves_edits(self, enabled: Path) -> None:
        (rule,) = load_extensions(enabled)
        assert rule.template is not None
        rule.template.write_text(
            rule.template.read_text().replace("climate:", "climate: Temperate")
        )
        before = {p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()}
        with pytest.raises(ValueError, match="already enabled"):
            enable_extension("example", enabled)
        assert before == {p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()}

    @pytest.mark.parametrize(
        "collision",
        [
            "reference/extensions/example/README.md",
            "reference/extensions/example/schemas/location.schema.json",
        ],
    )
    def test_collision(self, vault: Path, collision: str) -> None:
        path = vault / collision
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Keep me")
        before = set(vault.rglob("*"))
        with pytest.raises(FileExistsError):
            enable_extension("example", vault)
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
        real = shutil.copytree

        def copy(
            source: Path, destination: Path, *args: object, **kwargs: object
        ) -> Path:
            result = real(source, destination, *args, **kwargs)
            if Path(source) == ROOT / "extensions/example":
                raise failure("interrupted copy")
            return result

        monkeypatch.setattr("armarium.extensions.shutil.copytree", copy)
        with pytest.raises(failure):
            enable_extension("example", vault)
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
        shutil.copytree(ROOT / "extensions/example", source)
        (source / "templates/Location.md").write_text("invalid")
        monkeypatch.setattr(extensions, "_extension", lambda name: source)
        if existing_config:
            (vault / CONFIG).write_text("{}\n")
        before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        entries = set(vault.rglob("*"))
        with pytest.raises(ValueError):
            enable_extension("example", vault)
        assert set(vault.rglob("*")) == entries
        assert before == {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}

    def test_existing_records_require_migration(self, vault: Path) -> None:
        gear = add_content("Harbor", "Location", vault)
        original = gear.read_bytes()
        enable_extension("example", vault)
        assert gear.read_bytes() == original
        assert validate(gear, vault).failed
        lore = add_content("Legend", "Lore", vault)
        assert not validate(lore, vault).failed

    def test_portable(self, enabled: Path, tmp_path: Path) -> None:
        moved = enabled.rename(tmp_path / "moved")
        add_content("Harbor", "Location", moved)
        assert not validate(moved).failed


class TestExampleSchema:
    @pytest.mark.parametrize(
        "value,valid",
        [(None, True), ("Temperate", True), ("", False), (" ", False), (42, False)],
    )
    def test_climate(self, enabled: Path, value: object, valid: bool) -> None:
        from armarium.add import record_text

        path = add_content("Harbor", "Location", enabled)
        record, _ = Record.parse(path, enabled)
        assert record is not None
        data = dict(record.frontmatter)
        data["climate"] = value
        path.write_text(record_text(data, record.body.text))
        assert validate(path, enabled).failed != valid

    @pytest.mark.parametrize("field", ["climate", "parent_location"])
    def test_required_fields(self, enabled: Path, field: str) -> None:
        path = add_content("Harbor", "Location", enabled)
        path.write_text(path.read_text().replace(f"{field}: null\n", ""))
        assert validate(path, enabled).failed


class TestWriteConfig:
    def test_replaces_atomically(self, tmp_path: Path) -> None:
        path = tmp_path / "extensions.json"
        path.write_bytes(b"old")
        _write_config(path, b"new")
        assert path.read_bytes() == b"new"
        assert not path.with_suffix(".json.tmp").exists()

    def test_failure_preserves_original(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "extensions.json"
        path.write_bytes(b"old")

        def fail(path: Path, target: Path) -> Path:
            raise OSError("cannot replace")

        monkeypatch.setattr(Path, "replace", fail)
        with pytest.raises(OSError):
            _write_config(path, b"new")
        assert path.read_bytes() == b"old"
        assert not path.with_suffix(".json.tmp").exists()

    def test_existing_temporary_file(self, tmp_path: Path) -> None:
        path = tmp_path / "extensions.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_bytes(b"keep")
        with pytest.raises(FileExistsError):
            _write_config(path, b"new")
        assert temporary.read_bytes() == b"keep"


class TestRemoveExtension:
    def test_preserves_records_and_allows_reenable(
        self, enabled: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        record = add_content("Harbor", "Location", enabled)
        original = record.read_bytes()
        directory = enabled / "reference/extensions/example"
        # Removal uses the installation inventory, not today's package resources.
        with monkeypatch.context() as patch:

            def unavailable(name: str) -> Path:
                raise AssertionError("must not read installed package")

            patch.setattr("armarium.extensions._extension", unavailable)
            assert remove_extension("example", enabled) == enabled
        assert not load_extensions(enabled)
        assert record.read_bytes() == original
        assert not directory.exists()
        assert not validate(enabled).failed
        new = add_content("Bay", "Location", enabled)
        assert "climate:" not in new.read_text()
        enable_extension("example", enabled)
        assert validate(new, enabled).failed
        assert not validate(record, enabled).failed

    @pytest.mark.parametrize(
        "file",
        [
            "README.md",
            "schemas/location.schema.json",
            "templates/Location.md",
            "extra.md",
        ],
    )
    def test_local_edits_are_removed(self, enabled: Path, file: str) -> None:
        directory = enabled / "reference/extensions/example"
        path = directory / file
        path.write_text("Local changes")
        remove_extension("example", enabled)
        assert not directory.exists()
        assert not validate(enabled).failed

    def test_missing_installed_file(self, enabled: Path) -> None:
        (enabled / "reference/extensions/example/templates/Location.md").unlink()
        remove_extension("example", enabled)
        assert not validate(enabled).failed

    def test_unknown(self, vault: Path) -> None:
        with pytest.raises(ValueError, match="not enabled"):
            remove_extension("missing", vault)
        assert not (vault / CONFIG).exists()

    def test_manual_declaration(self, enabled: Path) -> None:
        config = enabled / CONFIG
        data = _declarations(config)
        data["example"].pop("installed")
        config.write_text(json.dumps(data))
        remove_extension("example", enabled)
        assert not load_extensions(enabled)
        assert (enabled / "reference/extensions/example").is_dir()

    def test_shared_file_refused(self, enabled: Path) -> None:
        config = enabled / CONFIG
        data = _declarations(config)
        data["custom"] = {
            "rules": [
                {"type": "Content", "schema": "extensions/example/location.schema.json"}
            ]
        }
        config.write_text(json.dumps(data))
        before = config.read_bytes()
        with pytest.raises(ValueError, match="used by another"):
            remove_extension("example", enabled)
        assert config.read_bytes() == before

    @pytest.mark.parametrize("stage", ["move", "write", "load"])
    @pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
    def test_failure_restores_files(
        self,
        enabled: Path,
        monkeypatch: pytest.MonkeyPatch,
        stage: str,
        failure: type[BaseException],
    ) -> None:
        import armarium.extensions as extensions

        before = {p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()}
        if stage == "move":
            real = Path.rename

            def rename(path: Path, target: Path) -> Path:
                if path.name == "example":
                    raise failure("failed move")
                return real(path, target)

            monkeypatch.setattr(Path, "rename", rename)
        elif stage == "write":

            def write(path: Path, contents: bytes) -> None:
                raise failure("failed configuration write")

            monkeypatch.setattr(extensions, "_write_config", write)
        else:

            def load(root: Path) -> list[ExtensionRule]:
                raise failure("failed remaining extension check")

            monkeypatch.setattr(extensions, "load_extensions", load)
        with pytest.raises(failure):
            remove_extension("example", enabled)
        assert before == {p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()}
        assert not list(enabled.glob(".armarium-extension-*"))


class TestExampleVault:
    def test_enabled_and_removable(self, tmp_path: Path) -> None:
        root = tmp_path / "example"
        shutil.copytree(ROOT / "vaults/example", root)
        assert len(load_extensions(root)) == 1
        assert not validate(root).failed
        for source in (ROOT / "extensions/example").rglob("*"):
            if source.is_file():
                installed = (
                    root
                    / "reference/extensions/example"
                    / source.relative_to(ROOT / "extensions/example")
                )
                assert installed.read_bytes() == source.read_bytes()
        remove_extension("example", root)
        assert not validate(root).failed


class TestIsTemplate:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("reference/templates/Content.md", True),
            ("reference/extensions/example/templates/Location.md", True),
            ("reference/extensions/example/templates/nested/Location.md", True),
            ("reference/extensions/example/README.md", False),
            ("reference/extensions/templates/Location.md", False),
            ("content/templates/Location.md", False),
        ],
    )
    def test_directories(self, vault: Path, path: str, expected: bool) -> None:
        assert is_template(vault / path, vault) == expected
