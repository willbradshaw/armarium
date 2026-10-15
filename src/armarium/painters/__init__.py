"""Image models that paint a record's picture, each behind one interface."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from armarium.painters.openai import OpenAI


@dataclass(frozen=True)
class Reference:
    """An image sent with a prompt to show the style to paint in.

    Attributes:
        name: The image's filename, as the request carries it.
        data: The image's bytes.
        media: The image's media type, such as image/png.
    """

    name: str
    data: bytes
    media: str


class Painter(Protocol):
    """An image model provider that paints candidates on a transparent ground.

    A painter lists only models that can paint on a transparent ground; a
    model that cannot is not offered at all.
    """

    @property
    def default_model(self) -> str:
        """The model used when none is named."""
        ...

    def accepts(self, model: str) -> bool:
        """Say whether the painter offers a model.

        Args:
            model: The model's name.

        Returns:
            bool: Whether the painter can paint with it.
        """
        ...

    def models(self) -> tuple[str, ...]:
        """List the models the painter offers, without dated snapshots.

        Returns:
            tuple[str, ...]: The model names, the default first.
        """
        ...

    def reference_limit(self, model: str) -> int:
        """Say how many reference images one request may carry.

        Args:
            model: A model the painter accepts.

        Returns:
            int: The largest number of references per request.
        """
        ...

    def paint(
        self,
        prompt: str,
        references: Sequence[Reference],
        *,
        model: str,
        count: int,
        transparent: bool,
    ) -> list[bytes]:
        """Paint candidates for one prompt.

        Args:
            prompt: What to paint.
            references: Images showing the style, at most reference_limit.
            model: A model the painter accepts.
            count: How many candidates to paint.
            transparent: Paint on a transparent ground; otherwise on an
                opaque one, as the prompt describes.

        Returns:
            list[bytes]: Each candidate's PNG bytes.

        Raises:
            ValueError: The painter is not configured, or the provider
                refused the request.
            OSError: The provider cannot be reached.
        """
        ...


# Painters in the order they are asked about a model; the first's default
# model is the default.
PAINTERS: tuple[Painter, ...] = (OpenAI(),)


def find_painter(model: str | None = None) -> tuple[Painter, str]:
    """Find the painter that offers a model.

    Args:
        model: The model's name, or None for the first painter's default.

    Returns:
        tuple[Painter, str]: The painter and the model to paint with.

    Raises:
        ValueError: No painter offers the model.
    """
    if model is None:
        return PAINTERS[0], PAINTERS[0].default_model
    for painter in PAINTERS:
        if painter.accepts(model):
            return painter, model
    known = ", ".join(name for painter in PAINTERS for name in painter.models())
    raise ValueError(f"no painter offers model {model}; choose one of {known}")
