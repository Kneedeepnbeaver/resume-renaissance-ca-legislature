"""FAISS vector store with Ollama embeddings (no onnxruntime dependency)."""
import json
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
import ollama


class VectorStore:
    """Vector store for RAG using FAISS and Ollama embeddings."""

    def __init__(
        self,
        persist_dir: Path,
        collection_name: str = "ca_legislature_resume_rag",
        embedding_model: str = "nomic-embed-text",
        ollama_host: str = "http://localhost:11434",
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.ollama_host = ollama_host
        self._index_path = self.persist_dir / f"{collection_name}.faiss"
        self._meta_path = self.persist_dir / f"{collection_name}_meta.json"
        self._index: Optional[faiss.IndexFlatIP] = None
        self._chunks: list[str] = []
        self._metadatas: list[dict] = []
        self._load()

    def _load(self) -> None:
        """Load index and metadata from disk if they exist."""
        if self._index_path.exists() and self._meta_path.exists():
            self._index = faiss.read_index(str(self._index_path))
            with open(self._meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._chunks = data.get("chunks", [])
                self._metadatas = data.get("metadatas", [])
        else:
            self._index = None
            self._chunks = []
            self._metadatas = []

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings from Ollama."""
        client = ollama.Client(host=self.ollama_host)
        response = client.embed(model=self.embedding_model, input=texts)
        return response["embeddings"]

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """L2-normalize vectors for cosine similarity via dot product."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vectors.astype(np.float32) / norms

    def add_chunks(
        self,
        chunks: list[str],
        metadatas: list[dict],
        ids: Optional[list[str]] = None,
        batch_size: int = 32,
    ) -> int:
        """Add chunks to the vector store. Returns count added."""
        if not chunks:
            return 0

        # ChromaDB-style metadata: only str, int, float, bool
        clean_metadatas = []
        for m in metadatas:
            clean = {}
            for k, v in m.items():
                if v is not None and isinstance(v, (str, int, float, bool)):
                    clean[k] = v
                elif isinstance(v, (list, dict)):
                    clean[k] = str(v)
                else:
                    clean[k] = str(v) if v else ""
            clean_metadatas.append(clean)

        all_embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            emb = self._embed(batch)
            all_embeddings.extend(emb)

        vectors = np.array(all_embeddings, dtype=np.float32)
        vectors = self._normalize(vectors)
        dim = vectors.shape[1]

        if self._index is None:
            self._index = faiss.IndexFlatIP(dim)

        self._index.add(vectors)
        self._chunks.extend(chunks)
        self._metadatas.extend(clean_metadatas)
        self._save()
        return len(chunks)

    def _save(self) -> None:
        """Persist index and metadata to disk."""
        if self._index is not None:
            faiss.write_index(self._index, str(self._index_path))
        with open(self._meta_path, "w", encoding="utf-8") as f:
            json.dump({"chunks": self._chunks, "metadatas": self._metadatas}, f, indent=0)

    def clear(self) -> None:
        """Clear the collection."""
        self._index = None
        self._chunks = []
        self._metadatas = []
        if self._index_path.exists():
            self._index_path.unlink()
        if self._meta_path.exists():
            self._meta_path.unlink()

    def search(
        self,
        query: str,
        top_k: int = 12,
        include_doc_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """Search for similar chunks. Returns list of {content, metadata, distance}."""
        if self._index is None or len(self._chunks) == 0:
            return []

        query_embedding = np.array(self._embed([query]), dtype=np.float32)
        query_embedding = self._normalize(query_embedding)

        # FAISS IndexFlatIP returns inner product (cosine sim for normalized vecs)
        # We fetch extra if filtering, then filter and trim
        fetch_k = top_k * 4 if include_doc_types else top_k
        fetch_k = min(fetch_k, self._index.ntotal)

        scores, indices = self._index.search(query_embedding, fetch_k)

        output = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0 or idx >= len(self._chunks):
                continue
            meta = self._metadatas[idx]
            if include_doc_types and meta.get("doc_type") not in include_doc_types:
                continue
            # Convert IP (higher=better) to distance (lower=better) for consistency
            distance = 1.0 - float(score)
            output.append({
                "content": self._chunks[idx],
                "metadata": meta,
                "distance": distance,
            })
            if len(output) >= top_k:
                break

        return output

    def count(self) -> int:
        """Return number of chunks in the collection."""
        if self._index is None:
            return 0
        return self._index.ntotal
