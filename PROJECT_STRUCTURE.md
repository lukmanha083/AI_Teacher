# AI Teacher - Project Structure

This document describes the directory structure of the AI Teacher POC.

## Directory Layout

```
AI_Teacher/
├── README.md                          # Main project documentation
├── STARTUP_PROPOSAL.md                # Business plan and market analysis
├── TECHNICAL_ARCHITECTURE.md          # System architecture details
├── DEVELOPMENT_ROADMAP.md             # 24-month development timeline
├── PROJECT_STRUCTURE.md               # This file
│
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
├── requirements.txt                   # Python dependencies
│
├── config/                            # Configuration modules
│   ├── __init__.py
│   └── settings.py                    # Settings loader (Pydantic)
│
├── src/                               # Source code
│   ├── __init__.py
│   │
│   ├── llm/                           # LLM integration
│   │   ├── __init__.py
│   │   ├── client.py                  # llama-server client
│   │   ├── prompts.py                 # Prompt templates (TODO)
│   │   └── chains.py                  # LangChain chains (TODO)
│   │
│   ├── rag/                           # RAG pipeline
│   │   ├── __init__.py
│   │   ├── duckdb_store.py            # DuckDB vector store (POC)
│   │   ├── embeddings.py              # Embedding generation (TODO)
│   │   ├── ingestion.py               # PDF processing (TODO)
│   │   └── retrieval.py               # Hybrid search (TODO)
│   │
│   ├── graph/                         # Knowledge graph
│   │   ├── __init__.py
│   │   ├── neo4j_client.py            # Neo4j integration (TODO)
│   │   ├── schema.py                  # Graph schema (TODO)
│   │   └── queries.py                 # Cypher queries (TODO)
│   │
│   ├── memory/                        # Memory & personalization
│   │   ├── __init__.py
│   │   ├── conversation.py            # Conversation buffer (TODO)
│   │   ├── student_profile.py         # Student profiling (TODO)
│   │   └── adaptive.py                # Adaptive learning (TODO)
│   │
│   └── api/                           # API server (future)
│       ├── __init__.py
│       ├── main.py                    # FastAPI app (TODO)
│       └── routes/                    # API routes (TODO)
│
├── data/                              # Data files (gitignored)
│   ├── .gitkeep
│   ├── models/                        # LLM model files (.gguf)
│   │   └── .gitkeep
│   ├── textbooks/                     # PDF textbooks
│   │   └── .gitkeep
│   ├── databases/                     # Local databases
│   │   ├── .gitkeep
│   │   ├── ai_teacher.duckdb          # Vector database (created at runtime)
│   │   └── neo4j/                     # Neo4j data directory
│   └── embeddings/                    # Pre-computed embeddings cache
│       └── .gitkeep
│
├── docs/                              # Documentation
│   ├── setup/                         # Setup guides
│   │   └── duckdb-vss-setup.md        # DuckDB VSS extension guide
│   ├── api/                           # API documentation (TODO)
│   └── user-guides/                   # User documentation (TODO)
│
├── tests/                             # Test suite
│   ├── unit/                          # Unit tests (TODO)
│   │   ├── test_duckdb_store.py
│   │   ├── test_llm_client.py
│   │   └── test_embeddings.py
│   ├── integration/                   # Integration tests (TODO)
│   │   └── test_rag_pipeline.py
│   └── conftest.py                    # Pytest configuration (TODO)
│
├── scripts/                           # Utility scripts
│   ├── setup_env.sh                   # Environment setup (TODO)
│   ├── download_textbooks.py          # BSE textbook downloader (TODO)
│   ├── generate_embeddings.py         # Batch embedding generation (TODO)
│   └── test_setup.py                  # Verify installation (TODO)
│
└── logs/                              # Application logs (gitignored)
    └── .gitkeep
```

## Key Files

### Configuration

