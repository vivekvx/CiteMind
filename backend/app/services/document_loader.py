from fastapi import UploadFile


async def load_document_text(file: UploadFile) -> str:
    content = await file.read()
    return content.decode("utf-8", errors="ignore").strip()
