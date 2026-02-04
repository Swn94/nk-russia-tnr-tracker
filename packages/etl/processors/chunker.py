"""Document chunking processor using chunklet-py."""

import re
from typing import Optional
from dataclasses import dataclass

import structlog

from packages.core.utils.config import get_settings

logger = structlog.get_logger()


@dataclass
class Chunk:
    """Represents a document chunk."""
    content: str
    index: int
    start_char: int
    end_char: int
    token_count: int
    metadata: dict


class DocumentChunker:
    """Chunk documents for processing and embedding."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size_tokens
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap_tokens

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: ~4 chars per token)."""
        return len(text) // 4

    def _split_by_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_by_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        paragraphs = re.split(r'\n\n+', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def chunk_text(
        self,
        text: str,
        source_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> list[Chunk]:
        """
        Chunk text into smaller pieces.

        Args:
            text: Text to chunk
            source_id: Optional source identifier
            metadata: Optional metadata to include in chunks

        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            return []

        base_metadata = metadata or {}
        if source_id:
            base_metadata["source_id"] = source_id

        chunks = []
        current_chunk = []
        current_tokens = 0
        char_position = 0

        # Split by paragraphs first for better context preservation
        paragraphs = self._split_by_paragraphs(text)

        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)

            # If single paragraph exceeds chunk size, split by sentences
            if para_tokens > self.chunk_size:
                sentences = self._split_by_sentences(para)
                for sentence in sentences:
                    sentence_tokens = self._estimate_tokens(sentence)

                    if current_tokens + sentence_tokens > self.chunk_size:
                        if current_chunk:
                            chunk_text = " ".join(current_chunk)
                            chunks.append(Chunk(
                                content=chunk_text,
                                index=len(chunks),
                                start_char=char_position - len(chunk_text),
                                end_char=char_position,
                                token_count=current_tokens,
                                metadata={**base_metadata, "chunk_index": len(chunks)},
                            ))

                            # Keep overlap
                            overlap_text = chunk_text[-self.chunk_overlap * 4:] if self.chunk_overlap else ""
                            current_chunk = [overlap_text] if overlap_text else []
                            current_tokens = self._estimate_tokens(overlap_text)

                    current_chunk.append(sentence)
                    current_tokens += sentence_tokens
                    char_position += len(sentence) + 1

            else:
                if current_tokens + para_tokens > self.chunk_size:
                    if current_chunk:
                        chunk_text = "\n\n".join(current_chunk)
                        chunks.append(Chunk(
                            content=chunk_text,
                            index=len(chunks),
                            start_char=char_position - len(chunk_text),
                            end_char=char_position,
                            token_count=current_tokens,
                            metadata={**base_metadata, "chunk_index": len(chunks)},
                        ))

                        # Keep overlap
                        overlap_text = chunk_text[-self.chunk_overlap * 4:] if self.chunk_overlap else ""
                        current_chunk = [overlap_text] if overlap_text else []
                        current_tokens = self._estimate_tokens(overlap_text)

                current_chunk.append(para)
                current_tokens += para_tokens
                char_position += len(para) + 2

        # Add remaining content
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(Chunk(
                content=chunk_text,
                index=len(chunks),
                start_char=char_position - len(chunk_text),
                end_char=char_position,
                token_count=current_tokens,
                metadata={**base_metadata, "chunk_index": len(chunks)},
            ))

        logger.info(
            "Document chunked",
            total_chunks=len(chunks),
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
        )

        return chunks

    def chunk_markdown(
        self,
        markdown_text: str,
        source_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> list[Chunk]:
        """
        Chunk markdown text, preserving header hierarchy.

        Args:
            markdown_text: Markdown text to chunk
            source_id: Optional source identifier
            metadata: Optional metadata

        Returns:
            List of Chunk objects
        """
        if not markdown_text or not markdown_text.strip():
            return []

        base_metadata = metadata or {}
        if source_id:
            base_metadata["source_id"] = source_id

        chunks = []

        # Split by headers
        header_pattern = r'^(#{1,6})\s+(.+)$'
        sections = re.split(r'(?=^#{1,6}\s+)', markdown_text, flags=re.MULTILINE)

        current_headers = {}
        char_position = 0

        for section in sections:
            if not section.strip():
                continue

            # Extract header if present
            header_match = re.match(header_pattern, section, re.MULTILINE)
            if header_match:
                level = len(header_match.group(1))
                header_text = header_match.group(2)
                current_headers[level] = header_text
                # Clear lower level headers
                for l in list(current_headers.keys()):
                    if l > level:
                        del current_headers[l]

            section_tokens = self._estimate_tokens(section)

            # If section is small enough, add as single chunk
            if section_tokens <= self.chunk_size:
                chunks.append(Chunk(
                    content=section,
                    index=len(chunks),
                    start_char=char_position,
                    end_char=char_position + len(section),
                    token_count=section_tokens,
                    metadata={
                        **base_metadata,
                        "chunk_index": len(chunks),
                        "headers": dict(current_headers),
                    },
                ))
            else:
                # Split large sections
                sub_chunks = self.chunk_text(
                    section,
                    source_id=source_id,
                    metadata={
                        **base_metadata,
                        "headers": dict(current_headers),
                    },
                )
                for sub_chunk in sub_chunks:
                    sub_chunk.index = len(chunks)
                    sub_chunk.start_char += char_position
                    sub_chunk.end_char += char_position
                    chunks.append(sub_chunk)

            char_position += len(section)

        logger.info(
            "Markdown chunked",
            total_chunks=len(chunks),
            chunk_size=self.chunk_size,
        )

        return chunks

    def to_dict_list(self, chunks: list[Chunk]) -> list[dict]:
        """Convert chunks to list of dictionaries."""
        return [
            {
                "content": chunk.content,
                "index": chunk.index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ]
