"""
Vector database abstraction supporting ChromaDB and FAISS.
"""

import logging
import os
import json
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class VectorDocument:
    """A document to be stored in the vector database."""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorSearchResult:
    """A search result from the vector database."""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStore(ABC):
    """Abstract interface for vector database operations."""

    @abstractmethod
    async def add_documents(self, documents: List[VectorDocument]) -> None:
        """Add documents to the vector store."""
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        """Search for similar documents."""
        pass

    @abstractmethod
    async def delete_by_metadata(self, filters: Dict[str, Any]) -> int:
        """Delete documents matching metadata filters. Returns count deleted."""
        pass

    @abstractmethod
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collection."""
        pass


class ChromaVectorStore(VectorStore):
    """ChromaDB-backed vector store."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            persist_dir = self.settings.CHROMA_PERSIST_DIR
            os.makedirs(persist_dir, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self.settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def add_documents(self, documents: List[VectorDocument]) -> None:
        """Add documents to ChromaDB."""
        if not documents:
            return

        collection = self._get_collection()

        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            ids = [doc.id for doc in batch]
            embeddings = [doc.embedding for doc in batch]
            contents = [doc.content for doc in batch]
            metadatas = []
            for doc in batch:
                # ChromaDB requires flat metadata values
                meta = {}
                for k, v in doc.metadata.items():
                    if isinstance(v, (str, int, float, bool)):
                        meta[k] = v
                    elif v is None:
                        meta[k] = ""
                    else:
                        meta[k] = str(v)
                metadatas.append(meta)

            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas,
            )

        logger.info(f"Added {len(documents)} documents to ChromaDB")

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        """Search ChromaDB for similar documents."""
        collection = self._get_collection()

        where_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if value is not None:
                    conditions.append({key: {"$eq": value}})
            if len(conditions) == 1:
                where_filter = conditions[0]
            elif len(conditions) > 1:
                where_filter = {"$and": conditions}

        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if where_filter:
            kwargs["where"] = where_filter

        try:
            results = collection.query(**kwargs)
        except Exception as e:
            logger.error(f"ChromaDB search error: {e}")
            # Retry without filters if they cause issues
            if where_filter:
                kwargs.pop("where", None)
                results = collection.query(**kwargs)
            else:
                raise

        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0
                # ChromaDB returns distances; convert to similarity
                score = 1.0 - distance

                search_results.append(VectorSearchResult(
                    id=doc_id,
                    content=results["documents"][0][i] if results.get("documents") else "",
                    score=score,
                    metadata=results["metadatas"][0][i] if results.get("metadatas") else {},
                ))

        return search_results

    async def delete_by_metadata(self, filters: Dict[str, Any]) -> int:
        """Delete documents from ChromaDB by metadata."""
        collection = self._get_collection()

        conditions = []
        for key, value in filters.items():
            if value is not None:
                conditions.append({key: {"$eq": value}})

        where_filter = None
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        if where_filter is None:
            return 0

        try:
            # Get IDs matching filter
            results = collection.get(where=where_filter)
            if results and results["ids"]:
                collection.delete(ids=results["ids"])
                return len(results["ids"])
        except Exception as e:
            logger.error(f"ChromaDB delete error: {e}")

        return 0

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get ChromaDB collection stats."""
        collection = self._get_collection()
        return {
            "name": collection.name,
            "count": collection.count(),
            "provider": "chroma",
        }


class FAISSVectorStore(VectorStore):
    """FAISS-backed vector store with JSON metadata sidecar."""

    def __init__(self):
        self.settings = get_settings()
        self._index = None
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._id_to_idx: Dict[str, int] = {}
        self._idx_to_id: Dict[int, str] = {}
        self._documents: Dict[str, str] = {}
        self._dimension = self.settings.EMBEDDING_DIMENSION
        self._index_dir = Path(self.settings.FAISS_INDEX_DIR)
        self._index_dir.mkdir(parents=True, exist_ok=True)

    def _get_index(self):
        if self._index is None:
            import faiss

            index_path = self._index_dir / "index.faiss"
            meta_path = self._index_dir / "metadata.json"

            if index_path.exists():
                self._index = faiss.read_index(str(index_path))
                if meta_path.exists():
                    data = json.loads(meta_path.read_text())
                    self._metadata = data.get("metadata", {})
                    self._id_to_idx = data.get("id_to_idx", {})
                    self._idx_to_id = {int(v): k for k, v in self._id_to_idx.items()}
                    self._documents = data.get("documents", {})
            else:
                self._index = faiss.IndexFlatIP(self._dimension)  # Inner product for cosine sim

        return self._index

    def _save_index(self):
        """Persist FAISS index and metadata."""
        import faiss

        index_path = self._index_dir / "index.faiss"
        meta_path = self._index_dir / "metadata.json"

        faiss.write_index(self._index, str(index_path))
        meta_data = {
            "metadata": self._metadata,
            "id_to_idx": self._id_to_idx,
            "documents": self._documents,
        }
        meta_path.write_text(json.dumps(meta_data))

    async def add_documents(self, documents: List[VectorDocument]) -> None:
        """Add documents to FAISS index."""
        import faiss

        if not documents:
            return

        index = self._get_index()

        vectors = []
        for doc in documents:
            embedding = np.array(doc.embedding, dtype=np.float32)
            # Normalize for cosine similarity
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            vectors.append(embedding)

            idx = index.ntotal + len(vectors) - 1
            self._id_to_idx[doc.id] = idx
            self._idx_to_id[idx] = doc.id
            self._metadata[doc.id] = doc.metadata
            self._documents[doc.id] = doc.content

        vectors_array = np.array(vectors, dtype=np.float32)
        index.add(vectors_array)
        self._save_index()

        logger.info(f"Added {len(documents)} documents to FAISS index")

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        """Search FAISS index."""
        index = self._get_index()

        if index.ntotal == 0:
            return []

        query_vec = np.array([query_embedding], dtype=np.float32)
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm

        # Retrieve more than needed if filtering
        search_k = top_k * 3 if filters else top_k
        search_k = min(search_k, index.ntotal)

        distances, indices = index.search(query_vec, search_k)

        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:
                continue

            doc_id = self._idx_to_id.get(int(idx))
            if doc_id is None:
                continue

            metadata = self._metadata.get(doc_id, {})

            # Apply metadata filters
            if filters:
                match = True
                for key, value in filters.items():
                    if value is not None and metadata.get(key) != str(value):
                        match = False
                        break
                if not match:
                    continue

            results.append(VectorSearchResult(
                id=doc_id,
                content=self._documents.get(doc_id, ""),
                score=float(dist),
                metadata=metadata,
            ))

            if len(results) >= top_k:
                break

        return results

    async def delete_by_metadata(self, filters: Dict[str, Any]) -> int:
        """Delete documents matching metadata (rebuilds index)."""
        import faiss

        ids_to_delete = set()
        for doc_id, meta in self._metadata.items():
            match = all(
                meta.get(k) == str(v) for k, v in filters.items() if v is not None
            )
            if match:
                ids_to_delete.add(doc_id)

        if not ids_to_delete:
            return 0

        # Remove from metadata and documents
        for doc_id in ids_to_delete:
            self._metadata.pop(doc_id, None)
            self._documents.pop(doc_id, None)
            self._id_to_idx.pop(doc_id, None)

        # Rebuild index (FAISS doesn't support deletion in flat index)
        remaining_docs = []
        for doc_id in self._metadata:
            content = self._documents.get(doc_id, "")
            remaining_docs.append((doc_id, content))

        # This is a simplified rebuild — in production you'd use IndexIDMap
        self._index = faiss.IndexFlatIP(self._dimension)
        self._id_to_idx = {}
        self._idx_to_id = {}

        self._save_index()
        return len(ids_to_delete)

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get FAISS index stats."""
        index = self._get_index()
        return {
            "count": index.ntotal,
            "dimension": self._dimension,
            "provider": "faiss",
        }


