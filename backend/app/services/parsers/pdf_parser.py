"""
PDF parser using PyMuPDF (fitz) and pdfplumber for text, image, and table extraction.
"""

import io
import logging
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF
try:
    import pdfplumber
except ImportError:
    pdfplumber = None
from PIL import Image

from app.services.parsers.base import (
    BaseParser, ParsedDocument, ExtractedText, ExtractedImage, ExtractedTable
)

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """
    Production PDF parser combining PyMuPDF for images/text speed
    and pdfplumber for precise table extraction.
    """

    def supported_extensions(self) -> List[str]:
        return [".pdf"]

    async def parse(self, file_path: Path, document_id: str, output_dir: Path) -> ParsedDocument:
        """Parse a PDF file extracting text, images, and tables."""
        logger.info(f"Parsing PDF: {file_path.name} (doc_id={document_id})")

        result = ParsedDocument(
            document_id=document_id,
            filename=file_path.name,
            file_type="pdf",
        )

        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Phase 1: Extract text and images with PyMuPDF (fast)
            await self._extract_with_pymupdf(file_path, document_id, images_dir, result)

            # Phase 2: Extract tables with pdfplumber (precise)
            await self._extract_tables_with_pdfplumber(file_path, document_id, result)

            # Extract document metadata
            self._extract_metadata(file_path, result)

        except Exception as e:
            logger.error(f"Error parsing PDF {file_path.name}: {e}")
            result.errors.append(f"PDF parsing error: {str(e)}")

        logger.info(
            f"PDF parsed: {result.page_count} pages, "
            f"{len(result.texts)} text blocks, "
            f"{len(result.images)} images, "
            f"{len(result.tables)} tables"
        )
        return result

    async def _extract_with_pymupdf(
        self, file_path: Path, document_id: str, images_dir: Path, result: ParsedDocument
    ):
        """Extract text and images using PyMuPDF."""
        doc = fitz.open(str(file_path))
        result.page_count = len(doc)

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_number = page_num + 1

            # Extract text
            text = page.get_text("text").strip()
            if text:
                # Try to extract headings from text blocks
                blocks = page.get_text("dict")["blocks"]
                heading = self._detect_heading(blocks)

                result.texts.append(ExtractedText(
                    text=text,
                    page_number=page_number,
                    heading=heading,
                    metadata={
                        "char_count": len(text),
                        "word_count": len(text.split()),
                    }
                ))

            # Extract images
            image_list = page.get_images(full=True)
            for img_idx, img_info in enumerate(image_list):
                try:
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)

                    if base_image and base_image.get("image"):
                        image_bytes = base_image["image"]
                        image_ext = base_image.get("ext", "png")
                        width = base_image.get("width", 0)
                        height = base_image.get("height", 0)

                        # Skip very small images (likely icons/decorations)
                        if width < 50 or height < 50:
                            continue

                        # Save image to disk
                        image_filename = f"{document_id}_p{page_number}_img{img_idx}.{image_ext}"
                        image_path = images_dir / image_filename
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)

                        result.images.append(ExtractedImage(
                            image_path=str(image_path),
                            image_bytes=image_bytes,
                            image_format=image_ext,
                            page_number=page_number,
                            width=width,
                            height=height,
                            metadata={"xref": xref}
                        ))
                except Exception as e:
                    logger.warning(f"Failed to extract image {img_idx} from page {page_number}: {e}")

        doc.close()

    async def _extract_tables_with_pdfplumber(
        self, file_path: Path, document_id: str, result: ParsedDocument
    ):
        """Extract tables using pdfplumber for precise table detection."""
        if pdfplumber is None:
            # Fallback to PyMuPDF find_tables()
            try:
                doc = fitz.open(str(file_path))
                for page_num, page in enumerate(doc):
                    tabs = page.find_tables()
                    for t_idx, tab in enumerate(tabs):
                        df = tab.extract()
                        if df and len(df) >= 2:
                            headers = [str(c) if c else f"Col_{i}" for i, c in enumerate(df[0])]
                            rows = [[str(c) if c else "" for c in r] for r in df[1:]]
                            result.tables.append(ExtractedTable(
                                headers=headers,
                                rows=rows,
                                page_number=page_num + 1,
                                metadata={"table_index": t_idx, "extraction_method": "pymupdf"}
                            ))
                doc.close()
            except Exception as e:
                logger.warning(f"PyMuPDF table extraction note: {e}")
            return

        try:
            with pdfplumber.open(str(file_path)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_number = page_num + 1
                    tables = page.extract_tables()

                    for table_idx, table_data in enumerate(tables):
                        if not table_data or len(table_data) < 2:
                            continue

                        # First row as headers, rest as data
                        headers = [str(h).strip() if h else f"Col_{i}"
                                   for i, h in enumerate(table_data[0])]
                        rows = []
                        for row in table_data[1:]:
                            cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                            rows.append(cleaned_row)

                        result.tables.append(ExtractedTable(
                            headers=headers,
                            rows=rows,
                            page_number=page_number,
                            metadata={
                                "table_index": table_idx,
                                "extraction_method": "pdfplumber"
                            }
                        ))
        except Exception as e:
            logger.warning(f"pdfplumber table extraction failed: {e}")
            result.errors.append(f"Table extraction warning: {str(e)}")

    def _detect_heading(self, blocks: list) -> Optional[str]:
        """Attempt to detect the main heading from text blocks by font size."""
        if not blocks:
            return None

        max_font_size = 0
        heading_text = None

        for block in blocks:
            if block.get("type") != 0:  # text block
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font_size = span.get("size", 0)
                    text = span.get("text", "").strip()
                    if font_size > max_font_size and len(text) > 3:
                        max_font_size = font_size
                        heading_text = text

        return heading_text

    def _extract_metadata(self, file_path: Path, result: ParsedDocument):
        """Extract PDF metadata."""
        try:
            doc = fitz.open(str(file_path))
            meta = doc.metadata
            result.metadata = {
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "subject": meta.get("subject", ""),
                "creator": meta.get("creator", ""),
                "producer": meta.get("producer", ""),
                "creation_date": meta.get("creationDate", ""),
                "modification_date": meta.get("modDate", ""),
                "file_size_bytes": file_path.stat().st_size,
            }
            doc.close()
        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata: {e}")
