# AI Teacher POC - Quick Start Guide

This guide will help you get started with the AI Teacher Proof of Concept on FreeBSD.

## Prerequisites

You mentioned you've already installed:
- ✅ DuckDB via `pkg install duckdb`
- ✅ Neo4j via `pkg install neo4j`

## Step 1: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On FreeBSD: source venv/bin/activate.csh (for csh)

# Install all dependencies
pip install -r requirements.txt
```

This will install:
- DuckDB Python bindings
- Neo4j Python driver
- LangChain, LlamaIndex
- sentence-transformers (for embeddings)
- All other required packages

## Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (use your preferred editor)
nano .env

# Key settings to configure:
# - LLAMA_SERVER_URL (if not using localhost:8080)
# - LLAMA_API_KEY (your llama-server API key)
# - NEO4J_PASSWORD (change from default "password")
```

## Step 3: Start Neo4j (if not running)

```bash
# Enable Neo4j service
sudo service neo4j enable

# Start Neo4j
sudo service neo4j start

# Check status
sudo service neo4j status

# Access Neo4j Browser: http://localhost:7474
# Default credentials: neo4j/neo4j (you'll be prompted to change)
```

## Step 4: Start llama-server

You mentioned you already have llama-server serving LFM2. Make sure it's running in API-only mode:

```bash
# Example: Run llama-server without web UI
./llama-server \
  -m /path/to/your/lfm2-model.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  --no-webui \
  --api-key "your-secret-key-here" \
  -c 4096 \
  -ngl 0  # CPU-only, adjust for GPU
```

**Important flags:**
- `--no-webui` - Disables the web chat interface (API-only)
- `--api-key` - Sets authentication key for API access

## Step 5: Verify Setup

Run the verification script to check everything is configured correctly:

```bash
python scripts/verify_setup.py
```

This will check:
- ✓ Python version (3.10+)
- ✓ All dependencies installed
- ✓ DuckDB VSS extension working
- ✓ Neo4j connection
- ✓ Project directories
- ✓ Configuration files
- ✓ llama-server connection
- ✓ DuckDB vector store functionality

## Step 6: Test Core Components

### Test DuckDB Vector Store

```bash
# Run the built-in test
python src/rag/duckdb_store.py
```

Expected output:
```
Inserted document with ID: 1
Search Results (1):
  - Hukum Newton 2 menyatakan bahwa F = m × a... (similarity: 0.XXXX)
Database Statistics:
  Total documents: 1
  By subject: {'Fisika': 1}
Test completed!
```

### Test LLM Client

```bash
# Test llama-server connection
python src/llm/client.py
```

Expected output:
```
✓ Server is healthy
=== Testing Chat Completion ===
Response: [LLM's explanation of acceleration in Indonesian]
```

### Test Configuration

```bash
# Verify configuration loading
python config/settings.py
```

Expected output:
```
=== AI Teacher Configuration ===
Project Root: /home/user/AI_Teacher
Data Directory: /home/user/AI_Teacher/data
DuckDB Path: /home/user/AI_Teacher/data/databases/ai_teacher.duckdb
Neo4j URI: bolt://localhost:7687
...
```

## Step 7: Understanding the DuckDB VSS Extension

**Important:** DuckDB uses the `vss` extension (Vector Similarity Search), not `pgvector`.

The `pgvector` extension is for PostgreSQL only. For DuckDB vector operations, use:

```python
import duckdb

conn = duckdb.connect('ai_teacher.duckdb')

# Install and load VSS extension
conn.execute("INSTALL vss;")
conn.execute("LOAD vss;")

# Create table with vector column
conn.execute("""
    CREATE TABLE embeddings (
        id INTEGER PRIMARY KEY,
        content TEXT,
        embedding FLOAT[768]  -- 768-dimensional vector
    )
""")

# Create HNSW index for fast similarity search
conn.execute("""
    CREATE INDEX embedding_idx
    ON embeddings
    USING HNSW (embedding)
""")

# Search using cosine similarity
results = conn.execute("""
    SELECT content,
           array_cosine_similarity(embedding, ?::FLOAT[768]) as similarity
    FROM embeddings
    ORDER BY similarity DESC
    LIMIT 5
""", [query_vector]).fetchall()
```

