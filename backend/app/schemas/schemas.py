"""
Pydantic schemas for request/response validation and serialization.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ─── Enums ─────────────────────────────────────────────────────────

class DocumentStatusSchema(str, Enum):
    UPLOADING = "uploading"
    PARSING = "parsing"
    EXTRACTING_IMAGES = "extracting_images"
    EXTRACTING_TABLES = "extracting_tables"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class ContentTypeSchema(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    CHART = "chart"


# ─── Document Schemas ──────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: DocumentStatusSchema
    message: str

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    document_type: str
    status: DocumentStatusSchema
    page_count: Optional[int] = None
    image_count: int = 0
    table_count: int = 0
    chunk_count: int = 0
    metadata_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


# ─── Query Schemas ─────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Natural language question")
    document_ids: Optional[List[uuid.UUID]] = Field(
        None, description="Filter to specific documents"
    )
    content_types: Optional[List[ContentTypeSchema]] = Field(
        None, description="Filter by content type"
    )
    conversation_id: Optional[uuid.UUID] = Field(
        None, description="Continue an existing conversation"
    )
    top_k: Optional[int] = Field(10, ge=1, le=50, description="Number of results to retrieve")
    enable_reranking: Optional[bool] = Field(True, description="Enable reranking")


class SourceResponse(BaseModel):
    document: str
    document_id: uuid.UUID
    page: Optional[int] = None
    content_type: str
    chunk_id: Optional[str] = None
    content_preview: Optional[str] = None
    score: float
    image_path: Optional[str] = None
    table_data: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    answer: str
    confidence: Optional[float] = None
    sources: List[SourceResponse]
    conversation_id: uuid.UUID
    query_id: uuid.UUID
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float


class StreamChunk(BaseModel):
    type: str  # "token" | "source" | "done" | "error"
    content: Optional[str] = None
    sources: Optional[List[SourceResponse]] = None
    metadata: Optional[Dict[str, Any]] = None


# ─── Conversation Schemas ──────────────────────────────────────────

class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: Optional[str] = None
    messages: List[MessageResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int


# ─── Evaluation Schemas ───────────────────────────────────────────

class EvaluationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    dataset: List[Dict[str, Any]] = Field(
        ..., description="List of {question, ground_truth} pairs"
    )
    config: Optional[Dict[str, Any]] = None


class EvaluationResultResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    dataset_size: int
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    avg_retrieval_latency_ms: Optional[float] = None
    avg_generation_latency_ms: Optional[float] = None
    avg_retrieved_chunks: Optional[float] = None
    hallucination_rate: Optional[float] = None
    citation_accuracy: Optional[float] = None
    status: str
    results_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EvaluationListResponse(BaseModel):
    results: List[EvaluationResultResponse]
    total: int


# ─── Health ────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    vector_db: str
    llm: str
    uptime_seconds: float


# ─── Chunk/Image/Table Detail Schemas ─────────────────────────────

class ChunkDetail(BaseModel):
    id: uuid.UUID
    chunk_index: int
    content: str
    content_type: str
    page_number: Optional[int] = None
    heading: Optional[str] = None

    class Config:
        from_attributes = True


class ImageDetail(BaseModel):
    id: uuid.UUID
    image_index: int
    page_number: Optional[int] = None
    image_path: str
    ocr_text: Optional[str] = None
    description: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

    class Config:
        from_attributes = True


class TableDetail(BaseModel):
    id: uuid.UUID
    table_index: int
    page_number: Optional[int] = None
    headers: Optional[List[str]] = None
    rows: Optional[List[List[Any]]] = None
    row_count: int
    column_count: int
    serialized: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentDetailResponse(DocumentResponse):
    chunks: List[ChunkDetail] = []
    images: List[ImageDetail] = []
    tables: List[TableDetail] = []