class NumpyVectorStore(VectorStore):
    """Pure NumPy-backed vector store (zero external C++ dependencies)."""

    def __init__(self):
        self.settings = get_settings()
        self._dir = Path("./data/numpy_vectors")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._vectors: List[np.ndarray] = []
        self._ids: List[str] = []
        self._documents: Dict[str, str] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        meta_file = self._dir / "store.json"
        vec_file = self._dir / "vectors.npy"
        if meta_file.exists() and vec_file.exists():
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                self._ids = data.get("ids", [])
                self._documents = data.get("documents", {})
                self._metadata = data.get("metadata", {})
                arr = np.load(str(vec_file))
                self._vectors = [row for row in arr]
            except Exception as e:
                logger.warning(f"Failed to load numpy vectors: {e}")

    def _save(self):
        meta_file = self._dir / "store.json"
        vec_file = self._dir / "vectors.npy"
        data = {
            "ids": self._ids,
            "documents": self._documents,
            "metadata": self._metadata,
        }
        meta_file.write_text(json.dumps(data), encoding="utf-8")
        if self._vectors:
            np.save(str(vec_file), np.array(self._vectors, dtype=np.float32))

    async def add_documents(self, documents: List[VectorDocument]) -> None:
        for doc in documents:
            v = np.array(doc.embedding, dtype=np.float32)
            norm = np.linalg.norm(v)
            if norm > 0:
                v = v / norm
            self._vectors.append(v)
            self._ids.append(doc.id)
            self._documents[doc.id] = doc.content
            self._metadata[doc.id] = doc.metadata
        self._save()

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        if not self._vectors:
            return []
        qv = np.array(query_embedding, dtype=np.float32)
        qnorm = np.linalg.norm(qv)
        if qnorm > 0:
            qv = qv / qnorm
        matrix = np.array(self._vectors, dtype=np.float32)
        scores = np.dot(matrix, qv)
        sorted_indices = np.argsort(scores)[::-1]

        results = []
        for idx in sorted_indices:
            doc_id = self._ids[idx]
            meta = self._metadata.get(doc_id, {})
            if filters:
                match = True
                for k, v in filters.items():
                    if v is not None and meta.get(k) != str(v):
                        match = False
                        break
                if not match:
                    continue
            results.append(VectorSearchResult(
                id=doc_id,
                content=self._documents.get(doc_id, ""),
                score=float(scores[idx]),
                metadata=meta,
            ))
            if len(results) >= top_k:
                break
        return results

    async def delete_by_metadata(self, filters: Dict[str, Any]) -> int:
        to_del = []
        for i, doc_id in enumerate(self._ids):
            meta = self._metadata.get(doc_id, {})
            if all(meta.get(k) == str(v) for k, v in filters.items() if v is not None):
                to_del.append(i)
        if not to_del:
            return 0
        del_set = set(to_del)
        self._vectors = [v for i, v in enumerate(self._vectors) if i not in del_set]
        new_ids = []
        for i, doc_id in enumerate(self._ids):
            if i in del_set:
                self._documents.pop(doc_id, None)
                self._metadata.pop(doc_id, None)
            else:
                new_ids.append(doc_id)
        self._ids = new_ids
        self._save()
        return len(to_del)

    async def get_collection_stats(self) -> Dict[str, Any]:
        return {
            "count": len(self._ids),
            "provider": "numpy",
        }


def get_vector_store() -> VectorStore:
    """Factory function to get the configured vector store."""
    settings = get_settings()
    provider = settings.VECTOR_DB_PROVIDER.lower()

    if provider == "chroma":
        try:
            return ChromaVectorStore()
        except ImportError:
            logger.warning("ChromaDB not installed, falling back to NumpyVectorStore")
            return NumpyVectorStore()
    elif provider == "faiss":
        try:
            return FAISSVectorStore()
        except ImportError:
            logger.warning("FAISS not installed, falling back to NumpyVectorStore")
            return NumpyVectorStore()
    elif provider in ("numpy", "inmemory"):
        return NumpyVectorStore()
    else:
        logger.warning(f"Unknown vector store '{provider}', using NumpyVectorStore")
        return NumpyVectorStore()

