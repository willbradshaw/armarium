"""Painters are found by the models they offer."""

import pytest

from armarium.painters import PAINTERS, Reference, find_painter
from armarium.painters.openai import OpenAI


class TestReference:
    def test_holds_an_image(self) -> None:
        reference = Reference("a.png", b"png", "image/png")
        assert (reference.name, reference.data, reference.media) == (
            "a.png",
            b"png",
            "image/png",
        )


class TestFindPainter:
    @pytest.mark.parametrize(
        ("model", "expected"),
        [
            (None, "gpt-image-2.5-sunburst"),
            ("gpt-image-2.5-flare", "gpt-image-2.5-flare"),
            ("gpt-image-2.5-flare-2026-09-08", "gpt-image-2.5-flare-2026-09-08"),
        ],
    )
    def test_finds_the_painter_that_offers_the_model(
        self, model: str | None, expected: str
    ) -> None:
        painter, chosen = find_painter(model)
        assert (isinstance(painter, OpenAI), chosen) == (True, expected)

    @pytest.mark.parametrize("model", ["gpt-image-2", "gpt-image-1", "dall-e-3", ""])
    def test_refuses_a_model_no_painter_offers(self, model: str) -> None:
        with pytest.raises(
            ValueError,
            match=(
                f"no painter offers model {model}; choose one of "
                "gpt-image-2.5-sunburst, gpt-image-2.5-flare"
            ),
        ):
            find_painter(model)


class TestPainters:
    def test_the_first_painter_supplies_the_default(self) -> None:
        assert PAINTERS[0].default_model == "gpt-image-2.5-sunburst"
