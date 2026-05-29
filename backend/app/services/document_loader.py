import html
import re
import zipfile
from html.parser import HTMLParser
from io import BytesIO
from typing import Optional

import fitz
from fastapi import HTTPException, UploadFile


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag in {"script", "style", "nav"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data.strip():
            self.parts.append(data.strip())


def _extract_document_text(content: bytes, filetype: str) -> str:
    try:
        with fitz.open(stream=content, filetype=filetype) as document:
            pages = []
            for page in document:
                try:
                    page_text = page.get_text("text", sort=True)
                except TypeError:
                    page_text = page.get_text("text")
                if page_text.strip():
                    pages.append(page_text.strip())
    except Exception as exc:
        label = filetype.upper()
        raise HTTPException(status_code=400, detail=f"Could not read {label} file.") from exc

    text = "\n\n".join(pages).strip()
    return _clean_extracted_text(text)


def _extract_pdf_text(content: bytes) -> str:
    text = _extract_document_text(content, "pdf")
    if not text:
        raise HTTPException(
            status_code=400,
            detail="PDF contains no extractable text.",
        )
    return text


def _extract_epub_text(content: bytes) -> str:
    try:
        text = _extract_document_text(content, "epub")
    except HTTPException:
        text = _extract_epub_text_from_zip(content)

    if _looks_like_raw_epub(content, text):
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable text from EPUB.",
        )
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable text from EPUB.",
        )
    return text


def _extract_epub_text_from_zip(content: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = [
                name
                for name in archive.namelist()
                if name.lower().endswith((".xhtml", ".html", ".htm"))
                and not name.lower().startswith("meta-inf/")
            ]
            pages = []
            for name in sorted(names):
                raw = archive.read(name)
                page = _html_to_text(raw.decode("utf-8", errors="ignore"))
                if page:
                    pages.append(page)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable text from EPUB.",
        ) from exc
    return _clean_extracted_text("\n\n".join(pages))


def _html_to_text(markup: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(markup)
    return _clean_extracted_text(html.unescape(" ".join(parser.parts)))


def _clean_extracted_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def _looks_like_raw_epub(content: bytes, text: str) -> bool:
    stripped = text.lstrip()
    return (
        content.startswith(b"PK")
        and (
            stripped.startswith("PK")
            or "META-INF/container.xml" in stripped
            or "mimetypeapplication/epub+zip" in stripped
        )
    )


def _ensure_readable_text(text: str) -> str:
    cleaned = _clean_extracted_text(text)
    alpha_count = sum(character.isalpha() for character in cleaned)
    if not cleaned or alpha_count / max(len(cleaned), 1) < 0.25:
        raise HTTPException(
            status_code=400,
            detail="No readable text could be extracted from this file.",
        )
    return cleaned


def load_document_content(content: bytes, filename: str) -> str:
    lower_filename = filename.lower()
    if lower_filename.endswith(".pdf"):
        return _ensure_readable_text(_extract_pdf_text(content))
    if lower_filename.endswith(".epub"):
        return _ensure_readable_text(_extract_epub_text(content))
    return _ensure_readable_text(content.decode("utf-8", errors="ignore"))


async def load_document_text(file: UploadFile) -> str:
    return load_document_content(await file.read(), file.filename or "")
