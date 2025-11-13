# Phase 1 POC: CozoDB on Linux Development

**Date:** November 2025
**Status:** DEVELOPMENT ARCHITECTURE
**Context:** User decision - FreeBSD for production (wait for Cassandra 5.0), Linux for development (CozoDB)

---

## Strategic Decision

### Production Strategy (When Ready)

**FreeBSD + Cassandra 5.0**:
- ✅ ZFS native (boot environments, snapshots, rollback)
- ✅ ZFS boot environments (atomic upgrades, instant rollback)
- ✅ Jails (container isolation)
- ✅ pf firewall (powerful, simple)
- ⏳ **Wait for Cassandra 5.0 FreeBSD port**

**Why wait for FreeBSD port vs build from source**:
- ✅ Official testing and support
- ✅ Easy upgrades: `pkg upgrade cassandra5`
- ✅ Port maintainer handles patches
- ✅ Avoid custom build maintenance

### Development Strategy (Now - Phase 1)

**Linux + CozoDB**:
- ✅ CozoDB available (no FreeBSD port yet)
- ✅ Test unified vector+graph+relational architecture
- ✅ Learn Datalog query language
- ✅ Validate POC with real data
- ✅ When Cassandra 5.0 arrives on FreeBSD → migrate

**Timeline estimate**:
- Phase 1 (Months 1-6): Develop on Linux with CozoDB
- Monitor FreeBSD ports: `cassandra5` availability
- Phase 2 (Month 7+): Migrate to FreeBSD when ready

---

## Part 1: CozoDB Architecture for POC

### Why CozoDB is Perfect for Phase 1

**Unified database** - Vector + Graph + Relational:
```
┌─────────────────────────────────────────────┐
│              CozoDB                         │
│                                             │
│  ┌──────────────┐  ┌──────────────┐        │
│  │   Vector     │  │    Graph     │        │
│  │   (HNSW)     │  │  (Datalog)   │        │
│  └──────────────┘  └──────────────┘        │
│                                             │
│         ┌──────────────┐                    │
│         │  Relational  │                    │
│         │    (SQL)     │                    │
│         └──────────────┘                    │
└─────────────────────────────────────────────┘
```

**vs PostgreSQL** (Phase 0 alternative):
- ❌ PostgreSQL: pgvector extension + no graph + separate tools
- ✅ CozoDB: Native vector + graph + relational in ONE database

**vs Cassandra** (future production):
- ✅ CozoDB: Learn architecture, test queries, validate POC
- ✅ Later: Migrate to Cassandra 5.0 with same concepts
- ✅ CozoDB backend can be SQLite (dev) or RocksDB (prod-like testing)

### CozoDB Storage Backends

**For Phase 1 POC**:

```python
# Development (single machine, fast iteration)
from pycozo import Client

db = Client(engine='sqlite', path='ai_teacher_dev.db')

# Production-like testing (better performance)
db = Client(engine='rocksdb', path='ai_teacher_prod_test')

# Future: Production on FreeBSD (when ready)
# db = Client(engine='tikv', options='tikv://pd1:2379')
```

**Why SQLite for Phase 1**:
- ✅ Single file (easy backup, copy, test)
- ✅ Zero configuration
- ✅ Fast for development (<10K documents)
- ✅ Perfect for POC validation

---

## Part 2: Development Environment Setup

### 2.1 Linux Setup (Ubuntu 24.04 LTS)

**Install CozoDB**:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip -y

# Create project directory
mkdir -p ~/ai-teacher-poc
cd ~/ai-teacher-poc

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install CozoDB Python client
pip install pycozo==0.7.6

# Install other dependencies
pip install \
    sentence-transformers==2.2.2 \
    numpy==1.24.3 \
    pandas==2.0.3 \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    python-multipart==0.0.6 \
    pypdf==3.17.0
```

**Verify installation**:

```python
# test_cozo.py
from pycozo import Client

