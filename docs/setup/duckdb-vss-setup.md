# DuckDB VSS Extension Setup Guide

## Overview

DuckDB uses the **VSS (Vector Similarity Search)** extension for vector operations, not pgvector (which is PostgreSQL-specific).

## Installation Methods

### Method 1: Python Package (Recommended for POC)

```bash
# Install DuckDB Python package with VSS support
pip install duckdb

# The vss extension can be installed from within Python
```

### Method 2: Using FreeBSD pkg DuckDB

Since you installed DuckDB via FreeBSD `pkg`, you can install extensions directly from DuckDB:

```bash
# Start DuckDB CLI
duckdb

# Inside DuckDB, install the vss extension
INSTALL vss;
LOAD vss;
```

## Python Usage

### Basic Setup

```python
import duckdb

# Connect to database (creates file if doesn't exist)
conn = duckdb.connect('ai_teacher.duckdb')

# Install and load vss extension
conn.execute("INSTALL vss;")
conn.execute("LOAD vss;")

# Verify installation
result = conn.execute("SELECT * FROM duckdb_extensions() WHERE extension_name = 'vss';").fetchall()
print("VSS Extension installed:", result)
```

### Create Vector Table

```python
# Create table for embeddings
conn.execute("""
    CREATE TABLE IF NOT EXISTS document_embeddings (
        id INTEGER PRIMARY KEY,
        content TEXT NOT NULL,
        embedding FLOAT[768],  -- 768-dimensional vector
        subject VARCHAR,
        grade INTEGER,
        chapter VARCHAR,
        topic VARCHAR,
        source_file VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Create HNSW index for fast similarity search
conn.execute("""
    CREATE INDEX IF NOT EXISTS embedding_idx
    ON document_embeddings
    USING HNSW (embedding)
""")
```

### Insert Embeddings

```python
import numpy as np

# Example embedding (768-dimensional)
embedding = np.random.rand(768).tolist()

conn.execute("""
    INSERT INTO document_embeddings
    (id, content, embedding, subject, grade, chapter, topic, source_file)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", [
    1,
    "Hukum Newton 2 menyatakan bahwa F = m × a",
    embedding,
    "Fisika",
    8,
    "Bab 2",
    "Hukum Newton",
    "Fisika_Kelas8_Bab2.pdf"
])

conn.commit()
```

### Vector Similarity Search

```python
# Query embedding
query_embedding = np.random.rand(768).tolist()

# Cosine similarity search (top 5 results)
results = conn.execute("""
    SELECT
        id,
        content,
        subject,
        grade,
        topic,
        array_cosine_similarity(embedding, ?::FLOAT[768]) as similarity
    FROM document_embeddings
    ORDER BY similarity DESC
    LIMIT 5
""", [query_embedding]).fetchall()

for row in results:
    print(f"ID: {row[0]}, Content: {row[1]}, Similarity: {row[5]:.4f}")
```

### Distance Metrics Available

DuckDB VSS extension supports multiple distance metrics:

```python
# 1. Cosine Similarity (recommended for semantic search)
array_cosine_similarity(embedding1, embedding2)

# 2. L2 Distance (Euclidean)
array_distance(embedding1, embedding2)

# 3. Inner Product
array_inner_product(embedding1, embedding2)
```

## Complete Example

