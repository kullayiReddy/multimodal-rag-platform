"""
FastAPI v1 API endpoints for the Multimodal RAG Platform.
"""

import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, File, UploadFile, HTTPException,
    BackgroundTasks, Query as QueryParam, Request
)
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import json

from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import (
    Document, DocumentChunk, DocumentImage, DocumentTable,
    Conversation, Message, Query as QueryModel, RetrievalResult as RetrievalResultModel,
    EvaluationRun, DocumentStatus, DocumentType, ContentType
)
from app.schemas.schemas import (
    DocumentUploadResponse, DocumentResponse, DocumentListResponse,
    DocumentDetailResponse, QueryRequest, QueryResponse, SourceResponse,
    ConversationResponse, ConversationListResponse, MessageResponse,
    EvaluationRequest, EvaluationResultResponse, EvaluationListResponse,
    HealthResponse, ChunkDetail, ImageDetail, TableDetail
)
from app.services.ingestion import IngestionPipeline
from app.services.security.protection import validate_file, validate_query, RateLimiter

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)

# Module-level singletons (initialized in app startup)
_rag_workflow = None
_ingestion_pipeline = None


def get_rag_workflow():
    """Get the RAG workflow singleton."""
    global _rag_workflow
    return _rag_workflow


def get_ingestion_pipeline():
    """Get the ingestion pipeline singleton."""
    global _ingestion_pipeline
    return _ingestion_pipeline


# ─── Health ────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    import app
    return HealthResponse(
        status="healthy",
        version=app.__version__,
        database="connected",
        vector_db=settings.VECTOR_DB_PROVIDER,
        llm=settings.GEMINI_MODEL,
        uptime_seconds=time.time(),
    )


# ─── Document Upload & Ingestion ──────────────────────────────────

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for processing."""
    # Validate file
    file_path = Path(file.filename or "unknown")
    is_valid, error = validate_file(file_path, file.size or 0)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Generate document ID
    doc_id = uuid.uuid4()
    ext = file_path.suffix.lower()

    # Determine document type
    type_map = {
        ".pdf": DocumentType.PDF,
        ".docx": DocumentType.DOCX,
        ".pptx": DocumentType.PPTX,
        ".txt": DocumentType.TXT,
        ".png": DocumentType.IMAGE,
        ".jpg": DocumentType.IMAGE,
        ".jpeg": DocumentType.IMAGE,
        ".webp": DocumentType.IMAGE,
    }
    doc_type = type_map.get(ext, DocumentType.TXT)

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = f"{doc_id}{ext}"
    saved_path = upload_dir / safe_filename

    try:
        content = await file.read()
        with open(saved_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create document record
    doc = Document(
        id=doc_id,
        filename=safe_filename,
        original_filename=file.filename or "unknown",
        file_path=str(saved_path),
        file_size=len(content),
        file_type=ext.lstrip("."),
        document_type=doc_type,
        mime_type=file.content_type,
        status=DocumentStatus.UPLOADING,
    )
    db.add(doc)
    await db.flush()

    # Start ingestion in background
    background_tasks.add_task(
        _run_ingestion, str(doc_id), str(saved_path)
    )

    return DocumentUploadResponse(
        id=doc_id,
        filename=file.filename or "unknown",
        status="uploading",
        message="Document uploaded. Processing will begin shortly.",
    )


async def _run_ingestion(document_id: str, file_path: str):
    """Background task to run document ingestion."""
    from app.db.session import init_db, get_session_factory

    engine, session_factory = init_db()
    async with session_factory() as session:
        try:
            pipeline = IngestionPipeline(db_session=session)
            await pipeline.ingest(
                file_path=Path(file_path),
                document_id=document_id,
                db_session=session,
            )
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Background ingestion failed: {e}")


@router.post("/documents/ingest")
async def ingest_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Trigger ingestion for an already-uploaded document."""
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    background_tasks.add_task(
        _run_ingestion, document_id, doc.file_path
    )

    return {"message": "Ingestion started", "document_id": document_id}


