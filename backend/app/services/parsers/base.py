"""
Base parser interface and common utilities for document processing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid


@dataclass
class ExtractedText:
    """Represents extracted text content."""
    text: str
    page_number: Optional[int] = None
    heading: Optional[str] = None
    section: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedImage:
    """Represents an extracted image."""
    image_path: str
    image_bytes: Optional[bytes] = None
    image_format: str = "png"
    page_number: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    ocr_text: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedTable:
    """Represents an extracted table."""
    headers: List[str]
    rows: List[List[Any]]
    page_number: Optional[int] = None
    row_count: int = 0
    column_count: int = 0
    serialized: str = ""
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.row_count = len(self.rows)
        self.column_count = len(self.headers) if self.headers else 0
        if not self.serialized:
            self.serialized = self._serialize()

    def _serialize(self) -> str:
        """Create a pipe-delimited text representation of the table."""
        if not self.headers and not self.rows:
            return ""
        lines = []
        if self.headers:
            lines.append(" | ".join(str(h) for h in self.headers))
            lines.append(" | ".join("---" for _ in self.headers))
        for row in self.rows:
            lines.append(" | ".join(str(cell) for cell in row))
        return "\n".join(lines)


@dataclass
class ParsedDocument:
    """Complete result of document parsing."""
    document_id: str
    filename: str
    file_type: str
    page_count: int = 0
    texts: List[ExtractedText] = field(default_factory=list)
    images: List[ExtractedImage] = field(default_factory=list)
    tables: List[ExtractedTable] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    async def parse(self, file_path: Path, document_id: str, output_dir: Path) -> ParsedDocument:
        """
        Parse a document and extract all content.

        Args:
            file_path: Path to the document file
            document_id: Unique identifier for the document
            output_dir: Directory for extracted artifacts (images, etc.)

        Returns:
            ParsedDocument with all extracted content
        """
        pass

    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        pass

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix.lower() in self.supported_extensions()
