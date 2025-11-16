"""
Document processing service using Docling

TODO: Implement this service to:
1. Parse PDF documents using Docling
2. Extract text, images, and tables
3. Store extracted content in database
4. Generate embeddings for text chunks
"""
from pathlib import Path
from typing import Dict, Any, List
from venv import logger
from rapidfuzz import fuzz

from sqlalchemy.orm import Session
from app.models.document import Document, DocumentChunk, DocumentImage, DocumentTable
from app.services.vector_store import VectorStore
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption, InputFormat

import re
import time
import uuid
from PIL import Image

UPLOAD_DIR = "uploads"
IMAGE_RESOLUTION_SCALE = 2.0


class DocumentProcessor:
    """
    Process PDF documents and extract multimodal content.
    
    This is a SKELETON implementation. You need to implement the core logic.
    """
    
    def __init__(self, db: Session):
        if not isinstance(db, Session):
            raise TypeError(f"Expected SQLAlchemy Session, got {type(db)}")
        self.db = db
        self.vector_store = VectorStore(db)

        tables_dir = Path(UPLOAD_DIR) / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)
        placeholder_path = tables_dir / "placeholder.png"
        if not placeholder_path.exists():
            Image.new("RGB", (1, 1), color="white").save(placeholder_path)
        self.table_placeholder_path = placeholder_path

        # Setup additional Docling converter
        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True

        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )

    async def _save_image(self, pic_item, document_id: int, doc) -> DocumentImage:
        img_dir = Path(UPLOAD_DIR) / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.png"
        path = img_dir / filename
        caption=''
        caption_method = getattr(pic_item, "caption_text", None)

        if callable(caption_method):
            try:
                caption = caption_method(doc)
                logger.info(f"1. caption_text(): {repr(caption)}")
            except Exception as e:
                logger.error(f"caption_text() call failed: {e}")
        else:
            caption = caption_method
            logger.info(f"1. caption_text (value): {repr(caption)}")

        try:
            img = pic_item.get_image(doc)
            if isinstance(img, Image.Image):
                img.save(path)
        except Exception:
            img_data = getattr(pic_item, "image_bytes", None)
            if img_data:
                with open(path, "wb") as f:
                    f.write(img_data)

        image_record = DocumentImage(
            document_id=document_id,
            page_number=getattr(pic_item, "page_number", 0),
            file_path=f"/{path}",
            caption=caption,
        )
        self.db.add(image_record)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return image_record

    async def _save_table(self, table_item, document_id: int, doc) -> DocumentTable:
        tables_dir = Path(UPLOAD_DIR) / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4().hex}.png"
        img_path = tables_dir / filename
        table_json, image_saved = {}, False

        try:
            if hasattr(table_item, "export_to_dataframe"):
                table_df = table_item.export_to_dataframe()
                table_json = table_df.to_dict(orient="records")

            if hasattr(table_item, "get_image"):
                img = table_item.get_image(doc)
                if isinstance(img, Image.Image):
                    img.save(img_path)
                    image_saved = True
        except Exception as e:
            print(f"⚠️ Table save error: {e}")
            table_json = {}

        image_path = f"/{img_path}" if image_saved else f"/{self.table_placeholder_path}"
        caption = ''
        caption_method = getattr(table_item, "caption_text", None)

        if callable(caption_method):
            try:
                caption = caption_method(doc)
                logger.info(f"1. caption_text(): {repr(caption)}")
            except Exception as e:
                logger.error(f"caption_text() call failed: {e}")
        else:
            caption = caption_method
            logger.info(f"1. caption_text (value): {repr(caption)}")
        table_record = DocumentTable(
            document_id=document_id,
            page_number=getattr(table_item, "page_number", 0),
            image_path=image_path,
            caption=caption,
            data=table_json,
        )
        self.db.add(table_record)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return table_record

    def _chunk_text(self, text: str, document_id: int, page_number: int) -> List[Dict[str, Any]]:
        """
        Merge headings with their following paragraphs and create chunks.
        """
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        merged = []

        i = 0
        while i < len(lines):
            line = lines[i]

            block = [line]
            i += 1

            # Merge with next lines if heading
            while i < len(lines):
                next_line = lines[i]
                next_is_heading = re.match(r"^\d+(\.\d+)*\s+[A-Za-z].*", next_line) or \
                                  re.match(r"^(Conclusion|Summary|Abstract)\b", next_line, re.I)
                if next_is_heading:
                    break
                block.append(next_line)
                i += 1

            merged.append(" ".join(block))

        # ---- Chunk by token limits ---- #
        chunks = []
        current_chunk = []
        token_count = 0
        max_tokens = 2048
        overlap = 1

        for block in merged:
            tokens = block.split()
            if token_count + len(tokens) > max_tokens:
                if current_chunk:
                    chunks.append({
                        "content": " ".join(current_chunk),
                        "metadata": {"document_id": document_id, "page_number": page_number},
                    })
                current_chunk = tokens[-overlap:] if overlap else []
                current_chunk.extend(tokens)
                token_count = len(current_chunk)
            else:
                current_chunk.extend(tokens)
                token_count += len(tokens)

        if current_chunk:
            chunks.append({
                "content": " ".join(current_chunk),
                "metadata": {"document_id": document_id, "page_number": page_number},
            })

        return chunks

    async def _update_document_status(self, document_id: int, status: str, error_message: str = None):
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.processing_status = status
            if error_message:
                document.error_message = error_message
            self.db.commit()

    def _merge_heading_chunks(self, chunks: list) -> list:
        """
        Merge heading-only chunks with the following chunk.
        """
        merged = []
        skip_next = False

        for i, chunk in enumerate(chunks):
            if skip_next:
                skip_next = False
                continue

            text = chunk["content"].strip()

            if re.match(r"^\d+(\.\d+)*\s+[A-Za-z].*", text) or \
                    re.match(r"^(Conclusion|Summary|Abstract)\b", text, re.I):
                if i + 1 < len(chunks):
                    next_text = chunks[i + 1]["content"]
                    merged_chunk = {
                        "content": f"{text} {next_text}",
                        "metadata": chunk["metadata"],
                    }
                    merged.append(merged_chunk)
                    skip_next = True
                else:
                    merged.append(chunk)
            else:
                merged.append(chunk)

        return merged
    async def process_document(self, file_path: str, document_id: int) -> Dict[str, Any]:
        start_time = time.time()
        try:
            await self._update_document_status(document_id, "processing")

            result = self.converter.convert(file_path)
            doc = result.document

            text_chunks, images, tables = [], [], []
            chunk_index = 0

            images_by_page = {}
            for pic_item in getattr(doc, "pictures", []):
                img_record = await self._save_image(pic_item, document_id, doc)
                images.append(img_record)
                images_by_page.setdefault(img_record.page_number, []).append({
                    "id": img_record.id,
                    "url": img_record.file_path,
                    "caption": img_record.caption,
                })

            tables_by_page = {}
            for tbl_item in getattr(doc, "tables", []):
                tbl_record = await self._save_table(tbl_item, document_id, doc)
                tables.append(tbl_record)
                tables_by_page.setdefault(tbl_record.page_number, []).append({
                    "id": tbl_record.id,
                    "url": tbl_record.image_path,
                    "caption": tbl_record.caption,
                    "data": tbl_record.data,
                })
            all_chunks = []

            for text_item in getattr(doc, "texts", []):
                content = getattr(text_item, "text", "").strip()
                if not content:
                    continue

                page_number = getattr(text_item, "page_number", 0)
                chunks = self._chunk_text(content, document_id, page_number)
                all_chunks.extend(chunks)

            all_chunks = self._merge_heading_chunks(all_chunks)
            for chunk_index, chunk in enumerate(all_chunks):
                chunk_text = chunk["content"].lower()
                page_number = chunk["metadata"]["page_number"]


                related_images = []
                for img in images_by_page.get(page_number, []):
                    caption = (img.get("caption") or "").lower().strip()
                    if not caption:
                        continue

                    # Use token_set_ratio for partial/fuzzy matching
                    similarity = fuzz.token_set_ratio(caption, chunk_text)
                    if similarity >= 70:
                        related_images.append(img)


                related_tables = []
                for tbl in tables_by_page.get(page_number, []):
                    caption = (tbl.get("caption") or "").lower().strip()
                    data = tbl.get("data") or []

                    caption_match = False
                    if caption:
                        similarity = fuzz.token_set_ratio(caption, chunk_text)
                        caption_match = similarity >= 70

                    header_match = False
                    if data and isinstance(data, list) and isinstance(data[0], list):
                        header_text = " ".join([str(h).lower() for h in data[0] if h is not None])
                        similarity = fuzz.token_set_ratio(header_text, chunk_text)
                        header_match = similarity >= 70

                    if caption_match or header_match:
                        related_tables.append(tbl)

                chunk_metadata = {
                    "document_id": document_id,
                    "page_number": page_number,
                    "related_images": related_images,
                    "related_tables": related_tables,
                }

                await self.vector_store.store_chunk(
                    content=chunk["content"],
                    document_id=document_id,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    metadata=chunk_metadata
                )

                chunk_record = DocumentChunk(
                    document_id=document_id,
                    content=chunk["content"],
                    embedding=None,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    metadata_chunk=chunk_metadata
                )
                self.db.add(chunk_record)

                chunk_index += 1

            text_chunks.extend(all_chunks)

            doc_record = self.db.query(Document).filter(Document.id == document_id).first()
            if doc_record:
                doc_record.total_pages = len(getattr(doc, "pages", []))
                doc_record.text_chunks_count = len(text_chunks)
                doc_record.images_count = len(images)
                doc_record.tables_count = len(tables)
                self.db.commit()

            await self._update_document_status(document_id, "completed")

            return {
                "status": "success",
                "pages": len(doc.pages),
                "text_chunks": len(text_chunks),
                "images": len(images),
                "tables": len(tables),
                "processing_time": round(time.time() - start_time, 2),
            }

        except Exception as e:
            await self._update_document_status(document_id, "error", str(e))
            return {"status": "error", "error": str(e)}

