"""
Chat engine service for multimodal RAG.

TODO: Implement this service to:
1. Process user messages
2. Search for relevant context using vector store
3. Find related images and tables
4. Generate responses using LLM
5. Support multi-turn conversations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.conversation import Conversation, Message
from app.services.vector_store import VectorStore
from app.core.config import settings
import time

LLM_PROVIDER = getattr(settings, "LLM_PROVIDER", "groq").lower()

OpenAI = None
GroqClient = None

if LLM_PROVIDER == "openai":
    try:
        from openai import OpenAI as _OpenAI
        OpenAI = _OpenAI
    except Exception:
        OpenAI = None

elif LLM_PROVIDER == "groq":
    try:
        from groq import Groq as _Groq
        GroqClient = _Groq(api_key=getattr(settings, "GROQ_API_KEY", None))
    except Exception:
        GroqClient = None

class ChatEngine:
    """
    Multimodal chat engine with RAG.
    
    This is a SKELETON implementation. You need to implement the core logic.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.vector_store = VectorStore(db)
        self.llm = None
        if LLM_PROVIDER == "openai" and OpenAI is not None:
            try:
                self.llm = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))
            except Exception:
                self.llm = None
        elif LLM_PROVIDER == "groq":
            self.llm = GroqClient

    async def process_message(
        self,
        conversation_id: int,
        message: str,
        document_id: Optional[int] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        history = await self._load_conversation_history(conversation_id)
        context_chunks = await self._search_context(message, document_id=document_id)
        media = await self._find_related_media(context_chunks)
        answer = await self._generate_response(message, context_chunks, history, media)
        user_msg = Message(conversation_id=conversation_id, role="user", content=message)
        bot_msg = Message(conversation_id=conversation_id, role="assistant", content=answer)
        self.db.add_all([user_msg, bot_msg])
        self.db.commit()
        sources = self._format_sources(context_chunks, media)
        processing_time = round(time.time() - start_time, 2)
        return {
            "answer": answer,
            "sources": sources,
            "processing_time": processing_time,
        }

    async def _load_conversation_history(
        self,
        conversation_id: int,
        limit: int = 5
    ) -> List[Dict[str, str]]:
        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )

        history = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(messages)
        ]
        return history

    async def _search_context(
        self,
        query: str,
        document_id: Optional[int] = None,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        results = await self.vector_store.similarity_search(query=query, k=k, document_id=document_id)
        context_chunks = []

        for r in results:
            metadata_chunk = r.get("metadata_chunk", {}) or {}
            context_chunks.append({
                "content": r.get("content"),
                "page_number": metadata_chunk.get("page_number"),
                "score": r.get("score", 0.0),
                "metadata_chunk": metadata_chunk,
                "related_images": metadata_chunk.get("related_images", []),
                "related_tables": metadata_chunk.get("related_tables", []),
            })

        return context_chunks

    async def _find_related_media(
            self,
            context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Collect related images and tables from context chunks, ensuring uniqueness.
        """
        images, tables = [], []
        seen_images = set()
        seen_tables = set()

        for chunk in context_chunks:
            meta = chunk.get("metadata_chunk", {})

            for img in meta.get("related_images", []):
                url = img.get("url")
                if url and url not in seen_images:
                    images.append({
                        "url": url,
                        "caption": img.get("caption"),
                        "page": img.get("page_number") or chunk.get("page_number")
                    })
                    seen_images.add(url)

            for tbl in meta.get("related_tables", []):
                url = tbl.get("url")
                if url and url not in seen_tables:
                    tables.append({
                        "url": url,
                        "caption": tbl.get("caption"),
                        "page": tbl.get("page_number") or chunk.get("page_number"),
                        "data": tbl.get("data", {})
                    })
                    seen_tables.add(url)

        return {"images": images, "tables": tables}

    async def _generate_response(
        self,
        message: str,
        context: List[Dict[str, Any]],
        history: List[Dict[str, str]],
        media: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Generate response using configured LLM provider.
        Falls back to a deterministic reply if no LLM client is available.
        """
        system_prompt = (
            "You are a helpful assistant with access to contextual documents. "
            "Use the provided text, images, and tables to answer clearly and accurately. "
            "Cite relevant pages, figures, or tables when appropriate. "
            "Do not mention any limitations about missing images or diagrams. "
            "If an image or figure is referenced, describe it using the provided context or infer its content based on surrounding information."
        )

        context_text = "\n\n".join([f"[p{c.get('page') or c.get('page_number')}] {c['content']}" for c in context[:5]])
        media_summary = ""
        if media:
            images = media.get("images", [])
            tables = media.get("tables", [])
            media_lines = []
            if images:
                media_lines.append(
                    "Images are available in the context. Example captions or references: " +
                    ", ".join([img.get("caption", f"Image {i + 1}") for i, img in enumerate(images)])
                )
            if tables:
                media_lines.append(
                    "Tables are available in the context. Example titles or references: " +
                    ", ".join([tbl.get("caption", f"Table {i + 1}") for i, tbl in enumerate(tables)])
                )
            media_summary = "\n".join(media_lines)

        chat_messages = [{"role": "system", "content": system_prompt}] + history
        chat_messages.append({"role": "user", "content": f"{message}\n\nContext:\n{context_text}\n\n{media_summary}"})

        if LLM_PROVIDER == "openai" and self.llm is not None:
            try:
                model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")  # fallback
                response = self.llm.chat.completions.create(
                    model=model,
                    messages=chat_messages,
                    temperature=getattr(settings, "OPENAI_TEMPERATURE", 0.2),
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[ChatEngine] OpenAI chat failed: {e}")

        if LLM_PROVIDER == "groq" and self.llm is not None:
            try:
                model = getattr(settings, "GROQ_MODEL", None) or "llama-3.3-70b-versatile"
                response = self.llm.chat.completions.create(
                    model=model,
                    messages=chat_messages,
                    temperature=getattr(settings, "GROQ_TEMPERATURE", 0.2),
                )
                if hasattr(response, "choices") and len(response.choices) > 0:
                    return getattr(response.choices[0].message, "content", str(response.choices[0])).strip()
                return str(response).strip()
            except Exception as e:
                print(f"[ChatEngine] Groq chat failed: {e}")

        # --- Fallback: automatic reply when no LLM client available ---
        summary = context_text[:1000]  # cap length
        fallback = (
            "I couldn't reach the configured LLM provider. "
            "Here's a short summary of the most relevant context I found:\n\n"
            f"{summary}\n\n"
        )
        return fallback

    def _format_sources(
        self,
        context: List[Dict[str, Any]],
        media: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Format sources for response.
        
        This is implemented as an example.
        """
        sources = []

        # Add text sources
        for chunk in context[:3]:  # Top 3 text chunks
            sources.append({
                "type": "text",
                "content": chunk["content"],
                "page": chunk.get("page_number"),
                "score": chunk.get("score", 0.0)
            })
        
        # Add image sources
        for image in media.get("images", []):
            sources.append({
                "type": "image",
                "url": image["url"],
                "caption": image.get("caption"),
                "page": image.get("page")
            })
        
        # Add table sources
        for table in media.get("tables", []):
            sources.append({
                "type": "table",
                "url": table["url"],
                "caption": table.get("caption"),
                "page": table.get("page"),
                "data": table.get("data")
            })
        
        return sources
