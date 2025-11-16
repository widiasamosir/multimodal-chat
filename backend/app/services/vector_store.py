"""
Vector store service using pgvector.

TODO: Implement this service to:
1. Generate embeddings for text chunks
2. Store embeddings in PostgreSQL with pgvector
3. Perform similarity search
4. Link related images and tables
"""
import asyncio
import json
from typing import List, Dict, Any, Optional
import numpy as np
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.document import DocumentChunk, DocumentImage, DocumentTable
from app.core.config import settings

LLM_PROVIDER = getattr(settings, "LLM_PROVIDER", "openai").lower()

# Lazy import Groq only if needed
GroqClient = None
if LLM_PROVIDER == "groq":
    try:
        from groq import Groq
        GroqClient = Groq(api_key=settings.GROQ_API_KEY)
    except Exception:
        GroqClient = None

_sentence_transformer = None

class VectorStore:
    """
    Vector store for document embeddings and similarity search.

    This is a SKELETON implementation. You need to implement the core logic.
    """

    def __init__(self, db: Session):
        self.db = db
        self.embeddings_model = None
        self._ensure_extension()

        if LLM_PROVIDER == "openai":
            if getattr(settings, "OPENAI_API_KEY", None) and OpenAI is not None:
                try:
                    self.embeddings_model = OpenAI(api_key=settings.OPENAI_API_KEY)
                except Exception:
                    self.embeddings_model = None

            # Groq client
        elif LLM_PROVIDER == "groq":
            global GroqClient
            self.embeddings_model = GroqClient

    def _ensure_extension(self):
        """
        Ensure pgvector extension is enabled.

        This is implemented as an example.
        """
        try:
            self.db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            self.db.commit()
        except Exception as e:
            print(f"pgvector extension already exists or error: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass

    async def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.
        TODO: Implement embedding generation

        Prefer OpenAI embeddings, fallback to sentence-transformers.
        Returns numpy array (float32).
        """
        if not text:
            return np.zeros((1,), dtype=np.float32)

        # --- OPENAI provider ---
        if LLM_PROVIDER == "openai" and self.embeddings_model:
            try:
                model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
                resp = self.embeddings_model.embeddings.create(model=model, input=text)
                emb = np.array(resp.data[0].embedding, dtype=np.float32)
                return emb
            except Exception as e:
                print(f"[VectorStore] OpenAI embeddings failed: {e}")

        # --- FALLBACK: sentence-transformers ---
        global _sentence_transformer
        if _sentence_transformer is None:
            try:
                from sentence_transformers import SentenceTransformer
                _sentence_transformer = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                raise RuntimeError(
                    "No embedding provider available. Install `sentence-transformers` "
                    "or set OPENAI_API_KEY/GROQ_API_KEY."
                ) from e

        emb = _sentence_transformer.encode(text, show_progress_bar=False, convert_to_numpy=True)

        # This is for case using HF: Expand 384 → 1536 by repeating 4 times
        emb = np.tile(emb, 4)

        return emb.astype(np.float32)

    async def store_chunk(
        self,
        content: str,
        document_id: int,
        page_number: int,
        chunk_index: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentChunk:
        """
        Store a text chunk and its embedding in the DB.
        Embedding stored as list for pgvector compatibility.
        """
        image_captions = " ".join(
            img.get("caption", "") for img in (metadata.get("related_images", []) or []) if img.get("caption")
        )
        table_captions = " ".join(
            tbl.get("caption", "") for tbl in (metadata.get("related_tables", []) or []) if tbl.get("caption")
        )
        text_for_embedding = content
        if image_captions:
            text_for_embedding += " " + image_captions
        if table_captions:
            text_for_embedding += " " + table_captions
        embedding = await self.generate_embedding(text_for_embedding)
        embedding_list = embedding.tolist()

        chunk = DocumentChunk(
            document_id=document_id,
            content=content,
            page_number=page_number,
            chunk_index=chunk_index,
            metadata_chunk=metadata or {},
            embedding=embedding_list
        )

        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    async def similarity_search(
            self,
            query: str,
            document_id: Optional[int] = None,
            k: int = 5,
    ) -> List[Dict[str, Any]]:
        if not query:
            return []

        query_emb = await self.generate_embedding(query)

        sql = """
            SELECT
        c.id,
        c.document_id,
        d.filename,
        d.file_path,
        c.content,
        c.page_number,
        c.metadata_chunk,
        (c.embedding <=> (:query_embedding)::vector) AS distance
    FROM document_chunks c
    JOIN documents d ON d.id = c.document_id
        """

        params = {
            "query_embedding": query_emb.tolist(),
            "query_text": f"%{query}%",
        }

        if document_id:
            sql += " WHERE document_id = :document_id "
            params["document_id"] = document_id

        sql += " ORDER BY distance"
        if k:
            sql += f" LIMIT {k} "
        def db_query():
            return self.db.execute(text(sql), params).fetchall()

        rows = await asyncio.to_thread(db_query)
        if not rows:
            return []

        related_map = await self.get_related_content_map([r.id for r in rows])

        results = []
        for row in rows:
            distance = getattr(row, "distance", None)
            similarity = 1.0 - float(distance) if distance is not None else 0.0

            meta = row.metadata_chunk
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    pass

            cid = row.id
            rel = related_map.get(cid, {"images": [], "tables": []})

            results.append({
                "chunk_id": cid,
                "content": row.content,
                "document_id": row.document_id,
                "document_path": row.file_path,
                "page_number": row.page_number,
                "metadata_chunk": meta,
                "score": similarity,
                "related_images": rel["images"],
                "related_tables": rel["tables"],
            })

        return results

    async def get_related_content_map(self, chunk_ids: List[int]) -> Dict[int, Dict[str, List]]:
        if not chunk_ids:
            return {}

        # Load only needed chunks
        chunks = (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.id.in_(chunk_ids))
            .all()
        )

        page_map = {}
        for c in chunks:
            key = (c.document_id, c.page_number)
            page_map.setdefault(key, []).append(c.id)

        result_map = {cid: {"images": [], "tables": []} for cid in chunk_ids}

        doc_ids = list({doc for (doc, _) in page_map.keys()})
        pages = list({pg for (_, pg) in page_map.keys()})

        img_rows = (
            self.db.query(DocumentImage)
            .filter(DocumentImage.document_id.in_(doc_ids))
            .filter(DocumentImage.page_number.in_(pages))
            .all()
        )

        for img in img_rows:
            key = (img.document_id, img.page_number)
            for cid in page_map.get(key, []):
                result_map[cid]["images"].append({
                    "id": img.id,
                    "page": img.page_number,
                    "file_path": img.file_path,
                    "caption": getattr(img, "caption", None),
                    "metadata": getattr(img, "metadata_chunk", None),
                })

        tbl_rows = (
            self.db.query(DocumentTable)
            .filter(DocumentTable.document_id.in_(doc_ids))
            .filter(DocumentTable.page_number.in_(pages))
            .all()
        )

        for tb in tbl_rows:
            key = (tb.document_id, tb.page_number)
            for cid in page_map.get(key, []):
                result_map[cid]["tables"].append({
                    "id": tb.id,
                    "page": tb.page_number,
                    "image_path": tb.image_path,
                    "caption": getattr(tb, "caption", None),
                    "data": getattr(tb, "data", None),
                    "metadata": getattr(tb, "metadata_chunk", None),
                })

        return result_map

