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
    ExtensionSet,
    _declarations,
    _extension,
    _local_path,
    _write_config,
    content_subtypes,
    enable_extension,
    is_template,
    load_extension_set,
    load_extensions,
    remove_extension,
)
from armarium.lib import SUBTYPES
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


@pytest.fixture
def relics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The example extension, extended to declare a Relic Content subtype."""
    import armarium.extensions as extensions

    source = tmp_path / "relics"
    shutil.copytree(ROOT / "extensions/example", source)
    declaration = _declarations(source / "extension.json")
    declaration["example"]["subtypes"] = {"Content": ["Relic"]}
    declaration["example"]["rules"].append(
        {
            "type": "Content",
            "subtype": "Relic",
            "schema": "schemas/relic.schema.json",
            "template": "templates/Relic.md",
        }
    )
    (source / "extension.json").write_text(json.dumps(declaration))
    (source / "schemas/relic.schema.json").write_text(
        json.dumps({"properties": {"frontmatter": {"required": ["origin"]}}})
    )
    (source / "templates/Relic.md").write_text(
        (ROOT / "vaults/starter/reference/templates/Content.md")
        .read_text()
        .replace("subtype:\n", "subtype: Relic\norigin:\n")
    )
    monkeypatch.setattr(extensions, "_extension", lambda name: source)
    return source


@pytest.fixture
def declared(vault: Path, relics: Path) -> Path:
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

    def test_subtypes(self, relics: Path) -> None:
        declaration = _declarations(relics / "extension.json")["example"]
        assert declaration["subtypes"] == {"Content": ["Relic"]}

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
            *[
                {
                    "custom": {
                        "rules": [{"type": "Content", "schema": "x"}],
                        "subtypes": subtypes,
                    }
                }
                for subtypes in (
                    [],
                    {"Note": ["Relic"]},
                    {"Content": []},
                    {"Content": "Relic"},
                    {"Content": ["Relic", "Relic"]},
                    {"Content": [""]},
                    {"Content": ["Holy relic"]},
                    {"Content": ["1st"]},
                    {"Content": [42]},
                )
            ],
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
        path = add_content("Harbor", "Location", enabled, frontmatter={"rating": 3})
        assert not validate(path, enabled).failed


class TestExtensionSet:
    def test_holds_rules_and_subtypes(self, enabled: Path) -> None:
        rules = load_extensions(enabled)
        extensions = ExtensionSet(rules, ("Lore",))
        assert extensions.rules == rules and extensions.subtypes == ("Lore",)
        with pytest.raises(AttributeError):
            extensions.subtypes = ()  # type: ignore[misc]


class TestLoadExtensionSet:
    def test_absent(self, vault: Path) -> None:
        assert load_extension_set(vault) == ExtensionSet([], SUBTYPES)

    def test_without_declared_subtypes(self, enabled: Path) -> None:
        extensions = load_extension_set(enabled)
        assert extensions.rules == load_extensions(enabled)
        assert extensions.subtypes == SUBTYPES

    def test_declared_subtypes(self, declared: Path) -> None:
        extensions = load_extension_set(declared)
        assert extensions.subtypes == (*SUBTYPES, "Relic")
        assert [r.subtype for r in extensions.rules] == ["Location", "Relic"]

    @pytest.mark.parametrize(
        ("scenario", "message"),
        [
            ("core", "declares core Content subtype Lore"),
            ("duplicate", "both declare Content subtype Relic"),
            ("no-template", "without a template"),
            ("foreign-template", "without a template"),
            ("unknown-rule", "selects unknown Content subtype Relik"),
        ],
    )
    def test_invalid_subtypes(
        self, declared: Path, scenario: str, message: str
    ) -> None:
        config = declared / CONFIG
        data = json.loads(config.read_text())
        relic = data["example"]["rules"][1]
        if scenario == "core":
            data["example"]["subtypes"]["Content"].append("Lore")
        elif scenario == "duplicate":
            data["local"] = {"subtypes": {"Content": ["Relic"]}, "rules": [relic]}
        elif scenario == "no-template":
            relic.pop("template")
        elif scenario == "foreign-template":
            data["example"]["rules"].remove(relic)
            data["local"] = {"rules": [relic]}
        else:
            data["local"] = {"rules": [{**relic, "subtype": "Relik"}]}
            data["local"]["rules"][0].pop("template")
        config.write_text(json.dumps(data))
        with pytest.raises(ValueError, match=message):
            load_extension_set(declared)
        assert validate(declared).failed

    def test_local_rule_for_declared_subtype(self, declared: Path) -> None:
        config = declared / CONFIG
        data = json.loads(config.read_text())
        data["house-rules"] = {
            "rules": [
                {
                    "type": "Content",
                    "subtype": "Relic",
                    "schema": "extensions/example/schemas/relic.schema.json",
                }
            ]
        }
        config.write_text(json.dumps(data))
        assert len(load_extension_set(declared).rules) == 3


class TestContentSubtypes:
    def test_core(self, vault: Path) -> None:
        assert content_subtypes(vault) == SUBTYPES

    def test_declared(self, declared: Path) -> None:
        assert content_subtypes(declared) == (*SUBTYPES, "Relic")


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

    def test_declared_subtype(self, declared: Path) -> None:
        assert _declarations(declared / CONFIG)["example"]["subtypes"] == {
            "Content": ["Relic"]
        }
        path = add_content("Crown", "Relic", declared)
        record, _ = Record.parse(path, declared)
        assert record is not None
        assert record.frontmatter["subtype"] == "Relic"
        assert record.frontmatter["origin"] is None
        assert not validate(declared).failed

    def test_declared_subtype_conflict(self, vault: Path, relics: Path) -> None:
        (vault / "reference/schemas/relic.schema.json").write_text("true")
        shutil.copy(relics / "templates/Relic.md", vault / "reference/templates")
        rule = {
            "type": "Content",
            "subtype": "Relic",
            "schema": "schemas/relic.schema.json",
            "template": "templates/Relic.md",
        }
        (vault / CONFIG).write_text(
            json.dumps({"local": {"subtypes": {"Content": ["Relic"]}, "rules": [rule]}})
        )
        before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        entries = set(vault.rglob("*"))
        with pytest.raises(ValueError, match="both declare"):
            enable_extension("example", vault)
        assert set(vault.rglob("*")) == entries
        assert before == {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}

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

    def test_declared_subtype_records_remain(self, declared: Path) -> None:
        path = add_content("Crown", "Relic", declared)
        original = path.read_bytes()
        remove_extension("example", declared)
        assert path.read_bytes() == original
        result = validate(declared)
        assert [
            (d.path, d.rule) for d in result.diagnostics if d.severity == "error"
        ] == [("content/Crown.md", "record.subtype")]
        enable_extension("example", declared)
        assert not validate(declared).failed

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


class TestArmariumVersion:
    @pytest.mark.parametrize("packaged", [False, True])
    def test_resource_version(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, packaged: bool
    ) -> None:
        import armarium.extensions as extensions

        package = tmp_path / "package"
        package.mkdir()
        if packaged:
            (package / "extensions").mkdir()
        project = tmp_path / "checkout"
        project.mkdir()
        (project / "pyproject.toml").write_text('[project]\nversion = "2.3.4"\n')
        monkeypatch.setattr(extensions, "files", lambda name: package)
        monkeypatch.setattr(
            extensions, "__file__", str(project / "src/armarium/extensions.py")
        )
        monkeypatch.setattr(extensions, "version", lambda name: "3.4.5")
        assert extensions._armarium_version() == ("3.4.5" if packaged else "2.3.4")


class TestInstallExtension:
    def test_records_version(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import armarium.extensions as extensions

        monkeypatch.setattr(extensions, "_armarium_version", lambda: "2.0.0")
        extensions._install_extension("example", vault, {})
        assert _declarations(vault / CONFIG)["example"]["armarium_version"] == "2.0.0"
        assert not validate(vault).failed


@pytest.fixture
def replacement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import armarium.extensions as extensions

    source = tmp_path / "replacement"
    shutil.copytree(ROOT / "extensions/example", source)
    monkeypatch.setattr(extensions, "_extension", lambda name: source)
    monkeypatch.setattr(extensions, "_armarium_version", lambda: "2.0.0")
    return source


class TestUpdateExtension:
    @pytest.mark.parametrize("previous", [None, "1.0.0", "2.0.0"])
    def test_replaces_files_and_tracks_version(
        self, enabled: Path, replacement: Path, previous: str | None
    ) -> None:
        from armarium.extensions import update_extension

        config = enabled / CONFIG
        data = _declarations(config)
        if previous is None:
            data["example"].pop("armarium_version", None)
        else:
            data["example"]["armarium_version"] = previous
        config.write_text(json.dumps(data))
        directory = enabled / "reference/extensions/example"
        (directory / "obsolete.md").write_text("Local addition")
        (directory / "README.md").write_text("Local edits")
        record = add_content("Harbor", "Location", enabled)
        before = record.read_bytes()
        (replacement / "README.md").write_text(
            (replacement / "README.md").read_text() + "\nUpdated reference.\n"
        )
        assert update_extension("example", enabled) == enabled
        assert not (directory / "obsolete.md").exists()
        assert (directory / "README.md").read_bytes() == (
            replacement / "README.md"
        ).read_bytes()
        assert _declarations(config)["example"]["armarium_version"] == "2.0.0"
        assert record.read_bytes() == before
        assert not validate(enabled).failed
        assert not list(enabled.glob(".armarium-update-*"))

    def test_keeps_custom_rules_and_shared_references(
        self, enabled: Path, replacement: Path
    ) -> None:
        from armarium.extensions import update_extension

        config = enabled / CONFIG
        data = _declarations(config)
        data["custom"] = {
            "rules": [
                {
                    "type": "Content",
                    "subtype": "Location",
                    "schema": "extensions/example/schemas/location.schema.json",
                }
            ]
        }
        config.write_text(json.dumps(data))
        update_extension("example", enabled)
        assert _declarations(config)["custom"] == data["custom"]
        assert not validate(enabled).failed

    @pytest.mark.parametrize("missing", ["schema", "directory"])
    def test_repairs_old_installation(
        self, enabled: Path, replacement: Path, missing: str
    ) -> None:
        from armarium.extensions import update_extension

        directory = enabled / "reference/extensions/example"
        if missing == "schema":
            (directory / "schemas/location.schema.json").unlink()
        else:
            shutil.rmtree(directory)
        update_extension("example", enabled)
        assert not validate(enabled).failed

    @pytest.mark.parametrize("local", [False, True])
    def test_requires_installed_extension(self, vault: Path, local: bool) -> None:
        from armarium.extensions import update_extension

        if local:
            (vault / CONFIG).write_text(
                json.dumps(
                    {
                        "example": {
                            "rules": [
                                {
                                    "type": "Content",
                                    "schema": "schemas/content.schema.json",
                                }
                            ]
                        }
                    }
                )
            )
        before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        with pytest.raises(ValueError, match="not installed"):
            update_extension("example", vault)
        assert before == {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}

    @pytest.mark.parametrize(
        "scenario", ["invalid-schema", "conflict", "unknown-source"]
    )
    def test_rejected_update_restores_original(
        self, enabled: Path, replacement: Path, scenario: str
    ) -> None:
        from armarium.extensions import update_extension

        if scenario == "invalid-schema":
            (replacement / "schemas/location.schema.json").write_text('{"type": "bad"}')
        elif scenario == "conflict":
            config = enabled / CONFIG
            data = _declarations(config)
            data["local"] = {
                "rules": [
                    {
                        "type": "Content",
                        "subtype": "Lore",
                        "schema": "schemas/content.schema.json",
                        "template": "templates/Lore.md",
                    }
                ]
            }
            config.write_text(json.dumps(data))
            template = enabled / "reference/templates/Lore.md"
            template.write_text(
                (enabled / "reference/templates/Content.md")
                .read_text()
                .replace("subtype:", "subtype: Lore")
            )
            declaration = _declarations(replacement / "extension.json")
            declaration["example"]["rules"][0].pop("subtype")
            (replacement / "extension.json").write_text(json.dumps(declaration))
        else:
            (replacement / "extension.json").unlink()
        before = {p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()}
        with pytest.raises((ValueError, OSError)):
            update_extension("example", enabled)
        assert before == {p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()}
        assert not list(enabled.glob(".armarium-update-*"))

    @pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
    @pytest.mark.parametrize("stage", ["move", "config", "install"])
    def test_interrupted_update_rolls_back(
        self,
        enabled: Path,
        monkeypatch: pytest.MonkeyPatch,
        stage: str,
        failure: type[BaseException],
    ) -> None:
        import armarium.extensions as extensions

        before = {p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()}
        if stage == "move":

            def rename(path: Path, target: Path) -> Path:
                raise failure("cannot move")

            monkeypatch.setattr(Path, "rename", rename)
        elif stage == "config":

            def write(path: Path, content: bytes) -> None:
                raise failure("cannot write")

            monkeypatch.setattr(extensions, "_write_config", write)
        else:
            install = extensions._install_extension

            def fail(name: str, root: Path, declarations: dict) -> None:
                install(name, root, declarations)
                raise failure("interrupted after replacement")

            monkeypatch.setattr(extensions, "_install_extension", fail)
        with pytest.raises(failure):
            extensions.update_extension("example", enabled)
        assert before == {p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()}
        assert not list(enabled.glob(".armarium-update-*"))


class TestUpdateDowngrade:
    @pytest.mark.parametrize(
        "previous,available,downgrade",
        [
            ("2.0", "1.0", True),
            ("0.10", "0.9", True),
            ("1.0", "1.0rc1", True),
            ("1.0.post1", "1.0", True),
            ("1.0", "1.0.dev1", True),
            ("1.0", "1.0.0", False),
            ("1.0rc1", "1.0", False),
            ("0.9", "0.10", False),
        ],
    )
    @pytest.mark.parametrize("allow", [False, True])
    def test_version_ordering(
        self,
        enabled: Path,
        monkeypatch: pytest.MonkeyPatch,
        previous: str,
        available: str,
        downgrade: bool,
        allow: bool,
    ) -> None:
        import armarium.extensions as extensions

        config = enabled / CONFIG
        declarations = _declarations(config)
        declarations["example"]["armarium_version"] = previous
        config.write_text(json.dumps(declarations))
        monkeypatch.setattr(extensions, "_armarium_version", lambda: available)
        before = {p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()}
        if downgrade and not allow:
            with pytest.raises(ValueError, match="--allow-downgrade"):
                extensions.update_extension("example", enabled)
            assert before == {
                p: p.read_bytes() for p in enabled.rglob("*") if p.is_file()
            }
            assert not list(enabled.glob(".armarium-update-*"))
        else:
            extensions.update_extension("example", enabled, allow_downgrade=allow)
            assert _declarations(config)["example"]["armarium_version"] == available

    @pytest.mark.parametrize("allow", [False, True])
    def test_invalid_recorded_version(self, enabled: Path, allow: bool) -> None:
        from armarium.extensions import update_extension

        config = enabled / CONFIG
        data = _declarations(config)
        data["example"]["armarium_version"] = "unknown"
        config.write_text(json.dumps(data))
        original = config.read_bytes()
        with pytest.raises(ValueError, match="Invalid version"):
            update_extension("example", enabled, allow_downgrade=allow)
        assert config.read_bytes() == original


class TestDndGearSchema:
    FIELDS = {
        "item_type": "Equipment",
        "rarity": "Mundane",
        "attunement": False,
        "consumable": False,
        "cursed": False,
        "sentient": False,
        "content_tags": [],
    }

    @pytest.mark.parametrize("campaign", [None, 1])
    def test_template_and_scope(self, vault: Path, campaign: int | None) -> None:
        enable_extension("dnd-5-5", vault)
        gear = add_content(
            "Compass", "Gear", vault, campaign=campaign, frontmatter=self.FIELDS
        )
        record, _ = Record.parse(gear, vault)
        assert record is not None
        for field, value in self.FIELDS.items():
            assert record.frontmatter[field] == value
        if campaign is not None:
            assert record.frontmatter[f"campaign_{campaign}"]["held_by"] is None
        add_content("Legend", "Lore", vault, campaign=campaign)
        assert not validate(vault).failed

    @pytest.mark.parametrize("field", [*FIELDS, "summary", "source"])
    def test_required_fields(self, vault: Path, field: str) -> None:
        enable_extension("dnd-5-5", vault)
        path = add_content("Compass", "Gear", vault, frontmatter=self.FIELDS)
        from armarium.add import record_text

        record, _ = Record.parse(path, vault)
        assert record is not None
        data = dict(record.frontmatter)
        del data[field]
        path.write_text(record_text(data, record.body.text))
        assert validate(path, vault).failed

    @pytest.mark.parametrize(
        "field,value,valid",
        [
            *[
                ("item_type", v, True)
                for v in (
                    "Equipment",
                    "Armor",
                    "Potion",
                    "Ring",
                    "Rod",
                    "Scroll",
                    "Staff",
                    "Wand",
                    "Weapon",
                    "Wondrous Item",
                )
            ],
            *[
                ("rarity", v, True)
                for v in (
                    "Mundane",
                    "Common",
                    "Uncommon",
                    "Rare",
                    "Very Rare",
                    "Legendary",
                    "Artifact",
                    "Varies",
                )
            ],
            *[
                (f, v, valid)
                for f in ("attunement", "consumable", "cursed", "sentient")
                for v, valid in [
                    (True, True),
                    (False, True),
                    ("true", False),
                    (0, False),
                ]
            ],
            *[(f, None, False) for f in FIELDS],
            ("item_type", "Shield", False),
            ("item_type", "armor", False),
            ("rarity", "rare", False),
            ("rarity", "", False),
            ("content_tags", ["Warding", "Utility"], True),
            ("content_tags", [], True),
            ("content_tags", ["Warding", "Warding"], False),
            ("content_tags", ["Custom tag"], True),
            ("content_tags", ["warding"], True),
            ("content_tags", [""], False),
            ("content_tags", [" "], False),
            ("content_tags", "Armor", False),
            ("content_tags", [42], False),
            ("attunement_restrictions", None, True),
            ("attunement_restrictions", "", False),
            ("attunement_restrictions", " ", False),
            ("attunement_restrictions", 42, False),
            ("provider_id", 1234, True),
        ],
    )
    def test_values(self, vault: Path, field: str, value: object, valid: bool) -> None:
        from armarium.add import record_text

        enable_extension("dnd-5-5", vault)
        path = add_content("Compass", "Gear", vault, frontmatter=self.FIELDS)
        record, _ = Record.parse(path, vault)
        assert record is not None
        data = dict(record.frontmatter)
        data[field] = value
        path.write_text(record_text(data, record.body.text))
        assert validate(path, vault).failed != valid

    @pytest.mark.parametrize("attunement", [None, False, True])
    def test_attunement_prerequisite(
        self, vault: Path, attunement: bool | None
    ) -> None:
        from armarium.add import record_text

        enable_extension("dnd-5-5", vault)
        path = add_content("Compass", "Gear", vault, frontmatter=self.FIELDS)
        record, _ = Record.parse(path, vault)
        assert record is not None
        data = dict(record.frontmatter)
        data.update(attunement=attunement, attunement_restrictions="A spellcaster")
        path.write_text(record_text(data, record.body.text))
        assert validate(path, vault).failed == (attunement is not True)

    def test_existing_gear_and_removal(self, vault: Path) -> None:
        gear = add_content("Compass", "Gear", vault)
        before = gear.read_bytes()
        enable_extension("dnd-5-5", vault)
        assert validate(gear, vault).failed
        assert gear.read_bytes() == before
        remove_extension("dnd-5-5", vault)
        assert gear.read_bytes() == before
        assert not validate(vault).failed

    @pytest.mark.parametrize("missing", list(FIELDS))
    def test_creation_requires_fields(self, vault: Path, missing: str) -> None:
        enable_extension("dnd-5-5", vault)
        fields = {k: v for k, v in self.FIELDS.items() if k != missing}
        with pytest.raises(ValueError, match="failed validation"):
            add_content("Compass", "Gear", vault, frontmatter=fields)
        assert not (vault / "content/Compass.md").exists()

    def test_custom_tags_at_creation(self, vault: Path) -> None:
        enable_extension("dnd-5-5", vault)
        tags = ["Local tradition", "Artisan-made"]
        path = add_content(
            "Compass", "Gear", vault, frontmatter={**self.FIELDS, "content_tags": tags}
        )
        record, _ = Record.parse(path, vault)
        assert record is not None and record.frontmatter["content_tags"] == tags
        assert not validate(path, vault).failed


class TestDndSpellSchema:
    FIELDS = {
        "source": "Homebrew",
        "level": 1,
        "school": "Abjuration",
        "casting_time": "1 Action",
        "ritual": True,
        "range": "Touch",
        "components": ["Verbal", "Material"],
        "material": "a pinch of sea salt",
        "duration": "8 hours",
        "concentration": False,
        "content_tags": [],
    }
    MISSING = object()

    def spell(self, vault: Path, **fields: object) -> Path:
        """Create a valid Spell, then rewrite fields; MISSING deletes one."""
        from armarium.add import record_text

        path = add_content("Salt Ward", "Spell", vault, frontmatter=self.FIELDS)
        record, _ = Record.parse(path, vault)
        assert record is not None
        data = dict(record.frontmatter)
        for field, value in fields.items():
            if value is self.MISSING:
                data.pop(field, None)
            else:
                data[field] = value
        path.write_text(record_text(data, record.body.text))
        return path

    @pytest.mark.parametrize("campaign", [None, 1])
    def test_template_and_scope(self, vault: Path, campaign: int | None) -> None:
        enable_extension("dnd-5-5", vault)
        assert "Spell" in content_subtypes(vault)
        path = add_content(
            "Salt Ward", "Spell", vault, campaign=campaign, frontmatter=self.FIELDS
        )
        record, _ = Record.parse(path, vault)
        assert record is not None
        assert record.frontmatter["subtype"] == "Spell"
        for field, value in self.FIELDS.items():
            assert record.frontmatter[field] == value
        assert record.body.text.startswith("> [!rules]")
        if campaign is not None:
            assert "held_by" not in record.frontmatter[f"campaign_{campaign}"]
        assert not validate(vault).failed

    @pytest.mark.parametrize("field", [*FIELDS, "summary"])
    def test_required_fields(self, vault: Path, field: str) -> None:
        enable_extension("dnd-5-5", vault)
        path = self.spell(vault, **{field: self.MISSING})
        assert validate(path, vault).failed

    @pytest.mark.parametrize(
        "field,value,valid",
        [
            *[("level", v, True) for v in range(10)],
            *[("level", v, False) for v in (-1, 10, 1.5, "1", True, None)],
            *[
                ("school", v, True)
                for v in (
                    "Abjuration",
                    "Conjuration",
                    "Divination",
                    "Enchantment",
                    "Evocation",
                    "Illusion",
                    "Necromancy",
                    "Transmutation",
                )
            ],
            ("school", "abjuration", False),
            ("school", "Chronurgy", False),
            *[
                (f, v, valid)
                for f in ("ritual", "concentration")
                for v, valid in [
                    (True, True),
                    (False, True),
                    ("true", False),
                    (0, False),
                    (None, False),
                ]
            ],
            *[
                (f, v, valid)
                for f in ("casting_time", "range", "duration")
                for v, valid in [
                    ("Special", True),
                    ("", False),
                    (" ", False),
                    (1, False),
                    (None, False),
                ]
            ],
            ("area", "20-foot Sphere", True),
            ("area", "40,000 square feet", True),
            ("area", None, True),
            ("area", MISSING, True),
            ("area", "", False),
            ("area", " ", False),
            ("area", 20, False),
            ("components", ["Material", "Verbal", "Somatic"], True),
            ("components", ["V", "Material"], False),
            ("components", ["Material", "Material"], False),
            ("components", "Material", False),
            ("material", "", False),
            ("material", " ", False),
            ("source", None, True),
            ("source", 42, False),
            ("source", "", False),
            ("content_tags", ["Warding", "Utility"], True),
            ("content_tags", ["Warding", "Warding"], False),
            ("content_tags", [""], False),
            ("content_tags", "Warding", False),
            ("image", None, True),
            ("image", "assets/salt-ward.webp", True),
            ("image", "", False),
            ("url", None, True),
            ("url", "https://example.org/salt-ward", True),
            ("url", "ftp://example.org/salt-ward", False),
            ("provider_id", 1234, True),
        ],
    )
    def test_values(self, vault: Path, field: str, value: object, valid: bool) -> None:
        enable_extension("dnd-5-5", vault)
        path = self.spell(vault, **{field: value})
        assert validate(path, vault).failed != valid

    @pytest.mark.parametrize(
        "components,material,valid",
        [
            (["Verbal", "Material"], "a pinch of sea salt", True),
            (["Verbal", "Material"], None, False),
            (["Verbal", "Material"], MISSING, False),
            (["Verbal", "Somatic"], None, True),
            (["Verbal", "Somatic"], MISSING, True),
            (["Verbal", "Somatic"], "a pinch of sea salt", False),
            ([], MISSING, True),
        ],
    )
    def test_material_component(
        self, vault: Path, components: list[str], material: object, valid: bool
    ) -> None:
        enable_extension("dnd-5-5", vault)
        path = self.spell(vault, components=components, material=material)
        assert validate(path, vault).failed != valid

    def test_rules_callout(self, vault: Path) -> None:
        enable_extension("dnd-5-5", vault)
        path = self.spell(vault)
        path.write_text(path.read_text().replace("> [!rules]\n>\n", ""))
        assert validate(path, vault).failed

    # The template's null source is valid: unrecorded provenance.
    @pytest.mark.parametrize("missing", [f for f in FIELDS if f != "source"])
    def test_creation_requires_fields(self, vault: Path, missing: str) -> None:
        enable_extension("dnd-5-5", vault)
        fields = {k: v for k, v in self.FIELDS.items() if k != missing}
        if missing == "material":
            fields["components"] = ["Verbal", "Material"]
        with pytest.raises(ValueError, match="failed validation"):
            add_content("Salt Ward", "Spell", vault, frontmatter=fields)
        assert not (vault / "content/Salt Ward.md").exists()

    def test_removal(self, vault: Path) -> None:
        enable_extension("dnd-5-5", vault)
        path = add_content("Salt Ward", "Spell", vault, frontmatter=self.FIELDS)
        before = path.read_bytes()
        remove_extension("dnd-5-5", vault)
        assert path.read_bytes() == before
        assert [d.rule for d in validate(path, vault).diagnostics] == ["record.subtype"]
