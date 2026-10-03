"""
Document ingestion pipeline — orchestrates the full document processing flow.
"""

import logging
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import get_settings
from app.models.models import (
    Document, DocumentPage, DocumentChunk, DocumentImage,
    DocumentTable, DocumentStatus, DocumentType, ContentType
)
from app.services.parsers.router import DocumentRouter
from app.services.parsers.base import ParsedDocument
from app.services.chunking import TextChunker, Chunk
from app.services.embeddings.provider import EmbeddingProvider, get_embedding_provider
from app.services.embeddings.vector_store import VectorStore, VectorDocument, get_vector_store
from app.services.llm.gemini import GeminiLLM
from app.services.security.protection import detect_prompt_injection

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Orchestrates the full document ingestion pipeline:
    1. Parse document (text, images, tables)
    2. Chunk text
    3. Understand images via LLM
    4. Generate embeddings
    5. Store in vector database
    6. Persist metadata to PostgreSQL
    """

    def __init__(
        self,
        db_session: Optional[AsyncSession] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None,
        llm: Optional[GeminiLLM] = None,
    ):
        self.settings = get_settings()
        self.router = DocumentRouter()
        self.chunker = TextChunker(
            chunk_size=self.settings.CHUNK_SIZE,
            chunk_overlap=self.settings.CHUNK_OVERLAP,
        )
        self.db_session = db_session
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.vector_store = vector_store or get_vector_store()
        self.llm = llm or GeminiLLM()

    async def ingest(
        self,
        file_path: Path,
        document_id: str,
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Run the full ingestion pipeline for a document.

        Returns:
            Summary dict with counts and status.
        """
        session = db_session or self.db_session
        output_dir = Path(self.settings.PROCESSED_DIR) / document_id
        output_dir.mkdir(parents=True, exist_ok=True)
        start_time = time.time()

        stats = {
            "document_id": document_id,
            "pages": 0,
            "text_chunks": 0,
            "images": 0,
            "tables": 0,
            "embeddings_generated": 0,
            "errors": [],
        }

        try:
            # Phase 1: Update status — Parsing
            await self._update_status(session, document_id, DocumentStatus.PARSING)

            # Phase 2: Parse document
            parsed = await self.router.parse(file_path, document_id, output_dir)
            stats["pages"] = parsed.page_count

            # Phase 3: Store pages
            if session:
                await self._store_pages(session, document_id, parsed)

            # Phase 4: Extract images
            await self._update_status(session, document_id, DocumentStatus.EXTRACTING_IMAGES)
            await self._process_images(session, document_id, parsed)
            stats["images"] = len(parsed.images)

            # Phase 5: Extract tables
            await self._update_status(session, document_id, DocumentStatus.EXTRACTING_TABLES)
            await self._process_tables(session, document_id, parsed)
            stats["tables"] = len(parsed.tables)

            # Phase 6: Chunk text
            chunks = self.chunker.chunk_texts(parsed.texts, document_id)

            # Add table chunks
            for idx, table in enumerate(parsed.tables):
                table_chunk = self.chunker.chunk_table(
                    serialized=table.serialized,
                    table_index=idx,
                    page_number=table.page_number,
                    document_id=document_id,
                    description=table.description,
                )
                table_chunk.chunk_index = len(chunks)
                chunks.append(table_chunk)

            # Add image description chunks
            for idx, image in enumerate(parsed.images):
                if image.description or image.ocr_text:
                    img_chunk = self.chunker.chunk_image_description(
                        description=image.description or "Image",
                        image_index=idx,
                        page_number=image.page_number,
                        document_id=document_id,
                        ocr_text=image.ocr_text,
                    )
                    img_chunk.chunk_index = len(chunks)
                    chunks.append(img_chunk)

            stats["text_chunks"] = len(chunks)

            # Phase 7: Generate embeddings
            await self._update_status(session, document_id, DocumentStatus.GENERATING_EMBEDDINGS)
            vector_docs = await self._generate_embeddings(
                chunks, document_id, parsed.filename
            )
            stats["embeddings_generated"] = len(vector_docs)

            # Phase 8: Index in vector store
            await self._update_status(session, document_id, DocumentStatus.INDEXING)
            await self.vector_store.add_documents(vector_docs)

            # Phase 9: Store chunks in DB
            if session:
                await self._store_chunks(session, document_id, chunks)

            # Phase 10: Update document record
            await self._update_status(session, document_id, DocumentStatus.COMPLETED)
            if session:
                await self._update_document_stats(
                    session, document_id, parsed, chunks
                )

        except Exception as e:
            logger.error(f"Ingestion failed for {document_id}: {e}")
            stats["errors"].append(str(e))
            await self._update_status(
                session, document_id, DocumentStatus.FAILED, error=str(e)
            )

        elapsed = time.time() - start_time
        stats["processing_time_seconds"] = elapsed
        logger.info(
            f"Ingestion complete for {document_id}: "
            f"{stats['text_chunks']} chunks, {stats['images']} images, "
            f"{stats['tables']} tables in {elapsed:.1f}s"
        )
        return stats

    async def _process_images(
        self, session: Optional[AsyncSession], document_id: str, parsed: ParsedDocument
    ):
        """Process images: OCR + LLM understanding."""
        for idx, image in enumerate(parsed.images):
            try:
                # Generate image description via LLM
                if self.llm and image.image_path:
                    understanding = await self.llm.understand_image(image.image_path)
                    if not understanding.get("error"):
                        image.description = understanding.get("description", "")

                # Scan for prompt injection in OCR text
                if image.ocr_text:
                    is_injection, _ = detect_prompt_injection(image.ocr_text)
                    if is_injection:
                        image.metadata["prompt_injection_detected"] = True

                # Store in DB
                if session:
                    db_image = DocumentImage(
                        document_id=uuid.UUID(document_id),
                        image_index=idx,
                        page_number=image.page_number,
                        image_path=image.image_path,
                        image_format=image.image_format,
                        width=image.width,
                        height=image.height,
                        ocr_text=image.ocr_text,
                        description=image.description,
                        metadata_json=image.metadata,
                    )
                    session.add(db_image)

            except Exception as e:
                logger.warning(f"Image processing failed for image {idx}: {e}")

        if session:
            await session.flush()

    async def _process_tables(
        self, session: Optional[AsyncSession], document_id: str, parsed: ParsedDocument
    ):
        """Process tables: normalize and store."""
        for idx, table in enumerate(parsed.tables):
            try:
                # Scan for prompt injection
                if table.serialized:
                    is_injection, _ = detect_prompt_injection(table.serialized)
                    if is_injection:
                        table.metadata["prompt_injection_detected"] = True

                if session:
                    db_table = DocumentTable(
                        document_id=uuid.UUID(document_id),
                        table_index=idx,
                        page_number=table.page_number,
                        headers=table.headers,
                        rows=table.rows,
                        row_count=table.row_count,
                        column_count=table.column_count,
                        serialized=table.serialized,
                        description=table.description,
                        metadata_json=table.metadata,
                    )
                    session.add(db_table)

            except Exception as e:
                logger.warning(f"Table processing failed for table {idx}: {e}")

        if session:
            await session.flush()

    async def _generate_embeddings(
        self, chunks: list, document_id: str, filename: str
    ) -> list:
        """Generate embeddings for all chunks."""
        if not chunks:
            return []

        texts = [c.content for c in chunks]

        try:
            embeddings = await self.embedding_provider.embed_texts(texts)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

        vector_docs = []
        for chunk, embedding in zip(chunks, embeddings):
            vec_id = f"{document_id}_{chunk.chunk_index}"
            vector_docs.append(VectorDocument(
                id=vec_id,
                content=chunk.content,
                embedding=embedding,
                metadata={
                    "document_id": document_id,
                    "document_name": filename,
                    "page_number": str(chunk.page_number) if chunk.page_number else "",
                    "content_type": chunk.content_type,
                    "heading": chunk.heading or "",
                    "chunk_index": str(chunk.chunk_index),
                    **({"image_path": chunk.metadata.get("image_path", "")}
                       if chunk.content_type == "image" else {}),
                }
            ))

        return vector_docs

    async def _store_pages(
        self, session: AsyncSession, document_id: str, parsed: ParsedDocument
    ):
        """Store document pages in DB."""
        page_texts = {}
        for text in parsed.texts:
            page = text.page_number or 1
            if page not in page_texts:
                page_texts[page] = []
            page_texts[page].append(text.text)

        for page_num in range(1, parsed.page_count + 1):
            text_content = "\n".join(page_texts.get(page_num, []))
            page = DocumentPage(
                document_id=uuid.UUID(document_id),
                page_number=page_num,
                text_content=text_content if text_content else None,
            )
            session.add(page)

        await session.flush()

    async def _store_chunks(
        self, session: AsyncSession, document_id: str, chunks: list
    ):
        """Store chunks in DB."""
        for chunk in chunks:
            db_chunk = DocumentChunk(
                document_id=uuid.UUID(document_id),
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                content_type=ContentType(chunk.content_type),
                page_number=chunk.page_number,
                heading=chunk.heading,
                token_count=chunk.token_count,
                embedding_id=f"{document_id}_{chunk.chunk_index}",
                metadata_json=chunk.metadata,
            )
            session.add(db_chunk)

        await session.flush()

    async def _update_status(
        self, session: Optional[AsyncSession], document_id: str,
        status: DocumentStatus, error: Optional[str] = None
    ):
        """Update document processing status."""
        if session is None:
            return
        try:
            result = await session.execute(
                select(Document).where(Document.id == uuid.UUID(document_id))
            )
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = status
                if error:
                    doc.error_message = error
                await session.flush()
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")

    async def _update_document_stats(
        self, session: AsyncSession, document_id: str,
        parsed: ParsedDocument, chunks: list
    ):
        """Update document with final statistics."""
        try:
            result = await session.execute(
                select(Document).where(Document.id == uuid.UUID(document_id))
            )
            doc = result.scalar_one_or_none()
            if doc:
                doc.page_count = parsed.page_count
                doc.image_count = len(parsed.images)
                doc.table_count = len(parsed.tables)
                doc.chunk_count = len(chunks)
                doc.metadata_json = parsed.metadata
                await session.flush()
        except Exception as e:
            logger.warning(f"Failed to update document stats: {e}")