See `docs/setup/duckdb-vss-setup.md` for complete examples and troubleshooting.

## Project Structure

```
AI_Teacher/
├── config/settings.py          # Configuration management
├── src/
│   ├── llm/client.py           # llama-server client (✅ Ready)
│   ├── rag/duckdb_store.py     # DuckDB vector store (✅ Ready)
│   ├── graph/                  # Neo4j knowledge graph (TODO)
│   └── memory/                 # Conversation memory (TODO)
├── data/
│   ├── models/                 # Put your .gguf models here
│   ├── textbooks/              # Put PDF textbooks here
│   ├── databases/              # DuckDB and Neo4j data
│   └── embeddings/             # Cached embeddings
├── docs/setup/                 # Setup guides
└── scripts/                    # Utility scripts
```

## Next Steps

Now that your environment is set up, you can:

### 1. Add Sample Textbook
```bash
# Place a PDF textbook in data/textbooks/
cp /path/to/Fisika_Kelas8.pdf data/textbooks/
```

### 2. Generate Embeddings (Next Session)
We'll implement:
- PDF text extraction
- Text chunking
- Embedding generation using sentence-transformers
- Storage in DuckDB

### 3. Build Knowledge Graph (Next Session)
We'll implement:
- Neo4j schema for STEM concepts
- Concept extraction from textbooks
- Relationship mapping (prerequisites, related topics)

### 4. RAG Pipeline (Next Session)
We'll implement:
- Hybrid search (vector + graph)
- Context retrieval
- LLM prompt construction
- Response generation

## Troubleshooting

### DuckDB VSS Extension Not Found

```python
# If extension not found, try:
conn.execute("SET custom_extension_repository='http://extensions.duckdb.org';")
conn.execute("INSTALL vss;")
conn.execute("LOAD vss;")
```

### Neo4j Connection Failed

```bash
# Check if Neo4j is running
sudo service neo4j status

# View Neo4j logs
tail -f /var/log/neo4j/neo4j.log

# Restart Neo4j
sudo service neo4j restart
```

### llama-server Not Responding

```bash
# Check if llama-server is running
ps aux | grep llama-server

# Test connection manually
curl http://localhost:8080/health

# With API key
curl -H "Authorization: Bearer your-api-key" http://localhost:8080/health
```

### Python Import Errors

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Check installed packages
pip list | grep duckdb
pip list | grep neo4j
```

## Useful Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run verification script
python scripts/verify_setup.py

# Test individual components
python src/rag/duckdb_store.py
python src/llm/client.py
python config/settings.py

# Start Python REPL with imports
python -i -c "from src.rag.duckdb_store import DuckDBVectorStore; from src.llm.client import LlamaServerClient"

# Format code
black src/ config/

# Type checking
mypy src/

# Run tests (when implemented)
pytest tests/
```

## Getting Help

- **DuckDB VSS Setup:** See `docs/setup/duckdb-vss-setup.md`
- **Project Structure:** See `PROJECT_STRUCTURE.md`
- **Technical Details:** See `TECHNICAL_ARCHITECTURE.md`
- **Development Roadmap:** See `DEVELOPMENT_ROADMAP.md`

## Summary

You now have:
- ✅ Complete POC directory structure
- ✅ DuckDB vector store (fully functional)
- ✅ LLM client for llama-server
- ✅ Configuration system
- ✅ Verification script

**Ready for next steps:**
- 📄 PDF ingestion and processing
- 🧮 Embedding generation
- 🕸️ Neo4j knowledge graph
- 🔗 RAG pipeline integration
- 🧠 Memory and personalization

---

**Development Environment:** FreeBSD
**POC Database:** DuckDB (vector) + Neo4j (graph)
**Production Migration:** Cassandra + JanusGraph (Months 9-11)

Happy coding! 🚀