# Create in-memory database
db = Client()

# Test basic query
result = db.run("""
    ?[val] <- [[1], [2], [3]]
    :replace test_relation {val: Int}
""")

print("CozoDB working:", result)
db.close()
```

```bash
python test_cozo.py
# Output: CozoDB working: {'headers': ['status', ...], 'rows': [...]}
```

### 2.2 Project Structure

```
ai-teacher-poc/
├── venv/                          # Python virtual environment
├── data/
│   ├── cozo.db                    # CozoDB SQLite database
│   ├── textbooks/                 # PDF textbooks
│   │   ├── physics_grade9.pdf
│   │   ├── math_grade9.pdf
│   │   └── ...
│   └── embeddings_cache/          # Cached embeddings
├── src/
│   ├── __init__.py
│   ├── config.py                  # Configuration
│   ├── cozo_client.py             # CozoDB wrapper
│   ├── embedding_service.py       # Sentence transformers
│   ├── pdf_processor.py           # Extract text from PDFs
│   ├── knowledge_graph.py         # Graph operations
│   └── api/
│       ├── __init__.py
│       └── sync_api.py            # FastAPI sync endpoint
├── scripts/
│   ├── init_schema.py             # Initialize CozoDB schema
│   ├── import_textbooks.py        # Import PDF textbooks
│   └── test_queries.py            # Test Datalog queries
├── tests/
│   ├── test_vector_search.py
│   ├── test_graph_queries.py
│   └── test_sync.py
├── requirements.txt
├── .env.example
└── README_POC.md
```

---

## Part 3: CozoDB Schema Design

### 3.1 Initialize Schema

**scripts/init_schema.py**:

```python
#!/usr/bin/env python3
"""Initialize CozoDB schema for AI Teacher POC"""

from pycozo import Client
from pathlib import Path

def init_schema():
    # Connect to CozoDB (SQLite backend for POC)
    db = Client(engine='sqlite', path='data/cozo.db')

    print("Initializing CozoDB schema...")

    # 1. Textbook chapters (relational)
    db.run("""
        :create chapter {
            chapter_id: Uuid,
            =>
            subject: String,
            grade: Int,
            title: String,
            content: String,
            created_at: Float,
            updated_at: Float,
        }
    """)

    # 2. Document embeddings (vector)
    db.run("""
        :create embedding {
            embedding_id: Uuid,
            =>
            chapter_id: Uuid,
            chunk_text: String,
            chunk_index: Int,
            embedding: <F32; 768>,  # 768-dimensional vector
        }
    """)

    # 3. Create HNSW index for vector similarity search
    db.run("""
        ::hnsw create embedding_ann_idx {
            dim: 768,
            m: 16,
            ef_construction: 200,
            distance: Cosine,
            fields: [embedding],
            filter: chapter_id,
        }
    """)

    # 4. Knowledge graph - Concepts (nodes)
    db.run("""
        :create concept {
            concept_id: Uuid,
            =>
            concept_name: String,
            concept_type: String,  # 'law', 'formula', 'definition', 'theorem'
            subject: String,
            grade: Int,
            description: String,
            difficulty_level: Int,  # 1-5
        }
    """)

    # 5. Knowledge graph - Relationships (edges)
    db.run("""
        :create prerequisite {
            from_concept: Uuid,
            to_concept: Uuid,
            =>
        }
    """)

    db.run("""
        :create related_to {
            concept_a: Uuid,
            concept_b: Uuid,
            =>
            relationship_type: String,  # 'application', 'example', 'contrast'
        }
    """)

    # 6. Student progress (for testing sync)
    db.run("""
        :create student_progress {
            student_id: Uuid,
            chapter_id: Uuid,
            =>
            completed: Bool,
            completion_date: Float?,
            time_spent_minutes: Int,
            questions_answered: Int,
            correct_answers: Int,
        }
    """)

    # 7. Sync metadata (version tracking)
    db.run("""
        :create sync_version {
            content_type: String,
            =>
            version: Int,
            last_updated: Float,
        }
    """)

    # Initialize sync versions
    import time
    now = time.time()

    db.run("""
        ?[content_type, version, last_updated] <- [
            ['textbook', 1, $now],
            ['embedding', 1, $now],
            ['graph', 1, $now],
        ]
        :replace sync_version {content_type, version, last_updated}
    """, {'now': now})

    print("✓ Schema initialized successfully!")
    print("\nCreated relations:")
    print("  - chapter (textbook content)")
    print("  - embedding (768-dim vectors with HNSW index)")
    print("  - concept (knowledge graph nodes)")
    print("  - prerequisite (concept dependencies)")
    print("  - related_to (concept relationships)")
    print("  - student_progress (learning tracking)")
    print("  - sync_version (version control)")

    db.close()

