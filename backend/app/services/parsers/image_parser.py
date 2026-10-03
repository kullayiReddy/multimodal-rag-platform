"""
Image parser for processing standalone image files with OCR.
"""

import io
import logging
from pathlib import Path
from typing import List, Optional
import shutil

from PIL import Image

from app.services.parsers.base import (
    BaseParser, ParsedDocument, ExtractedText, ExtractedImage
)

logger = logging.getLogger(__name__)


class ImageParser(BaseParser):
    """Parser for standalone image files (PNG, JPG, JPEG, WebP)."""

    def supported_extensions(self) -> List[str]:
        return [".png", ".jpg", ".jpeg", ".webp"]

    async def parse(self, file_path: Path, document_id: str, output_dir: Path) -> ParsedDocument:
        logger.info(f"Parsing image: {file_path.name}")

        result = ParsedDocument(
            document_id=document_id,
            filename=file_path.name,
            file_type="image",
            page_count=1,
        )

        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy image to output directory
            ext = file_path.suffix.lstrip(".")
            image_filename = f"{document_id}_img0.{ext}"
            image_path = images_dir / image_filename
            shutil.copy2(str(file_path), str(image_path))

            # Read image and get dimensions
            with Image.open(str(file_path)) as img:
                width, height = img.size
                image_format = img.format or ext

            with open(str(file_path), "rb") as f:
                image_bytes = f.read()

            # OCR extraction
            ocr_text = await self._extract_ocr_text(file_path)

            result.images.append(ExtractedImage(
                image_path=str(image_path),
                image_bytes=image_bytes,
                image_format=ext,
                page_number=1,
                width=width,
                height=height,
                ocr_text=ocr_text,
                metadata={
                    "original_filename": file_path.name,
                    "mode": img.mode if hasattr(img, 'mode') else None,
                }
            ))

            # If OCR extracted text, also store as text content
            if ocr_text and ocr_text.strip():
                result.texts.append(ExtractedText(
                    text=ocr_text,
                    page_number=1,
                    metadata={
                        "source": "ocr",
                        "image_file": file_path.name,
                    }
                ))

            result.metadata = {
                "width": width,
                "height": height,
                "format": image_format,
                "file_size_bytes": file_path.stat().st_size,
            }

        except Exception as e:
            logger.error(f"Error parsing image {file_path.name}: {e}")
            result.errors.append(f"Image parsing error: {str(e)}")

        return result

    async def _extract_ocr_text(self, file_path: Path) -> Optional[str]:
        """Extract text from image using OCR."""
        try:
            import pytesseract
            img = Image.open(str(file_path))

            # Convert to RGB if needed
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            text = pytesseract.image_to_string(img)
            return text.strip() if text else None
        except ImportError:
            logger.warning("pytesseract not installed, skipping OCR")
            return None
        except Exception as e:
            logger.warning(f"OCR failed for {file_path.name}: {e}")
            return None


class TextParser(BaseParser):
    """Parser for plain text files."""

    def supported_extensions(self) -> List[str]:
        return [".txt"]

    async def parse(self, file_path: Path, document_id: str, output_dir: Path) -> ParsedDocument:
        logger.info(f"Parsing text file: {file_path.name}")

        result = ParsedDocument(
            document_id=document_id,
            filename=file_path.name,
            file_type="txt",
            page_count=1,
        )

        try:
            # Try multiple encodings
            text = None
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    text = file_path.read_text(encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if text is None:
                text = file_path.read_text(encoding="utf-8", errors="replace")

            if text.strip():
                # Estimate pages (~3000 chars per page)
                result.page_count = max(1, len(text) // 3000 + 1)

                # Split into page-sized blocks for better chunking
                chars_per_page = 3000
                for i in range(0, len(text), chars_per_page):
                    page_text = text[i:i + chars_per_page].strip()
                    page_num = i // chars_per_page + 1
                    if page_text:
                        result.texts.append(ExtractedText(
                            text=page_text,
                            page_number=page_num,
                            metadata={"char_offset": i}
                        ))

            result.metadata = {
                "file_size_bytes": file_path.stat().st_size,
                "char_count": len(text) if text else 0,
            }

        except Exception as e:
            logger.error(f"Error parsing text file {file_path.name}: {e}")
            result.errors.append(f"Text parsing error: {str(e)}")

        return result
