from __future__ import annotations

import pytest

from app.core.errors import ToolInputError
from app.core.security import sanitize_text, scrub_secrets, sniff_image_type, validate_image_upload

PNG_1PX = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_sniff_image_type_png():
    assert sniff_image_type(PNG_1PX) == "png"
    assert sniff_image_type(b"not an image") is None


def test_validate_image_rejects_large(monkeypatch):
    big = b"\xff\xd8\xff" + b"0" * (9 * 1024 * 1024)
    with pytest.raises(ToolInputError):
        validate_image_upload(big, max_mb=8)


def test_validate_image_rejects_unknown_format():
    with pytest.raises(ToolInputError):
        validate_image_upload(b"%PDF-1.4 fake")


def test_scrub_secrets_redacts_keys():
    txt = "calling api with api_key=sk-abcdef1234567890 and Authorization: Bearer abcdef1234567"
    out = scrub_secrets(txt)
    assert "sk-abcdef1234567890" not in out
    assert "<redacted>" in out


def test_sanitize_text_caps_and_strips_control_chars():
    assert sanitize_text("hello\x00world", max_len=100) == "helloworld"
    assert len(sanitize_text("a" * 5000, max_len=100)) == 100