if __name__ == '__main__':
    init_schema()
```

Run:
```bash
python scripts/init_schema.py
```

### 3.2 Import Textbook Data

**scripts/import_textbooks.py**:

```python
#!/usr/bin/env python3
"""Import PDF textbooks into CozoDB"""

import uuid
import time
from pathlib import Path
from typing import List, Dict
import pypdf
from sentence_transformers import SentenceTransformer
from pycozo import Client

class TextbookImporter:
    def __init__(self, db_path: str = 'data/cozo.db'):
        self.db = Client(engine='sqlite', path=db_path)
        self.embedding_model = SentenceTransformer(
            'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
        )

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF file"""
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            text = ''
            for page in reader.pages:
                text += page.extract_text() + '\n\n'
        return text

    def chunk_text(self, text: str, chunk_size: int = 512) -> List[str]:
        """Split text into chunks for embedding"""
        # Simple chunking by sentences (in production, use smarter chunking)
        sentences = text.split('. ')

        chunks = []
        current_chunk = ''

        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + '. '
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + '. '

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def import_chapter(self, pdf_path: Path, subject: str, grade: int, title: str):
        """Import a single chapter"""
        print(f"\nImporting: {title}")

        # Extract text
        print("  - Extracting text from PDF...")
        content = self.extract_text_from_pdf(pdf_path)

        # Generate chapter ID
        chapter_id = str(uuid.uuid4())
        now = time.time()

        # Insert chapter
        print("  - Saving chapter metadata...")
        self.db.run("""
            ?[chapter_id, subject, grade, title, content, created_at, updated_at] <- [
                [$chapter_id, $subject, $grade, $title, $content, $now, $now]
            ]
            :put chapter {chapter_id, subject, grade, title, content, created_at, updated_at}
        """, {
            'chapter_id': chapter_id,
            'subject': subject,
            'grade': grade,
            'title': title,
            'content': content,
            'now': now
        })

        # Chunk text
        print("  - Chunking text...")
        chunks = self.chunk_text(content)
        print(f"    → {len(chunks)} chunks")

        # Generate embeddings
        print("  - Generating embeddings...")
        embeddings = self.embedding_model.encode(chunks, show_progress_bar=True)

        # Insert embeddings (batch)
        print("  - Saving embeddings to CozoDB...")
        embedding_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            embedding_data.append([
                str(uuid.uuid4()),     # embedding_id
                chapter_id,            # chapter_id
                chunk,                 # chunk_text
                i,                     # chunk_index
                embedding.tolist()     # embedding (convert numpy to list)
            ])

        self.db.run("""
            ?[embedding_id, chapter_id, chunk_text, chunk_index, embedding] <- $embedding_data
            :put embedding {embedding_id, chapter_id, chunk_text, chunk_index, embedding}
        """, {'embedding_data': embedding_data})

        print(f"  ✓ Imported: {len(chunks)} embeddings")

        # Update sync version
        self.db.run("""
            ?[content_type, version, last_updated] <- [
                ['textbook', version + 1, $now],
                ['embedding', version + 1, $now],
            ]
            :update sync_version {content_type, version, last_updated}
        """, {'now': now})

        return chapter_id

    def close(self):
        self.db.close()

def main():
    importer = TextbookImporter()

    # Import sample textbooks
    textbooks = [
        ('data/textbooks/physics_grade9_newton.pdf', 'Physics', 9, 'Hukum Newton'),
        ('data/textbooks/math_grade9_algebra.pdf', 'Math', 9, 'Aljabar Dasar'),
    ]

    for pdf_path, subject, grade, title in textbooks:
        path = Path(pdf_path)
        if path.exists():
            importer.import_chapter(path, subject, grade, title)
        else:
            print(f"⚠ File not found: {pdf_path}")

    importer.close()
    print("\n✓ All textbooks imported!")

if __name__ == '__main__':
    main()
```

---

## Part 4: Datalog Queries (CozoDB)

### 4.1 Vector Similarity Search

**Example: Find similar textbook chunks**:

```python
# src/cozo_client.py
from pycozo import Client
from typing import List, Dict
import numpy as np

class CozoClient:
    def __init__(self, db_path: str = 'data/cozo.db'):
        self.db = Client(engine='sqlite', path=db_path)

    def vector_search(self, query_embedding: List[float], k: int = 5,
                      subject_filter: str = None) -> List[Dict]:
        """
        Search for similar textbook chunks using HNSW index

        Args:
            query_embedding: 768-dim query vector
            k: Number of results
            subject_filter: Optional subject filter ('Physics', 'Math', etc.)
        """

        if subject_filter:
            # Vector search with subject filter
            result = self.db.run("""
                # Search using HNSW index
                idx_result[embedding_id, chapter_id, distance] :=
                    ~embedding_ann_idx{
                        query: $query_vector,
                        k: $k,
                        ef: 100,
                        filter: (chapter_id)
                    | embedding_id, distance
                    },
                    *embedding{embedding_id, chapter_id}

                # Join with chapter to filter by subject
                ?[embedding_id, chapter_id, chunk_text, distance, subject, title] :=
                    idx_result[embedding_id, chapter_id, distance],
                    *embedding{embedding_id, chapter_id, chunk_text},
                    *chapter{chapter_id, subject, title},
                    subject == $subject_filter

                :order distance
                :limit $k
            """, {
                'query_vector': query_embedding,
                'k': k * 2,  # Fetch more, filter, then limit
                'subject_filter': subject_filter
            })
        else:
            # Vector search without filter
            result = self.db.run("""
                ?[embedding_id, chapter_id, chunk_text, distance, subject, title] :=
                    ~embedding_ann_idx{
                        query: $query_vector,
                        k: $k,
                        ef: 100
                    | embedding_id, distance
                    },
                    *embedding{embedding_id, chapter_id, chunk_text},
                    *chapter{chapter_id, subject, title}

                :order distance
                :limit $k
            """, {'query_vector': query_embedding, 'k': k})

        # Convert to list of dicts
        results = []
        for row in result['rows']:
            results.append({
                'embedding_id': row[0],
                'chapter_id': row[1],
                'chunk_text': row[2],
                'distance': row[3],
                'similarity': 1 - row[3],  # Cosine similarity = 1 - distance
                'subject': row[4],
                'title': row[5]
            })

        return results
```

### 4.2 Knowledge Graph Queries

**Example: Find prerequisites for a concept**:

```python
def get_prerequisites(self, concept_name: str, max_depth: int = 3) -> List[Dict]:
    """
    Find all prerequisites for a concept (recursive graph traversal)

    Args:
        concept_name: Name of the concept (e.g., "Hukum Newton 2")
        max_depth: Maximum traversal depth
    """

    result = self.db.run("""
        # Find the concept
        start_concept[concept_id, concept_name] :=
            *concept{concept_id, concept_name},
            concept_name == $concept_name

        # Recursive prerequisite traversal
        prerequisites[from_id, to_id, level] :=
            start_concept[from_id, _],
            *prerequisite{from_id, to_id},
            level = 1

        prerequisites[from_id, to_id, level] :=
            prerequisites[mid_id, _, prev_level],
            *prerequisite{mid_id: from_id, to_id},
            level = prev_level + 1,
            level <= $max_depth

        # Get concept details
        ?[prerequisite_name, prerequisite_type, subject, level] :=
            prerequisites[_, concept_id, level],
            *concept{concept_id, concept_name: prerequisite_name, concept_type: prerequisite_type, subject}

        :order level, prerequisite_name
    """, {'concept_name': concept_name, 'max_depth': max_depth})

    return [
        {
            'name': row[0],
            'type': row[1],
            'subject': row[2],
            'level': row[3]
        }
        for row in result['rows']
    ]

def get_related_concepts(self, concept_name: str) -> List[Dict]:
    """Find related concepts (non-prerequisite relationships)"""

    result = self.db.run("""
        # Find the concept
        start_concept[concept_id] :=
            *concept{concept_id, concept_name},
            concept_name == $concept_name

        # Find related concepts (bidirectional)
        ?[related_name, relationship_type, subject] :=
            start_concept[concept_id],
            *related_to{concept_a: concept_id, concept_b: related_id, relationship_type},
            *concept{concept_id: related_id, concept_name: related_name, subject}

        ?[related_name, relationship_type, subject] :=
            start_concept[concept_id],
            *related_to{concept_b: concept_id, concept_a: related_id, relationship_type},
            *concept{concept_id: related_id, concept_name: related_name, subject}
    """, {'concept_name': concept_name})

    return [
        {
            'name': row[0],
            'relationship': row[1],
            'subject': row[2]
        }
        for row in result['rows']
    ]
```

### 4.3 Hybrid Query (Vector + Graph)

**Example: Find similar content with prerequisite context**:

```python
def hybrid_search(self, query_text: str, subject: str = None) -> Dict:
    """
    Hybrid search: vector similarity + knowledge graph traversal

    Returns relevant chunks plus prerequisite concepts
    """
    from sentence_transformers import SentenceTransformer

    # 1. Generate query embedding
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
    query_embedding = model.encode([query_text])[0].tolist()

    # 2. Vector search for similar chunks
    similar_chunks = self.vector_search(query_embedding, k=5, subject_filter=subject)

    # 3. Extract concepts mentioned in top chunks (simple keyword matching for POC)
    # In production, use NER or LLM extraction
    chunk_text = ' '.join([chunk['chunk_text'] for chunk in similar_chunks[:3]])

    # 4. Find prerequisites for extracted concepts
    # (Simplified: assume we extract concept names from chunks)
    extracted_concepts = self._extract_concepts(chunk_text)

    prerequisites = {}
    for concept in extracted_concepts:
        prereqs = self.get_prerequisites(concept, max_depth=2)
        if prereqs:
            prerequisites[concept] = prereqs

    return {
        'similar_chunks': similar_chunks,
        'prerequisites': prerequisites,
        'related_concepts': {}  # Can add related concepts similarly
    }

def _extract_concepts(self, text: str) -> List[str]:
    """Extract concept names from text (simplified for POC)"""
    # In production: use NER, LLM extraction, or keyword matching against concept database
    result = self.db.run("""
        ?[concept_name] :=
            *concept{concept_name},
            contains($text, concept_name)
    """, {'text': text})

    return [row[0] for row in result['rows']]
```

---

## Part 5: Testing Queries

**scripts/test_queries.py**:

```python
#!/usr/bin/env python3
"""Test CozoDB queries for POC validation"""

from src.cozo_client import CozoClient
from sentence_transformers import SentenceTransformer

def test_vector_search():
    print("\n=== Test 1: Vector Similarity Search ===")

    client = CozoClient()
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

    # Query
    query = "Jelaskan hubungan antara gaya dan percepatan"
    query_embedding = model.encode([query])[0].tolist()

    # Search
    results = client.vector_search(query_embedding, k=3, subject_filter='Physics')

    print(f"Query: {query}")
    print(f"\nTop 3 similar chunks:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Similarity: {result['similarity']:.4f}")
        print(f"   Chapter: {result['title']}")
        print(f"   Text: {result['chunk_text'][:150]}...")

def test_graph_queries():
    print("\n=== Test 2: Knowledge Graph Traversal ===")

    client = CozoClient()

    # Find prerequisites
    concept = "Hukum Newton 2"
    prereqs = client.get_prerequisites(concept, max_depth=3)

    print(f"Prerequisites for '{concept}':")
    for prereq in prereqs:
        indent = "  " * prereq['level']
        print(f"{indent}→ {prereq['name']} ({prereq['type']}) - Level {prereq['level']}")

def test_hybrid_search():
    print("\n=== Test 3: Hybrid Search (Vector + Graph) ===")

    client = CozoClient()

    query = "Bagaimana cara menghitung gaya jika massa dan percepatan diketahui?"
    results = client.hybrid_search(query, subject='Physics')

    print(f"Query: {query}")
    print(f"\n✓ Found {len(results['similar_chunks'])} similar chunks")
    print(f"✓ Found {len(results['prerequisites'])} concepts with prerequisites")

if __name__ == '__main__':
    test_vector_search()
    test_graph_queries()
    test_hybrid_search()
```

---

## Part 6: Migration Path to Cassandra 5.0

### When Cassandra 5.0 Arrives on FreeBSD

**Timeline estimate**: 6-12 months after Cassandra 5.0 GA
- Cassandra 5.0 GA: September 2024
- FreeBSD port: Est. Q2-Q3 2025

**Check port status**:
```bash
# On FreeBSD
pkg search cassandra
# Currently: cassandra4-4.0.8
# Waiting for: cassandra5-5.0.x
```

### Migration Strategy

**Step 1: Export from CozoDB**

```python
# scripts/export_to_cassandra.py
from pycozo import Client
from cassandra.cluster import Cluster

# Connect to CozoDB
cozo_db = Client(engine='sqlite', path='data/cozo.db')

# Connect to Cassandra
cassandra_cluster = Cluster(['cassandra1', 'cassandra2', 'cassandra3'])
cassandra_session = cassandra_cluster.connect('ai_teacher')

# Export chapters
chapters = cozo_db.run("""
    ?[chapter_id, subject, grade, title, content] :=
        *chapter{chapter_id, subject, grade, title, content}
