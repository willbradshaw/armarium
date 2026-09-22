"""Standalone schema checks; no Armarium runtime or production parser."""

import copy
import json
import unittest
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "vaults/starter/reference/schemas"
MAPPING = {
    "[[types/Content]]": "content",
    "[[types/Clue]]": "clue",
    "[[types/Session]]": "session",
    "[[types/Player]]": "player",
    "[[types/Transcript]]": "transcript",
    "[[Reference]]": "reference",
    "[[Type]]": "type",
    "[[Status]]": "status",
}


def no_retrieval(uri):
    raise AssertionError(f"Unexpected external reference: {uri}")


def normalize(value):
    """Only normalization needed by these trusted committed YAML fixtures."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = {
            name: json.loads((SCHEMAS / f"{name}.schema.json").read_text())
            for name in MAPPING.values()
        }
        cls.validators = {
            name: Draft202012Validator(
                schema,
                format_checker=FormatChecker(),
                registry=Registry(retrieve=no_retrieval),
            )
            for name, schema in cls.schemas.items()
        }
        cls.fixtures = {
            name: json.loads(
                (Path(__file__).parent / "fixtures" / f"{name}.json").read_text()
            )
            for name in MAPPING.values()
        }

    def assert_valid(self, name, record, expected=True):
        errors = list(self.validators[name].iter_errors(record))
        self.assertEqual(not errors, expected, "\n".join(str(e) for e in errors))

    def test_meta_schemas_and_offline_references(self):
        def walk(node, schema):
            if isinstance(node, dict):
                if "$ref" in node:
                    self.assertTrue(node["$ref"].startswith("#/"))
                    target = schema
                    for part in node["$ref"][2:].split("/"):
                        target = target[part.replace("~1", "/").replace("~0", "~")]
                    self.assertIsInstance(target, (dict, bool))
                for value in node.values():
                    walk(value, schema)
            elif isinstance(node, list):
                for value in node:
                    walk(value, schema)

        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(schema)
                walk(schema, schema)

    def test_fixtures(self):
        for name, fixture in self.fixtures.items():
            self.assert_valid(name, fixture["base"])
            for case in fixture["cases"]:
                with self.subTest(schema=name, case=case["name"]):
                    record = copy.deepcopy(fixture["base"])
                    record["frontmatter"].update(case.get("frontmatter", {}))
                    record["body"] = case.get("body", record["body"])
                    self.assert_valid(name, record, case["valid"])

    def test_required_keys_wrong_types_and_custom_fields(self):
        for name, fixture in self.fixtures.items():
            base = fixture["base"]
            for key in ("frontmatter", "body"):
                with self.subTest(schema=name, missing=key):
                    record = copy.deepcopy(base)
                    del record[key]
                    self.assert_valid(name, record, False)
                for value in (None, [], 7):
                    with self.subTest(schema=name, field=key, value=value):
                        record = copy.deepcopy(base)
                        record[key] = value
                        self.assert_valid(name, record, False)
            fm_schema = self.schemas[name]["properties"]["frontmatter"]
            for key in fm_schema["required"]:
                with self.subTest(schema=name, missing_field=key):
                    record = copy.deepcopy(base)
                    del record["frontmatter"][key]
                    self.assert_valid(name, record, False)
            for key in fm_schema["properties"]:
                with self.subTest(schema=name, wrong_type=key):
                    record = copy.deepcopy(base)
                    record["frontmatter"][key] = {"unexpected": True}
                    self.assert_valid(name, record, False)
            record = copy.deepcopy(base)
            record["frontmatter"]["custom"] = {"anything": [None, 1, True]}
            self.assert_valid(name, record)
            record["unexpected"] = 1
            self.assert_valid(name, record, False)

    def test_required_headings_and_order(self):
        for name in ("session", "content"):
            base = self.fixtures[name]["base"]
            headings = [
                line
                for line in base["body"].splitlines()
                if line.startswith(("# ", "## "))
            ]
            for index, heading in enumerate(headings):
                with self.subTest(schema=name, missing=heading):
                    record = copy.deepcopy(base)
                    record["body"] = base["body"].replace(heading + "\n", "", 1)
                    self.assert_valid(name, record, False)
                if index + 1 < len(headings):
                    with self.subTest(schema=name, swapped=heading):
                        record = copy.deepcopy(base)
                        lines = base["body"].splitlines()
                        a, b = lines.index(heading), lines.index(headings[index + 1])
                        lines[a], lines[b] = lines[b], lines[a]
                        record["body"] = "\n".join(lines) + "\n"
                        self.assert_valid(name, record, False)
        for name, fixture in self.fixtures.items():
            record = copy.deepcopy(fixture["base"])
            record["body"] = record["body"].replace("\n", "\r\n")
            self.assert_valid(name, record)

    def test_documented_regex_limits(self):
        for name in ("session", "content", "transcript"):
            record = copy.deepcopy(self.fixtures[name]["base"])
            record["body"] = "```markdown\n" + record["body"] + "\n```\n"
            self.assert_valid(name, record)
        for name in ("session", "content"):
            record = copy.deepcopy(self.fixtures[name]["base"])
            record["body"] += record["body"]
            self.assert_valid(name, record)
        record = copy.deepcopy(self.fixtures["clue"]["base"])
        record["body"] = "## Sessions\n![[missing.base]]\n"
        self.assert_valid("clue", record)

    def test_committed_records(self):
        counts = dict.fromkeys(MAPPING.values(), 0)
        campaign_types = {
            path: set()
            for path in (ROOT / "vaults/example/campaigns").iterdir()
            if path.is_dir()
        }
        for vault in ("starter", "example"):
            for path in (ROOT / "vaults" / vault).rglob("*.md"):
                if "templates" in path.parts:
                    continue
                text = path.read_text()
                if not text.startswith("---\n"):
                    continue
                # Trusted fixture framing only; production parsing belongs to #24.
                frontmatter, body = text[4:].split("\n---\n", 1)
                fm = normalize(yaml.safe_load(frontmatter))
                if "type" not in fm:
                    continue
                with self.subTest(path=str(path.relative_to(ROOT))):
                    self.assertIn(fm["type"], MAPPING)
                    name = MAPPING[fm["type"]]
                    record = json.loads(
                        json.dumps({"frontmatter": fm, "body": body}, allow_nan=False)
                    )
                    self.assert_valid(name, record)
                    counts[name] += 1
                    for campaign, kinds in campaign_types.items():
                        if path.is_relative_to(campaign):
                            kinds.add(name)
        self.assertTrue(all(counts.values()), counts)
        self.assertTrue(campaign_types, "The example must exercise campaign records")
        for campaign, kinds in campaign_types.items():
            with self.subTest(campaign=campaign.name):
                self.assertEqual(kinds, set(MAPPING.values()) - {"type", "status"})

    def test_date_normalization_and_format_assertions(self):
        self.assertIn("uri", FormatChecker.checkers)
        self.assertIn("date", FormatChecker.checkers)
        for scalar in ("2024-02-29", '"2024-02-29"'):
            record = copy.deepcopy(self.fixtures["session"]["base"])
            record["frontmatter"]["date"] = normalize(yaml.safe_load(scalar))
            self.assertEqual(record["frontmatter"]["date"], "2024-02-29")
            self.assert_valid("session", record)
        timestamp = normalize(yaml.safe_load("2026-06-05T12:30:00+02:00"))
        self.assertEqual(timestamp, "2026-06-05T12:30:00+02:00")
        record["frontmatter"]["date"] = timestamp
        self.assert_valid("session", record, False)

    def test_mirrored_schemas_and_references(self):
        for folder in ("schemas", "types", "statuses"):
            starter = ROOT / "vaults/starter/reference" / folder
            example = ROOT / "vaults/example/reference" / folder
            self.assertEqual(
                {p.name for p in starter.iterdir()}, {p.name for p in example.iterdir()}
            )
            for path in starter.iterdir():
                with self.subTest(path=path.name):
                    self.assertEqual(
                        path.read_bytes(), (example / path.name).read_bytes()
                    )


class TestDefinitionSchemas:
    @pytest.mark.parametrize(
        ("vault", "folder", "declared_type", "path"),
        [
            (vault, folder, declared_type, path)
            for vault in ("starter", "example")
            for folder, declared_type in (("types", "Type"), ("statuses", "Status"))
            for path in sorted(
                (ROOT / "vaults" / vault / "reference" / folder).glob("*.md")
            )
        ],
        ids=lambda value: value.name if isinstance(value, Path) else value,
    )
    def test_typed_definition(
        self, vault: str, folder: str, declared_type: str, path: Path
    ) -> None:
        root = ROOT / "vaults" / vault
        text = path.read_text()
        assert text.startswith("---\n")
        metadata, body = text[4:].split("\n---\n", 1)
        frontmatter = yaml.safe_load(metadata)
        assert frontmatter["type"] == f"[[{declared_type}]]"
        schema = json.loads(
            (
                root / "reference/schemas" / f"{declared_type.lower()}.schema.json"
            ).read_text()
        )
        assert (
            list(
                Draft202012Validator(schema).iter_errors(
                    {"frontmatter": frontmatter, "body": body}
                )
            )
            == []
        )
        if folder == "statuses":
            target = root / "reference" / (frontmatter["applies_to"][2:-2] + ".md")
            assert target.is_file()
            target_metadata = target.read_text()[4:].split("\n---\n", 1)[0]
            assert yaml.safe_load(target_metadata)["type"] == "[[Type]]"

    @pytest.mark.parametrize("vault", ["starter", "example"])
    @pytest.mark.parametrize("name", ["Type", "Status"])
    def test_type_definitions_exist(self, vault: str, name: str) -> None:
        path = ROOT / "vaults" / vault / "reference/types" / f"{name}.md"
        assert path.is_file()
        metadata = path.read_text()[4:].split("\n---\n", 1)[0]
        assert yaml.safe_load(metadata)["type"] == "[[Type]]"


if __name__ == "__main__":
    unittest.main()
