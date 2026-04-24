import os


JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
WEBP_RIFF_MAGIC = b"RIFF"
WEBP_WEBP_MAGIC = b"WEBP"
PDF_MAGIC = b"%PDF"


def detect_content_type(data: bytes) -> str | None:
    if data.startswith(JPEG_MAGIC):
        return "image/jpeg"
    if data.startswith(PNG_MAGIC):
        return "image/png"
    if len(data) >= 12 and data[:4] == WEBP_RIFF_MAGIC and data[8:12] == WEBP_WEBP_MAGIC:
        return "image/webp"
    if data.startswith(PDF_MAGIC):
        return "application/pdf"
    return None


def normalize_filename(filename: str | None, fallback: str = "upload") -> str:
    raw = (filename or fallback).strip().replace("\x00", "")
    base = os.path.basename(raw)
    return base[:180] or fallback