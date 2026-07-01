"""Document chunking strategies for the RAG pipeline."""

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal


@dataclass
class Chunk:
    """A single document chunk with metadata."""

    text: str
    chunk_id: str
    metadata: Dict[str, str] = field(default_factory=dict)


class DocumentChunker:
    """Configurable document chunker with multiple strategies."""

    def __init__(self, chunk_size: int = 512, overlap: int = 128) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_document(
        self,
        text: str,
        strategy: Literal["headings", "paragraphs", "semantic"] = "headings",
        metadata: Dict[str, str] | None = None,
    ) -> List[Chunk]:
        """Chunk a document using the selected strategy."""
        if not text or not text.strip():
            return []

        base_meta = metadata or {}

        if strategy == "headings":
            raw_chunks = self._by_headings(text)
        elif strategy == "paragraphs":
            raw_chunks = self._by_paragraphs(text)
        elif strategy == "semantic":
            raw_chunks = self._by_semantic_boundaries(text)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

        chunks: List[Chunk] = []
        for idx, (chunk_text, chunk_meta) in enumerate(raw_chunks):
            merged_meta = {**base_meta, **chunk_meta}
            chunk_id = self._make_chunk_id(chunk_text, merged_meta, idx)
            chunks.append(Chunk(text=chunk_text, chunk_id=chunk_id, metadata=merged_meta))

        return chunks

    def chunk_file(self, filepath: str | Path) -> List[Chunk]:
        """Auto-detect file type and chunk accordingly."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        text = path.read_text(encoding="utf-8")
        suffix = path.suffix.lower()

        base_meta: Dict[str, str] = {"source": str(path)}

        if suffix == ".md":
            strategy: Literal["headings", "paragraphs", "semantic"] = "headings"
        elif suffix == ".txt":
            strategy = "paragraphs"
        else:
            strategy = "semantic"

        return self.chunk_document(text, strategy=strategy, metadata=base_meta)

    # ------------------------------------------------------------------
    # Chunking strategies
    # ------------------------------------------------------------------

    def _by_headings(self, text: str) -> List[tuple[str, Dict[str, str]]]:
        """Split by markdown headings (##, ###, etc.), keep heading as prefix."""
        heading_pattern = re.compile(r"^(#{1,6}\s+.+)$", re.MULTILINE)
        matches = list(heading_pattern.finditer(text))

        if not matches:
            # No headings found: fall back to paragraphs
            return self._by_paragraphs(text)

        chunks: List[tuple[str, Dict[str, str]]] = []
        for i, match in enumerate(matches):
            heading = match.group(1).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()

            if not body:
                continue

            # If body exceeds chunk_size, split further at paragraph boundaries
            if len(body) > self.chunk_size:
                sub_chunks = self._split_at_size(body, self.chunk_size, self.overlap)
                for sub in sub_chunks:
                    prefixed = f"{heading}\n\n{sub}" if sub else heading
                    chunks.append((prefixed, {"heading": heading}))
            else:
                chunks.append((body, {"heading": heading}))

        return chunks

    def _by_paragraphs(self, text: str) -> List[tuple[str, Dict[str, str]]]:
        """Split by double newlines, merge small paragraphs to meet chunk_size."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        chunks: List[tuple[str, Dict[str, str]]] = []
        current: List[str] = []
        current_len = 0

        for para in paragraphs:
            para_len = len(para)

            # Very long paragraph: split it first
            if para_len > self.chunk_size:
                if current:
                    chunks.append(("\n\n".join(current), {}))
                    current = []
                    current_len = 0

                sub_chunks = self._split_at_size(para, self.chunk_size, self.overlap)
                for sub in sub_chunks:
                    chunks.append((sub, {}))
                continue

            if current_len + para_len + (2 * len(current)) <= self.chunk_size:
                current.append(para)
                current_len += para_len
            else:
                if current:
                    chunks.append(("\n\n".join(current), {}))
                current = [para]
                current_len = para_len

        if current:
            chunks.append(("\n\n".join(current), {}))

        return chunks

    def _by_semantic_boundaries(self, text: str) -> List[tuple[str, Dict[str, str]]]:
        """Split at sentence boundaries near chunk_size."""
        sentences = self._split_sentences(text)
        if not sentences:
            return []

        chunks: List[tuple[str, Dict[str, str]]] = []
        current: List[str] = []
        current_len = 0

        for sent in sentences:
            sent_len = len(sent)

            if sent_len > self.chunk_size:
                if current:
                    chunks.append((" ".join(current), {}))
                    current = []
                    current_len = 0

                sub_chunks = self._split_at_size(sent, self.chunk_size, self.overlap)
                for sub in sub_chunks:
                    chunks.append((sub, {}))
                continue

            if current_len + sent_len + len(current) <= self.chunk_size:
                current.append(sent)
                current_len += sent_len
            else:
                if current:
                    chunks.append((" ".join(current), {}))
                current = [sent]
                current_len = sent_len

        if current:
            chunks.append((" ".join(current), {}))

        return chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences using a simple regex heuristic."""
        sentence_endings = re.compile(r"(?<=[.!?。！？])\s+")
        return [s.strip() for s in sentence_endings.split(text) if s.strip()]

    @staticmethod
    def _split_at_size(text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into fixed-size chunks with overlap."""
        if len(text) <= chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
            if start >= len(text):
                break

        return chunks

    @staticmethod
    def _make_chunk_id(text: str, metadata: Dict[str, str], index: int) -> str:
        """Generate a deterministic chunk ID from content and metadata."""
        source = metadata.get("source", "")
        heading = metadata.get("heading", "")
        content = f"{source}:{heading}:{index}:{text[:200]}"
        hash_hex = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return f"chunk-{hash_hex}-{str(uuid.uuid4())[:8]}"
