import re
from typing import List, Dict, Optional
from services.logger import logger


class DocumentChunker:
    """
    Chunks documents into smaller segments for vector embedding and retrieval.

    Uses token-based chunking with overlap to preserve context across chunk boundaries.
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Initialize the document chunker.

        Args:
            chunk_size: Target size in tokens per chunk (default 500)
            overlap: Number of overlapping tokens between chunks (default 50)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_document(
        self, content: str, document_id: str, metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Split document into overlapping chunks.

        Args:
            content: The document text to chunk
            document_id: Unique identifier for the document
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with structure:
            [{"chunk_id": "doc1_chunk_0", "content": "...", "document_id": "doc1",
              "start": 0, "end": 500, "metadata": {...}}]
        """
        if not content or not content.strip():
            return []

        # Split into sentences for better boundary preservation
        sentences = self._split_into_sentences(content)

        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)

            # If adding this sentence would exceed chunk_size, create a chunk
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Create chunk from accumulated sentences
                chunk_content = " ".join(current_chunk)
                chunks.append(
                    self._create_chunk(
                        chunk_content, document_id, chunk_index, metadata
                    )
                )
                chunk_index += 1

                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk, self.overlap
                )
                current_chunk = overlap_sentences
                current_tokens = sum(
                    self._estimate_tokens(s) for s in overlap_sentences
                )

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Add final chunk if there's remaining content
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            chunks.append(
                self._create_chunk(chunk_content, document_id, chunk_index, metadata)
            )

        return chunks

    def chunk_multiple_documents(
        self, documents: List[Dict]
    ) -> List[Dict]:
        """
        Chunk multiple documents in batch.

        Args:
            documents: List of dicts with keys: "id", "content", "metadata" (optional)

        Returns:
            Flat list of all chunks from all documents
        """
        all_chunks = []

        for doc in documents:
            doc_id = doc.get("id")
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            if not doc_id:
                logger.warning("Skipping document without ID", service="chunking")
                continue

            chunks = self.chunk_document(content, doc_id, metadata)
            all_chunks.extend(chunks)

        return all_chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences while preserving markdown headers and lists.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Preserve markdown headers as complete units
        lines = text.split("\n")
        sentences = []

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Preserve markdown headers as single units
            if line.startswith("#"):
                sentences.append(line)
                continue

            # Preserve list items as single units
            if re.match(r"^[\*\-\+]\s", line) or re.match(r"^\d+\.\s", line):
                sentences.append(line)
                continue

            # Split regular text into sentences
            # Simple sentence splitting on ., !, ?
            sentence_parts = re.split(r"(?<=[.!?])\s+", line)
            sentences.extend([s.strip() for s in sentence_parts if s.strip()])

        return sentences

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses simple heuristic: ~0.75 tokens per word.
        For more accurate counting, use tiktoken library.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        words = text.split()
        return int(len(words) * 0.75)

    def _get_overlap_sentences(
        self, sentences: List[str], target_overlap_tokens: int
    ) -> List[str]:
        """
        Get last N sentences that fit within target overlap size.

        Args:
            sentences: List of sentences
            target_overlap_tokens: Target number of tokens for overlap

        Returns:
            List of sentences for overlap
        """
        overlap_sentences = []
        overlap_tokens = 0

        # Work backwards from end of sentences
        for sentence in reversed(sentences):
            sentence_tokens = self._estimate_tokens(sentence)

            if overlap_tokens + sentence_tokens > target_overlap_tokens:
                break

            overlap_sentences.insert(0, sentence)
            overlap_tokens += sentence_tokens

        return overlap_sentences

    def _create_chunk(
        self, content: str, document_id: str, chunk_index: int, metadata: Optional[Dict]
    ) -> Dict:
        """
        Create chunk dictionary with standard structure.

        Args:
            content: Chunk content
            document_id: Parent document ID
            chunk_index: Index of this chunk within document
            metadata: Optional metadata

        Returns:
            Chunk dictionary
        """
        chunk_id = f"{document_id}_chunk_{chunk_index}"

        chunk = {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "content": content,
            "chunk_index": chunk_index,
            "token_count": self._estimate_tokens(content),
        }

        if metadata:
            chunk["metadata"] = metadata

        return chunk


# Simple mock tokenizer for testing without tiktoken
def estimate_tokens_simple(text: str) -> int:
    """
    Simple token estimation without external dependencies.

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    # Rough approximation: 0.75 tokens per word
    words = text.split()
    return int(len(words) * 0.75)
