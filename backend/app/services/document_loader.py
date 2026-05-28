import fitz
from fastapi import HTTPException, UploadFile


def _extract_pdf_text(content: bytes) -> str:
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            pages = []
            for page in document:
                try:
                    page_text = page.get_text("text", sort=True)
                except TypeError:
                    page_text = page.get_text("text")
                if page_text.strip():
                    pages.append(page_text.strip())
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read PDF file.") from exc

    text = "\n\n".join(pages).strip()
    if not text:
        raise HTTPException(
            status_code=400,
            detail="PDF contains no extractable text.",
        )
    return text


async def load_document_text(file: UploadFile) -> str:
    content = await file.read()
    filename = file.filename or ""
    if filename.lower().endswith(".pdf"):
        return _extract_pdf_text(content)
    return content.decode("utf-8", errors="ignore").strip()
