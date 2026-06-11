import asyncio
import html
import re
import tempfile
import threading
import zipfile
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Optional

import fitz
from fastapi import HTTPException, UploadFile

from backend.app.core.config import get_settings

try:
    from markitdown import MarkItDown
except ImportError:
    MarkItDown = None  # type: ignore[assignment,misc]

try:
    from llama_parse import LlamaParse
except ImportError:
    LlamaParse = None  # type: ignore[assignment]


MARKITDOWN_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls",
    ".html", ".htm", ".csv", ".json", ".xml",
    ".zip", ".mp3", ".wav", ".m4a",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
}


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


def _convert_with_markitdown(content: bytes, filename: str) -> str:
    if MarkItDown is None:
        raise HTTPException(
            status_code=400,
            detail="markitdown is not installed. Run: pip install 'markitdown[all]'",
        )

    suffix = Path(filename).suffix.lower() or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        tmp_path = tmp.name

    try:
        md = MarkItDown()
        result = md.convert(tmp_path)
        text = result.text_content or ""
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"MarkItDown could not process this {suffix} file.",
        ) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return _clean_extracted_text(text)


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


def _extract_pdf_text(content: bytes, filename: str) -> str:
    parser = get_settings().document_parser

    if parser == "markitdown":
        return _convert_with_markitdown(content, filename)

    if parser == "llama_parse":
        return _extract_pdf_markdown_with_llama_parse(content)

    text = _extract_document_text(content, "pdf")
    if not text:
        raise HTTPException(
            status_code=400,
            detail="PDF contains no extractable text.",
        )
    return text


def _extract_pdf_markdown_with_llama_parse(content: bytes) -> str:
    settings = get_settings()
    if not settings.llama_cloud_api_key:
        raise HTTPException(
            status_code=400,
            detail="LLAMA_CLOUD_API_KEY is required when DOCUMENT_PARSER=llama_parse.",
        )
    if LlamaParse is None:
        raise HTTPException(
            status_code=400,
            detail="llama-parse is not installed. Install it before using DOCUMENT_PARSER=llama_parse.",
        )

    with tempfile.NamedTemporaryFile(suffix=".pdf") as temporary_file:
        temporary_file.write(content)
        temporary_file.flush()
        parser = LlamaParse(
            api_key=settings.llama_cloud_api_key,
            result_type="markdown",
        )
        documents = _run_llama_parse(parser, temporary_file.name)

    markdown_parts = [_document_to_markdown(document) for document in documents]
    return _clean_extracted_text("\n\n".join(part for part in markdown_parts if part))


def _run_llama_parse(parser: object, file_path: str) -> list[object]:
    if hasattr(parser, "aload_data"):
        return _run_coroutine_sync(parser.aload_data(file_path))  # type: ignore[attr-defined]
    if hasattr(parser, "load_data"):
        return parser.load_data(file_path)  # type: ignore[attr-defined]
    raise HTTPException(status_code=400, detail="Configured LlamaParse parser cannot load PDFs.")


def _run_coroutine_sync(coroutine: object) -> list[object]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)  # type: ignore[arg-type]

    result: list[object] = []
    error: list[BaseException] = []

    def runner() -> None:
        try:
            result.extend(asyncio.run(coroutine))  # type: ignore[arg-type]
        except BaseException as exc:
            error.append(exc)

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    if error:
        raise error[0]
    return result


def _document_to_markdown(document: object) -> str:
    text = getattr(document, "text", None)
    if isinstance(text, str):
        return text
    text_resource = getattr(document, "text_resource", None)
    resource_text = getattr(text_resource, "text", None)
    if isinstance(resource_text, str):
        return resource_text
    return str(document)


def _extract_epub_text(content: bytes) -> str:
    settings = get_settings()
    if settings.document_parser == "markitdown" and MarkItDown is not None:
        text = _convert_with_markitdown(content, "document.epub")
        if text and not _looks_like_raw_epub(content, text):
            return text

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
    suffix = Path(lower_filename).suffix

    if lower_filename.endswith(".pdf"):
        return _ensure_readable_text(_extract_pdf_text(content, filename))

    if lower_filename.endswith(".epub"):
        return _ensure_readable_text(_extract_epub_text(content))

    if suffix in MARKITDOWN_EXTENSIONS and get_settings().document_parser == "markitdown":
        text = _convert_with_markitdown(content, filename)
        if text:
            return _ensure_readable_text(text)

    if lower_filename.endswith((".md", ".txt", ".text")):
        return _ensure_readable_text(content.decode("utf-8", errors="ignore"))

    if get_settings().document_parser == "markitdown" and MarkItDown is not None:
        text = _convert_with_markitdown(content, filename)
        if text:
            return _ensure_readable_text(text)

    return _ensure_readable_text(content.decode("utf-8", errors="ignore"))


async def load_document_text(file: UploadFile) -> str:
    return load_document_content(await file.read(), file.filename or "")
