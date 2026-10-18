"""Renaming a record rewrites every link to it and keeps the vault valid."""

import shutil
from pathlib import Path

import pytest

from armarium.rename import rename
from armarium.validate import validate

EXAMPLE = Path(__file__).resolve().parents[1] / "vaults/example"


@pytest.fixture
def example(tmp_path: Path) -> Path:
    root = tmp_path.resolve() / "example"
    shutil.copytree(EXAMPLE, root)
    return root


class TestRename:
    def test_renames_and_rewrites_every_link(self, example: Path) -> None:
        plan = rename(Path("content/Port Briselle.md"), "Briselle", example)
        assert plan.changes[0].output == (
            "content/Port Briselle.md\t\t\trenamed to content/Briselle.md"
        )
        assert plan.files.moves == {
            example / "content/Port Briselle.md": example / "content/Briselle.md"
        }
        assert (example / "content/Port Briselle.md").exists()
        plan.files.apply()
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
        plan.files.apply()
        peter = example / "campaigns/campaign_2/reference/players/Peter.md"
        assert '"[[campaign_2/content/Bram Kest]]"' in peter.read_text()
        ellis = example / "campaigns/campaign_1/reference/players/Ellis.md"
        assert '"[[campaign_1/content/Bram Kest]]"' in ellis.read_text()
        assert not validate(example).failed

    def test_case_only(self, example: Path) -> None:
        plan = rename(Path("content/Wake-lark.md"), "Wake-Lark", example)
        plan.files.apply()
        assert "Wake-Lark.md" in [p.name for p in (example / "content").iterdir()]
        assert not validate(example).failed

    def test_record_links_to_itself(self, example: Path) -> None:
        path = example / "content/Wake-lark.md"
        path.write_text(path.read_text() + "\nSee [[Wake-lark#Notes]].\n")
        plan = rename(path, "Lark")
        assert "See [[Lark#Notes]]." in plan.files.read_text(path)

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