""")

for row in chapters['rows']:
    cassandra_session.execute("""
        INSERT INTO chapters (chapter_id, subject, grade, title, content)
        VALUES (?, ?, ?, ?, ?)
    """, row)

# Export embeddings with native VECTOR type
embeddings = cozo_db.run("""
    ?[embedding_id, chapter_id, chunk_text, embedding] :=
        *embedding{embedding_id, chapter_id, chunk_text, embedding}
""")

for row in embeddings['rows']:
    # Cassandra 5.0 native vector type
    cassandra_session.execute("""
        INSERT INTO embeddings (embedding_id, chapter_id, chunk_text, embedding)
        VALUES (?, ?, ?, ?)
    """, row)  # embedding is already a list of floats

print("✓ Migration complete!")
```

**Step 2: Update Schema for Cassandra**

```cql
-- Cassandra 5.0 schema (equivalent to CozoDB)
CREATE KEYSPACE ai_teacher
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};

USE ai_teacher;

-- Chapters (same as CozoDB)
CREATE TABLE chapters (
    chapter_id UUID PRIMARY KEY,
    subject TEXT,
    grade INT,
    title TEXT,
    content TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Embeddings with native vector type
CREATE TABLE embeddings (
    embedding_id UUID PRIMARY KEY,
    chapter_id UUID,
    chunk_text TEXT,
    chunk_index INT,
    embedding VECTOR<FLOAT, 768>  -- Cassandra 5.0 native!
);

-- Create SAI index for vector search
CREATE CUSTOM INDEX embedding_ann_idx
ON embeddings (embedding)
USING 'StorageAttachedIndex'
WITH OPTIONS = {'similarity_function': 'COSINE'};

-- Knowledge graph (stored as wide columns + JSON)
CREATE TABLE concepts (
    concept_id UUID PRIMARY KEY,
    concept_name TEXT,
    concept_type TEXT,
    subject TEXT,
    grade INT,
    description TEXT,
    difficulty_level INT,
    prerequisites LIST<UUID>,  -- Store as list
    related_concepts MAP<UUID, TEXT>  -- Map of concept_id -> relationship_type
);
```

**Step 3: Update Application Code**

```python
# Minimal code changes - same concepts, different syntax

# CozoDB (Datalog)
result = cozo_db.run("""
    ?[chapter_id, chunk_text, distance] :=
        ~embedding_ann_idx{query: $q, k: 5 | _, distance},
        *embedding{embedding_id, chapter_id, chunk_text}
