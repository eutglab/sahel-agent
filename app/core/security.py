"""Input validation, upload guards, and log sanitisation."""
from __future__ import annotations

import io
import re
from typing import Optional

from app.core.config import settings
from app.core.errors import ToolInputError

# Accepted raster image signatures (magic bytes).
_IMAGE_MAGIC = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"RIFF": "webp",  # followed by 'WEBP' at offset 8; checked below
}

_SECRET_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9_\-]{10,}|api[_-]?key\s*[=:]\s*\S+|bearer\s+[A-Za-z0-9._\-]{10,})",
    re.IGNORECASE,
)


def sniff_image_type(data: bytes) -> Optional[str]:
    """Return an image type string from magic bytes, or None if unrecognised."""
    for magic, kind in _IMAGE_MAGIC.items():
        if data.startswith(magic):
            if kind == "webp":
                return "webp" if data[8:12] == b"WEBP" else None
            return kind
    return None


def validate_image_upload(data: bytes, *, max_mb: Optional[int] = None) -> str:
    """Validate raw uploaded image bytes.

    Returns the detected image type. Raises ``ToolInputError`` on any problem so
    the agent can continue *without* a vision observation rather than crash.
    """
    limit = (max_mb if max_mb is not None else settings.max_upload_mb) * 1024 * 1024
    if not data:
        raise ToolInputError("empty image upload")
    if len(data) > limit:
        raise ToolInputError(
            f"image too large: {len(data) / 1_048_576:.1f} MB (limit {limit / 1_048_576:.0f} MB)"
        )
    kind = sniff_image_type(data)
    if kind is None:
        raise ToolInputError("unsupported image format (expected JPEG, PNG, GIF or WebP)")
    return kind


def load_image_safe(data: bytes):
    """Open bytes with Pillow, verifying integrity. Returns a PIL Image (RGB)."""
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - Pillow is a hard dependency
        raise ToolInputError(f"Pillow not available: {exc}") from exc

    validate_image_upload(data)
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()  # detect truncated/corrupt files
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:  # noqa: BLE001 - any decode error is an input error
        raise ToolInputError(f"could not decode image: {exc}") from exc
    return img


def sanitize_text(value: str, *, max_len: int = 2000) -> str:
    """Trim, cap length, and strip control characters from free text input."""
    if value is None:
        return ""
    cleaned = "".join(ch for ch in str(value) if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return cleaned.strip()[:max_len]


def scrub_secrets(text: str) -> str:
    """Redact anything that looks like a credential before it reaches a log."""
    return _SECRET_PATTERN.sub("<redacted>", str(text))
