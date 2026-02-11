#!/usr/bin/env python
"""
Knowledge Base Ingestion Script

Scans a directory for markdown documents, chunks them, and ingests into the vector store.

Usage:
    python scripts/ingest_knowledge.py --path ./knowledge --recursive
    python scripts/ingest_knowledge.py --path ./knowledge/product_info.md
    python scripts/ingest_knowledge.py --help
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.chunking import DocumentChunker
from services.vector_store import VectorStore


def find_markdown_files(path: str, recursive: bool = False) -> list:
    """
    Find all markdown files in a directory.

    Args:
        path: Directory or file path
        recursive: Whether to search subdirectories

    Returns:
        List of file paths
    """
    path_obj = Path(path)

    if path_obj.is_file():
        if path_obj.suffix.lower() in [".md", ".markdown"]:
            return [str(path_obj)]
        else:
            print(f"⚠️ {path} is not a markdown file")
            return []

    if path_obj.is_dir():
        if recursive:
            pattern = "**/*.md"
        else:
            pattern = "*.md"

        files = list(path_obj.glob(pattern))
        return [str(f) for f in files if f.is_file()]

    return []


def read_document(file_path: str) -> dict:
    """
    Read a markdown document and extract metadata.

    Args:
        file_path: Path to markdown file

    Returns:
        Dictionary with id, content, metadata
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Generate document ID from file path
        doc_id = Path(file_path).stem  # Filename without extension

        # Extract title from first H1 header if present
        title = doc_id
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        metadata = {
            "source": file_path,
            "title": title,
            "filename": Path(file_path).name,
        }

        return {"id": doc_id, "content": content, "metadata": metadata}

    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None


def ingest_documents(
    path: str, recursive: bool = False, chunk_size: int = 500, overlap: int = 50
):
    """
    Main ingestion function.

    Args:
        path: Directory or file path
        recursive: Whether to search subdirectories
        chunk_size: Token size per chunk
        overlap: Overlap between chunks
    """
    print(f"🔍 Scanning for markdown files in: {path}")
    print(f"   Recursive: {recursive}")
    print(f"   Chunk size: {chunk_size} tokens")
    print(f"   Overlap: {overlap} tokens\n")

    # Find all markdown files
    files = find_markdown_files(path, recursive)

    if not files:
        print("❌ No markdown files found")
        return

    print(f"✅ Found {len(files)} markdown file(s)\n")

    # Read documents
    documents = []
    for file_path in files:
        print(f"📄 Reading: {file_path}")
        doc = read_document(file_path)
        if doc:
            documents.append(doc)

    if not documents:
        print("\n❌ No documents successfully read")
        return

    print(f"\n✅ Successfully read {len(documents)} document(s)\n")

    # Chunk documents
    print(f"✂️ Chunking documents...")
    chunker = DocumentChunker(chunk_size=chunk_size, overlap=overlap)
    all_chunks = chunker.chunk_multiple_documents(documents)

    if not all_chunks:
        print("❌ No chunks generated")
        return

    print(f"✅ Generated {len(all_chunks)} chunks\n")

    # Display chunking statistics
    print("📊 Chunking Statistics:")
    for doc in documents:
        doc_chunks = [c for c in all_chunks if c["document_id"] == doc["id"]]
        print(f"   • {doc['metadata']['title']}: {len(doc_chunks)} chunks")

    print()

    # Ingest into vector store
    print("💾 Ingesting into vector store...")
    vector_store = VectorStore()

    success = vector_store.ingest_documents(all_chunks)

    if success:
        print("\n✅ Ingestion complete!\n")

        # Show vector store stats
        stats = vector_store.get_stats()
        print("📊 Vector Store Statistics:")
        print(f"   • Total chunks: {stats['total_chunks']}")
        print(f"   • Total documents: {stats['total_documents']}")
        print(f"   • Mode: {'Mock (in-memory)' if vector_store.is_mock else 'Snowflake'}")

        if vector_store.is_mock:
            print(
                "\n💡 Tip: Set Snowflake credentials in .env to use persistent storage"
            )

    else:
        print("\n❌ Ingestion failed")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest markdown documents into Elli knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest all files in knowledge directory (non-recursive)
  python scripts/ingest_knowledge.py --path ./knowledge

  # Ingest all files recursively
  python scripts/ingest_knowledge.py --path ./knowledge --recursive

  # Ingest a single file
  python scripts/ingest_knowledge.py --path ./knowledge/product_info.md

  # Custom chunk size
  python scripts/ingest_knowledge.py --path ./knowledge --chunk-size 800 --overlap 100
        """,
    )

    parser.add_argument(
        "--path",
        required=True,
        help="Path to directory or markdown file",
    )

    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively search subdirectories",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Target chunk size in tokens (default: 500)",
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Overlap between chunks in tokens (default: 50)",
    )

    args = parser.parse_args()

    # Validate path exists
    if not os.path.exists(args.path):
        print(f"❌ Error: Path does not exist: {args.path}")
        sys.exit(1)

    # Run ingestion
    try:
        ingest_documents(
            path=args.path,
            recursive=args.recursive,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
        )
    except KeyboardInterrupt:
        print("\n\n⚠️ Ingestion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
