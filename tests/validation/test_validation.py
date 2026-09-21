"""Validator regressions and the separate distribution contract for starter/."""

from collections.abc import Iterable
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from validation import validate_vault
from validation.parsing import Diagnostic, parse_page

type Replacements = Iterable[tuple[str, str]]


class VaultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="armarium tests ")
        self.addCleanup(self.temp.cleanup)
        self.vault = Path(self.temp.name) / "vault with spaces"
        (ROOT / "starter").copy(self.vault)

    def write(self, path: str, text: str) -> Path:
        target = self.vault / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def template(self, kind: str, path: str, replacements: Replacements = ()) -> Path:
        text = (self.vault / "templates" / f"{kind}.md").read_text()
        for old, new in replacements:
            text = text.replace(old, new)
        return self.write(path, text)

    def errors(self) -> list[Diagnostic]:
        return validate_vault(self.vault)

    def assertRule(self, rule: str, path: str | None = None, field: str | None = None) -> None:
        errors = self.errors()
        self.assertTrue(any(e.rule == rule and (path is None or e.path == path) and
                            (field is None or e.field == field) for e in errors),
                        "\n".join(map(str, errors)))

    def snapshot(self) -> dict[str, bytes]:
        return {p.relative_to(self.vault).as_posix(): p.read_bytes()
                for p in self.vault.rglob("*") if p.is_file()}

    def cli(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(ROOT / "scripts/validate_vault.py"), str(path)],
                              cwd=self.temp.name, text=True, capture_output=True)

    def session(self) -> Path:
        return self.template("Session", "campaign_1/sessions/S-1-001.md", [
            ("session_number:", "session_number: 1"), ("aliases:\n  -", "aliases: []")])

    def test_starter_copy_cli_read_only_and_external_cwd(self) -> None:
        self.assertEqual(validate_vault(ROOT / "starter"), [])
        before = self.snapshot()
        self.assertEqual(self.errors(), [])
        result = self.cli(self.vault)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_populated_entities_and_links(self) -> None:
        self.session()
        self.write("campaign_1/players/Alex.md", '---\ntype: "[[types/Player]]"\n---\n')
        self.template("Location", "world/locations/Île aux vents.md")
        for kind, folder in (("NPC", "npcs"), ("Faction", "factions"), ("Lore", "lore"),
                             ("Object", "objects"), ("PC", "pcs")):
            self.template(kind, f"campaign_1/{folder}/{kind} record.md", [
                ('summary: ""', 'summary: A known fact'),
                ('stats:\n', 'stats:\n  system: custom\n  strength: 3\n'),
                ('birth_year:\n', 'birth_year: Before the long winter\n'),
                ('aliases:\n', 'aliases: [Old name]\n'),
                ('members:\n', 'members: ["[[campaign_1/npcs/NPC record]]"]\n'),
                ('player:\n', 'player: "[[campaign_1/players/Alex]]"\n'),
                ('pronouns:\n', 'pronouns: they/them\n'),
                ('held_by:\n', 'held_by: "[[campaign_1/pcs/PC record]]"\n'),
                ('first_session:\n', 'first_session: "[[campaign_1/sessions/S-1-001]]"\n'),
                ('type:', 'custom_property: {anything: [1, true]}\ntype:')])
        self.template("Clue", "campaign_1/clues/C-1-0001.md", [
            ('text: ""', 'text: The gate is open'),
            ('subjects:\n', 'subjects: ["[[world/locations/Île aux vents]]"]\n')])
        self.write("assets/map image.png", "asset")
        self.write("Travel notes.md", '[[world/locations/Île aux vents.md#Port|The island]]\n'
                   '[[Île aux vents#^block]] [[#Local]] [[#^local]] ![[assets/map image.png]]\n'
                   '| Place |\n| --- |\n| [[world/locations/Île aux vents\\|Island]] |\n')
        self.assertEqual(self.errors(), [])

    def test_campaign_ids_beyond_one(self) -> None:
        shutil.copytree(self.vault / "campaign_1", self.vault / "campaign_27")
        self.template("Session", "campaign_27/sessions/S-27-003.md", [
            ("campaign_1", "campaign_27"), ("session_number:", "session_number: 3"),
            ("aliases:\n  -", "aliases: []")])
        self.template("NPC", "campaign_27/npcs/Person.md", [("campaign_1", "campaign_27")])
        self.assertEqual(self.errors(), [])

    def test_empty_values_and_root_entities(self) -> None:
        self.template("NPC", "Root person.md")
        self.template("Faction", "world/factions/Empty group.md", [("members:", "members: []")])
        self.template("Location", "world/locations/Place.md", [("parent_location:", 'parent_location: "[[world/locations/Other]]"')])
        self.template("Location", "world/locations/Other.md")
        self.write("extra folder/Journal.md", "Ordinary prose, no entity metadata.\n")
        self.assertEqual(self.errors(), [])

    def test_hidden_symlinks_and_gitkeep_ignored(self) -> None:
        self.write(".scratch/bad.md", "[[Missing]]")
        self.write(".git/bad.md", "[[Missing]]")
        self.write("extra/.cache/bad.md", "[[Missing]]")
        external = Path(self.temp.name) / "outside"
        external.mkdir()
        (external / "bad.md").write_text("[[Missing]]")
        (self.vault / "outside").symlink_to(external, target_is_directory=True)
        (self.vault / "bad.md").symlink_to(external / "bad.md")
        self.assertEqual(self.errors(), [])
        self.write("links.md", "[[outside/bad]]")
        self.assertRule("link.missing")

    def test_unused_directories_are_optional(self) -> None:
        for directory in ("world/npcs", "campaign_1/sessions", "assets", "reference"):
            with self.subTest(directory=directory):
                shutil.rmtree(self.vault / directory)
                self.assertEqual(self.errors(), [])

    def test_starter_distribution_includes_promised_folders(self) -> None:
        # Packaging promise for our starter, not a requirement on user vaults.
        shared = ("locations", "npcs", "factions", "lore", "objects")
        campaign = shared + ("pcs", "players", "sessions", "clues", "transcripts", "index")
        required = {"world", "templates", "types", "statuses", "reference", "assets"}
        required.update(f"world/{folder}" for folder in shared)
        required.update(f"campaign_1/{folder}" for folder in campaign)
        for directory in sorted(required):
            with self.subTest(directory=directory):
                self.assertTrue((ROOT / "starter" / directory).is_dir())

    def test_yaml_errors_survive_discovery_and_scan_continues(self) -> None:
        for name, content, rule in (
            ("syntax", 'type: [unclosed', "yaml.syntax"),
            ("duplicate", 'type: 1\ntype: 2', "yaml.duplicate"),
            ("nested", 'custom:\n  a: 1\n  a: 2', "yaml.duplicate"),
            ("list", '- item', "yaml.mapping"),
            ("date", 'date: 2026-99-99', "yaml.syntax"),
        ):
            with self.subTest(name=name):
                path = f"campaign_1/npcs/{name}.md"
                self.write(path, f"---\n{content}\n---\n")
                self.assertRule(rule, path)
        self.write("reference/open.md", "---\nkey: value")
        self.assertRule("yaml.syntax", "reference/open.md")
        self.write("reference/broken.md", "[[No such page]]")
        self.assertRule("link.missing", "reference/broken.md")
        before = self.snapshot()
        result = self.cli(self.vault)
        self.assertEqual(result.returncode, 1)
        self.assertIn("[yaml.duplicate]", result.stdout)
        self.assertIn("reference/broken.md:1: [link.missing]", result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_duplicate_reports_line(self) -> None:
        _, errors = parse_page("note.md", "---\na: 1\na: 2\n---\n")
        self.assertEqual(errors[0].line, 3)

    def test_missing_type_and_required_fields(self) -> None:
        self.write("world/npcs/Person.md", "No properties")
        self.assertRule("field.required", "world/npcs/Person.md", "type")
        for kind, field in (("NPC", "stats"), ("NPC", "birth_year"), ("NPC", "aliases"),
                            ("Location", "parent_location"), ("PC", "player"), ("PC", "pronouns"),
                            ("Faction", "members"), ("Lore", "summary"), ("Clue", "subjects"),
                            ("Session", "date")):
            with self.subTest(kind=kind, field=field):
                path = f"templates/{kind}.md"
                original = (self.vault / path).read_text()
                self.write(path, '\n'.join(line for line in original.splitlines() if not line.startswith(field + ':')) + '\n')
                self.assertRule("field.required", path, field)
                self.write(path, original)

    def test_known_field_shapes(self) -> None:
        cases = {"summary": "[]", "aliases": "text", "stats": "[]", "birth_year": "true",
                 "pronouns": "{}", "members": "text", "subjects": "{}", "players_absent": "false",
                 "date": "[]", "in_game_start_date": "{}", "session_number": "true",
                 "campaign_1": "null"}
        for field, value in cases.items():
            with self.subTest(field=field):
                self.write("reference/Bad.md", f"---\n{field}: {value}\n---\n")
                self.assertRule("field.shape", "reference/Bad.md", field)
        for field in ("parent_location", "player", "held_by", "first_session", "last_session"):
            with self.subTest(field=field):
                self.write("reference/Bad.md", f"---\n{field}: 123\n---\n")
                self.assertRule("field.link", "reference/Bad.md", field)

    def test_campaign_state_fields(self) -> None:
        path = "templates/Object.md"
        self.template("Object", "Object backup.md")
        original = (self.vault / path).read_text()
        for field in ("held_by", "first_session", "last_session"):
            with self.subTest(field=field):
                self.write(path, original.replace(f"  {field}:\n", ""))
                self.assertRule("field.required", path, "campaign_1." + field)
        self.write(path, original.replace("campaign_1:", "campaign_99:"))
        self.assertRule("identity.campaign", path)
        self.write(path, original.replace("  held_by:", "  held_by: []"))
        self.assertRule("field.link", path, "campaign_1.held_by")

    def test_link_resolution_failures(self) -> None:
        self.write("extra/One.md", '---\naliases: [Nickname]\n---\n')
        for link, rule, explanation in (("[[Absent]]", "link.missing", "Absent"),
                ("[[NPC]]", "link.ambiguous", "types/NPC.md"),
                ("[[Nickname]]", "link.alias", "extra/One.md"),
                ("[[../outside]]", "link.path", "relative")):
            with self.subTest(link=link):
                self.write("reference/Links.md", link)
                self.assertRule(rule, "reference/Links.md")
                self.assertTrue(any(explanation in e.message for e in self.errors()))
        self.write("reference/Links.md", "[[extra/One|Nickname]]")
        self.assertEqual(self.errors(), [])

    def test_link_kinds_and_status_applicability(self) -> None:
        for field, link in (("type", "templates/NPC"), ("player", "types/Player"),
                            ("parent_location", "campaign_1/Campaign"), ("first_session", "templates/Session"),
                            ("applies_to", "templates/Clue")):
            with self.subTest(field=field):
                self.write("reference/Bad.md", f'---\n{field}: "[[{link}]]"\n---\n')
                self.assertRule("link.kind", "reference/Bad.md", field)
        self.write("statuses/Pending.md", '---\napplies_to: "[[types/NPC]]"\n---\n')
        self.assertRule("status.applicability", "templates/Clue.md")
        self.template("Clue", "campaign_1/clues/C-1-0001.md", [
            ('[[statuses/Pending]]', '[[types/Clue]]')])
        self.assertRule("link.kind", "campaign_1/clues/C-1-0001.md", "status")

    def test_malformed_and_table_links(self) -> None:
        for text, rule in (("[[types/NPC]", "link.syntax"), ("[[ ]]", "link.syntax"),
                           ("| [[types/NPC|Person]] |", "link.table-pipe")):
            with self.subTest(text=text):
                self.write("reference/Bad.md", text)
                self.assertRule(rule, "reference/Bad.md")

    def test_code_examples_versus_executable_links(self) -> None:
        self.write("reference/Code.md", '```markdown\n[[Missing example]]\n```\n'
                   '~~~text\n[[Missing example]]\n~~~\n`[[Missing inline example]]`\n'
                   '```dataview\nWHERE type = [[types/NPC]]\n```\n'
                   '`= [[types/NPC]]`\n')
        self.assertEqual(self.errors(), [])
        for text in ('```dataview\nWHERE x = [[Missing]]\n```',
                     '```dataviewjs\ndv.page("[[Missing]]")\n```',
                     '`= [[Missing]]`', '`$= [[Missing]]`'):
            with self.subTest(text=text):
                self.write("reference/Code.md", text)
                self.assertRule("link.missing", "reference/Code.md")

    def test_body_missing_order_and_nested_content(self) -> None:
        path = "templates/NPC.md"
        original = (self.vault / path).read_text()
        self.write(path, original.replace("## Notes", "### Notes"))
        self.assertRule("body.section", path)
        self.write(path, original[:original.index("## Notes")] + "## Appearances\n## Notes\n## Active Clues\n")
        self.assertRule("body.order", path)
        self.write(path, original.replace("## Notes", "## Notes\n### Custom nested content\nDetails"))
        self.assertEqual(self.errors(), [])
        self.template("Session", "templates/Session.md", [("# Preparation", "# Prep")])
        self.assertRule("body.section", "templates/Session.md")

    def test_identity_and_placement(self) -> None:
        self.session()
        for kind, path, rule in (("Clue", "campaign_1/clues/Wrong.md", "identity.filename"),
                ("Clue", "campaign_1/clues/C-2-0001.md", "identity.campaign"),
                ("Session", "campaign_1/sessions/S-1-002.md", "identity.session-number"),
                ("PC", "world/npcs/Person.md", "structure.placement"),
                ("NPC", "campaign_1/locations/Person.md", "structure.placement"),
                ("Clue", "Root clue.md", "identity.campaign")):
            with self.subTest(path=path):
                self.template(kind, path)
                self.assertRule(rule, path)
                (self.vault / path).unlink()
        self.template("Session", "campaign_1/sessions/S-1-002.md", [
            ("session_number:", "session_number: 1"), ("aliases:\n  -", "aliases: []")])
        self.assertRule("identity.session-number", "campaign_1/sessions/S-1-002.md")

    def test_actual_session_empty_alias_item_is_invalid(self) -> None:
        self.template("Session", "campaign_1/sessions/S-1-001.md", [("session_number:", "session_number: 1")])
        self.assertRule("field.shape", "campaign_1/sessions/S-1-001.md", "aliases")

    def test_cross_campaign_identity(self) -> None:
        shutil.copytree(self.vault / "campaign_1", self.vault / "campaign_2")
        self.session()
        self.template("Session", "campaign_2/sessions/S-2-001.md", [
            ("session_number:", "session_number: 1"), ("aliases:\n  -", "aliases: []")])
        self.assertRule("identity.campaign", "campaign_2/sessions/S-2-001.md", "campaign")
        self.template("NPC", "campaign_2/npcs/Person.md")
        self.assertRule("identity.campaign", "campaign_2/npcs/Person.md", "campaign_2")
        self.template("Clue", "campaign_2/clues/C-2-0001.md", [
            ("first_session:", 'first_session: "[[campaign_1/sessions/S-1-001]]"')])
        self.assertRule("identity.campaign", "campaign_2/clues/C-2-0001.md", "first_session")
        self.template("NPC", "templates/NPC.md", [
            ("campaign_1:", "campaign_2:"),
            ("first_session:", 'first_session: "[[campaign_1/sessions/S-1-001]]"')])
        self.assertRule("identity.campaign", "templates/NPC.md", "campaign_2.first_session")

    def test_templates_definitions_and_session_order(self) -> None:
        original = (self.vault / "templates/Session.md").read_text()
        self.write("templates/Session.md", original.replace('type: "[[types/Session]]"\n', ""))
        self.assertRule("field.required", "templates/Session.md", "type")
        self.write("templates/Session.md", original.replace("## Preamble", "## Temporary").replace(
            "## Events", "## Preamble").replace("## Temporary", "## Events"))
        self.assertRule("body.order", "templates/Session.md")
        self.write("statuses/Pending.md", "A status without applicability")
        self.assertRule("field.required", "statuses/Pending.md", "applies_to")

    def test_link_lists_and_type_must_be_canonical(self) -> None:
        for content, rule, field in (
                ('type: null', "field.link", "type"),
                ('members: [null]', "field.link", "members[0]"),
                ('subjects: ["[[types/NPC]]"]', "link.kind", "subjects[0]"),
                ('aliases: [123]', "field.shape", "aliases"),
                ('campaign: 123', "field.link", "campaign"),
                ('status: "[[templates/Clue]]"', "link.kind", "status")):
            with self.subTest(content=content):
                self.write("reference/Bad.md", f"---\n{content}\n---\n")
                self.assertRule(rule, "reference/Bad.md", field)

    def test_invalid_encoding_does_not_stop_scan(self) -> None:
        (self.vault / "reference/Bad.md").write_bytes(b"\xff")
        self.write("reference/Broken.md", "[[Missing]]")
        self.assertRule("io.read", "reference/Bad.md")
        self.assertRule("link.missing", "reference/Broken.md")

    def test_invalid_root_cli(self) -> None:
        result = self.cli(self.vault / "nonexistent")
        self.assertEqual(result.returncode, 1)
        self.assertIn("[structure.root]", result.stdout)


class UserVaultTests(unittest.TestCase):
    """Handwritten populated fixtures independent of starter files/templates."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="populated user vault ")
        self.addCleanup(temporary.cleanup)
        self.vault = Path(temporary.name) / "My setting"
        (ROOT / "tests/validation/fixtures/populated").copy(self.vault)

    def test_populated_vault_without_starter_layout(self) -> None:
        self.assertFalse((self.vault / "templates").exists())
        self.assertFalse((self.vault / "campaign_1").exists())
        self.assertEqual(validate_vault(self.vault), [])
        before = {p.relative_to(self.vault): p.read_bytes()
                  for p in self.vault.rglob("*") if p.is_file()}
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_vault.py"), str(self.vault)],
            cwd=self.vault.parent, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        after = {p.relative_to(self.vault): p.read_bytes()
                 for p in self.vault.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_shared_world_without_any_campaigns(self) -> None:
        # Retain only a type and a shared NPC which has no campaign state.
        for path in tuple(self.vault.iterdir()):
            if path.name not in {"types", "world"}:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        shutil.rmtree(self.vault / "world/objects")
        self.assertEqual(validate_vault(self.vault), [])

    def test_real_records_still_require_valid_data(self) -> None:
        cases = (
            ("world/npcs/Élan the guide.md", "summary: A river guide.\n", "", "field.required"),
            ("world/objects/Compass.md", "campaign_72:", "campaign_99:", "identity.campaign"),
            ("campaign_27/sessions/S-27-003.md", "session_number: 3", "session_number: 4", "identity.session-number"),
            ("campaign_27/clues/C-27-0012.md", "[[statuses/Proposed]]", "[[Missing status]]", "link.missing"),
            ("Travel journal.md", "[[#Local notes]]", "[[Missing note]]", "link.missing"),
        )
        for path, old, new, rule in cases:
            with self.subTest(path=path, rule=rule):
                target = self.vault / path
                original = target.read_text()
                target.write_text(original.replace(old, new))
                errors = validate_vault(self.vault)
                self.assertTrue(any(error.path == path and error.rule == rule for error in errors))
                target.write_text(original)

    def test_campaign_entity_needs_its_own_state(self) -> None:
        source = self.vault / "world/npcs/Élan the guide.md"
        target = self.vault / "campaign_27/npcs/Élan the guide.md"
        target.parent.mkdir()
        source.copy(target)
        errors = validate_vault(self.vault)
        self.assertTrue(any(
            error.path == "campaign_27/npcs/Élan the guide.md"
            and error.rule == "identity.campaign" and error.field == "campaign_27"
            for error in errors
        ))


if __name__ == "__main__":
    unittest.main()