# ─── Document CRUD ────────────────────────────────────────────────

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    skip: int = QueryParam(0, ge=0),
    limit: int = QueryParam(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all documents."""
    # Count
    count_result = await db.execute(select(func.count(Document.id)))
    total = count_result.scalar() or 0

    # Fetch
    result = await db.execute(
        select(Document)
        .order_by(desc(Document.created_at))
        .offset(skip)
        .limit(limit)
    )
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
    )


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Get document details including chunks, images, and tables."""
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get chunks
    chunks_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == uuid.UUID(document_id))
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()

    # Get images
    images_result = await db.execute(
        select(DocumentImage)
        .where(DocumentImage.document_id == uuid.UUID(document_id))
        .order_by(DocumentImage.image_index)
    )
    images = images_result.scalars().all()

    # Get tables
    tables_result = await db.execute(
        select(DocumentTable)
        .where(DocumentTable.document_id == uuid.UUID(document_id))
        .order_by(DocumentTable.table_index)
    )
    tables = tables_result.scalars().all()

    response = DocumentDetailResponse.model_validate(doc)
    response.chunks = [ChunkDetail.model_validate(c) for c in chunks]
    response.images = [ImageDetail.model_validate(i) for i in images]
    response.tables = [TableDetail.model_validate(t) for t in tables]

    return response


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a document and all related data."""
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from vector store
    try:
        from app.services.embeddings.vector_store import get_vector_store
        vs = get_vector_store()
        await vs.delete_by_metadata({"document_id": document_id})
    except Exception as e:
        logger.warning(f"Failed to delete from vector store: {e}")

    # Delete file
    try:
        if doc.file_path and Path(doc.file_path).exists():
            Path(doc.file_path).unlink()
    except Exception:
        pass

    # Delete processed directory
    try:
        processed_dir = Path(settings.PROCESSED_DIR) / document_id
        if processed_dir.exists():
            shutil.rmtree(str(processed_dir))
    except Exception:
        pass

    # Delete from DB (cascades)
    await db.delete(doc)

    return {"message": "Document deleted", "document_id": document_id}


# ─── Query ─────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Ask a question about uploaded documents."""
    # Rate limiting
    client_ip = req.client.host if req.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Validate query
    is_valid, error = validate_query(request.query)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    workflow = get_rag_workflow()
    if not workflow:
        raise HTTPException(status_code=503, detail="RAG workflow not initialized")

    total_start = time.time()

    # Create or get conversation
    conv_id = request.conversation_id
    if not conv_id:
        conv = Conversation(title=request.query[:100])
        db.add(conv)
        await db.flush()
        conv_id = conv.id
    else:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        if not result.scalar_one_or_none():
            conv = Conversation(id=conv_id, title=request.query[:100])
            db.add(conv)
            await db.flush()

    # Store user message
    user_msg = Message(
        conversation_id=conv_id,
        role="user",
        content=request.query,
    )
    db.add(user_msg)

    # Run RAG workflow
    doc_ids = [str(d) for d in request.document_ids] if request.document_ids else None

    result = await workflow.run(
        query=request.query,
        document_ids=doc_ids,
        conversation_id=str(conv_id),
        top_k=request.top_k or 10,
        enable_reranking=request.enable_reranking if request.enable_reranking is not None else True,
    )

    # Build source responses
    sources = []
    for s in result.get("sources", []):
        sources.append(SourceResponse(
            document=s.get("document", "Unknown"),
            document_id=uuid.UUID(s["document_id"]) if s.get("document_id") else uuid.uuid4(),
            page=s.get("page"),
            content_type=s.get("content_type", "text"),
            chunk_id=s.get("chunk_id"),
            content_preview=s.get("content_preview"),
            score=s.get("score", 0),
            image_path=s.get("image_path"),
            table_data=s.get("table_data"),
        ))

    # Store assistant message
    asst_msg = Message(
        conversation_id=conv_id,
        role="assistant",
        content=result.get("answer", ""),
        sources=[s.model_dump() for s in sources],
    )
    db.add(asst_msg)

    # Store query record
    query_record = QueryModel(
        conversation_id=conv_id,
        original_query=request.query,
        rewritten_query=None,
        query_type=str(result.get("query_classification", {}).get("types", [])),
        answer=result.get("answer", ""),
        confidence=result.get("confidence"),
        retrieval_latency_ms=result.get("retrieval_latency_ms"),
        generation_latency_ms=result.get("generation_latency_ms"),
        total_tokens_used=result.get("tokens_used"),
        sources=[s.model_dump() for s in sources],
    )
    db.add(query_record)

    total_latency = (time.time() - total_start) * 1000

    return QueryResponse(
        answer=result.get("answer", ""),
        confidence=result.get("confidence"),
        sources=sources,
        conversation_id=conv_id,
        query_id=query_record.id,
        retrieval_latency_ms=result.get("retrieval_latency_ms", 0),
        generation_latency_ms=result.get("generation_latency_ms", 0),
        total_latency_ms=total_latency,
    )


