"""Standalone async script for ingesting documents into the knowledge base."""

import argparse
import asyncio
import hashlib
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# Ensure app imports work when running as a standalone script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.db.models.knowledge import KnowledgeChunk
from app.rag.chunker import Chunk, DocumentChunker
from app.rag.embeddings import EmbeddingService
from app.rag.vector_store import Point, QdrantStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ingest")


# ------------------------------------------------------------------
# File reading
# ------------------------------------------------------------------


def read_text_file(filepath: Path) -> str:
    """Read a text file (.md, .txt)."""
    return filepath.read_text(encoding="utf-8")


def read_pdf_file(filepath: Path) -> str:
    """Read a PDF file using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF (fitz) is required for PDF ingestion. "
            "Install it with: pip install PyMuPDF"
        ) from exc

    text_parts: List[str] = []
    with fitz.open(filepath) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n\n".join(text_parts)


def read_docx_file(filepath: Path) -> str:
    """Read a .docx file using python-docx."""
    try:
        from docx import Document
    except ImportError as exc:
        raise ImportError(
            "python-docx is required for DOCX ingestion. "
            "Install it with: pip install python-docx"
        ) from exc

    doc = Document(str(filepath))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def read_file(filepath: Path) -> str:
    """Auto-detect file type and read content."""
    suffix = filepath.suffix.lower()
    if suffix in (".md", ".txt"):
        return read_text_file(filepath)
    if suffix == ".pdf":
        return read_pdf_file(filepath)
    if suffix == ".docx":
        return read_docx_file(filepath)
    raise ValueError(f"Unsupported file type: {suffix}")


# ------------------------------------------------------------------
# Deduplication
# ------------------------------------------------------------------


def compute_content_hash(text: str) -> str:
    """Compute a SHA-256 hash of the text for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def get_existing_hashes(session: AsyncSession) -> set[str]:
    """Fetch all existing content hashes from the knowledge base."""
    result = await session.execute(select(KnowledgeChunk.content_hash))
    return {row[0] for row in result.all()}


# ------------------------------------------------------------------
# Ingestion
# ------------------------------------------------------------------


