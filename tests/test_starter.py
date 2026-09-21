"""Acceptance tests for the starter installer, not a general vault linter."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts import create_vault


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/create_vault.py"


def metadata(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    return yaml.safe_load(text.split("---", 2)[1])


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class StarterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="armarium-test-")
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.vault = self.parent / "A setting with spaces"

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.vault), *args],
                              cwd=self.parent, capture_output=True, text=True)

    def install(self, campaigns=None):
        return create_vault.install(self.vault, 'The "Lantern": Coast',
                                    campaigns or [("1", "First Campaign")])

    def assert_vault_links_resolve(self):
        for path in self.vault.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            # Ignore fenced syntax examples; inspect real frontmatter and body links.
            text = re.sub(r"(?ms)^```[^\n]*\n.*?^```\s*$", "", text)
            for target in re.findall(r"\[\[([^\]\n]+)\]\]", text):
                target = target.split("|", 1)[0].split("#", 1)[0]
                with self.subTest(page=str(path.relative_to(self.vault)), link=target):
                    self.assertTrue((self.vault / (target + ".md")).is_file())

    def test_cli_installs_from_unrelated_working_directory(self):
        result = self.cli("--name", "A New World")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.vault / "Home.md").is_file())
        self.assertTrue((self.vault / "campaigns/1/Campaign-1.md").is_file())
        self.assertTrue((self.vault / ".obsidian/app.json").is_file())
        self.assertFalse((self.vault / ".git").exists())
        self.assertFalse((self.vault / "scripts").exists())
        self.assertFalse((self.vault / ".agents/skills").exists())
        self.assertFalse(any(p.is_symlink() for p in self.vault.rglob("*")))
        self.assert_vault_links_resolve()

    def test_two_campaigns_and_yaml_safe_names(self):
        result = self.cli("--name", 'World: "Élan" #1',
                          "--campaign", "expedition", 'Survey: "One"',
                          "--campaign", "return", "The Return")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads((self.vault / "armarium.json").read_text())
        self.assertEqual(config["name"], 'World: "Élan" #1')
        self.assertEqual([c["id"] for c in config["campaigns"]], ["expedition", "return"])
        self.assertEqual(metadata(self.vault / "Home.md")["name"], config["name"])
        self.assertEqual(metadata(self.vault / "campaigns/expedition/Campaign-expedition.md")["name"], 'Survey: "One"')
        for path in self.vault.rglob("*.md"):
            value = metadata(path)
            if value is not None:
                self.assertIsInstance(value, dict, str(path))
            self.assertNotRegex(path.read_text(), r"\{\{[A-Z_]+\}\}")
        self.assert_vault_links_resolve()

    def test_numeric_campaign_identity_stays_a_string(self):
        self.install()
        self.assertEqual(metadata(self.vault / "campaigns/1/Campaign-1.md")["id"], "1")

    def test_existing_nonempty_and_empty_destinations_are_untouched(self):
        self.vault.mkdir()
        empty = self.cli("--name", "World")
        self.assertNotEqual(empty.returncode, 0)
        self.assertEqual(list(self.vault.iterdir()), [])
        (self.vault / "important.txt").write_text("Keep my work")
        before = snapshot(self.vault)
        result = self.cli("--name", "World")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, snapshot(self.vault))

    def test_existing_file_and_dangling_symlink_are_rejected(self):
        self.vault.write_text("Do not replace")
        self.assertNotEqual(self.cli("--name", "World").returncode, 0)
        self.assertEqual(self.vault.read_text(), "Do not replace")
        self.vault.unlink()
        self.vault.symlink_to(self.parent / "missing")
        self.assertNotEqual(self.cli("--name", "World").returncode, 0)
        self.assertTrue(self.vault.is_symlink())
        self.assertFalse((self.parent / "missing").exists())

    def test_invalid_input_creates_nothing(self):
        cases = [
            ["--name", "World", "--campaign", "../escape", "Bad"],
            ["--name", "World", "--campaign", "one", "A", "--campaign", "one", "B"],
            ["--name", "World\nInjected"],
            ["--name", "   "],
            ["--name", "World", "--campaign", "A", "Uppercase"],
        ]
        for args in cases:
            with self.subTest(args=args):
                self.assertNotEqual(self.cli(*args).returncode, 0)
                self.assertFalse(self.vault.exists())
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_destination_inside_toolkit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            create_vault.install(ROOT / "should-not-be-created", "World", [("1", "A")])
        self.assertFalse((ROOT / "should-not-be-created").exists())

    def test_missing_parent_is_rejected_without_creating_directories(self):
        with self.assertRaisesRegex(ValueError, "Parent directory"):
            create_vault.install(self.parent / "missing" / "vault", "World", [("1", "A")])
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_destination_created_during_render_is_not_overwritten(self):
        original_copy = shutil.copytree

        def competing_creation(source, destination):
            destination.mkdir()
            (destination / "other-work.txt").write_text("Keep this")
            return original_copy(source, destination)

        with patch.object(create_vault.shutil, "copytree", side_effect=competing_creation):
            with self.assertRaises(FileExistsError):
                self.install()
        self.assertEqual(snapshot(self.vault), {"other-work.txt": b"Keep this"})

    @unittest.skipUnless(shutil.which("git"), "Git required for ignore-policy check")
    def test_vault_can_be_its_own_repository_with_local_inputs_ignored(self):
        self.install()
        subprocess.run(["git", "init", "-q", str(self.vault)], check=True)
        (self.vault / ".input/unprocessed/source.txt").write_text("Private input")
        (self.vault / ".scratch/draft.txt").write_text("Working draft")
        (self.vault / "assets/handouts/map.txt").write_text("Durable handout")
        for path in (".input/unprocessed/source.txt", ".scratch/draft.txt"):
            result = subprocess.run(["git", "-C", str(self.vault), "check-ignore", "-q", path])
            self.assertEqual(result.returncode, 0, path)
        result = subprocess.run(["git", "-C", str(self.vault), "check-ignore", "-q", "assets/handouts/map.txt"])
        self.assertEqual(result.returncode, 1)

    def test_bad_template_fails_before_destination_is_created(self):
        source = self.parent / "bad-starter"
        shutil.copytree(ROOT / "starter", source)
        (source / "vault/bad.md").write_text("{{UNKNOWN_INSTALL_TOKEN}}")
        with patch.object(create_vault, "STARTER", source):
            with self.assertRaisesRegex(ValueError, "Unknown starter"):
                self.install()
        self.assertFalse(self.vault.exists())
        self.assertFalse(list(self.parent.glob(".armarium-starter-*")))

    def test_reproducible_portable_installation_and_customization(self):
        self.install()
        first = snapshot(self.vault)
        second = self.parent / "elsewhere"
        create_vault.install(second, 'The "Lantern": Coast', [("1", "First Campaign")])
        self.assertEqual(first, snapshot(second))
        moved = self.parent / "moved-vault"
        self.vault.rename(moved)
        self.vault = moved
        self.assert_vault_links_resolve()
        (self.vault / "templates/NPC.md").write_text("My custom structure")
        before = snapshot(self.vault)
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(before, snapshot(self.vault))
        for content in first.values():
            self.assertNotIn(str(ROOT).encode(), content)
            self.assertNotIn(str(self.parent).encode(), content)

    def test_example_has_separate_histories_without_candidate_canon(self):
        self.install([("expedition", "The Survey"), ("homecoming", "The Return")])
        shutil.copytree(ROOT / "examples/two-campaigns/content", self.vault, dirs_exist_ok=True)
        self.assert_vault_links_resolve()
        location = self.vault / "world/locations/Old Observatory.md"
        state = metadata(location)["campaigns"]
        self.assertEqual(set(state), {"expedition", "homecoming"})
        self.assertIn("S-expedition-001", state["expedition"]["first_session"])
        self.assertIn("S-homecoming-001", state["homecoming"]["first_session"])
        clue = metadata(self.vault / "campaigns/expedition/clues/C-expedition-0001.md")
        self.assertEqual(clue["status"], "[[statuses/Abandoned]]")
        self.assertIsNone(clue["last_session"])
        self.assertIn("hidden passage", clue["text"])
        self.assertNotIn("hidden passage", location.read_text())
        for path in self.vault.rglob("*.md"):
            data = metadata(path)
            if data is not None:
                self.assertIsInstance(data, dict)


if __name__ == "__main__":
    unittest.main()
