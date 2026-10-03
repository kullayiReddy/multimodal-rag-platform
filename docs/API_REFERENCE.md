# API Reference - Multimodal RAG Platform

Base URL: `http://localhost:8000/api/v1`

## Health & System Status
### `GET /health`
Returns system status, active database connection, vector store provider, and LLM configuration.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "vector_db": "chroma",
  "llm": "gemini-2.0-flash",
  "uptime_seconds": 1284.5
}
```

---

## Document Management

### `POST /documents/upload`
Upload a document (PDF, DOCX, PPTX, PNG, JPG) to trigger layout extraction, chunking, and vector indexing.

- **Content-Type**: `multipart/form-data`
- **Body**: `file: Binary`

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "annual_report.pdf",
  "status": "uploading",
  "message": "Document uploaded. Processing will begin shortly."
}
```

### `GET /documents`
List all ingested documents with pagination.

**Query Parameters:**
- `skip`: Integer (default 0)
- `limit`: Integer (default 20)

### `GET /documents/{document_id}`
Retrieve granular document details including all parsed text chunks, detected tables, and visual elements.

### `DELETE /documents/{document_id}`
Deletes the document, its extracted images/tables, and its vector embeddings from ChromaDB.

---

## Multimodal Retrieval & Query

### `POST /query`
Ask questions against the multimodal document corpus.

**Request Body:**
```json
{
  "query": "What was the revenue in Q3 according to the financial table?",
  "document_ids": null,
  "top_k": 10,
  "enable_reranking": true
}
```

**Response:**
```json
{
  "answer": "According to Table 1, Q3 2024 total revenue reached $15.5 million...",
  "confidence": 0.96,
  "sources": [
    {
      "document": "annual_report.pdf",
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "page": 3,
      "content_type": "table",
      "chunk_id": "chunk_3_tb_1",
      "content_preview": "Table 1: Quarterly Financial Summary...",
      "score": 0.942,
      "table_data": {
        "headers": ["Quarter", "Revenue ($M)", "Growth (%)"],
        "rows": [["Q3", "15.5", "+27.8%"]]
      }
    }
  ],
  "retrieval_latency_ms": 124,
  "generation_latency_ms": 388,
  "total_latency_ms": 512,
  "tokens_used": 482
}
```

---

## Evaluation & Benchmarks

### `POST /evaluation/run`
Run automated RAGAS evaluation on test samples.

**Request Body:**
```json
{
  "samples": [
    {
      "query": "What was Q3 revenue?",
      "contexts": ["Q3 2024 revenue reached $15.5 million."],
      "ground_truth": "$15.5 million"
    }
  ]
}
```

**Response:**
```json
{
  "id": "eval-run-001",
  "faithfulness": 0.952,
  "answer_relevancy": 0.924,
  "context_precision": 0.891,
  "context_recall": 0.908,
  "hallucination_score": 0.019,
  "overall_score": 0.932
}
```
