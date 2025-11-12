# AI Teacher - Technical Architecture Documentation

**Version:** 1.0
**Date:** November 2025
**Status:** Design Phase

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Layers](#architecture-layers)
4. [Client Architecture](#client-architecture)
5. [Server Architecture](#server-architecture)
6. [Data Flow](#data-flow)
7. [LLM Pipeline](#llm-pipeline)
8. [RAG Implementation](#rag-implementation)
9. [Memory & Personalization](#memory--personalization)
10. [Security & Privacy](#security--privacy)
11. [Deployment Strategy](#deployment-strategy)
12. [Performance Optimization](#performance-optimization)
13. [Monitoring & Observability](#monitoring--observability)

---

## System Overview

AI Teacher is a hybrid architecture combining local LLM inference with cloud-based knowledge retrieval. The system is designed to:

- **Minimize latency:** Local LLM processing for instant responses
- **Reduce costs:** No per-query cloud inference fees
- **Enable offline:** Core functionality works without internet
- **Scale efficiently:** Centralized knowledge base, distributed inference

### Design Principles

1. **Local-First:** Maximum processing on user device
2. **Graceful Degradation:** Fallback mechanisms for failures
3. **Privacy-Preserving:** Student data stays on device
4. **Resource-Efficient:** Works on low-end hardware
5. **Modular:** Components can be upgraded independently

---

## Technology Stack

### Client-Side Technologies

#### Desktop Application
```
┌─────────────────────────────────────┐
│         User Interface              │
│  - Electron / Qt Framework          │
│  - React / Vue.js (if Electron)     │
│  - Tailwind CSS for styling         │
└─────────────────────────────────────┘
                 │
┌─────────────────────────────────────┐
│      Application Layer              │
│  - Python 3.10+                     │
│  - LangChain 0.1.x                  │
│  - LlamaIndex 0.9.x                 │
└─────────────────────────────────────┘
                 │
┌─────────────────────────────────────┐
│       LLM Runtime Layer             │
│  - LFM2 (llama.cpp binding)         │
│  - GGUF quantized models            │
│  - CPU inference optimizations      │
└─────────────────────────────────────┘
```

**Key Libraries:**
- **Electron:** Cross-platform desktop framework (if web tech stack)
- **Qt/PyQt:** Native desktop UI (alternative, better performance)
- **llama.cpp:** Fast CPU inference for LFM2
- **LangChain:** LLM orchestration and memory
- **LlamaIndex:** RAG framework
- **Chroma/FAISS:** Local vector database (optional cache)
- **SQLite:** Local conversation history and user data

#### Mobile Application (Android)
```
┌─────────────────────────────────────┐
│         User Interface              │
│  - React Native / Flutter           │
│  - Native Android components        │
└─────────────────────────────────────┘
                 │
┌─────────────────────────────────────┐
│      Application Layer              │
│  - JavaScript/TypeScript (RN)       │
│  - Dart (Flutter)                   │
│  - Native bridges                   │
└─────────────────────────────────────┘
                 │
┌─────────────────────────────────────┐
│       LLM Runtime Layer             │
│  - llama.cpp Android build          │
│  - 4-bit quantized LFM2             │
│  - JNI/FFI bindings                 │
└─────────────────────────────────────┘
```

**Key Technologies:**
- **React Native:** Familiar tech stack (JavaScript)
- **Flutter:** Better performance, smaller app size (alternative)
- **llama.cpp Android:** Native LLM inference
- **SQLite:** Local storage
- **Realm:** Alternative local database (better performance)

### Server-Side Technologies

#### Infrastructure
- **Operating System:** FreeBSD 13.x or 14.x
- **Containerization:** FreeBSD Jails
- **Networking:** vnet (virtual networking), Tailscale VPN
- **File System:** ZFS (snapshots, compression, integrity)

#### Databases
```
┌─────────────────────────────────────┐
│      Vector Database                │
│  - Apache Cassandra 4.x             │
│  - Python Driver: cassandra-driver  │
│  - Replication Factor: 3            │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│      Knowledge Graph                │
│  - JanusGraph 1.0.x                 │
│  - Backend: Cassandra               │
│  - Index: Elasticsearch (optional)  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│      Relational Database            │
│  - PostgreSQL 15+                   │
│  - User accounts, subscriptions     │
│  - Analytics (aggregated)           │
└─────────────────────────────────────┘
```

#### API & Services
- **Framework:** FastAPI (Python) or Go Fiber
- **Authentication:** JWT tokens
- **API Gateway:** Nginx or Traefik
- **Message Queue:** Redis (for async tasks)
- **Caching:** Redis
- **File Storage:** MinIO (S3-compatible)

#### DevOps & Monitoring
- **CI/CD:** GitHub Actions or GitLab CI
- **Monitoring:** Prometheus + Grafana
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana) or Loki
- **Alerting:** Alertmanager
- **Backup:** Restic + S3-compatible storage

---

## Architecture Layers

### High-Level System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                             │
│                                                                   │
│  ┌────────────────┐              ┌────────────────┐             │
│  │    Desktop     │              │     Mobile     │             │
│  │  Application   │              │  Application   │             │
│  │                │              │   (Android)    │             │
│  │  [LFM2 Local]  │              │  [LFM2 Local]  │             │
│  └────────────────┘              └────────────────┘             │
│          │                               │                       │
└──────────┼───────────────────────────────┼───────────────────────┘
           │                               │
           │         HTTPS/REST API        │
           │                               │
┌──────────┼───────────────────────────────┼───────────────────────┐
│          │      API GATEWAY LAYER        │                       │
│          ▼                               ▼                       │
│  ┌────────────────────────────────────────────────┐             │
│  │         Nginx / Traefik (Load Balancer)        │             │
│  │  - TLS termination                             │             │
│  │  - Rate limiting                               │             │
│  │  - Request routing                             │             │
│  └────────────────────────────────────────────────┘             │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
┌──────────────────────────────────┼───────────────────────────────┐
│          APPLICATION LAYER       │                               │
│                                  ▼                               │
│  ┌────────────────────────────────────────────────┐             │
│  │           FastAPI Application                  │             │
│  │  - Authentication Service                      │             │
│  │  - User Management                             │             │
│  │  - Subscription Service                        │             │
│  │  - Model Distribution Service                  │             │
│  │  - RAG Query Service (fallback)                │             │
│  │  - Analytics Service                           │             │
│  └────────────────────────────────────────────────┘             │
│                    │                                             │
└────────────────────┼─────────────────────────────────────────────┘
                     │
┌────────────────────┼─────────────────────────────────────────────┐
│      DATA LAYER    │                                             │
│                    ▼                                             │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐ │
│  │   Vector Database       │  │   Knowledge Graph            │ │
│  │   (Cassandra)           │  │   (JanusGraph)               │ │
│  │   - Embeddings          │  │   - Concepts                 │ │
│  │   - Semantic search     │  │   - Relationships            │ │
│  │                         │  │   - Prerequisites            │ │
│  └─────────────────────────┘  └──────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐ │
│  │   PostgreSQL            │  │   Redis                      │ │
│  │   - Users               │  │   - Cache                    │ │
│  │   - Subscriptions       │  │   - Sessions                 │ │
│  │   - Analytics           │  │   - Task queue               │ │
│  └─────────────────────────┘  └──────────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │   MinIO (S3)                                             │  │
│  │   - Model files (.gguf)                                  │  │
│  │   - Textbook PDFs                                        │  │
│  │   - Animations / media                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Client Architecture

### Desktop Application Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                         │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │  Chat UI       │  │  Dashboard     │  │  Settings      │ │
│  │  Component     │  │  Component     │  │  Component     │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────┐
│       APPLICATION LOGIC    │                                  │
│                            ▼                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │            Conversation Manager                        │  │
│  │  - Handle user input                                   │  │
│  │  - Route to appropriate service                        │  │
│  │  - Manage conversation state                           │  │
│  └────────────────────────────────────────────────────────┘  │
│                    │                │                         │
│         ┌──────────┼────────────────┼──────────┐             │
│         ▼          ▼                ▼          ▼             │
│  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌──────────────┐    │
│  │ LangChain│ │LlamaIndex│ │ LFM2     │ │ API Client   │    │
│  │ Memory   │ │ RAG      │ │ Inference│ │ (Server)     │    │
│  └──────────┘ └─────────┘ └──────────┘ └──────────────┘    │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────┐
│         DATA LAYER         │                                  │
│                            ▼                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │  SQLite DB     │  │  Local Cache   │  │  Model Files   │ │
│  │  - History     │  │  - Embeddings  │  │  - LFM2.gguf   │ │
│  │  - User data   │  │  - Responses   │  │  - Vocab       │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Chat Interface
- Real-time message display
- Markdown rendering for formatted responses
- Code syntax highlighting (for math equations)
- LaTeX rendering for mathematical formulas
- Image/animation embedding
- Loading indicators
- Error handling and retry

#### 2. LangChain Memory Module
```python
from langchain.memory import ConversationBufferWindowMemory
from langchain.memory import ConversationSummaryMemory

# Short-term memory (last N messages)
short_term_memory = ConversationBufferWindowMemory(
    k=10,  # Last 10 messages
    return_messages=True
)

# Long-term memory (summarized history)
long_term_memory = ConversationSummaryMemory(
    llm=llm,
    max_token_limit=500
)

# Student profile memory (mem0)
from mem0 import Memory
student_memory = Memory(
    config={
        "vector_store": {
            "provider": "chroma",
            "config": {"path": "./student_profile.db"}
        }
    }
)
```

**Memory Types:**
- **Conversation Buffer:** Recent conversation history
- **Summary Memory:** Compressed older conversations
- **Entity Memory:** Key facts about student (strengths, weaknesses)
- **Vector Memory (mem0):** Semantic memory for personalization

#### 3. LlamaIndex RAG Pipeline
```python
from llama_index import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    ServiceContext
)
from llama_index.vector_stores import CassandraVectorStore

# Vector store connection (to Cassandra)
vector_store = CassandraVectorStore(
    contact_points=["server.example.com"],
    keyspace="ai_teacher",
    table="embeddings"
)

# Create index
service_context = ServiceContext.from_defaults(
    llm=local_llm,  # LFM2
    embed_model=embedding_model
)

index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
    service_context=service_context
)

# Query engine
query_engine = index.as_query_engine(
    similarity_top_k=5,
    response_mode="tree_summarize"
)
```

#### 4. LFM2 Inference Engine
```python
from llama_cpp import Llama

# Load model
llm = Llama(
    model_path="./models/lfm2-indo-stem-q4.gguf",
    n_ctx=4096,  # Context window
    n_threads=4,  # CPU threads
    n_gpu_layers=0,  # CPU-only
    verbose=False
)

# Inference function
def generate_response(prompt: str, max_tokens: int = 512):
    response = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=0.7,
        top_p=0.9,
        stop=["User:", "\n\n\n"],
        echo=False
    )
    return response["choices"][0]["text"]
```

#### 5. System Prompt Chain
```python
from langchain import PromptTemplate, LLMChain

# Base system prompt
SYSTEM_PROMPT = """
Kamu adalah AI Teacher, asisten belajar STEM untuk siswa SMP Indonesia.

ATURAN PENTING:
1. HANYA jawab pertanyaan tentang Matematika, Fisika, Kimia, dan Biologi
2. Jika pertanyaan di luar topik STEM, tolak dengan sopan
3. Gunakan Bahasa Indonesia yang mudah dipahami siswa SMP
4. Berikan contoh konkret dan relevan dengan kehidupan sehari-hari
5. Jika siswa salah memahami, koreksi dengan lembut dan jelaskan yang benar
6. Sesuaikan tingkat kesulitan dengan kemampuan siswa

Informasi Siswa:
{student_profile}

Riwayat Percakapan:
{chat_history}

Materi Relevan dari Buku:
{retrieved_context}

Pertanyaan Siswa: {question}

Jawaban AI Teacher:
"""

prompt_template = PromptTemplate(
    input_variables=["student_profile", "chat_history", "retrieved_context", "question"],
    template=SYSTEM_PROMPT
)

chain = LLMChain(llm=llm, prompt=prompt_template)
```

#### 6. Response Validation
```python
def validate_response(question: str, response: str) -> dict:
    """Validate that response is STEM-related and appropriate"""

    # Check for off-topic rejection
    rejection_phrases = [
        "tidak bisa", "di luar topik", "hanya jawab", "tidak relevan"
    ]
    is_rejection = any(phrase in response.lower() for phrase in rejection_phrases)

    # Check for STEM keywords
    stem_keywords = [
        "matematika", "fisika", "kimia", "biologi",
        "rumus", "persamaan", "hukum", "teori", "konsep"
    ]
    has_stem_content = any(keyword in response.lower() for keyword in stem_keywords)

    # Detect potential hallucination (very low confidence)
    confidence_score = calculate_confidence(response)

    return {
        "is_valid": is_rejection or (has_stem_content and confidence_score > 0.6),
        "confidence": confidence_score,
        "is_rejection": is_rejection,
        "needs_human_review": confidence_score < 0.5
    }
```

---

## Server Architecture

### FreeBSD Jail Configuration

```
Host System (FreeBSD)
│
├── Jail 1: vector-db
│   ├── Cassandra node 1
│   ├── IP: 10.0.1.10 (vnet)
│   └── Ports: 9042 (CQL), 7000 (inter-node)
│
├── Jail 2: vector-db-2
│   ├── Cassandra node 2 (replication)
│   ├── IP: 10.0.1.11 (vnet)
│   └── Ports: 9042, 7000
│
├── Jail 3: knowledge-graph
│   ├── JanusGraph + Gremlin Server
│   ├── IP: 10.0.1.20 (vnet)
│   └── Ports: 8182 (Gremlin), 8184 (management)
│
├── Jail 4: api-server
│   ├── FastAPI application
│   ├── IP: 10.0.1.30 (vnet)
│   └── Ports: 8000 (API)
│
├── Jail 5: postgres-db
│   ├── PostgreSQL
│   ├── IP: 10.0.1.40 (vnet)
│   └── Ports: 5432
│
├── Jail 6: redis-cache
│   ├── Redis
│   ├── IP: 10.0.1.50 (vnet)
│   └── Ports: 6379
│
└── Jail 7: reverse-proxy
    ├── Nginx
    ├── IP: 10.0.1.100 (vnet)
    └── Ports: 80, 443 (exposed to internet)
```

### Jail Network Configuration

```bash
# /etc/jail.conf

exec.start = "/bin/sh /etc/rc";
exec.stop = "/bin/sh /etc/rc.shutdown";
exec.clean;
mount.devfs;

# Vector Database Jail 1
vector_db {
    host.hostname = "vector-db-1.ai-teacher.local";
    path = "/jails/vector-db-1";

    vnet;
    vnet.interface = "epair0b";
    exec.prestart = "ifconfig epair0 create up";
    exec.prestart += "ifconfig epair0a up";
    exec.prestart += "ifconfig bridge0 addm epair0a";
    exec.start = "ifconfig epair0b 10.0.1.10/24";
    exec.start += "route add default 10.0.1.1";
    exec.poststop = "ifconfig epair0a destroy";

    persist;
}

# API Server Jail
api_server {
    host.hostname = "api.ai-teacher.local";
    path = "/jails/api-server";

    vnet;
    vnet.interface = "epair3b";
    exec.prestart = "ifconfig epair3 create up";
    exec.prestart += "ifconfig epair3a up";
    exec.prestart += "ifconfig bridge0 addm epair3a";
    exec.start = "ifconfig epair3b 10.0.1.30/24";
    exec.start += "route add default 10.0.1.1";
    exec.poststop = "ifconfig epair3a destroy";

    persist;
}

# ... (similar for other jails)
```

### Tailscale VPN Setup

```bash
# Install Tailscale on FreeBSD host
pkg install tailscale

# Start Tailscale
service tailscaled enable
service tailscaled start

# Authenticate
tailscale up

# Enable subnet routing (for jail network)
tailscale up --advertise-routes=10.0.1.0/24 --accept-routes

# Now accessible from anywhere via Tailscale IP
```

---

## Data Flow

### Typical User Query Flow

```
┌──────────────────────────────────────────────────────────────┐
│  STEP 1: User Input                                          │
│  User: "Jelaskan hukum Newton 2"                             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 2: Input Processing                                    │
│  - Language detection (Bahasa Indonesia)                     │
│  - Intent classification (question/explanation request)      │
│  - Topic extraction ("Fisika", "Hukum Newton")               │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 3: Memory Retrieval (LangChain)                        │
│  - Load recent conversation history                          │
│  - Load student profile from mem0                            │
│    * Previous topics covered: [Gerak Lurus, Gaya]            │
│    * Comprehension level: Medium                             │
│    * Learning style: Visual + Examples                       │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 4: RAG Retrieval (LlamaIndex)                          │
│  A. Generate query embedding                                 │
│  B. Search Cassandra vector DB (top-k=5 chunks)              │
│     Results:                                                 │
│     - Buku Fisika SMP Kelas 8, Hal 45-46 (score: 0.92)      │
│     - Buku Fisika SMP Kelas 8, Hal 47 (score: 0.88)         │
│     - Buku Fisika SMP Kelas 9, Hal 12 (score: 0.75)         │
│  C. Query JanusGraph for related concepts                    │
│     - Prerequisites: [Gaya, Massa, Percepatan]               │
│     - Related: [Hukum Newton 1, Hukum Newton 3]              │
│  D. Combine and rank results                                 │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 5: Prompt Construction                                 │
│  Combine:                                                    │
│  - System prompt (domain restriction, persona)               │
│  - Student profile (from memory)                             │
│  - Conversation history (last 10 messages)                   │
│  - Retrieved context (textbook chunks)                       │
│  - Current question                                          │
│                                                              │
│  Final prompt: ~2500 tokens                                  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 6: LFM2 Inference (Local)                              │
│  - Load model from memory (if not already loaded)            │
│  - Generate response (streaming)                             │
│  - Max tokens: 512                                           │
│  - Temperature: 0.7                                          │
│  - Generation time: ~3-5 seconds on modern CPU               │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 7: Response Validation                                 │
│  - Check for STEM relevance ✓                                │
│  - Check for inappropriate content ✓                         │
│  - Validate factual accuracy (confidence check)              │
│  - Format markdown/LaTeX                                     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 8: Memory Update                                       │
│  - Save conversation to buffer                               │
│  - Update student profile:                                   │
│    * Topics covered: +[Hukum Newton 2]                       │
│    * Comprehension signals (understood/confused)             │
│  - Store in local SQLite                                     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 9: Display to User                                     │
│  Response:                                                   │
│  "Hukum Newton 2 mengatakan bahwa percepatan suatu benda     │
│   berbanding lurus dengan gaya yang bekerja padanya dan      │
│   berbanding terbalik dengan massanya.                       │
│                                                              │
│   Rumusnya: F = m × a                                        │
│                                                              │
│   Contoh: Jika kamu mendorong meja yang berat (massa        │
│   besar) dengan gaya yang sama seperti mendorong buku        │
│   (massa kecil), buku akan bergerak lebih cepat..."          │
│                                                              │
│  [Animation button: Visualisasi Hukum Newton 2]             │
└──────────────────────────────────────────────────────────────┘
```

---

## LLM Pipeline

### Model Selection: LFM2

**LFM2 Specifications:**
- **Architecture:** Transformer-based (similar to LLaMA 2/3)
- **Parameters:** 7B or 13B (depending on device capability)
- **Quantization:** 4-bit (GGUF format) for mobile, 8-bit for desktop
- **Context Window:** 4096 tokens
- **Languages:** Multilingual (focus: Indonesian)

### Fine-Tuning Strategy

#### Phase 1: Indonesian Language Adaptation
```python
# Dataset composition
indonesian_corpus = {
    "general_indonesian": 50_000,  # Wikipedia, news, books
    "educational_content": 100_000,  # Textbooks, articles
    "conversation_pairs": 20_000,  # Q&A format
}

# Training config
training_config = {
    "method": "LoRA",  # Low-Rank Adaptation
    "rank": 8,
    "alpha": 16,
    "target_modules": ["q_proj", "v_proj"],
    "learning_rate": 3e-4,
    "epochs": 3,
    "batch_size": 4,
    "gradient_accumulation": 8,
}
```

#### Phase 2: STEM Knowledge Injection
```python
# STEM dataset
stem_dataset = {
    "mathematics": {
        "textbooks": ["BSE Mat 7", "BSE Mat 8", "BSE Mat 9"],
        "problems": 10_000,
        "solutions": 10_000
    },
    "physics": {
        "textbooks": ["BSE Fisika 7", "BSE Fisika 8", "BSE Fisika 9"],
        "problems": 8_000,
        "solutions": 8_000
    },
    "chemistry": {
        "textbooks": ["BSE Kimia 7", "BSE Kimia 8", "BSE Kimia 9"],
        "problems": 6_000,
        "solutions": 6_000
    },
    "biology": {
        "textbooks": ["BSE Biologi 7", "BSE Biologi 8", "BSE Biologi 9"],
        "problems": 6_000,
        "solutions": 6_000
    }
}
```

#### Phase 3: RAG Optimization
```python
# Train for better retrieval awareness
rag_training = {
    "format": "Given context: {context}\nQuestion: {question}\nAnswer:",
    "num_samples": 50_000,
    "strategy": "contrastive_learning",
    # Teach model to:
    # 1. Cite sources from context
    # 2. Say "I don't know" when context insufficient
    # 3. Distinguish context info from parametric knowledge
}
```

### Model Quantization for Mobile

```python
# Original model: 7B parameters × 16-bit = ~14GB
# Quantized model: 7B parameters × 4-bit = ~3.5GB

from llama_cpp import Llama

# Desktop: 8-bit quantization (better quality)
llama_cpp/quantize \
    ./models/lfm2-indo-stem-fp16.bin \
    ./models/lfm2-indo-stem-q8.gguf \
    q8_0

# Mobile: 4-bit quantization (smaller size)
llama_cpp/quantize \
    ./models/lfm2-indo-stem-fp16.bin \
    ./models/lfm2-indo-stem-q4.gguf \
    q4_k_m

# Performance comparison
# Desktop (8-bit): ~1.5GB RAM, 20 tokens/sec (CPU)
# Mobile (4-bit): ~600MB RAM, 8 tokens/sec (CPU)
```

---

## RAG Implementation

### Document Processing Pipeline

```python
from llama_index import (
    SimpleDirectoryReader,
    Document,
    VectorStoreIndex
)
from llama_index.node_parser import SimpleNodeParser
from llama_index.text_splitter import TokenTextSplitter

# Step 1: Load PDFs
documents = SimpleDirectoryReader(
    input_dir="./textbooks/",
    required_exts=[".pdf"],
    recursive=True
).load_data()

# Step 2: Extract metadata
for doc in documents:
    # Parse filename: "Matematika_Kelas8_Bab2_Persamaan_Linear.pdf"
    metadata = extract_metadata(doc.metadata["file_name"])
    doc.metadata.update({
        "subject": metadata["subject"],  # Matematika
        "grade": metadata["grade"],      # 8
        "chapter": metadata["chapter"],  # Bab 2
        "topic": metadata["topic"]       # Persamaan Linear
    })

# Step 3: Chunk documents
text_splitter = TokenTextSplitter(
    chunk_size=512,       # ~300 words
    chunk_overlap=50,     # Overlap for context preservation
    separator="\n\n"
)

node_parser = SimpleNodeParser.from_defaults(
    text_splitter=text_splitter,
    include_metadata=True
)

nodes = node_parser.get_nodes_from_documents(documents)

# Step 4: Generate embeddings
from llama_index.embeddings import HuggingFaceEmbedding

embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    # Supports Indonesian language
)

# Step 5: Store in Cassandra
from llama_index.vector_stores import CassandraVectorStore

vector_store = CassandraVectorStore(
    contact_points=["10.0.1.10"],
    keyspace="ai_teacher",
    table="document_embeddings",
    embedding_dimension=768
)

index = VectorStoreIndex(
    nodes=nodes,
    vector_store=vector_store,
    embed_model=embed_model
)
```

### Cassandra Schema

```cql
-- Create keyspace
CREATE KEYSPACE ai_teacher
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 3
};

USE ai_teacher;

-- Embeddings table
CREATE TABLE document_embeddings (
    id UUID PRIMARY KEY,
    content TEXT,
    embedding VECTOR<FLOAT, 768>,

    -- Metadata
    subject TEXT,
    grade INT,
    chapter TEXT,
    topic TEXT,
    page_number INT,
    source_file TEXT,

    -- Timestamps
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Create vector index (Cassandra 5.0+)
CREATE CUSTOM INDEX embedding_idx
ON document_embeddings(embedding)
USING 'StorageAttachedIndex';

-- Metadata indexes
CREATE INDEX ON document_embeddings(subject);
CREATE INDEX ON document_embeddings(grade);
CREATE INDEX ON document_embeddings(topic);
```

### JanusGraph Knowledge Graph Schema

```groovy
// Vertex labels (Concepts)
mgmt = graph.openManagement()

// Concept vertex
concept = mgmt.makeVertexLabel('Concept').make()
mgmt.makePropertyKey('name').dataType(String.class).make()
mgmt.makePropertyKey('subject').dataType(String.class).make()
mgmt.makePropertyKey('description').dataType(String.class).make()
mgmt.makePropertyKey('grade_level').dataType(Integer.class).make()

// Edge labels (Relationships)
prerequisite = mgmt.makeEdgeLabel('PREREQUISITE').make()
related_to = mgmt.makeEdgeLabel('RELATED_TO').make()
part_of = mgmt.makeEdgeLabel('PART_OF').make()
example_of = mgmt.makeEdgeLabel('EXAMPLE_OF').make()

mgmt.commit()

// Example data
g.addV('Concept')
  .property('name', 'Hukum Newton 2')
  .property('subject', 'Fisika')
  .property('description', 'F = m × a')
  .property('grade_level', 8)
  .next()

g.addV('Concept')
  .property('name', 'Gaya')
  .property('subject', 'Fisika')
  .property('grade_level', 7)
  .next()

// Create prerequisite relationship
newton2 = g.V().has('name', 'Hukum Newton 2').next()
force = g.V().has('name', 'Gaya').next()
newton2.addEdge('PREREQUISITE', force)
```

### Hybrid Search Strategy

```python
async def hybrid_search(query: str, student_profile: dict):
    """Combine vector search + knowledge graph + student context"""

    # 1. Vector similarity search
    vector_results = await vector_store.similarity_search(
        query=query,
        k=10,
        filter={
            "grade": student_profile["grade"]  # Filter by student grade
        }
    )

    # 2. Knowledge graph traversal
    # Find related concepts and prerequisites
    graph_results = await knowledge_graph.traverse(
        start_concept=extract_main_concept(query),
        depth=2,
        include_prerequisites=True
    )

    # 3. Combine and rerank
    combined_results = rerank_results(
        vector_results=vector_results,
        graph_results=graph_results,
        student_profile=student_profile,
        # Boost factors:
        # - Student's current topics (higher relevance)
        # - Prerequisites not yet mastered (fill gaps)
        # - Appropriate difficulty level
    )

    # 4. Select top-k
    return combined_results[:5]
```

---

## Memory & Personalization

### Student Profile Model

```python
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime

class StudentProfile(BaseModel):
    user_id: str
    grade: int  # 7, 8, or 9 (SMP)

    # Learning characteristics
    comprehension_level: Dict[str, float]  # Per subject: 0.0 - 1.0
    # {
    #     "matematika": 0.75,
    #     "fisika": 0.60,
    #     "kimia": 0.70,
    #     "biologi": 0.80
    # }

    # Topics covered
    mastered_topics: List[str]
    # ["Aljabar Dasar", "Hukum Newton 1", "Struktur Atom"]

    struggling_topics: List[str]
    # ["Persamaan Kuadrat", "Hukum Newton 3"]

    # Learning preferences
    preferred_explanation_style: str  # "concise" | "detailed" | "visual"
    prefers_examples: bool
    prefers_step_by_step: bool

    # Engagement metrics
    total_questions_asked: int
    avg_session_duration: int  # minutes
    last_active: datetime
    streak_days: int

    # Progress tracking
    weekly_progress: Dict[str, int]  # Questions per subject
    monthly_test_scores: List[float]

    # Adaptive parameters
    current_difficulty_level: float  # 0.0 (easy) - 1.0 (hard)
    recent_response_quality: List[float]  # Last 10 responses rated by user

class ConversationContext(BaseModel):
    session_id: str
    messages: List[Dict[str, str]]
    current_topic: str
    topic_depth: int  # How deep into topic (1 = intro, 5 = advanced)
    confusion_indicators: int  # Count of "tidak mengerti", "bingung", etc.
```

### Adaptive Learning Algorithm

```python
class AdaptiveLearningEngine:
    def __init__(self, student_profile: StudentProfile):
        self.profile = student_profile

    def adjust_difficulty(self, user_feedback: str, response_time: int):
        """Adjust explanation complexity based on user signals"""

        # Confusion indicators
        confusion_keywords = [
            "bingung", "tidak mengerti", "susah", "sulit",
            "bisa dijelaskan lagi", "tidak paham"
        ]
        is_confused = any(kw in user_feedback.lower() for kw in confusion_keywords)

        # Comprehension indicators
        understanding_keywords = [
            "mengerti", "paham", "jelas", "thanks", "terima kasih",
            "oke", "ok", "siap"
        ]
        understands = any(kw in user_feedback.lower() for kw in understanding_keywords)

        # Adjust difficulty
        if is_confused:
            self.profile.current_difficulty_level *= 0.8  # Simplify
            # Add to struggling topics
            if self.profile.current_topic not in self.profile.struggling_topics:
                self.profile.struggling_topics.append(self.profile.current_topic)

        elif understands:
            self.profile.current_difficulty_level *= 1.1  # Increase challenge
            self.profile.current_difficulty_level = min(1.0, self.profile.current_difficulty_level)

            # Maybe ready to move to mastered topics
            if self.profile.current_topic in self.profile.struggling_topics:
                self.profile.struggling_topics.remove(self.profile.current_topic)

            if self.profile.current_topic not in self.profile.mastered_topics:
                self.profile.mastered_topics.append(self.profile.current_topic)

        # Response time analysis
        if response_time > 300:  # User took >5 min to respond
            # Might indicate processing complex info (good)
            # OR confusion (bad) - disambiguate with follow-up
            pass

        return self.profile

    def generate_personalized_prompt_additions(self) -> str:
        """Add student-specific context to prompt"""

        additions = []

        # Difficulty level
        if self.profile.current_difficulty_level < 0.4:
            additions.append("Jelaskan dengan sangat sederhana, seperti berbicara dengan adik kelas.")
        elif self.profile.current_difficulty_level < 0.7:
            additions.append("Jelaskan dengan bahasa yang mudah dipahami siswa SMP.")
        else:
            additions.append("Kamu bisa jelaskan secara mendalam, siswa ini cukup mahir.")

        # Learning style
        if self.profile.prefers_examples:
            additions.append("Berikan contoh konkret dari kehidupan sehari-hari.")

        if self.profile.prefers_step_by_step:
            additions.append("Jelaskan langkah demi langkah secara sistematis.")

        # Struggling topics (provide extra support)
        if self.profile.current_topic in self.profile.struggling_topics:
            additions.append(
                f"Siswa ini kesulitan dengan {self.profile.current_topic}. "
                "Bersabarlah dan pastikan konsep dasar sudah dipahami."
            )

        # Prerequisites check
        prerequisites = self.get_prerequisites(self.profile.current_topic)
        not_mastered = [p for p in prerequisites if p not in self.profile.mastered_topics]
        if not_mastered:
            additions.append(
                f"Siswa mungkin belum menguasai: {', '.join(not_mastered)}. "
                "Jelaskan konsep prasyarat jika perlu."
            )

        return "\n".join(additions)
```

### mem0 Integration

```python
from mem0 import Memory

# Initialize mem0
memory = Memory(config={
    "vector_store": {
        "provider": "chroma",
        "config": {
            "path": "./student_memory.db",
            "collection_name": "student_profiles"
        }
    },
    "llm": {
        "provider": "llama",
        "config": {
            "model": "lfm2-indo-stem-q8.gguf",
            "temperature": 0.3
        }
    }
})

# Store conversation with context
memory.add(
    messages=[
        {"role": "user", "content": "Jelaskan hukum Newton 2"},
        {"role": "assistant", "content": "Hukum Newton 2 mengatakan..."}
    ],
    user_id=student_id,
    metadata={
        "subject": "Fisika",
        "topic": "Hukum Newton 2",
        "comprehension": "high",  # Inferred from follow-up questions
        "timestamp": datetime.now()
    }
)

# Retrieve relevant memories for context
relevant_memories = memory.search(
    query="Apa itu percepatan?",
    user_id=student_id,
    limit=5
)
# Returns previous conversations about "percepatan" or related topics
```

---

## Security & Privacy

### Data Privacy Principles

1. **Local-First Architecture**
   - All conversation data stored locally on device
   - No conversation content sent to server
   - Only anonymous analytics (aggregated) sent

2. **Minimal Server Data**
   - Server stores: User ID, subscription status, device ID
   - Server does NOT store: Conversations, student performance, personal info

3. **Encryption**
   - Local SQLite database: Encrypted with SQLCipher
   - API communication: TLS 1.3
   - Model files: Signed and checksummed

### Authentication & Authorization

```python
# JWT-based authentication
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

security = HTTPBearer()

def create_access_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=30),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=403, detail="Invalid token")

        # Check subscription status
        is_subscribed = await check_subscription(user_id)
        if not is_subscribed:
            raise HTTPException(status_code=402, detail="Subscription expired")

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=403, detail="Invalid token")
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/query")
@limiter.limit("100/hour")  # 100 queries per hour per IP
async def handle_query(query: str, user_id: str = Depends(verify_token)):
    # Handle query
    pass
```

---

## Deployment Strategy

### Client Deployment

#### Desktop Application

**Build Process:**
```bash
# Using Electron
npm run build:windows
npm run build:mac
npm run build:linux

# Using PyInstaller (Python-based)
pyinstaller --onefile --windowed \
    --add-data "models:models" \
    --add-data "assets:assets" \
    --icon=icon.ico \
    ai_teacher_desktop.py

# Result: Single executable (~4GB with model)
```

**Distribution:**
- Website download (self-hosted)
- GitHub Releases
- Update mechanism: Built-in auto-updater

#### Mobile Application

**Build Process:**
```bash
# Android (React Native)
cd android
./gradlew assembleRelease

# Result: APK/AAB with bundled model
```

**Distribution:**
- Google Play Store
- APK direct download (for devices without Play Store)
- Model downloaded on first launch (to reduce initial APK size)

### Server Deployment

#### Initial Setup (Single FreeBSD Server)

```bash
# 1. Install FreeBSD 14.0
# 2. Configure ZFS
zpool create -f data ada1 ada2  # RAID mirror
zfs create -o mountpoint=/jails data/jails

# 3. Create jails
for jail in vector-db-1 vector-db-2 knowledge-graph api-server postgres redis nginx; do
    zfs create data/jails/$jail
    # Install base system
    bsdinstall jail /jails/$jail
done

# 4. Install Tailscale
pkg install tailscale
service tailscaled enable && service tailscaled start
tailscale up --advertise-routes=10.0.1.0/24

# 5. Configure jails (see jail.conf above)
service jail enable
service jail start

# 6. Install services in jails
jexec vector-db-1 pkg install cassandra4
jexec knowledge-graph pkg install openjdk11 janusgraph
jexec api-server pkg install python39 py39-pip
# ... etc

# 7. Deploy application code
cd /jails/api-server/home
git clone https://github.com/your-org/ai-teacher-api.git
cd ai-teacher-api
pip install -r requirements.txt

# 8. Start services
jexec api-server service ai_teacher_api start
```

#### Scaling Strategy

**Phase 1 (0-10K users):** Single server with jails
**Phase 2 (10K-50K users):** Add second server, Cassandra cluster
**Phase 3 (50K-200K users):** Multiple servers, load balancer, CDN

---

## Performance Optimization

### Client-Side Optimizations

#### Model Loading
```python
# Lazy loading: Load model only when first query arrives
class LLMManager:
    def __init__(self):
        self.model = None

    def get_model(self):
        if self.model is None:
            print("Loading LFM2 model (one-time, ~10 seconds)...")
            self.model = Llama(
                model_path="./models/lfm2-q8.gguf",
                n_ctx=4096,
                n_threads=os.cpu_count() - 1,  # Leave one core free
                use_mlock=True,  # Lock in RAM (prevent swapping)
            )
        return self.model
```

#### Caching Strategy
```python
import hashlib
import pickle

class ResponseCache:
    """Cache frequently asked questions"""

    def __init__(self, cache_file="./cache.db"):
        self.cache_file = cache_file
        self.cache = self.load_cache()

    def get_cache_key(self, query: str, context: str) -> str:
        content = f"{query}|{context}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, query: str, context: str):
        key = self.get_cache_key(query, context)
        return self.cache.get(key)

    def set(self, query: str, context: str, response: str):
        key = self.get_cache_key(query, context)
        self.cache[key] = {
            "response": response,
            "timestamp": datetime.now(),
            "hit_count": 0
        }
        self.save_cache()
```

### Server-Side Optimizations

#### Database Optimization

**Cassandra:**
```yaml
# cassandra.yaml optimizations
compaction_throughput_mb_per_sec: 64
concurrent_reads: 32
concurrent_writes: 32
memtable_allocation_type: heap_buffers
file_cache_size_in_mb: 2048

# Use SSD-optimized settings
disk_optimization_strategy: ssd
```

**PostgreSQL:**
```sql
-- postgresql.conf optimizations
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1  # SSD
effective_io_concurrency = 200
work_mem = 64MB
max_worker_processes = 8
max_parallel_workers_per_gather = 4
```

#### API Response Time Targets

| Endpoint | Target | 95th Percentile |
|----------|--------|-----------------|
| `/auth/login` | < 200ms | < 500ms |
| `/user/profile` | < 100ms | < 300ms |
| `/rag/query` | < 500ms | < 1000ms |
| `/model/download` | N/A (large file) | N/A |

---

## Monitoring & Observability

### Metrics Collection

```python
from prometheus_client import Counter, Histogram, Gauge

# API metrics
request_count = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

# LLM metrics
llm_inference_duration = Histogram(
    'llm_inference_duration_seconds',
    'LLM inference time'
)

llm_tokens_generated = Counter(
    'llm_tokens_generated_total',
    'Total tokens generated'
)

# User metrics
active_users = Gauge(
    'active_users',
    'Number of active users'
)

# Database metrics
cassandra_query_duration = Histogram(
    'cassandra_query_duration_seconds',
    'Cassandra query duration'
)
```

### Logging Strategy

```python
import structlog

logger = structlog.get_logger()

# Structured logging
logger.info(
    "llm_query_completed",
    user_id=user_id,
    query=query[:50],  # Truncate for privacy
    response_length=len(response),
    inference_time_ms=inference_time_ms,
    tokens_generated=tokens_generated,
    rag_retrieved_docs=len(retrieved_docs),
    cache_hit=cache_hit
)
```

### Alerting Rules

```yaml
# Prometheus alerting rules
groups:
  - name: ai_teacher_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(api_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: SlowLLMInference
        expr: histogram_quantile(0.95, llm_inference_duration_seconds) > 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "LLM inference is slow (95th percentile > 10s)"

      - alert: CassandraDown
        expr: up{job="cassandra"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Cassandra node is down"
```

### Dashboard (Grafana)

Key panels:
1. **User Metrics:** Active users, new signups, churn rate
2. **Performance:** API response times, LLM inference times
3. **System Health:** CPU, RAM, disk usage per jail
4. **Database:** Cassandra throughput, JanusGraph query times
5. **Business:** Revenue, subscription conversion, CAC
6. **Learning Outcomes:** Questions asked per subject, user ratings

---

## Next Steps

1. **Prototype Development:**
   - Build minimal RAG pipeline
   - Test LFM2 inference on target hardware
   - Create basic UI mockups

2. **Dataset Acquisition:**
   - Download BSE textbooks
   - Create initial embedding dataset
   - Build knowledge graph schema

3. **Infrastructure Setup:**
   - Purchase/rent FreeBSD server
   - Set up jails and databases
   - Configure Tailscale VPN

4. **MVP Development:**
   - Desktop application (Phase 1 focus)
   - Mathematics + Physics coverage
   - Beta testing with 10-20 students

---

**Document Maintainer:** CTO / Technical Lead
**Last Updated:** November 2025
**Review Cycle:** Monthly during development, quarterly post-launch

---

*This is a living document. As technology evolves and requirements change, this architecture will be updated to reflect the current system design.*