async def ingest_documents(
    directory: Path,
    collection: str,
    chunker: DocumentChunker,
    embedder: EmbeddingService,
    vector_store: QdrantStore,
    session: AsyncSession,
) -> None:
    """Ingest all supported documents from a directory."""
    files = sorted(
        f
        for f in directory.rglob("*")
        if f.is_file() and f.suffix.lower() in (".md", ".txt", ".pdf", ".docx")
    )

    if not files:
        logger.warning("No supported documents found in %s", directory)
        return

    logger.info("Found %d files to ingest", len(files))

    existing_hashes = await get_existing_hashes(session)
    logger.info("Loaded %d existing content hashes", len(existing_hashes))

    all_chunks: List[Chunk] = []

    # Step 1: Read and chunk all files
    for filepath in files:
        try:
            text = read_file(filepath)
        except Exception as exc:
            logger.error("Failed to read %s: %s", filepath, exc)
            continue

        relative = str(filepath.relative_to(directory))
        meta = {"source": relative, "chapter": filepath.parent.name or "root"}
        chunks = chunker.chunk_document(text, strategy="headings", metadata=meta)

        if not chunks:
            logger.warning("No chunks produced for %s", filepath)
            continue

        logger.info("File %s -> %d chunks", relative, len(chunks))
        all_chunks.extend(chunks)

    if not all_chunks:
        logger.warning("No chunks to ingest after processing")
        return

    # Step 2: Deduplicate and filter existing chunks
    new_chunks: List[Chunk] = []
    skipped = 0
    for chunk in all_chunks:
        content_hash = compute_content_hash(chunk.text)
        if content_hash in existing_hashes:
            skipped += 1
            continue
        new_chunks.append(chunk)

    if skipped:
        logger.info("Skipped %d existing chunks", skipped)

    if not new_chunks:
        logger.info("All chunks already exist in the knowledge base")
        return

    logger.info("Embedding %d new chunks in batches of %d", len(new_chunks), embedder.batch_size)

    # Step 3: Batch embed new chunks
    all_embeddings: List[List[float]] = []
    for i in range(0, len(new_chunks), embedder.batch_size):
        batch = new_chunks[i : i + embedder.batch_size]
        texts = [c.text for c in batch]
        try:
            embeddings = await embedder.embed(texts)
        except Exception as exc:
            logger.error("Batch embedding failed for chunk %d-%d: %s", i, i + len(batch), exc)
            # Pad with zero vectors so we can continue
            embeddings = [[0.0] * embedder.dimensions] * len(batch)
        all_embeddings.extend(embeddings)

    # Step 4: Store in Qdrant and MySQL
    points: List[Point] = []
    knowledge_chunks: List[KnowledgeChunk] = []

    for chunk, vector in zip(new_chunks, all_embeddings):
        content_hash = compute_content_hash(chunk.text)
        payload = {
            "source": chunk.metadata.get("source", ""),
            "chapter": chunk.metadata.get("chapter", ""),
            "heading": chunk.metadata.get("heading", ""),
            "content": chunk.text[:500],  # Store preview in payload
        }
        points.append(Point(id=chunk.chunk_id, vector=vector, payload=payload))

        knowledge_chunks.append(
            KnowledgeChunk(
                chunk_id=chunk.chunk_id,
                source=chunk.metadata.get("source", ""),
                chapter=chunk.metadata.get("chapter", ""),
                knowledge_point=chunk.metadata.get("heading", "general"),
                difficulty=0.5,
                content=chunk.text,
                content_hash=content_hash,
                created_at=datetime.utcnow(),
            )
        )

    # Store in Qdrant
    try:
        await vector_store.add(collection, points)
        logger.info("Stored %d points in Qdrant collection '%s'", len(points), collection)
    except Exception as exc:
        logger.error("Failed to store points in Qdrant: %s", exc)
        raise

    # Store in MySQL
    for kc in knowledge_chunks:
        session.add(kc)
    await session.commit()
    logger.info("Stored %d chunks in MySQL knowledge_chunks table", len(knowledge_chunks))


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest documents into the EduAgent knowledge base"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Directory containing documents to ingest (not required with --stats)",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="course_materials",
        help="Qdrant collection name (default: course_materials)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Chunk size in characters (default: 512)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=128,
        help="Chunk overlap in characters (default: 128)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="deepseek",
        choices=["deepseek", "local"],
        help="Embedding provider (default: deepseek)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the Qdrant collection before ingestion",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show collection statistics instead of running ingestion",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if args.stats:
        from qdrant_client import QdrantClient
        settings = get_settings()
        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        try:
            collections = client.get_collections().collections
            for col in collections:
                info = client.get_collection(col.name)
                count = client.count(col.name).count
                print(f"  集合: {col.name}")
                print(f"  向量数: {count}")
                print(f"  向量维度: {info.config.params.vectors.size}")
                print(f"  距离算法: {info.config.params.vectors.distance}")
                print()
            if not collections:
                print("  知识库为空，请先运行导入: python scripts/ingest.py --dir docs/test_data")
        finally:
            client.close()
        return

    if not args.dir.exists() or not args.dir.is_dir():
        logger.error("Directory does not exist: %s", args.dir)
        sys.exit(1)

    chunker = DocumentChunker(chunk_size=args.chunk_size, overlap=args.overlap)
    embedder = EmbeddingService(provider=args.provider)
    vector_store = QdrantStore()

    if args.rebuild:
        logger.info("Rebuilding Qdrant collection: %s", args.collection)
        await vector_store.rebuild(args.collection)

    async with async_session_factory() as session:
        try:
            await ingest_documents(
                directory=args.dir,
                collection=args.collection,
                chunker=chunker,
                embedder=embedder,
                vector_store=vector_store,
                session=session,
            )
        except Exception as exc:
            logger.error("Ingestion failed: %s", exc)
            await session.rollback()
            raise
        finally:
            await session.close()

    await embedder.close()
    logger.info("Ingestion complete")


if __name__ == "__main__":
    asyncio.run(main())
