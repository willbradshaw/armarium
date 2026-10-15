"""Paint with OpenAI's image models, through its HTTP API."""

import base64
import json
import os
import re
import urllib.error
import urllib.request
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from armarium.painters import Reference

API = "https://api.openai.com/v1/images"
KEY = "OPENAI_API_KEY"
# Models that paint on a transparent ground, the default first. Each may also
# be named by a dated snapshot, such as gpt-image-2.5-flare-2026-09-08.
MODELS = ("gpt-image-2.5-sunburst", "gpt-image-2.5-flare")
SNAPSHOT = re.compile(r"-\d{4}-\d{2}-\d{2}")
# Input images one edit request may carry.
REFERENCE_LIMIT = 16
SIZE = "1024x1024"
QUALITY = "high"
# Seconds to wait for a response: one request paints every candidate.
TIMEOUT = 600


def _multipart(
    fields: Sequence[tuple[str, str]], files: Sequence["Reference"]
) -> tuple[bytes, str]:
    """Encode a multipart/form-data body.

    Args:
        fields: Text fields, as name and value.
        files: Images, each sent as an image[] part.

    Returns:
        tuple[bytes, str]: The body and its Content-Type header.
    """
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
            f"\r\n\r\n{value}\r\n".encode()
        )
    for file in files:
        filename = file.name.replace('"', "")
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="image[]"; filename="{filename}"\r\n'
            f"Content-Type: {file.media}\r\n\r\n".encode()
            + file.data
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _refusal(exc: urllib.error.HTTPError) -> str:
    """Read why the API refused a request.

    Args:
        exc: The error response.

    Returns:
        str: The status and the API's message, when it sent one.
    """
    try:
        message = json.loads(exc.read())["error"]["message"]
    except ValueError, KeyError, TypeError, OSError:
        message = exc.reason
    return f"OpenAI refused the request ({exc.code}): {message}"


class OpenAI:
    """OpenAI's GPT Image models."""

    default_model = MODELS[0]

    def accepts(self, model: str) -> bool:
        """Say whether a model is one of MODELS or a dated snapshot of one.

        Args:
            model: The model's name.

        Returns:
            bool: Whether the painter can paint with it.
        """
        return any(
            model == name
            or (model.startswith(name) and SNAPSHOT.fullmatch(model[len(name) :]))
            for name in MODELS
        )

    def models(self) -> tuple[str, ...]:
        """List the models offered.

        Returns:
            tuple[str, ...]: MODELS.
        """
        return MODELS

    def reference_limit(self, model: str) -> int:
        """Say how many reference images one request may carry.

        Args:
            model: A model the painter accepts.

        Returns:
            int: REFERENCE_LIMIT, for every model.
        """
        return REFERENCE_LIMIT

    def paint(
        self,
        prompt: str,
        references: Sequence["Reference"],
        *,
        model: str,
        count: int,
        transparent: bool,
    ) -> list[bytes]:
        """Paint candidates in one request.

        Without references the prompt goes to the generations endpoint; with
        them, to the edits endpoint, which paints against input images.

        Args:
            prompt: What to paint.
            references: Images showing the style, at most REFERENCE_LIMIT.
            model: A model the painter accepts.
            count: How many candidates to paint.
            transparent: Paint on a transparent ground; otherwise leave the
                ground to the prompt.

        Returns:
            list[bytes]: Each candidate's PNG bytes.

        Raises:
            ValueError: OPENAI_API_KEY is not set, or the API refused the
                request or answered with something other than images.
            OSError: The API cannot be reached.
        """
        key = os.environ.get(KEY)
        if not key:
            raise ValueError(f"{KEY} is not set")
        fields = [
            ("model", model),
            ("prompt", prompt),
            ("n", str(count)),
            ("size", SIZE),
            ("quality", QUALITY),
            ("output_format", "png"),
        ]
        if transparent:
            fields.append(("background", "transparent"))
        if references:
            body, kind = _multipart(fields, references)
            url = f"{API}/edits"
        else:
            data = dict(fields) | {"n": count}
            body, kind = json.dumps(data).encode(), "application/json"
            url = f"{API}/generations"
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": kind},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                answer = response.read()
        except urllib.error.HTTPError as exc:
            raise ValueError(_refusal(exc)) from exc
        try:
            items = json.loads(answer)["data"]
            return [base64.b64decode(item["b64_json"]) for item in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("OpenAI answered without images") from exc
