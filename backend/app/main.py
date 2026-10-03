"""
FastAPI application entry point.
"""

import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.session import init_db, create_tables
from app.api.v1.endpoints import router as v1_router
from app.services.embeddings.provider import get_embedding_provider
from app.services.embeddings.vector_store import get_vector_store
from app.services.retrieval.hybrid import HybridRetriever
from app.services.retrieval.reranker import Reranker
from app.services.retrieval.rag_workflow import RAGWorkflow
from app.services.llm.gemini import GeminiLLM

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    setup_logging(level=settings.LOG_LEVEL)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Initialize database
    try:
        engine, session_factory = init_db()
        await create_tables()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")

    # Initialize AI components
    try:
        embedding_provider = get_embedding_provider()
        vector_store = get_vector_store()
        llm = GeminiLLM()
        retriever = HybridRetriever(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            semantic_weight=settings.SEMANTIC_WEIGHT,
            keyword_weight=settings.KEYWORD_WEIGHT,
        )
        reranker = Reranker()
        workflow = RAGWorkflow(
            llm=llm,
            retriever=retriever,
            reranker=reranker,
        )

        # Set module-level singletons
        import app.api.v1.endpoints as endpoints
        endpoints._rag_workflow = workflow
        endpoints._ingestion_pipeline = None  # Created per-request with DB session

        logger.info("AI components initialized")
    except Exception as e:
        logger.warning(f"AI components initialization deferred: {e}")

    yield

    logger.info("Shutting down application")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "A production-grade Multimodal RAG Document Intelligence Platform. "
            "Upload documents (PDF, DOCX, PPTX, images) and ask natural language questions "
            "about both textual and visual content."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request timing middleware
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"
        return response

    # Global error handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred. Please try again later."},
        )

    # Register routes
    app.include_router(v1_router, prefix="/api/v1")

    return app


# Application instance
app = create_app()