```python
import duckdb
import numpy as np
from typing import List, Tuple

class DuckDBVectorStore:
    def __init__(self, db_path: str = 'ai_teacher.duckdb'):
        self.conn = duckdb.connect(db_path)
        self._setup_vss()
        self._create_tables()

    def _setup_vss(self):
        """Install and load VSS extension"""
        try:
            self.conn.execute("INSTALL vss;")
        except:
            pass  # Already installed
        self.conn.execute("LOAD vss;")

    def _create_tables(self):
        """Create embeddings table with HNSW index"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS document_embeddings (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                embedding FLOAT[768],
                subject VARCHAR,
                grade INTEGER,
                chapter VARCHAR,
                topic VARCHAR,
                source_file VARCHAR,
                page_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create HNSW index for fast similarity search
        try:
            self.conn.execute("""
                CREATE INDEX embedding_idx
                ON document_embeddings
                USING HNSW (embedding)
            """)
        except:
            pass  # Index might already exist

    def insert(self, content: str, embedding: List[float], metadata: dict):
        """Insert document with embedding"""
        self.conn.execute("""
            INSERT INTO document_embeddings
            (content, embedding, subject, grade, chapter, topic, source_file, page_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            content,
            embedding,
            metadata.get('subject'),
            metadata.get('grade'),
            metadata.get('chapter'),
            metadata.get('topic'),
            metadata.get('source_file'),
            metadata.get('page_number')
        ])
        self.conn.commit()

    def search(self, query_embedding: List[float], k: int = 5, filter_dict: dict = None) -> List[Tuple]:
        """Search for similar documents"""
        query = """
            SELECT
                id,
                content,
                subject,
                grade,
                chapter,
                topic,
                source_file,
                page_number,
                array_cosine_similarity(embedding, ?::FLOAT[768]) as similarity
            FROM document_embeddings
        """

        params = [query_embedding]

        # Add filters
        if filter_dict:
            conditions = []
            if 'subject' in filter_dict:
                conditions.append("subject = ?")
                params.append(filter_dict['subject'])
            if 'grade' in filter_dict:
                conditions.append("grade = ?")
                params.append(filter_dict['grade'])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY similarity DESC LIMIT ?"
        params.append(k)

        return self.conn.execute(query, params).fetchall()

    def close(self):
        """Close database connection"""
        self.conn.close()

# Usage example
if __name__ == "__main__":
    # Initialize vector store
    store = DuckDBVectorStore()

    # Insert sample document
    sample_embedding = np.random.rand(768).tolist()
    store.insert(
        content="Hukum Newton 2 menyatakan bahwa percepatan benda berbanding lurus dengan gaya.",
        embedding=sample_embedding,
        metadata={
            'subject': 'Fisika',
            'grade': 8,
            'chapter': 'Bab 2',
            'topic': 'Hukum Newton',
            'source_file': 'Fisika_Kelas8.pdf',
            'page_number': 45
        }
    )

    # Search
    query_embedding = np.random.rand(768).tolist()
    results = store.search(query_embedding, k=5, filter_dict={'subject': 'Fisika'})

    print("Search Results:")
    for result in results:
        print(f"Content: {result[1]}")
        print(f"Similarity: {result[8]:.4f}")
        print("---")

    store.close()
```

## Performance Tips

1. **Use HNSW Index**: Always create an HNSW index for large datasets (>1000 vectors)
2. **Batch Inserts**: Insert multiple rows at once for better performance
3. **Appropriate Vector Dimension**: Match embedding model dimension (768 for sentence-transformers)
4. **Filter Before Search**: Use WHERE clauses to narrow search space
5. **Connection Pooling**: Reuse database connections

## Troubleshooting

### Extension Not Found

```python
# If vss extension not found, try:
conn.execute("SET custom_extension_repository='http://extensions.duckdb.org';")
conn.execute("INSTALL vss;")
conn.execute("LOAD vss;")
```

### Vector Dimension Mismatch

```python
# Ensure your embeddings match the table definition
# If using 384-dim embeddings (MiniLM), change table to:
# embedding FLOAT[384]
```

### Slow Queries

```python
# Create index if not exists
conn.execute("CREATE INDEX IF NOT EXISTS embedding_idx ON document_embeddings USING HNSW (embedding);")

# Check index exists
conn.execute("SELECT * FROM duckdb_indexes() WHERE table_name = 'document_embeddings';").fetchall()
```

## Next Steps

1. Install sentence-transformers for generating embeddings
2. Process Indonesian textbooks (PDF → chunks)
3. Generate embeddings for all chunks
4. Store in DuckDB with metadata
5. Implement hybrid search (vector + metadata filtering)

See `src/rag/duckdb_store.py` for full implementation.
