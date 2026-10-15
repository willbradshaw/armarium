"""The OpenAI painter sends prompts and reference images to the image API."""

import base64
import email.parser
import email.policy
import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from armarium.painters import Reference
from armarium.painters import openai as module
from armarium.painters.openai import OpenAI, _multipart, _refusal

PAINTER = OpenAI()


def parts(body: bytes, kind: str) -> list[tuple[str, str | None, bytes]]:
    """Split a multipart body into each part's name, filename and bytes."""
    message = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
        f"Content-Type: {kind}\r\n\r\n".encode() + body
    )
    return [
        (
            part.get_param("name", header="content-disposition"),
            part.get_filename(),
            part.get_payload(decode=True),
        )
        for part in message.iter_parts()
    ]


class Response(io.BytesIO):
    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class TestOpenAIAccepts:
    @pytest.mark.parametrize(
        ("model", "expected"),
        [
            ("gpt-image-2.5-sunburst", True),
            ("gpt-image-2.5-flare", True),
            ("gpt-image-2.5-sunburst-2026-09-08", True),
            ("gpt-image-2.5-sunburst-latest", False),
            ("gpt-image-2.5-sunburst-2026-09", False),
            ("gpt-image-2", False),
            ("gpt-image-2-2026-04-21", False),
            ("gpt-image-1", False),
        ],
    )
    def test_offers_only_models_that_paint_transparent(
        self, model: str, expected: bool
    ) -> None:
        assert PAINTER.accepts(model) is expected


class TestOpenAIModels:
    def test_lists_the_default_first(self) -> None:
        assert PAINTER.models() == ("gpt-image-2.5-sunburst", "gpt-image-2.5-flare")
        assert PAINTER.default_model == PAINTER.models()[0]


class TestOpenAIReferenceLimit:
    @pytest.mark.parametrize("model", ["gpt-image-2.5-sunburst", "gpt-image-2.5-flare"])
    def test_is_sixteen(self, model: str) -> None:
        assert PAINTER.reference_limit(model) == 16


class TestMultipart:
    def test_encodes_fields_then_images(self) -> None:
        body, kind = _multipart(
            [("model", "m"), ("prompt", "Paint it.\nWhole.")],
            [
                Reference("a.png", b"\x89PNG\r\n--x", "image/png"),
                Reference('b"c.webp', b"RIFF", "image/webp"),
            ],
        )
        assert kind.startswith("multipart/form-data; boundary=")
        assert parts(body, kind) == [
            ("model", None, b"m"),
            ("prompt", None, b"Paint it.\nWhole."),
            ("image[]", "a.png", b"\x89PNG\r\n--x"),
            ("image[]", "bc.webp", b"RIFF"),
        ]

    def test_each_body_has_its_own_boundary(self) -> None:
        assert _multipart([], [])[1] != _multipart([], [])[1]


class TestRefusal:
    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            (
                b'{"error": {"message": "Invalid model."}}',
                "OpenAI refused the request (400): Invalid model.",
            ),
            (b"<html>", "OpenAI refused the request (400): Bad Request"),
            (b'{"error": "x"}', "OpenAI refused the request (400): Bad Request"),
        ],
    )
    def test_reports_the_status_and_message(self, body: bytes, expected: str) -> None:
        exc = urllib.error.HTTPError(
            "https://x",
            400,
            "Bad Request",
            {},
            io.BytesIO(body),  # type: ignore[arg-type]
        )
        assert _refusal(exc) == expected


