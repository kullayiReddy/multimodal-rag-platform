"""
SQLAlchemy ORM models for the Multimodal RAG Platform.
All tables use UUIDs as primary keys.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON, Enum as SAEnum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
import enum

from app.db.session import Base


# ─── Enums ─────────────────────────────────────────────────────────

class DocumentStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PARSING = "parsing"
    EXTRACTING_IMAGES = "extracting_images"
    EXTRACTING_TABLES = "extracting_tables"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class ContentType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    CHART = "chart"


class DocumentType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    TXT = "txt"
    IMAGE = "image"


# ─── Documents ─────────────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType), nullable=False
    )
    mime_type: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus), default=DocumentStatus.UPLOADING
    )
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    table_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    images = relationship("DocumentImage", back_populates="document", cascade="all, delete-orphan")
    tables = relationship("DocumentTable", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_status", "status"),
        Index("ix_documents_created_at", "created_at"),
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    table_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    document = relationship("Document", back_populates="pages")

    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_doc_page"),
        Index("ix_doc_pages_document", "document_id"),
    )


# ─── Chunks ────────────────────────────────────────────────────────

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[ContentType] = mapped_column(
        SAEnum(ContentType), default=ContentType.TEXT
    )
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    heading: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_document", "document_id"),
        Index("ix_chunks_content_type", "content_type"),
        Index("ix_chunks_page", "page_number"),
    )


# ─── Images ────────────────────────────────────────────────────────

class DocumentImage(Base):
    __tablename__ = "document_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    image_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    image_format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    objects_detected: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    document = relationship("Document", back_populates="images")

    __table_args__ = (
        Index("ix_images_document", "document_id"),
        Index("ix_images_page", "page_number"),
    )


# ─── Tables ────────────────────────────────────────────────────────

class DocumentTable(Base):
    __tablename__ = "document_tables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    table_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    headers: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    rows: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    serialized: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    document = relationship("Document", back_populates="tables")

    __table_args__ = (
        Index("ix_tables_document", "document_id"),
        Index("ix_tables_page", "page_number"),
    )


# ─── Conversations ────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conversation", "conversation_id"),
    )


# ─── Queries ───────────────────────────────────────────────────────

class Query(Base):
    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True
    )
    original_query: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    query_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    retrieval_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    generation_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_queries_conversation", "conversation_id"),
        Index("ix_queries_created_at", "created_at"),
    )


# ─── Retrieval Results ────────────────────────────────────────────

class RetrievalResult(Base):
    __tablename__ = "retrieval_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    content_type: Mapped[ContentType] = mapped_column(
        SAEnum(ContentType), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_retrieval_query", "query_id"),
    )


# ─── Evaluation ───────────────────────────────────────────────────

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dataset_size: Mapped[int] = mapped_column(Integer, default=0)
    faithfulness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    answer_relevancy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    context_precision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    context_recall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_retrieval_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_generation_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_retrieved_chunks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hallucination_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    citation_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    results_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    __table_args__ = (
        Index("ix_eval_runs_created", "created_at"),
    )
