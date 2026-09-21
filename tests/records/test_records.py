# /// script
# requires-python = ">=3.10"
# dependencies = ["PyYAML>=6,<7"]
# ///
"""Focused assertions for the Player/Transcript templates and original fixture."""

from pathlib import Path
import re
import shutil
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixture"


class RecordTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.vault = Path(temporary.name) / "vault"
        shutil.copytree(ROOT / "starter", self.vault)
        shutil.copytree(FIXTURE, self.vault, dirs_exist_ok=True)

    def test_empty_templates(self):
        for kind, field in (("Player", "plays"), ("Transcript", "session")):
            with self.subTest(kind=kind):
                text = (self.vault / "templates" / f"{kind}.md").read_text()
                opening, metadata, body = text.split("---", 2)
                self.assertEqual(opening, "")
                self.assertIn(f'type: "[[types/{kind}]]"', metadata)
                self.assertEqual(yaml.safe_load(metadata), {
                    "type": f"[[types/{kind}]]", field: None,
                })
                # An unused template must not invent targets or utterances.
                self.assertNotIn("[[", body)
                if kind == "Player":
                    self.assertFalse(body.strip())
                else:
                    self.assertEqual(body.split(), ["##", "Recap", "##", "Scene", "##", "Wrap-up"])
                description = (self.vault / "types" / f"{kind}.md").read_text()
                self.assertIn(f"[[templates/{kind}]]", description)

    def test_fixture_yaml_and_links(self):
        records = {}
        for path in sorted(FIXTURE.rglob("*.md")):
            relative = path.relative_to(FIXTURE)
            text = (self.vault / relative).read_text()
            opening, metadata, _ = text.split("---", 2)
            self.assertEqual(opening, "")
            records[str(relative)] = yaml.safe_load(metadata)
            for target in re.findall(r"\[\[([^\]]+)\]\]", text):
                with self.subTest(record=str(relative), target=target):
                    self.assertIn("/", target)
                    self.assertTrue((self.vault / f"{target}.md").is_file())
                    self.assertIn(f'"[[{target}]]"', metadata)
        self.assertEqual(records["campaign_1/players/Example Player.md"], {
            "type": "[[types/Player]]", "plays": ["[[campaign_1/pcs/Mira]]"],
        })
        transcript = records["campaign_1/transcripts/S-1-001 Transcript.md"]
        self.assertEqual(transcript, {
            "type": "[[types/Transcript]]", "session": "[[campaign_1/sessions/S-1-001]]",
        })
        for relative, meta in records.items():
            if meta["type"] == "[[types/Transcript]]":
                session = Path(meta["session"][2:-2])
                campaign = session.parts[0]
                self.assertRegex(session.name, r"^S-\d+-\d{3}$")
                self.assertEqual(campaign, f"campaign_{session.name.split('-')[1]}")
                self.assertEqual(Path(relative), Path(campaign) / "transcripts" / f"{session.name} Transcript.md")

    def test_transcript_content_and_uncertainty(self):
        text = (FIXTURE / "campaign_1/transcripts/S-1-001 Transcript.md").read_text()
        body = text.split("---", 2)[2]
        headings = []
        speakers = set()
        for line in body.splitlines():
            if not line:
                continue
            if line.startswith("## "):
                headings.append(line)
                continue
            self.assertTrue(headings, "Utterance must be under a content heading")
            match = re.fullmatch(r"\[(GM|Mira\??|Player\?|Table)\] \S.*", line)
            self.assertIsNotNone(match, line)
            speakers.add(match[1])
        self.assertEqual(headings, ["## Recap", "## Opening the Observatory", "## Wrap-up"])
        self.assertEqual(speakers, {"GM", "Mira", "Mira?", "Player?", "Table"})
        self.assertIn("three [?].", body)


if __name__ == "__main__":
    unittest.main()
