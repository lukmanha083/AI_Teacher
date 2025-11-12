# AI Teacher - Affordable STEM Education Platform

> **Local LLM-powered adaptive learning for Indonesian junior & middle school students**

[![Status](https://img.shields.io/badge/status-proof--of--concept-orange)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![Target](https://img.shields.io/badge/target-Indonesian%20Students-green)]()

---

## Overview

AI Teacher is an affordable, locally-powered educational platform designed to democratize STEM education for Indonesian students. By leveraging local LLM technology (LFM2) that runs on CPU and Android devices, we eliminate expensive cloud inference costs and provide low-latency, personalized learning experiences.

**Key Value Proposition:**
- 💰 **Affordable:** IDR 100,000/month (~$6.50 USD) - 50-80% cheaper than competitors
- 🚀 **Fast:** Local LLM processing = zero latency, instant responses
- 🔒 **Private:** All student data stays on device
- 📚 **Curriculum-Aligned:** Fine-tuned on Indonesian textbooks (Kurikulum Merdeka)
- 📱 **Accessible:** Works on budget laptops and mid-range Android devices
- 🌐 **Offline-First:** Core functionality works without internet

---

## Project Status: Proof of Concept

**Current Phase:** Phase 0 - Pre-Development & Technical Validation
**Started:** November 2025

### ✅ Completed
- [x] Comprehensive startup proposal documentation
- [x] Technical architecture design
- [x] 24-month development roadmap
- [x] LFM2 model serving via llama-server

### 🚧 In Progress
- [ ] RAG pipeline with DuckDB + pgvector
- [ ] Knowledge graph with Neo4j
- [ ] Memory system with LangChain + mem0
- [ ] Desktop application prototype

### 📋 Next Steps
- [ ] Dataset acquisition (BSE textbooks)
- [ ] Fine-tuning LFM2 on Indonesian STEM dataset
- [ ] MVP desktop application
- [ ] Beta testing with 100+ students

---

## Documentation

- 📄 **[STARTUP_PROPOSAL.md](./STARTUP_PROPOSAL.md)** - Complete business plan, market analysis, financial projections
- 🏗️ **[TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md)** - Detailed system architecture and technology stack
- 🗓️ **[DEVELOPMENT_ROADMAP.md](./DEVELOPMENT_ROADMAP.md)** - 24-month development plan with milestones

---

## Technology Stack

### Core Components

#### LLM & Inference
- **[LFM2](https://huggingface.co/)** - 7B parameter foundation model
- **[llama.cpp](https://github.com/ggml-org/llama.cpp)** - Fast CPU inference
- **Quantization:** Q8 (desktop), Q4 (mobile)

#### RAG (Retrieval-Augmented Generation)
- **[LlamaIndex](https://www.llamaindex.ai/)** - RAG orchestration framework
- **[DuckDB](https://duckdb.org/)** - Embedded vector database with [pgvector extension](https://github.com/duckdb/duckdb_vss)
- **[Neo4j](https://neo4j.com/)** - Knowledge graph for concept relationships

#### Memory & Personalization
- **[LangChain](https://www.langchain.com/)** - LLM orchestration and chains
- **[mem0](https://mem0.ai/)** - Conversational memory for adaptive learning
- **[SQLite](https://sqlite.org/)** - Local conversation history

#### Infrastructure (Future)
- **FreeBSD** - Operating system
- **Jails** - Lightweight containerization
- **Tailscale** - Secure VPN for remote management

---

## Quick Start (Proof of Concept)

### Prerequisites

- Python 3.10+
- llama.cpp compiled with `llama-server`
- LFM2 model file (GGUF format)
- 8GB+ RAM (for 7B Q8 model)
- 16GB+ disk space (for model + embeddings)

### 1. Setting Up llama-server

#### Download and Compile llama.cpp

```bash
# Clone llama.cpp repository
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp

# Compile (CPU-only)
make -j

# Or compile with GPU support (CUDA)
make LLAMA_CUDA=1 -j

# The binary will be at: ./llama-server
```

#### Download LFM2 Model

```bash
# Option 1: Download from Hugging Face using llama-server
./llama-server -hf <user>/<model>:Q8_0

# Option 2: Manual download (example with a similar model)
# Replace with actual LFM2 model when available
wget https://huggingface.co/.../lfm2-7b-q8_0.gguf -O models/lfm2-7b-q8_0.gguf
```

### 2. Running llama-server (Headless, API-Only)

#### Basic Setup (No Authentication)

```bash
./llama-server \
  -m models/lfm2-7b-q8_0.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --no-webui \
  -c 4096 \
  -ngl 0
```

**Flag Explanation:**
- `-m, --model` - Path to model file (GGUF format)
- `--host` - IP address to bind (0.0.0.0 = all interfaces, 127.0.0.1 = localhost only)
- `--port` - Port to listen on (default: 8080)
- `--no-webui` - **Disable web chat UI** (API-only mode)
- `-c, --ctx-size` - Context window size (default: 2048)
- `-ngl, --n-gpu-layers` - Number of layers to offload to GPU (0 = CPU-only)

#### Production Setup (With API Key Authentication)

```bash
# Option 1: Single API key
./llama-server \
  -m models/lfm2-7b-q8_0.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  --no-webui \
  --api-key "your-secret-api-key-here" \
  -c 4096 \
  -ngl 0

# Option 2: Multiple API keys from file
echo "api-key-1" > api_keys.txt
echo "api-key-2" >> api_keys.txt
echo "api-key-3" >> api_keys.txt

./llama-server \
  -m models/lfm2-7b-q8_0.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  --no-webui \
  --api-key-file api_keys.txt \
  -c 4096 \
  -ngl 0
```

#### Advanced Configuration

```bash
./llama-server \
  -m models/lfm2-7b-q8_0.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  --no-webui \
  --api-key "your-secret-api-key" \
  -c 4096 \
  -ngl 0 \
  --threads 8 \
  --threads-http 4 \
  --timeout 600 \
  --metrics \
  --log-format text
```

**Additional Flags:**
- `--threads N` - Number of threads for inference (default: auto)
- `--threads-http N` - Number of threads for HTTP request processing
- `--timeout N` - Server read/write timeout in seconds (default: 600)
- `--metrics` - Enable Prometheus-compatible metrics endpoint at `/metrics`
- `--log-format` - Log format: `text` or `json`
- `--slots` - Enable slot monitoring endpoint (default: enabled)
- `--embedding` - Restrict to embedding-only mode

#### SSL/TLS Configuration (Optional)

```bash
./llama-server \
  -m models/lfm2-7b-q8_0.gguf \
  --host 0.0.0.0 \
  --port 8443 \
  --no-webui \
  --api-key "your-secret-api-key" \
  --ssl-key-file /path/to/private-key.pem \
  --ssl-cert-file /path/to/certificate.pem
```

### 3. Testing the API

#### Without API Key

```bash
# Health check
curl http://localhost:8080/health

# Completion endpoint
curl -X POST http://localhost:8080/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Jelaskan hukum Newton 2 dengan bahasa yang mudah dipahami.",
    "n_predict": 512,
    "temperature": 0.7,
    "top_p": 0.9,
    "stop": ["\n\n\n"]
  }'

# Chat completion endpoint (OpenAI-compatible)
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lfm2-7b-q8",
    "messages": [
      {"role": "system", "content": "Kamu adalah guru STEM untuk siswa SMP Indonesia."},
      {"role": "user", "content": "Apa itu percepatan?"}
    ],
    "max_tokens": 512,
    "temperature": 0.7
  }'
```

#### With API Key (Bearer Token)

```bash
# Set API key as environment variable
export API_KEY="your-secret-api-key"

# Completion with authentication
curl -X POST http://localhost:8080/completion \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "prompt": "Jelaskan hukum Newton 2 dengan bahasa yang mudah dipahami.",
    "n_predict": 512
  }'

# Chat completion with authentication
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "lfm2-7b-q8",
    "messages": [
      {"role": "user", "content": "Apa itu percepatan?"}
    ]
  }'
```

### 4. Python Client Example

```python
import requests
import json

class LFM2Client:
    def __init__(self, base_url="http://localhost:8080", api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def chat_completion(self, messages, max_tokens=512, temperature=0.7):
        """OpenAI-compatible chat completion"""
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json={
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()

    def completion(self, prompt, max_tokens=512, temperature=0.7):
        """Native completion endpoint"""
        response = requests.post(
            f"{self.base_url}/completion",
            headers=self.headers,
            json={
                "prompt": prompt,
                "n_predict": max_tokens,
                "temperature": temperature,
            }
        )
        response.raise_for_status()
        return response.json()

# Usage
client = LFM2Client(api_key="your-secret-api-key")

# Chat-style interaction
response = client.chat_completion([
    {"role": "system", "content": "Kamu adalah guru STEM untuk siswa SMP Indonesia."},
    {"role": "user", "content": "Jelaskan hukum Newton 2"}
])
print(response["choices"][0]["message"]["content"])

# Direct completion
response = client.completion("Apa itu percepatan?")
print(response["content"])
```

---

## API Key Management Best Practices

### Generating Secure API Keys

```bash
# Generate random API key (Linux/Mac)
openssl rand -hex 32

# Or use Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Or use uuidgen
uuidgen
```

### Storing API Keys Securely

```bash
# Use environment variables
export LLAMA_API_KEY="your-generated-key-here"

# Or use .env file (DO NOT commit to git!)
echo "LLAMA_API_KEY=your-generated-key-here" > .env

# Add to .gitignore
echo ".env" >> .gitignore
echo "api_keys.txt" >> .gitignore
```

### Multi-User Setup

```bash
# Create API keys file
cat > api_keys.txt <<EOF
# Student API keys
student-key-abc123  # Student A
student-key-def456  # Student B
student-key-ghi789  # Student C

# Admin API keys
admin-key-xyz123    # Admin dashboard
EOF

# Run server with multiple keys
./llama-server \
  -m models/lfm2-7b-q8_0.gguf \
  --api-key-file api_keys.txt \
  --no-webui
```

---

## Next Steps: RAG + Memory Implementation

### Upcoming Components (Next Chat)

#### 1. DuckDB with pgvector Extension
- **Purpose:** Embedded vector database for document embeddings
- **Advantages over Cassandra:**
  - Lightweight, embedded (no separate server)
  - Excellent for single-machine deployments
  - SQL interface familiar to developers
  - Perfect for prototyping and desktop apps

**Installation:**
```bash
pip install duckdb duckdb-vss
```

**Usage Preview:**
```python
import duckdb

# Create in-memory or file-based database
conn = duckdb.connect('ai_teacher.duckdb')

# Install and load vss extension (vector similarity search)
conn.execute("INSTALL vss;")
conn.execute("LOAD vss;")

# Create embeddings table
conn.execute("""
    CREATE TABLE embeddings (
        id INTEGER PRIMARY KEY,
        content TEXT,
        embedding FLOAT[768],
        subject VARCHAR,
        grade INTEGER
    )
""")

# Vector similarity search
query_embedding = [0.1, 0.2, ...]  # 768-dim vector
results = conn.execute("""
    SELECT content, subject,
           array_distance(embedding, ?::FLOAT[768]) as distance
    FROM embeddings
    ORDER BY distance ASC
    LIMIT 5
""", [query_embedding]).fetchall()
```

#### 2. Neo4j Knowledge Graph
- **Purpose:** Store concept relationships and prerequisites
- **Advantages over JanusGraph:**
  - Industry-standard graph database
  - Excellent Cypher query language
  - Great visualization tools (Neo4j Browser)
  - Strong community and documentation

**Installation:**
```bash
# Using Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Or use Neo4j Desktop
# Download from: https://neo4j.com/download/
```

**Usage Preview:**
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password")
)

# Create concept nodes and relationships
with driver.session() as session:
    session.run("""
        CREATE (n2:Concept {
            name: 'Hukum Newton 2',
            subject: 'Fisika',
            grade: 8,
            description: 'F = m × a'
        })
    """)

    session.run("""
        MATCH (n2:Concept {name: 'Hukum Newton 2'})
        MATCH (f:Concept {name: 'Gaya'})
        CREATE (n2)-[:REQUIRES]->(f)
    """)

    # Query prerequisites
    result = session.run("""
        MATCH (concept:Concept {name: 'Hukum Newton 2'})-[:REQUIRES*]->(prereq)
        RETURN prereq.name as prerequisite
    """)
```

#### 3. LangChain + mem0 Integration
- **Conversation memory management**
- **Student profile tracking**
- **Adaptive difficulty adjustment**

---

## Project Structure (Planned)

```
AI_Teacher/
├── README.md                          # This file
├── STARTUP_PROPOSAL.md                # Business plan
├── TECHNICAL_ARCHITECTURE.md          # System design
├── DEVELOPMENT_ROADMAP.md             # Development timeline
│
├── docs/                              # Additional documentation
│   ├── api/                           # API documentation
│   ├── deployment/                    # Deployment guides
│   └── user-guides/                   # User documentation
│
├── src/                               # Source code
│   ├── llm/                           # LLM integration
│   │   ├── client.py                  # llama-server client
│   │   ├── prompts.py                 # Prompt templates
│   │   └── chains.py                  # LangChain chains
│   │
│   ├── rag/                           # RAG pipeline
│   │   ├── ingestion.py               # Document processing
│   │   ├── embeddings.py              # Embedding generation
│   │   ├── retrieval.py               # Hybrid search
│   │   └── duckdb_store.py            # DuckDB vector store
│   │
│   ├── graph/                         # Knowledge graph
│   │   ├── neo4j_client.py            # Neo4j integration
│   │   ├── schema.py                  # Graph schema
│   │   └── queries.py                 # Cypher queries
│   │
│   ├── memory/                        # Memory & personalization
│   │   ├── conversation.py            # Conversation buffer
│   │   ├── student_profile.py         # Student profiling
│   │   ├── adaptive.py                # Adaptive learning
│   │   └── mem0_integration.py        # mem0 integration
│   │
│   ├── api/                           # Backend API
│   │   ├── main.py                    # FastAPI app
│   │   ├── routes/                    # API routes
│   │   └── models/                    # Pydantic models
│   │
│   ├── desktop/                       # Desktop application
│   │   ├── ui/                        # UI components
│   │   ├── main.py                    # Entry point
│   │   └── config.py                  # Configuration
│   │
│   └── mobile/                        # Mobile application (future)
│       └── ...
│
├── data/                              # Data files (gitignored)
│   ├── models/                        # LLM model files
│   ├── textbooks/                     # PDF textbooks
│   ├── embeddings/                    # Pre-computed embeddings
│   └── databases/                     # Local databases
│       ├── ai_teacher.duckdb          # Vector DB
│       ├── conversations.db           # SQLite
│       └── neo4j/                     # Neo4j data
│
├── tests/                             # Test suite
│   ├── unit/                          # Unit tests
│   ├── integration/                   # Integration tests
│   └── e2e/                           # End-to-end tests
│
├── scripts/                           # Utility scripts
│   ├── setup_llama_server.sh          # llama-server setup
│   ├── download_textbooks.py          # BSE textbook downloader
│   ├── generate_embeddings.py         # Batch embedding generation
│   └── populate_graph.py              # Knowledge graph population
│
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Poetry/PDM config
├── .env.example                       # Environment variables template
└── .gitignore                         # Git ignore rules
```

---

## Features

### Current (Proof of Concept)
- ✅ LFM2 model serving via llama-server
- ✅ API key authentication
- ✅ Headless operation (no web UI)
- ✅ OpenAI-compatible API

### Phase 1 (MVP - Months 3-5)
- [ ] RAG pipeline (DuckDB + LlamaIndex)
- [ ] Knowledge graph (Neo4j)
- [ ] Conversation memory (LangChain + mem0)
- [ ] Desktop application (Electron/Qt)
- [ ] Mathematics + Physics coverage
- [ ] Indonesian language fine-tuning

### Phase 2 (Beta - Months 6-8)
- [ ] Chemistry + Biology coverage
- [ ] Progress tracking dashboard
- [ ] Parent dashboard
- [ ] Adaptive difficulty adjustment
- [ ] 500 beta users

### Phase 3 (Mobile - Months 9-11)
- [ ] Android application
- [ ] 4-bit quantized model
- [ ] Offline mode
- [ ] Payment integration

### Phase 4 (Launch - Month 12)
- [ ] Public launch
- [ ] 10,000 active users
- [ ] Marketing campaigns
- [ ] Customer support system

---

## Contributing

We're currently in the early stages of development and not yet accepting external contributions. However, if you're interested in:

- **Beta testing** (students or parents)
- **Partnership opportunities** (schools, tutoring centers)
- **Investment opportunities**
- **Advisory roles** (education experts, AI/ML engineers)

Please reach out via [contact information to be added].

---

## Target Market

**Primary:** Indonesian junior & middle school students (ages 12-15)
- Total addressable market: ~18 million students
- Focus: Low to middle-income families
- Geographic: Urban and semi-urban areas (initially)

**Subjects Covered:**
- 📐 Mathematics (Matematika)
- ⚛️ Physics (Fisika)
- 🧪 Chemistry (Kimia)
- 🌱 Biology (Biologi)

**Curriculum:** Aligned with Kurikulum Merdeka and Indonesian national standards

---

## Business Model

**Subscription Pricing:**
- **IDR 100,000/month** (~$6.50 USD)
- All STEM subjects included
- Unlimited questions
- Progress tracking
- Parent dashboard

**Competitive Advantage:**
- 50-80% cheaper than competitors (Ruangguru, Zenius)
- Works offline (no internet dependency)
- Truly personalized (AI-adaptive)
- Fine-tuned for Indonesian students

---

## Technical Requirements

### Desktop Application
- **OS:** Windows 10+, macOS 10.15+, Linux (Ubuntu 20.04+)
- **RAM:** 8GB minimum, 16GB recommended
- **Storage:** 16GB available space
- **Processor:** Modern multi-core CPU (2015+)

### Mobile Application (Future)
- **OS:** Android 8.0+ (API level 26+)
- **RAM:** 3GB minimum, 4GB+ recommended
- **Storage:** 8GB available space
- **Processor:** ARM64 (64-bit)

### Server Requirements (Production)
- **OS:** FreeBSD 13.x+ or Linux
- **RAM:** 32GB+ (for Cassandra/Neo4j)
- **Storage:** 500GB+ SSD
- **Bandwidth:** 100Mbps+
- **Processor:** 16+ cores

---

## Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Response latency | <5 seconds | 🚧 Testing |
| Answer accuracy | >85% | ⏳ TBD |
| User retention (D30) | >50% | ⏳ TBD |
| App crash rate | <1% | ⏳ TBD |
| Monthly uptime | >99.5% | ⏳ TBD |

---

## Roadmap Summary

| Phase | Timeline | Milestone |
|-------|----------|-----------|
| **Phase 0** | Months 1-2 | Technical validation, dataset acquisition |
| **Phase 1** | Months 3-5 | MVP desktop app (Math + Physics) |
| **Phase 2** | Months 6-8 | Beta launch (500 users, all subjects) |
| **Phase 3** | Months 9-11 | Mobile app development |
| **Phase 4** | Month 12 | Public launch (10,000 users) |
| **Phase 5** | Months 13-24 | Scaling (200,000 users) |

---

## License

[To be determined - likely MIT or Apache 2.0]

---

## Acknowledgments

This project builds upon incredible open-source work:

- **[llama.cpp](https://github.com/ggml-org/llama.cpp)** - Fast LLM inference
- **[LlamaIndex](https://www.llamaindex.ai/)** - RAG framework
- **[LangChain](https://www.langchain.com/)** - LLM orchestration
- **[DuckDB](https://duckdb.org/)** - Embedded analytics database
- **[Neo4j](https://neo4j.com/)** - Graph database platform
- **Buku Sekolah Elektronik (BSE)** - Free Indonesian textbooks

Special thanks to the Indonesian Ministry of Education for providing free, high-quality textbooks via the BSE program.

---

## Contact

**Project Status:** Pre-seed, actively seeking funding and team members

**Looking for:**
- Co-founders (business & technical)
- Angel investors
- Beta testers (students & parents)
- Education advisors
- AI/ML engineers

**Email:** [To be added]
**Website:** [To be added]
**GitHub:** https://github.com/[org]/AI_Teacher

---

## FAQ

### Q: Why local LLM instead of cloud APIs like OpenAI?
**A:** Local LLM provides:
1. **Zero ongoing inference costs** - Critical for IDR 100K pricing
2. **Works offline** - Essential for Indonesia's connectivity challenges
3. **Privacy** - Student data never leaves device
4. **Low latency** - No network round-trip

### Q: Why focus on Indonesia specifically?
**A:** Indonesia has:
1. Large market (45M+ students)
2. High demand for affordable education
3. Significant education inequality (urban vs. rural)
4. Growing smartphone penetration
5. Government support for education technology

### Q: Can this work in other countries?
**A:** Yes! The architecture is language-agnostic. We can fine-tune for other languages and curricula. Indonesia is our beachhead market, with plans to expand to Southeast Asia.

### Q: How do you ensure answer accuracy?
**A:** Multiple layers:
1. RAG grounds answers in textbook content
2. Fine-tuning on validated Q&A datasets
3. Response validation checks
4. Human review of common queries
5. User feedback loop

### Q: What about content moderation?
**A:** Chain-of-prompts system restricts to STEM topics only. Off-topic or inappropriate queries are politely rejected.

### Q: Will you replace teachers?
**A:** No. We're a **supplementary learning tool**, not a replacement. Think of us as an always-available tutor for homework help and practice.

---

<div align="center">

**Built with ❤️ for Indonesian students**

*Making quality STEM education accessible to everyone*

---

**Status:** 🚧 In Development | **Version:** 0.1.0-poc | **Updated:** November 2025

</div>