""", {'q': query_vector})

# Cassandra 5.0 (CQL with vector search)
result = cassandra_session.execute("""
    SELECT chapter_id, chunk_text,
           similarity_cosine(embedding, ?) AS similarity
    FROM embeddings
    ORDER BY embedding ANN OF ?
    LIMIT 5
""", [query_vector, query_vector])
```

**Abstraction layer** (good practice):

```python
# src/vector_store_interface.py
from abc import ABC, abstractmethod

class VectorStore(ABC):
    @abstractmethod
    def vector_search(self, query_embedding, k):
        pass

class CozoVectorStore(VectorStore):
    def vector_search(self, query_embedding, k):
        # CozoDB implementation
        pass

class CassandraVectorStore(VectorStore):
    def vector_search(self, query_embedding, k):
        # Cassandra implementation
        pass

# Easy to swap!
# vector_store = CozoVectorStore()  # Phase 1
# vector_store = CassandraVectorStore()  # Phase 2
```

---

## Part 7: Phase 1 Timeline

### Month 1-2: Setup & Import

**Week 1-2**: Development environment
- [ ] Setup Ubuntu 24.04 VM or laptop
- [ ] Install CozoDB, dependencies
- [ ] Initialize schema
- [ ] Test basic queries

**Week 3-4**: Import sample data
- [ ] Collect 5-10 PDF textbooks (Physics, Math)
- [ ] Import chapters into CozoDB
- [ ] Generate embeddings (15K chunks)
- [ ] Create sample knowledge graph (50 concepts)

**Week 5-6**: Build knowledge graph
- [ ] Define concept taxonomy (laws, formulas, definitions)
- [ ] Extract concepts from textbooks (manual for POC)
- [ ] Define prerequisite relationships
- [ ] Test graph traversal queries

### Month 3-4: Core Features

**Week 7-8**: Query implementation
- [ ] Implement vector similarity search
- [ ] Implement graph traversal (prerequisites)
- [ ] Implement hybrid queries
- [ ] Benchmark performance (latency, accuracy)

**Week 9-10**: Student progress tracking
- [ ] Implement progress storage
- [ ] Test progress queries
- [ ] Simulate multiple students

**Week 11-12**: Sync API (simple version)
- [ ] FastAPI REST endpoints
- [ ] Version tracking
- [ ] Export/import for sync
- [ ] Test with 10 simulated clients

### Month 5-6: POC Validation

**Week 13-14**: Integration testing
- [ ] End-to-end tests (query → retrieve → respond)
- [ ] Load testing (simulate 100 users)
- [ ] Measure vector search accuracy
- [ ] Measure graph traversal performance

**Week 15-16**: LLM integration
- [ ] Connect LFM2 (llama-server)
- [ ] Use retrieved context for answers
- [ ] Test Indonesian STEM questions
- [ ] Evaluate answer quality

**Week 17-18**: Performance optimization
- [ ] Tune HNSW parameters (m, ef_construction)
- [ ] Optimize Datalog queries
- [ ] Add caching if needed
- [ ] Benchmark improvements

**Week 19-24**: Documentation & Handoff
- [ ] Document Datalog queries
- [ ] Document schema design
- [ ] Create migration guide (CozoDB → Cassandra)
- [ ] Prepare for Phase 2

---

## Part 8: Why This Approach Works

### 1. Learn on CozoDB, Scale on Cassandra

**CozoDB (Phase 1)**:
- ✅ Unified API (vector + graph + relational)
- ✅ Fast iteration (SQLite backend)
- ✅ Learn Datalog (powerful query language)
- ✅ Validate architecture

**Cassandra 5.0 (Phase 2)**:
- ✅ Same concepts (vector search, wide columns, secondary indexes)
- ✅ Production-proven at scale
- ✅ FreeBSD native (when port arrives)

### 2. FreeBSD Benefits Preserved

**Why wait for FreeBSD port**:
- ✅ ZFS boot environments (atomic upgrades, rollback)
- ✅ Snapshots before Cassandra upgrades
- ✅ Jails (process isolation)
- ✅ pf firewall (simple, powerful)
- ✅ Official port support (easy maintenance)

**Development on Linux is temporary**:
- CozoDB not on FreeBSD yet → use Linux
- When Cassandra 5.0 on FreeBSD → migrate to production
- Clean separation: dev (Linux) vs prod (FreeBSD)

### 3. Minimal Migration Effort

**CozoDB → Cassandra concepts map directly**:
- Vector search → Native VECTOR type
- Graph edges → Wide columns / Lists / Maps
- Datalog → CQL (different syntax, same operations)

**Abstraction layer makes migration easy**:
```python
class VectorStore(ABC):
    @abstractmethod
    def search(self, query): pass

# Swap implementations without changing application code
```

---

## Summary

### Strategic Decisions ✅

1. **Development**: Linux + CozoDB (Phase 1, now)
   - No FreeBSD CozoDB port yet
   - Learn unified vector+graph architecture
   - Validate POC with real data

2. **Production**: FreeBSD + Cassandra 5.0 (Phase 2, when ready)
   - Wait for official FreeBSD port
   - ZFS boot environments (critical for production)
   - Production-proven, officially supported

3. **No Kafka**: Simple REST API for 10K users
   - Kafka at 100K+ users only
   - Pull-based sync (6-24hr frequency)

### Phase 1 Deliverables

**Month 1-2**: Setup + Data Import
- CozoDB schema initialized
- 5-10 textbooks imported
- 15K embeddings generated
- 50 concept knowledge graph

**Month 3-4**: Core Features
- Vector similarity search working
- Graph traversal (prerequisites)
- Hybrid queries implemented
- Simple sync API

**Month 5-6**: POC Validation
- Integration tests passing
- Performance benchmarks done
- LLM integration working
- Migration guide documented

### Next Steps

**This week**:
- [ ] Setup Linux development VM (Ubuntu 24.04)
- [ ] Install CozoDB and dependencies
- [ ] Run init_schema.py

**Next week**:
- [ ] Collect sample PDF textbooks
- [ ] Run import_textbooks.py
- [ ] Test basic vector search

**Monitor**:
- [ ] FreeBSD ports for `cassandra5` availability
- [ ] When available: migrate to FreeBSD production

---

**Status**: ✅ PHASE 1 ARCHITECTURE READY

**Recommendation**: Start development on Linux with CozoDB, migrate to FreeBSD + Cassandra 5.0 when port is ready

The full Phase 1 guide is ready for implementation!
