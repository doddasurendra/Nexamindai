"""Document text extraction (PDF, DOCX, XLSX, CSV, TXT, images) with optional OCR."""
from __future__ import annotations

import csv
import io
import shutil
from pathlib import Path
from typing import Any

from ..config import get_settings

settings = get_settings()


def ocr_available() -> bool:
    return shutil.which("tesseract") is not None


def _ocr_image(image) -> str:
    import pytesseract

    return pytesseract.image_to_string(image)


def extract_text(path: Path, filename: str, mime_type: str = "") -> tuple[str, dict[str, Any]]:
    suffix = Path(filename).suffix.lower()
    meta: dict[str, Any] = {"extractor": "", "pages": 0, "ocr": False}

    if suffix == ".pdf" or mime_type == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        meta["pages"] = len(reader.pages)
        meta["extractor"] = "pypdf"
        parts = [(page.extract_text() or "") for page in reader.pages]
        text = "\n\n".join(parts).strip()
        if len(text) < 50 and ocr_available():
            try:
                import pypdfium2 as pdfium

                pdf = pdfium.PdfDocument(str(path))
                ocr_parts = []
                for index in range(min(len(pdf), 20)):
                    page = pdf[index]
                    image = page.render(scale=2).to_pil()
                    ocr_parts.append(_ocr_image(image))
                text = "\n\n".join(ocr_parts).strip()
                meta["ocr"] = True
                meta["extractor"] = "pypdfium2+tesseract"
            except Exception as exc:  # noqa: BLE001
                meta["ocr_error"] = str(exc)
        return text, meta

    if suffix == ".docx":
        from docx import Document as DocxDocument

        doc = DocxDocument(str(path))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    parts.append(" | ".join(cells))
        meta["extractor"] = "python-docx"
        return "\n".join(parts), meta

    if suffix in {".xlsx", ".xlsm"}:
        from openpyxl import load_workbook

        workbook = load_workbook(str(path), read_only=True, data_only=True)
        parts = []
        for sheet in workbook.worksheets:
            parts.append(f"## Sheet: {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                values = [str(v) for v in row if v is not None]
                if values:
                    parts.append(" | ".join(values))
        meta["extractor"] = "openpyxl"
        meta["sheets"] = len(workbook.worksheets)
        return "\n".join(parts), meta

    if suffix == ".csv":
        raw = path.read_text(encoding="utf-8", errors="replace")
        reader = csv.reader(io.StringIO(raw))
        rows = [" | ".join(row) for row in reader]
        meta["extractor"] = "csv"
        return "\n".join(rows), meta

    if suffix in {".txt", ".md", ".json", ".log"}:
        meta["extractor"] = "text"
        return path.read_text(encoding="utf-8", errors="replace"), meta

    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
        if not ocr_available():
            raise RuntimeError("OCR is unavailable: install the Tesseract binary to extract image text")
        from PIL import Image

        meta["extractor"] = "tesseract"
        meta["ocr"] = True
        return _ocr_image(Image.open(path)), meta

    raise RuntimeError(f"Unsupported document type: {suffix or mime_type}")


def chunk_text(text: str, size: int = 1200, overlap: int = 200) -> list[str]:
    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        if end < len(cleaned):
            boundary = cleaned.rfind("\n", start + size // 2, end)
            if boundary > start:
                end = boundary
        chunks.append(cleaned[start:end].strip())
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]
