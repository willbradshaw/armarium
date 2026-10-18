"""Deleting a record refuses while links remain, or turns them into text."""

import shutil
from pathlib import Path

import pytest

from armarium.delete import StillLinked, delete
from armarium.trace import Reference
from armarium.validate import validate

EXAMPLE = Path(__file__).resolve().parents[1] / "vaults/example"


@pytest.fixture
def example(tmp_path: Path) -> Path:
    root = tmp_path.resolve() / "example"
    shutil.copytree(EXAMPLE, root)
    return root


def files(root: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}


class TestStillLinked:
    @pytest.mark.parametrize(
        ("count", "expected"),
        [(1, "1 link to a.md remains; "), (2, "2 links to a.md remain; ")],
    )
    def test_message(self, count: int, expected: str) -> None:
        references = [Reference("b.md", "", line) for line in range(count)]
        error = StillLinked("a.md", references)
        assert str(error).startswith(expected)
        assert "--unlink" in str(error)
        assert error.references == references
        assert error.details == [reference.text for reference in references]


class TestDelete:
    def test_unlinked_record(self, example: Path) -> None:
        path = example / "notes/Spare.md"
        path.write_text('---\ntype: "[[types/Note]]"\n---\n')
        plan = delete(path)
        assert [c.output for c in plan.changes] == ["notes/Spare.md\t\t\tdeleted"]
        assert plan.files.deletes == {path} and plan.files.writes == {}
        plan.files.apply()
        assert not path.exists()

    def test_refuses_while_links_remain(self, example: Path) -> None:
        before = files(example)
        with pytest.raises(StillLinked) as exc:
            delete(Path("content/Wake-lark.md"), example)
        assert Reference("content/Captain Mara Vey.md", "summary", 0) in (
            exc.value.references
        )
        assert files(example) == before

    def test_unlink(self, example: Path) -> None:
        plan = delete(Path("content/Wake-lark.md"), example, unlink=True)
        assert plan.changes[0].output == "content/Wake-lark.md\t\t\tdeleted"
        plan.files.apply()
        mara = (example / "content/Captain Mara Vey.md").read_text()
        assert "captain of Wake-lark who" in mara
        assert "[[Wake-lark" not in mara
        assert not (example / "content/Wake-lark.md").exists()

    def test_unlink_a_session(self, example: Path) -> None:
        session = example / "campaigns/campaign_1/sessions/S-1-002.md"
        delete(session, unlink=True).files.apply()
        chart = (example / "campaigns/campaign_1/content/Shoal Chart.md").read_text()
        assert "  first_session:\n  last_session:\n" in chart
        assert chart.endswith("## Appearances\n\n- N/A\n")
        mara = (example / "content/Captain Mara Vey.md").read_text()
        assert 'last_session: "[[S-1-001]]"' in mara
        assert "[[S-1-002]]" not in mara
        failures = {
            d.path for d in validate(example).diagnostics if d.severity == "error"
        }
        assert failures == {
            "campaigns/campaign_1/sessions/transcripts/S-1-002 Transcript.md"
        }

    def test_notes_the_image(self, example: Path) -> None:
        path = example / "notes/Spare.md"
        path.write_text('---\ntype: "[[types/Note]]"\nimage: assets/a.png\n---\n')
        assert delete(path).notes == [
            "notes/Spare.md: its image assets/a.png is left in place"
        ]

    @pytest.mark.parametrize(
        "image", ["https://example.com/a.png", "HTTP://example.com/a.png", "", "null"]
    )
    def test_no_note_without_an_image_file(self, example: Path, image: str) -> None:
        path = example / "notes/Spare.md"
        path.write_text(f'---\ntype: "[[types/Note]]"\nimage: {image}\n---\n')
        assert delete(path).notes == []

    @pytest.mark.parametrize(
        ("relative", "message"),
        [
            ("reference/types/Note.md", "is a Type record"),
            ("reference/statuses/Pending.md", "is a Status record"),
            ("campaigns/campaign_1/reference/Campaign.md", "every campaign requires"),
            ("content/Nobody.md", "does not exist"),
        ],
    )
    def test_refuses(self, example: Path, relative: str, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            delete(Path(relative), example, unlink=True)
