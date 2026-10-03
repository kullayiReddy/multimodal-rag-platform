"""
Text chunking service with semantic-aware splitting.
"""

import logging
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from app.services.parsers.base import ExtractedText

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A single chunk of text with metadata."""
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    heading: Optional[str] = None
    content_type: str = "text"
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Rough token estimation (1 token ≈ 4 chars for English)
        if self.token_count == 0:
            self.token_count = len(self.content) // 4


class TextChunker:
    """
    Semantic-aware text chunker that respects paragraph and sentence boundaries.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_texts(self, texts: List[ExtractedText], document_id: str) -> List[Chunk]:
        """
        Chunk a list of extracted texts into smaller pieces.
        Tries to split at paragraph > sentence > word boundaries.
        """
        chunks: List[Chunk] = []
        chunk_index = 0

        for extracted in texts:
            text = extracted.text.strip()
            if not text:
                continue

            # Split into paragraphs first
            paragraphs = self._split_paragraphs(text)

            current_chunk = ""
            current_page = extracted.page_number

            for para in paragraphs:
                # If adding this paragraph would exceed the chunk size
                if len(current_chunk) + len(para) + 1 > self.chunk_size:
                    if current_chunk.strip():
                        chunks.append(Chunk(
                            content=current_chunk.strip(),
                            chunk_index=chunk_index,
                            page_number=current_page,
                            heading=extracted.heading,
                            content_type="text",
                            metadata={
                                "document_id": document_id,
                                **extracted.metadata,
                            }
                        ))
                        chunk_index += 1

                    # Handle overlap
                    if self.chunk_overlap > 0 and current_chunk:
                        overlap_text = current_chunk[-self.chunk_overlap:]
                        current_chunk = overlap_text + "\n" + para
                    else:
                        current_chunk = para

                    # If paragraph itself is larger than chunk size, split it
                    if len(para) > self.chunk_size:
                        sub_chunks = self._split_large_paragraph(para)
                        for i, sub in enumerate(sub_chunks):
                            chunks.append(Chunk(
                                content=sub.strip(),
                                chunk_index=chunk_index,
                                page_number=current_page,
                                heading=extracted.heading,
                                content_type="text",
                                metadata={
                                    "document_id": document_id,
                                    "sub_chunk": True,
                                    **extracted.metadata,
                                }
                            ))
                            chunk_index += 1
                        current_chunk = ""
                else:
                    current_chunk += "\n" + para if current_chunk else para

            # Don't forget the last chunk
            if current_chunk.strip():
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    page_number=current_page,
                    heading=extracted.heading,
                    content_type="text",
                    metadata={
                        "document_id": document_id,
                        **extracted.metadata,
                    }
                ))
                chunk_index += 1

        logger.info(f"Created {len(chunks)} chunks from {len(texts)} text blocks")
        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_large_paragraph(self, text: str) -> List[str]:
        """Split a large paragraph at sentence boundaries."""
        # Split at sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) + 1 > self.chunk_size:
                if current:
                    chunks.append(current)
                current = sentence
            else:
                current += " " + sentence if current else sentence

        if current:
            chunks.append(current)

        return chunks

    def chunk_table(self, serialized: str, table_index: int,
                    page_number: Optional[int], document_id: str,
                    description: Optional[str] = None) -> Chunk:
        """Create a chunk from a serialized table."""
        content = f"TABLE {table_index + 1}:\n{serialized}"
        if description:
            content = f"{description}\n\n{content}"

        return Chunk(
            content=content,
            chunk_index=0,  # Will be set by caller
            page_number=page_number,
            content_type="table",
            metadata={
                "document_id": document_id,
                "table_index": table_index,
            }
        )

    def chunk_image_description(self, description: str, image_index: int,
                                page_number: Optional[int], document_id: str,
                                ocr_text: Optional[str] = None) -> Chunk:
        """Create a chunk from an image description."""
        content = f"IMAGE {image_index + 1}: {description}"
        if ocr_text:
            content += f"\nVisible text: {ocr_text}"

        return Chunk(
            content=content,
            chunk_index=0,  # Will be set by caller
            page_number=page_number,
            content_type="image",
            metadata={
                "document_id": document_id,
                "image_index": image_index,
            }
        )
