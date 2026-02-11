import os
from typing import List, Dict, Optional
import json
from services.logger import logger


class VectorStore:
    """
    Vector store for semantic search over document chunks.

    Supports Snowflake Cortex Vector Search (primary) with mock fallback.
    """

    def __init__(
        self,
        user: Optional[str] = None,
        password: Optional[str] = None,
        account: Optional[str] = None,
        warehouse: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        role: Optional[str] = None,
    ):
        """
        Initialize vector store with Snowflake connection.

        Args:
            user: Snowflake username (optional, defaults to env var)
            password: Snowflake password (optional, defaults to env var)
            account: Snowflake account identifier (optional, defaults to env var)
            warehouse: Snowflake warehouse (optional, defaults to env var)
            database: Snowflake database (optional, defaults to env var)
            schema: Snowflake schema (optional, defaults to env var)
            role: Snowflake role (optional, defaults to env var)
        """
        self.user = user or os.environ.get("SNOWFLAKE_USER")
        self.password = password or os.environ.get("SNOWFLAKE_PASSWORD")
        self.account = account or os.environ.get("SNOWFLAKE_ACCOUNT")
        self.warehouse = warehouse or os.environ.get("SNOWFLAKE_WAREHOUSE")
        self.database = database or os.environ.get("SNOWFLAKE_DATABASE", "ELLI_DB")
        self.schema = schema or os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC")
        self.role = role or os.environ.get("SNOWFLAKE_ROLE")

        # Try to initialize Snowflake connection
        self.connection = None
        self.is_mock = True
        self.mock_chunks = []  # In-memory storage for mock mode

        if all([self.user, self.password, self.account, self.warehouse]):
            try:
                import snowflake.connector

                self.connection = snowflake.connector.connect(
                    user=self.user,
                    password=self.password,
                    account=self.account,
                    warehouse=self.warehouse,
                    database=self.database,
                    schema=self.schema,
                    role=self.role,
                )
                self.is_mock = False
                logger.info("Connected to Snowflake for vector storage", service="vector_store", mode="real")

                # Initialize tables if needed
                self._initialize_tables()

            except ImportError:
                logger.warning(
                    "snowflake-connector-python not installed, using mock vector store",
                    service="vector_store"
                )
            except Exception as e:
                logger.error(f"Could not connect to Snowflake: {e}", service="vector_store", error=str(e))
        else:
            logger.info("Snowflake credentials not found, using mock vector store", service="vector_store", mode="mock")

    def _initialize_tables(self):
        """Create vector store tables if they don't exist."""
        if not self.connection or self.is_mock:
            return

        try:
            cursor = self.connection.cursor()

            # Create knowledge base table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS elli_knowledge_base (
                    chunk_id VARCHAR PRIMARY KEY,
                    document_id VARCHAR,
                    content TEXT,
                    metadata VARIANT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
                )
            """
            )

            cursor.close()
            logger.info("Vector store tables initialized", service="vector_store")

        except Exception as e:
            logger.error(f"Could not initialize tables: {e}", service="vector_store", error=str(e))

    def ingest_documents(self, chunks: List[Dict]) -> bool:
        """
        Ingest document chunks into vector store.

        Args:
            chunks: List of chunk dictionaries from DocumentChunker

        Returns:
            Success boolean
        """
        if not chunks:
            logger.warning("No chunks to ingest", service="vector_store")
            return False

        if not self.is_mock and self.connection:
            return self._ingest_snowflake(chunks)
        else:
            return self._ingest_mock(chunks)

    def _ingest_snowflake(self, chunks: List[Dict]) -> bool:
        """Ingest chunks into Snowflake vector store."""
        try:
            cursor = self.connection.cursor()

            # Insert chunks into table
            for chunk in chunks:
                chunk_id = chunk["chunk_id"]
                document_id = chunk["document_id"]
                content = chunk["content"]
                metadata = json.dumps(chunk.get("metadata", {}))

                cursor.execute(
                    """
                    INSERT INTO elli_knowledge_base (chunk_id, document_id, content, metadata)
                    VALUES (%s, %s, %s, PARSE_JSON(%s))
                """,
                    (chunk_id, document_id, content, metadata),
                )

            self.connection.commit()
            cursor.close()

            logger.info(f"Ingested {len(chunks)} chunks into Snowflake vector store", service="vector_store", chunks_count=len(chunks))
            return True

        except Exception as e:
            logger.error(f"Error ingesting chunks: {e}", service="vector_store", error=str(e))
            return False

    def _ingest_mock(self, chunks: List[Dict]) -> bool:
        """Ingest chunks into mock in-memory store."""
        self.mock_chunks.extend(chunks)
        logger.info(
            f"Ingested {len(chunks)} chunks into mock vector store (total: {len(self.mock_chunks)})",
            service="vector_store",
            chunks_count=len(chunks),
            total_chunks=len(self.mock_chunks)
        )
        return True

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Semantic search for relevant document chunks.

        Args:
            query: User's question
            top_k: Number of results to return

        Returns:
            List of chunks with relevance scores:
            [{"content": "...", "score": 0.95, "chunk_id": "...", "metadata": {...}}]
        """
        if not self.is_mock and self.connection:
            return self._search_snowflake(query, top_k)
        else:
            return self._search_mock(query, top_k)

    def _search_snowflake(self, query: str, top_k: int) -> List[Dict]:
        """
        Search using Snowflake Cortex embeddings and cosine similarity.

        Note: Requires Snowflake Cortex Search Service (Enterprise feature).
        For simpler implementation, we use direct embedding comparison.
        """
        try:
            cursor = self.connection.cursor()

            # Generate embedding for query using Snowflake Cortex
            query_embedding_sql = """
                SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', %s) as embedding
            """
            cursor.execute(query_embedding_sql, (query,))
            query_embedding_result = cursor.fetchone()

            if not query_embedding_result:
                logger.warning("Could not generate query embedding", service="vector_store")
                return []

            query_embedding = query_embedding_result[0]

            # Search for similar chunks using cosine similarity
            # Note: This is a simplified version. Production should use Cortex Search Service
            search_sql = """
                SELECT
                    chunk_id,
                    document_id,
                    content,
                    metadata,
                    VECTOR_COSINE_SIMILARITY(
                        SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', content),
                        %s
                    ) as score
                FROM elli_knowledge_base
                ORDER BY score DESC
                LIMIT %s
            """

            cursor.execute(search_sql, (query_embedding, top_k))
            results = cursor.fetchall()
            cursor.close()

            # Format results
            formatted_results = []
            for row in results:
                formatted_results.append(
                    {
                        "chunk_id": row[0],
                        "document_id": row[1],
                        "content": row[2],
                        "metadata": json.loads(row[3]) if row[3] else {},
                        "score": float(row[4]),
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error(f"Snowflake search error: {e}, falling back to mock search", service="vector_store", error=str(e))
            return self._search_mock(query, top_k)

    def _search_mock(self, query: str, top_k: int) -> List[Dict]:
        """
        Mock semantic search using keyword matching.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of matching chunks with mock scores
        """
        if not self.mock_chunks:
            logger.debug("No chunks in mock store", service="vector_store")
            return []

        # Simple keyword-based scoring
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []
        for chunk in self.mock_chunks:
            content_lower = chunk["content"].lower()
            content_words = set(content_lower.split())

            # Calculate simple overlap score
            overlap = len(query_words.intersection(content_words))
            total_query_words = len(query_words)

            if total_query_words > 0:
                score = overlap / total_query_words
            else:
                score = 0.0

            # Add bonus for exact phrase matches
            if query_lower in content_lower:
                score += 0.3

            if score > 0:
                results.append(
                    {
                        "chunk_id": chunk["chunk_id"],
                        "document_id": chunk["document_id"],
                        "content": chunk["content"],
                        "metadata": chunk.get("metadata", {}),
                        "score": min(score, 1.0),  # Cap at 1.0
                    }
                )

        # Sort by score and return top K
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """
        Retrieve a specific chunk by ID.

        Args:
            chunk_id: Chunk identifier

        Returns:
            Chunk dictionary or None if not found
        """
        if not self.is_mock and self.connection:
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    SELECT chunk_id, document_id, content, metadata
                    FROM elli_knowledge_base
                    WHERE chunk_id = %s
                """,
                    (chunk_id,),
                )
                result = cursor.fetchone()
                cursor.close()

                if result:
                    return {
                        "chunk_id": result[0],
                        "document_id": result[1],
                        "content": result[2],
                        "metadata": json.loads(result[3]) if result[3] else {},
                    }
            except Exception as e:
                logger.error(f"Error retrieving chunk: {e}", service="vector_store", error=str(e))
                return None
        else:
            # Mock mode
            for chunk in self.mock_chunks:
                if chunk["chunk_id"] == chunk_id:
                    return chunk
            return None

    def delete_document(self, document_id: str) -> bool:
        """
        Delete all chunks for a document.

        Args:
            document_id: Document identifier

        Returns:
            Success boolean
        """
        if not self.is_mock and self.connection:
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    "DELETE FROM elli_knowledge_base WHERE document_id = %s",
                    (document_id,),
                )
                deleted_count = cursor.rowcount
                self.connection.commit()
                cursor.close()

                logger.info(f"Deleted {deleted_count} chunks for document {document_id}", service="vector_store", document_id=document_id, deleted_count=deleted_count)
                return True

            except Exception as e:
                logger.error(f"Error deleting document: {e}", service="vector_store", error=str(e))
                return False
        else:
            # Mock mode
            original_count = len(self.mock_chunks)
            self.mock_chunks = [
                c for c in self.mock_chunks if c["document_id"] != document_id
            ]
            deleted_count = original_count - len(self.mock_chunks)
            logger.info(f"Deleted {deleted_count} chunks for document {document_id}", service="vector_store", document_id=document_id, deleted_count=deleted_count)
            return True

    def get_stats(self) -> Dict:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with stats: total_chunks, total_documents
        """
        if not self.is_mock and self.connection:
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_chunks,
                        COUNT(DISTINCT document_id) as total_documents
                    FROM elli_knowledge_base
                """
                )
                result = cursor.fetchone()
                cursor.close()

                return {"total_chunks": result[0], "total_documents": result[1]}

            except Exception as e:
                logger.error(f"Error getting stats: {e}", service="vector_store", error=str(e))
                return {"total_chunks": 0, "total_documents": 0}
        else:
            # Mock mode
            unique_docs = set(c["document_id"] for c in self.mock_chunks)
            return {
                "total_chunks": len(self.mock_chunks),
                "total_documents": len(unique_docs),
            }

    def close(self):
        """Close the Snowflake connection."""
        if self.connection:
            self.connection.close()
            logger.info("Vector store connection closed", service="vector_store")

    def __del__(self):
        """Cleanup connection on deletion."""
        self.close()
