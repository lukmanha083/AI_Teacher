"""
DuckDB Vector Store for POC
Embedded vector database using DuckDB with VSS extension
"""

import duckdb
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from loguru import logger


class DuckDBVectorStore:
    """
    Vector store implementation using DuckDB with VSS extension
    For POC/Development - will migrate to Cassandra in production
    """

    def __init__(self, db_path: str = "ai_teacher.duckdb", embedding_dim: int = 768):
        """
        Initialize DuckDB vector store

        Args:
            db_path: Path to DuckDB database file
            embedding_dim: Dimension of embeddings (default: 768 for mpnet)
        """
        self.db_path = Path(db_path)
        self.embedding_dim = embedding_dim
        self.conn = None
        self._connect()
        self._setup_vss()
        self._create_tables()

    def _connect(self):
        """Connect to DuckDB database"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = duckdb.connect(str(self.db_path))
            logger.info(f"Connected to DuckDB at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to DuckDB: {e}")
            raise

    def _setup_vss(self):
        """Install and load VSS extension"""
        try:
            # Try to install (will skip if already installed)
            self.conn.execute("INSTALL vss;")
            logger.info("VSS extension installed")
        except Exception as e:
            logger.debug(f"VSS extension already installed: {e}")

        try:
            # Load the extension
            self.conn.execute("LOAD vss;")
            logger.info("VSS extension loaded")
        except Exception as e:
            logger.error(f"Failed to load VSS extension: {e}")
            raise

    def _create_tables(self):
        """Create embeddings table with HNSW index"""
        try:
            # Create main embeddings table
            self.conn.execute(f"""
                CREATE TABLE IF NOT EXISTS document_embeddings (
                    id INTEGER PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding FLOAT[{self.embedding_dim}],
                    subject VARCHAR,
                    grade INTEGER,
                    chapter VARCHAR,
                    topic VARCHAR,
                    source_file VARCHAR,
                    page_number INTEGER,
                    chunk_index INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created document_embeddings table")

            # Create HNSW index for fast similarity search
            try:
                self.conn.execute("""
                    CREATE INDEX IF NOT EXISTS embedding_hnsw_idx
                    ON document_embeddings
                    USING HNSW (embedding)
                """)
                logger.info("Created HNSW index on embeddings")
            except Exception as e:
                logger.warning(f"HNSW index might already exist: {e}")

            # Create metadata indexes
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_subject
                ON document_embeddings(subject)
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_grade
                ON document_embeddings(grade)
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_topic
                ON document_embeddings(topic)
            """)

            self.conn.commit()
            logger.info("All indexes created successfully")

        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    def insert(
        self,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict] = None,
    ) -> int:
        """
        Insert a document with its embedding

        Args:
            content: Document text content
            embedding: Vector embedding (must match embedding_dim)
            metadata: Optional metadata dict with keys:
                - subject, grade, chapter, topic, source_file,
                  page_number, chunk_index

        Returns:
            Inserted document ID
        """
        if metadata is None:
            metadata = {}

        if len(embedding) != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension {len(embedding)} doesn't match "
                f"expected {self.embedding_dim}"
            )

        try:
            # Get next ID
            result = self.conn.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM document_embeddings"
            ).fetchone()
            next_id = result[0]

            # Insert document
            self.conn.execute(
                """
                INSERT INTO document_embeddings
                (id, content, embedding, subject, grade, chapter, topic,
                 source_file, page_number, chunk_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    next_id,
                    content,
                    embedding,
                    metadata.get("subject"),
                    metadata.get("grade"),
                    metadata.get("chapter"),
                    metadata.get("topic"),
                    metadata.get("source_file"),
                    metadata.get("page_number"),
                    metadata.get("chunk_index"),
                ],
            )

            self.conn.commit()
            logger.debug(f"Inserted document with ID {next_id}")
            return next_id

        except Exception as e:
            logger.error(f"Failed to insert document: {e}")
            raise

    def insert_batch(
        self, documents: List[Tuple[str, List[float], Dict]]
    ) -> List[int]:
        """
        Insert multiple documents at once (faster than individual inserts)

        Args:
            documents: List of (content, embedding, metadata) tuples

        Returns:
            List of inserted document IDs
        """
        ids = []
        try:
            for content, embedding, metadata in documents:
                doc_id = self.insert(content, embedding, metadata)
                ids.append(doc_id)

            logger.info(f"Batch inserted {len(ids)} documents")
            return ids

        except Exception as e:
            logger.error(f"Failed to batch insert documents: {e}")
            raise

    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        similarity_threshold: float = 0.0,
    ) -> List[Dict]:
        """
        Search for similar documents using cosine similarity

        Args:
            query_embedding: Query vector
            k: Number of results to return
            filter_dict: Optional filters (subject, grade, topic, etc.)
            similarity_threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            List of result dicts with content, metadata, and similarity score
        """
        if len(query_embedding) != self.embedding_dim:
            raise ValueError(
                f"Query embedding dimension {len(query_embedding)} doesn't match "
                f"expected {self.embedding_dim}"
            )

        try:
            # Build query
            query = f"""
                SELECT
                    id,
                    content,
                    subject,
                    grade,
                    chapter,
                    topic,
                    source_file,
                    page_number,
                    chunk_index,
                    array_cosine_similarity(embedding, ?::FLOAT[{self.embedding_dim}]) as similarity
                FROM document_embeddings
            """

            params = [query_embedding]

            # Add filters
            conditions = []
            if filter_dict:
                if "subject" in filter_dict:
                    conditions.append("subject = ?")
                    params.append(filter_dict["subject"])
                if "grade" in filter_dict:
                    conditions.append("grade = ?")
                    params.append(filter_dict["grade"])
                if "topic" in filter_dict:
                    conditions.append("topic = ?")
                    params.append(filter_dict["topic"])
                if "chapter" in filter_dict:
                    conditions.append("chapter = ?")
                    params.append(filter_dict["chapter"])

            # Add similarity threshold
            if similarity_threshold > 0:
                conditions.append(
                    f"array_cosine_similarity(embedding, ?::FLOAT[{self.embedding_dim}]) >= ?"
                )
                params.append(query_embedding)
                params.append(similarity_threshold)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY similarity DESC LIMIT ?"
            params.append(k)

            # Execute search
            results = self.conn.execute(query, params).fetchall()

            # Format results
            formatted_results = []
            for row in results:
                formatted_results.append(
                    {
                        "id": row[0],
                        "content": row[1],
                        "subject": row[2],
                        "grade": row[3],
                        "chapter": row[4],
                        "topic": row[5],
                        "source_file": row[6],
                        "page_number": row[7],
                        "chunk_index": row[8],
                        "similarity": float(row[9]),
                    }
                )

            logger.debug(f"Search returned {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def get_statistics(self) -> Dict:
        """Get database statistics"""
        try:
            total_docs = self.conn.execute(
                "SELECT COUNT(*) FROM document_embeddings"
            ).fetchone()[0]

            by_subject = self.conn.execute("""
                SELECT subject, COUNT(*) as count
                FROM document_embeddings
                WHERE subject IS NOT NULL
                GROUP BY subject
                ORDER BY count DESC
            """).fetchall()

            by_grade = self.conn.execute("""
                SELECT grade, COUNT(*) as count
                FROM document_embeddings
                WHERE grade IS NOT NULL
                GROUP BY grade
                ORDER BY grade
            """).fetchall()

            return {
                "total_documents": total_docs,
                "by_subject": dict(by_subject),
                "by_grade": dict(by_grade),
                "embedding_dimension": self.embedding_dim,
                "database_path": str(self.db_path),
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            raise

    def delete_all(self):
        """Delete all documents (use with caution!)"""
        try:
            self.conn.execute("DELETE FROM document_embeddings")
            self.conn.commit()
            logger.warning("Deleted all documents from vector store")
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Closed DuckDB connection")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


if __name__ == "__main__":
    # Test the vector store
    import numpy as np

    print("Testing DuckDB Vector Store...")

    with DuckDBVectorStore("test_ai_teacher.duckdb") as store:
        # Insert test document
        test_embedding = np.random.rand(768).tolist()
        doc_id = store.insert(
            content="Hukum Newton 2 menyatakan bahwa F = m × a",
            embedding=test_embedding,
            metadata={
                "subject": "Fisika",
                "grade": 8,
                "chapter": "Bab 2",
                "topic": "Hukum Newton",
                "source_file": "Fisika_Kelas8.pdf",
                "page_number": 45,
            },
        )
        print(f"Inserted document with ID: {doc_id}")

        # Search
        query_embedding = np.random.rand(768).tolist()
        results = store.search(
            query_embedding, k=5, filter_dict={"subject": "Fisika"}
        )

        print(f"\nSearch Results ({len(results)}):")
        for result in results:
            print(f"  - {result['content'][:50]}... (similarity: {result['similarity']:.4f})")

        # Statistics
        stats = store.get_statistics()
        print(f"\nDatabase Statistics:")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"  By subject: {stats['by_subject']}")

    print("\nTest completed!")
