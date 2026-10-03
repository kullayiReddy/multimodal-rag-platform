"""
Document Router — routes files to the appropriate parser based on file type.
"""

import logging
from pathlib import Path
from typing import Dict, Type

from app.services.parsers.base import BaseParser, ParsedDocument
from app.services.parsers.pdf_parser import PDFParser
from app.services.parsers.docx_parser import DOCXParser
from app.services.parsers.pptx_parser import PPTXParser
from app.services.parsers.image_parser import ImageParser, TextParser

logger = logging.getLogger(__name__)


class DocumentRouter:
    """Routes documents to the appropriate parser based on file extension."""

    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}
        self._register_default_parsers()

    def _register_default_parsers(self):
        """Register all built-in parsers."""
        parsers = [
            PDFParser(),
            DOCXParser(),
            PPTXParser(),
            ImageParser(),
            TextParser(),
        ]
        for parser in parsers:
            for ext in parser.supported_extensions():
                self._parsers[ext.lower()] = parser

    def register_parser(self, extension: str, parser: BaseParser):
        """Register a custom parser for a file extension."""
        self._parsers[extension.lower()] = parser

    def get_parser(self, file_path: Path) -> BaseParser:
        """Get the appropriate parser for a file."""
        ext = file_path.suffix.lower()
        parser = self._parsers.get(ext)
        if parser is None:
            raise ValueError(f"No parser registered for extension: {ext}")
        return parser

    async def parse(self, file_path: Path, document_id: str, output_dir: Path) -> ParsedDocument:
        """Parse a document using the appropriate parser."""
        file_path = Path(file_path)
        output_dir = Path(output_dir)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        parser = self.get_parser(file_path)
        logger.info(f"Routing {file_path.name} to {parser.__class__.__name__}")

        return await parser.parse(file_path, document_id, output_dir)

    @property
    def supported_extensions(self) -> list:
        """Return all supported file extensions."""
        return list(self._parsers.keys())