@router.post("/query/stream")
async def query_documents_stream(
    request: QueryRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Stream a query response token by token."""
    is_valid, error = validate_query(request.query)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    workflow = get_rag_workflow()
    if not workflow:
        raise HTTPException(status_code=503, detail="RAG workflow not initialized")

    async def generate():
        try:
            # First, do retrieval
            result = await workflow.run(
                query=request.query,
                top_k=request.top_k or 10,
            )

            # Stream the answer
            answer = result.get("answer", "")
            # Simulate streaming for the answer
            words = answer.split(" ")
            for i, word in enumerate(words):
                chunk = {"type": "token", "content": word + " "}
                yield f"data: {json.dumps(chunk)}\n\n"

            # Send sources
            sources_chunk = {
                "type": "sources",
                "sources": result.get("sources", []),
            }
            yield f"data: {json.dumps(sources_chunk)}\n\n"

            # Done
            done_chunk = {
                "type": "done",
                "metadata": {
                    "retrieval_latency_ms": result.get("retrieval_latency_ms", 0),
                    "generation_latency_ms": result.get("generation_latency_ms", 0),
                    "confidence": result.get("confidence"),
                }
            }
            yield f"data: {json.dumps(done_chunk)}\n\n"

        except Exception as e:
            error_chunk = {"type": "error", "content": str(e)}
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ─── Conversations ────────────────────────────────────────────────

@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = QueryParam(0, ge=0),
    limit: int = QueryParam(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations."""
    count_result = await db.execute(select(func.count(Conversation.id)))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Conversation)
        .order_by(desc(Conversation.updated_at))
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().all()

    conv_responses = []
    for conv in conversations:
        msgs_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        )
        messages = msgs_result.scalars().all()

        conv_responses.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            messages=[MessageResponse.model_validate(m) for m in messages],
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        ))

    return ConversationListResponse(conversations=conv_responses, total=total)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get a conversation with all messages."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    messages = msgs_result.scalars().all()

    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        messages=[MessageResponse.model_validate(m) for m in messages],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


# ─── Evaluation ───────────────────────────────────────────────────

@router.post("/evaluate")
async def run_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """Start an evaluation run."""
    eval_run = EvaluationRun(
        name=request.name,
        description=request.description,
        dataset_size=len(request.dataset),
        config_json=request.config,
        status="running",
    )
    db.add(eval_run)
    await db.flush()

    background_tasks.add_task(
        _run_evaluation, str(eval_run.id), request.dataset, request.name
    )

    return {
        "id": str(eval_run.id),
        "message": "Evaluation started",
        "status": "running",
    }


async def _run_evaluation(eval_id: str, dataset: List, run_name: str):
    """Background evaluation task."""
    from app.db.session import init_db
    from app.services.evaluation.engine import EvaluationEngine, EvaluationSample

    engine, session_factory = init_db()
    async with session_factory() as session:
        try:
            workflow = get_rag_workflow()
            if not workflow:
                return

            eval_engine = EvaluationEngine(workflow)
            samples = [
                EvaluationSample(
                    question=d["question"],
                    ground_truth=d.get("ground_truth", ""),
                    category=d.get("category", "text"),
                )
                for d in dataset
            ]

            results = await eval_engine.evaluate(samples, run_name)

            # Update evaluation run
            result = await session.execute(
                select(EvaluationRun).where(EvaluationRun.id == uuid.UUID(eval_id))
            )
            eval_run = result.scalar_one_or_none()
            if eval_run:
                eval_run.faithfulness = results.get("faithfulness")
                eval_run.answer_relevancy = results.get("answer_relevancy")
                eval_run.context_precision = results.get("context_precision")
                eval_run.context_recall = results.get("context_recall")
                eval_run.avg_retrieval_latency_ms = results.get("avg_retrieval_latency_ms")
                eval_run.avg_generation_latency_ms = results.get("avg_generation_latency_ms")
                eval_run.avg_retrieved_chunks = results.get("avg_retrieved_chunks")
                eval_run.hallucination_rate = results.get("hallucination_rate")
                eval_run.results_json = results
                eval_run.status = "completed"
                from datetime import datetime
                eval_run.completed_at = datetime.utcnow()

            await session.commit()

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            await session.rollback()


@router.get("/evaluation/results", response_model=EvaluationListResponse)
async def get_evaluation_results(
    skip: int = QueryParam(0, ge=0),
    limit: int = QueryParam(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get evaluation results."""
    count_result = await db.execute(select(func.count(EvaluationRun.id)))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(EvaluationRun)
        .order_by(desc(EvaluationRun.created_at))
        .offset(skip)
        .limit(limit)
    )
    runs = result.scalars().all()

    return EvaluationListResponse(
        results=[EvaluationResultResponse.model_validate(r) for r in runs],
        total=total,
    )


# ─── Image Serving ────────────────────────────────────────────────

@router.get("/images/{document_id}/{image_filename}")
async def serve_image(document_id: str, image_filename: str):
    """Serve an extracted image."""
    image_path = Path(settings.PROCESSED_DIR) / document_id / "images" / image_filename
    if not image_path.exists():
        # Try upload dir
        image_path = Path(settings.IMAGES_DIR) / image_filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(str(image_path))
