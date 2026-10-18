"""Renaming a record rewrites every link to it and keeps the vault valid."""

import shutil
from pathlib import Path

import pytest

from armarium.parse import Frontmatter
from armarium.rename import check_name, clashes, read_record, rename
from armarium.validate import validate

EXAMPLE = Path(__file__).resolve().parents[1] / "vaults/example"


@pytest.fixture
def example(tmp_path: Path) -> Path:
    root = tmp_path.resolve() / "example"
    shutil.copytree(EXAMPLE, root)
    return root


class TestReadRecord:
    @pytest.mark.parametrize(
        "relative",
        ["content/Captain Mara Vey.md", "notes/Coast design notes.md"],
    )
    def test_record(self, example: Path, relative: str) -> None:
        assert read_record(example, example / relative).type in {"Content", "Note"}

    @pytest.mark.parametrize(
        ("relative", "message"),
        [
            ("assets/handouts/.gitkeep", "is not a record"),
            ("AGENTS.md", "is not a record"),
            ("reference/templates/Content.md", "is not a record"),
            ("reference/types/Content.md", "is a Type record"),
            ("reference/statuses/Pending.md", "is a Status record"),
            ("campaigns/campaign_1/sessions/S-1-001.md", "is a Session record"),
            ("campaigns/campaign_1/clues/C-1-0001.md", "is a Clue record"),
            (
                "campaigns/campaign_1/reference/Campaign.md",
                "is a file every campaign requires",
            ),
            (
                "campaigns/campaign_2/reference/indexes/Clues.md",
                "is a file every campaign requires",
            ),
        ],
    )
    def test_refuses(self, example: Path, relative: str, message: str) -> None:
        path = example / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        with pytest.raises(ValueError, match=message):
            read_record(example, path)

    def test_unparseable(self, example: Path) -> None:
        path = example / "notes/Broken.md"
        path.write_text("---\na: [\n---\n")
        with pytest.raises(ValueError, match="cannot parse notes/Broken.md"):
            read_record(example, path)


class TestCheckName:
    @pytest.mark.parametrize("name", ["Mara", "Wren's Rest", "12 Highsail 312", "É"])
    def test_accepts(self, name: str) -> None:
        check_name(name)

    @pytest.mark.parametrize(
        ("name", "message"),
        [
            ("", "blank"),
            ("  ", "blank"),
            (" Mara", "whitespace"),
            (".Mara", "dot"),
            ("Mara.md", "without .md"),
            *((f"Ma{c}ra", "must not contain") for c in "#^[]|\\/:"),
        ],
    )
    def test_refuses(self, name: str, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            check_name(name)


class TestClashes:
    @pytest.mark.parametrize(
        ("relative", "name", "expected"),
        [
            ("content/Captain Mara Vey.md", "Wake-lark", ["content/Wake-lark.md"]),
            (
                "content/Captain Mara Vey.md",
                "Bram Kest",
                ["campaigns/campaign_2/content/Bram Kest.md"],
            ),
            ("campaigns/campaign_1/content/Esme Calder.md", "Bram Kest", []),
            ("content/Captain Mara Vey.md", "Captain Mara Vey", []),
            ("content/Captain Mara Vey.md", "Nobody", []),
            ("content/Captain Mara Vey.md", "Content", []),
        ],
    )
    def test_clashes(
        self, example: Path, relative: str, name: str, expected: list[str]
    ) -> None:
        path = example / relative
        frontmatter = Frontmatter.parse(path.read_text())[0]
        assert clashes(example, path, name, frontmatter) == expected

    def test_structural_records_take_no_part(self, example: Path) -> None:
        path = example / "reference/Glossary.md"
        path.write_text('---\ntype: "[[Reference]]"\n---\n')
        frontmatter = Frontmatter.parse(path.read_text())[0]
        assert clashes(example, path, "Wake-lark", frontmatter) == []
        mara = example / "content/Captain Mara Vey.md"
        frontmatter = Frontmatter.parse(mara.read_text())[0]
        assert clashes(example, mara, "Glossary", frontmatter) == []

    def test_unparseable_record_counts(self, example: Path) -> None:
        (example / "notes/Gull.md").write_text("---\na: [\n---\n")
        mara = example / "content/Captain Mara Vey.md"
        frontmatter = Frontmatter.parse(mara.read_text())[0]
        assert clashes(example, mara, "Gull", frontmatter) == ["notes/Gull.md"]


class TestRename:
    def test_renames_and_rewrites_every_link(self, example: Path) -> None:
        plan = rename(Path("content/Port Briselle.md"), "Briselle", example)
        assert plan.changes[0].output == (
            "content/Port Briselle.md\t\t\trenamed to content/Briselle.md"
        )
        assert plan.renamed == {
            example / "content/Port Briselle.md": example / "content/Briselle.md"
        }
        assert (example / "content/Port Briselle.md").exists()
        plan.apply()
        assert not (example / "content/Port Briselle.md").exists()
        text = (example / "campaigns/campaign_1/content/Quay Nine.md").read_text()
        assert 'parent_location: "[[Briselle]]"' in text
        assert "[[Briselle|Briselle]]" in text
        assert not validate(example).failed

    def test_lengthens_links_to_a_record_of_another_campaign(
        self, example: Path
    ) -> None:
        esme = example / "campaigns/campaign_1/content/Esme Calder.md"
        plan = rename(esme, "Bram Kest")
        plan.apply()
        peter = example / "campaigns/campaign_2/reference/players/Peter.md"
        assert '"[[campaign_2/content/Bram Kest]]"' in peter.read_text()
        ellis = example / "campaigns/campaign_1/reference/players/Ellis.md"
        assert '"[[campaign_1/content/Bram Kest]]"' in ellis.read_text()
        assert not validate(example).failed

    def test_case_only(self, example: Path) -> None:
        plan = rename(Path("content/Wake-lark.md"), "Wake-Lark", example)
        plan.apply()
        assert "Wake-Lark.md" in [p.name for p in (example / "content").iterdir()]
        assert not validate(example).failed

    def test_record_links_to_itself(self, example: Path) -> None:
        path = example / "content/Wake-lark.md"
        path.write_text(path.read_text() + "\nSee [[Wake-lark#Notes]].\n")
        plan = rename(path, "Lark")
        assert "See [[Lark#Notes]]." in plan.texts[path]

    @pytest.mark.parametrize(
        ("relative", "name", "message"),
        [
            ("content/Wake-lark.md", "Wake-lark", "already has that name"),
            ("content/Wake-lark.md", "Port Briselle", "already exists"),
            (
                "content/Wake-lark.md",
                "quay nine",
                "already a name of campaigns/campaign_1/content/Quay Nine.md",
            ),
            ("content/Wake-lark.md", "a/b", "must not contain"),
            ("reference/types/Content.md", "Thing", "is a Type record"),
            ("content/Nobody.md", "Thing", "does not exist"),
        ],
    )
    def test_refuses(
        self, example: Path, relative: str, name: str, message: str
    ) -> None:
        before = {p: p.read_bytes() for p in example.rglob("*") if p.is_file()}
        with pytest.raises(ValueError, match=message):
            rename(Path(relative), name, example)
        assert before == {p: p.read_bytes() for p in example.rglob("*") if p.is_file()}