class TestOpenAIPaint:
    IMAGES = [b"\x89PNG one", b"\x89PNG two"]

    @pytest.fixture
    def sent(self, monkeypatch: pytest.MonkeyPatch) -> list[urllib.request.Request]:
        requests: list[urllib.request.Request] = []

        def urlopen(request: urllib.request.Request, timeout: float) -> Response:
            assert timeout == module.TIMEOUT
            requests.append(request)
            data = [
                {"b64_json": base64.b64encode(image).decode()} for image in self.IMAGES
            ]
            return Response(json.dumps({"data": data}).encode())

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(module.urllib.request, "urlopen", urlopen)
        return requests

    def test_without_references_asks_the_generations_endpoint(
        self, sent: list[urllib.request.Request]
    ) -> None:
        painted = PAINTER.paint(
            "Paint it.", [], model="gpt-image-2.5-flare", count=2, transparent=True
        )
        assert painted == self.IMAGES
        (request,) = sent
        assert request.full_url == "https://api.openai.com/v1/images/generations"
        assert request.get_header("Authorization") == "Bearer sk-test"
        assert request.get_header("Content-type") == "application/json"
        assert isinstance(request.data, bytes)
        assert json.loads(request.data) == {
            "model": "gpt-image-2.5-flare",
            "prompt": "Paint it.",
            "n": 2,
            "size": "1024x1024",
            "quality": "high",
            "output_format": "png",
            "background": "transparent",
        }

    @pytest.mark.parametrize(
        ("transparent", "background"),
        [(True, [("background", None, b"transparent")]), (False, [])],
    )
    def test_with_references_asks_the_edits_endpoint(
        self,
        sent: list[urllib.request.Request],
        transparent: bool,
        background: list[tuple[str, None, bytes]],
    ) -> None:
        reference = Reference("a.png", b"\x89PNG ref", "image/png")
        PAINTER.paint(
            "Paint it.",
            [reference],
            model="gpt-image-2.5-sunburst",
            count=1,
            transparent=transparent,
        )
        (request,) = sent
        assert request.full_url == "https://api.openai.com/v1/images/edits"
        kind = request.get_header("Content-type")
        assert isinstance(kind, str) and isinstance(request.data, bytes)
        fields: list[tuple[str, Any, bytes]] = [
            ("model", None, b"gpt-image-2.5-sunburst"),
            ("prompt", None, b"Paint it."),
            ("n", None, b"1"),
            ("size", None, b"1024x1024"),
            ("quality", None, b"high"),
            ("output_format", None, b"png"),
        ]
        assert parts(request.data, kind) == [
            *fields,
            *background,
            ("image[]", "a.png", b"\x89PNG ref"),
        ]

    def test_needs_an_api_key(
        self, sent: list[urllib.request.Request], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY")
        with pytest.raises(ValueError, match="OPENAI_API_KEY is not set"):
            PAINTER.paint(
                "Paint it.", [], model="gpt-image-2.5-flare", count=1, transparent=True
            )
        assert sent == []

    def test_reports_a_refusal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def urlopen(request: urllib.request.Request, timeout: float) -> Response:
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                {},  # type: ignore[arg-type]
                io.BytesIO(b'{"error": {"message": "Incorrect API key."}}'),
            )

        monkeypatch.setenv("OPENAI_API_KEY", "sk-bad")
        monkeypatch.setattr(module.urllib.request, "urlopen", urlopen)
        with pytest.raises(
            ValueError, match=r"refused the request \(401\): Incorrect API key"
        ):
            PAINTER.paint(
                "Paint it.", [], model="gpt-image-2.5-flare", count=1, transparent=True
            )

    @pytest.mark.parametrize("answer", [b"<html>", b'{"data": [{}]}', b"{}"])
    def test_reports_an_answer_without_images(
        self, monkeypatch: pytest.MonkeyPatch, answer: bytes
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(
            module.urllib.request, "urlopen", lambda request, timeout: Response(answer)
        )
        with pytest.raises(ValueError, match="OpenAI answered without images"):
            PAINTER.paint(
                "Paint it.", [], model="gpt-image-2.5-flare", count=1, transparent=True
            )

    def test_an_unreachable_api_raises_oserror(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def urlopen(request: urllib.request.Request, timeout: float) -> Response:
            raise urllib.error.URLError("no route")

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(module.urllib.request, "urlopen", urlopen)
        with pytest.raises(OSError, match="no route"):
            PAINTER.paint(
                "Paint it.", [], model="gpt-image-2.5-flare", count=1, transparent=True
            )