- **`.env`** - Environment variables (create from `.env.example`)
- **`config/settings.py`** - Centralized configuration using Pydantic
- **`requirements.txt`** - Python dependencies

### Core Modules

- **`src/llm/client.py`** - LLM server client (communicates with llama-server)
- **`src/rag/duckdb_store.py`** - Vector database for POC
- **`src/graph/neo4j_client.py`** - Knowledge graph client (TODO)
- **`src/memory/conversation.py`** - Conversation memory (TODO)

### Documentation

- **`README.md`** - Project overview and quickstart
- **`docs/setup/duckdb-vss-setup.md`** - DuckDB setup guide
- **`TECHNICAL_ARCHITECTURE.md`** - Detailed architecture

## Development Workflow

### 1. Initial Setup

```bash
# Create .env from template
cp .env.example .env

# Edit .env with your settings
nano .env

# Install dependencies
pip install -r requirements.txt
```

### 2. Verify Setup

```bash
# Test configuration loading
python config/settings.py

# Test DuckDB vector store
python src/rag/duckdb_store.py

# Test LLM client (requires llama-server running)
python src/llm/client.py
```

### 3. Development

```bash
# Run tests
pytest tests/

# Format code
black src/

# Type checking
mypy src/
```

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Document Ingestion (scripts/generate_embeddings.py) │
│    - Load PDF textbooks                                 │
│    - Chunk documents                                    │
│    - Generate embeddings                                │
│    - Store in DuckDB                                    │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ 2. Knowledge Graph Population (src/graph/)              │
│    - Define concepts                                    │
│    - Create relationships                               │
│    - Store in Neo4j                                     │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ 3. Query Processing (src/rag/retrieval.py)              │
│    - User asks question                                 │
│    - Generate query embedding                           │
│    - Search DuckDB (vector similarity)                  │
│    - Query Neo4j (related concepts)                     │
│    - Combine results                                    │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ 4. LLM Generation (src/llm/client.py)                   │
│    - Build prompt with context                          │
│    - Send to llama-server                               │
│    - Generate response                                  │
│    - Return to user                                     │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ 5. Memory Update (src/memory/)                          │
│    - Store conversation                                 │
│    - Update student profile                             │
│    - Track progress                                     │
└─────────────────────────────────────────────────────────┘
```

## Next Steps

### Immediate (POC Phase)

1. ✅ Set up project structure
2. ✅ Create configuration system
3. ✅ Implement DuckDB vector store
4. ✅ Create LLM client
5. ⏳ Implement PDF ingestion
6. ⏳ Add embedding generation
7. ⏳ Create Neo4j knowledge graph
8. ⏳ Build RAG retrieval pipeline
9. ⏳ Add conversation memory

### Near Term (MVP)

1. Fine-tune LFM2 on Indonesian STEM dataset
2. Process all Math + Physics textbooks
3. Build desktop application UI
4. Add progress tracking
5. Implement adaptive learning

### Long Term (Production)

1. Migrate DuckDB → Cassandra
2. Migrate Neo4j → JanusGraph
3. Add mobile application
4. Scale infrastructure
5. Launch to 10K+ users

## Database Migration Strategy

**POC (Current):**
- DuckDB for vectors (single file, embedded)
- Neo4j for graphs (easy setup, great tooling)

**Production (Months 9-11):**
- Migrate to Cassandra (distributed vector store)
- Migrate to JanusGraph (distributed graph)
- Use abstraction layer for seamless transition

See `README.md` section "Database Migration Strategy" for details.

## Contributing

This is currently a POC project. For development:

1. Create feature branch
2. Make changes
3. Write tests
4. Run `black` and `mypy`
5. Submit for review

## Support

For questions or issues:
- Check documentation in `docs/`
- Review `README.md`
- Consult `TECHNICAL_ARCHITECTURE.md`

---

**Last Updated:** November 2025
**Project Phase:** POC (Phase 0)
**Development OS:** FreeBSD 13.x/14.x
