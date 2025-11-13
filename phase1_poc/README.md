# Phase 1 POC: Local-First AI Teacher with CozoDB + LFM2

This is the Phase 1 Proof of Concept implementation for the AI Teacher platform, demonstrating the local-first architecture using:

- **CozoDB** - Embedded unified relational-graph-vector database
- **LFM2** - Liquid Foundation Model 2 (7B parameters) via llama.cpp
- **Sentence Transformers** - Multilingual embeddings for Indonesian text

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      User Question                       │
│                 "Jelaskan hukum Newton"                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Sentence Transformer                        │
│         paraphrase-multilingual-mpnet                    │
│              (768-dim embedding)                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   CozoDB Embedded                        │
│  ┌────────────────────────────────────────────────┐    │
│  │ HNSW Vector Search (embedding_ann_idx)         │    │
│  │ Returns top-K most similar chunks              │    │
│  └────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────┐    │
│  │ Relational Data (chapter metadata)             │    │
│  │ subject, grade, title, content                 │    │
│  └────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   RAG Prompt Builder                     │
│  System: "Anda adalah AI Teacher..."                    │
│  Context: [Retrieved chunks with metadata]              │
│  User: [Original question]                              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              LFM2 via llama.cpp                          │
│         (7B model, Q8 quantization)                      │
│            Local CPU inference                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                 Answer in Indonesian                     │
│        "Hukum Newton kedua menyatakan..."                │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
phase1_poc/
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── .env.example               # Configuration template
├── .env                       # Your configuration (create from .env.example)
│
├── scripts/
│   ├── 1_init_schema.py       # Initialize CozoDB schema
│   ├── 2_import_textbooks.py  # Import PDFs and generate embeddings
│   └── 3_test_qa.py           # Test Q&A with interactive mode
│
├── data/
│   ├── textbooks/             # Place PDF files here
│   └── ai_teacher.db          # CozoDB database (created by scripts)
│
└── models/
    └── lfm2-7b-q8_0.gguf      # LFM2 model (download separately)
```

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 24.04 LTS recommended)
  - CozoDB does not have FreeBSD port yet
  - Development on Linux, production on FreeBSD when available
- **Python**: 3.10 or higher
- **RAM**: Minimum 8GB (16GB recommended)
- **Storage**: ~15GB free space
  - LFM2 model: ~7.5GB (Q8 quantization)
  - Dependencies: ~2GB
  - Database + embeddings: ~1GB per 10 textbooks

### Software Dependencies

1. **Python 3.10+**
   ```bash
   python3 --version
   ```

2. **pip and venv**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv
   ```

3. **llama.cpp** (for running LFM2)
   ```bash
   # Clone llama.cpp
   git clone https://github.com/ggerganov/llama.cpp
   cd llama.cpp

   # Build (CPU-only)
   make

   # Or with CUDA support (if you have NVIDIA GPU)
   make LLAMA_CUDA=1
   ```

## Setup Instructions

### Step 1: Clone and Setup Python Environment

```bash
# Navigate to phase1_poc directory
cd AI_Teacher/phase1_poc

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

**Note**: First-time installation may take 5-10 minutes as it downloads:
- Sentence transformers models (~500MB)
- PyTorch dependencies (~2GB)

### Step 2: Download LFM2 Model

You have two options:

#### Option A: Use LFM2 7B Q8 (Recommended for POC)

```bash
# Create models directory
mkdir -p models

# Download from HuggingFace (requires git-lfs)
# Note: Replace with actual LFM2 GGUF model URL when available
# For now, you can use llama-2-7b-chat as a placeholder:

cd models
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q8_0.gguf
mv llama-2-7b-chat.Q8_0.gguf lfm2-7b-q8_0.gguf
cd ..
```

**Note**: When LFM2 GGUF models become publicly available, replace the above URL.

#### Option B: Use Smaller Model for Testing (if RAM limited)

```bash
# Download 3B model with Q4 quantization (~2GB)
cd models
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf
mv llama-2-7b-chat.Q4_K_M.gguf lfm2-7b-q4_0.gguf
cd ..
```

### Step 3: Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration (if needed)
nano .env
```

**Default configuration** (should work out of the box):
```bash
COZODB_ENGINE=sqlite
COZODB_PATH=./data/ai_teacher.db
MODEL_PATH=./models/lfm2-7b-q8_0.gguf
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
EMBEDDING_DIMENSION=768
```

### Step 4: Initialize CozoDB Schema

```bash
# Make scripts executable
chmod +x scripts/*.py

# Initialize database schema
python scripts/1_init_schema.py
```

**Expected output**:
```
Initializing CozoDB with engine: sqlite
Database path: ./data/ai_teacher.db

1. Creating 'chapter' relation (relational data)...
   ✓ Created 'chapter' relation
2. Creating 'embedding' relation (vector data)...
   ✓ Created 'embedding' relation
...
✓ Schema initialization complete!
```

### Step 5: Prepare Sample Textbooks

Place PDF textbooks in `data/textbooks/` directory with naming convention:

**Format**: `{subject}_{grade}_chapter{number}.pdf`

**Examples**:
```bash
data/textbooks/
├── matematika_7_chapter1.pdf
├── matematika_7_chapter2.pdf
├── fisika_8_chapter1.pdf
└── kimia_9_chapter1.pdf
```

**Supported subjects**:
- `matematika` - Mathematics
- `fisika` - Physics
- `kimia` - Chemistry
- `biologi` - Biology

**Sample textbooks for testing**:
You can use any Indonesian SMP textbook PDFs. Some sources:
- [Buku Kemdikbud](https://buku.kemdikbud.go.id/)
- Download 2-3 sample chapters to test

### Step 6: Import Textbooks

```bash
# Import all PDFs in data/textbooks/
python scripts/2_import_textbooks.py
```

**Expected output**:
```
Phase 1 POC - Textbook Import
Found 4 PDF file(s) to import
  - matematika_7_chapter1.pdf
  - fisika_8_chapter1.pdf
  ...

Loading embedding model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
✓ Model loaded. Embedding dimension: 768

Processing: matematika_7_chapter1.pdf
   Subject: matematika
   Grade: 7
   Chapter: 1
   Extracted 15234 characters
   Created 25 chunks
   Generating embeddings for 25 chunks...
   ✓ Successfully imported matematika_7_chapter1.pdf

...

✓ Successfully imported: 4 file(s)
Database Statistics:
  - Total chapters: 4
  - Total embeddings: 102
```

### Step 7: Start llama.cpp Server

Open a **new terminal** and start the llama.cpp server:

```bash
# Navigate to llama.cpp directory
cd /path/to/llama.cpp

# Start server (CPU-only, no GPU)
./llama-server \
  -m /path/to/AI_Teacher/phase1_poc/models/lfm2-7b-q8_0.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  -c 4096 \
  -ngl 0 \
  --threads 4

# Or with GPU acceleration (if available)
./llama-server \
  -m /path/to/AI_Teacher/phase1_poc/models/lfm2-7b-q8_0.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  -c 4096 \
  -ngl 35 \
  --threads 4
```

**Server startup log** should show:
```
llama server listening at http://127.0.0.1:8080
```

**Keep this terminal running** - the server must stay active for Q&A testing.

### Step 8: Test Q&A

Return to your **original terminal** (with Python venv activated):

```bash
# Make sure venv is activated
source venv/bin/activate

# Interactive Q&A mode
python scripts/3_test_qa.py
```

**Interactive mode**:
```
Phase 1 POC - Q&A Testing
Checking llama.cpp server at http://127.0.0.1:8080...
✓ llama.cpp server is running
✓ Database connected (102 embeddings)
✓ Model loaded

Interactive Q&A Mode
Type your questions in Indonesian. Type 'exit' to stop.

Pertanyaan: Jelaskan hukum Newton kedua

======================================================================
Pertanyaan: Jelaskan hukum Newton kedua
======================================================================

[1/4] Generating query embedding...
      ✓ Embedding generated (0.15s)

[2/4] Searching for relevant context (top-3)...
      ✓ Found 3 relevant chunks (0.08s)

      Retrieved context:
      [1] Fisika - Chapter 1 (Kelas 8) - Distance: 0.2341
          Preview: Hukum Newton kedua menyatakan bahwa...
      [2] Fisika - Chapter 2 (Kelas 8) - Distance: 0.3512
          Preview: Dalam fisika, gaya adalah...
      [3] Matematika - Chapter 3 (Kelas 7) - Distance: 0.4521
          Preview: Persamaan linear dapat digunakan...

[3/4] Building RAG prompt...
      ✓ Prompt built (2341 chars)

[4/4] Generating answer from LFM2...
      (This may take 10-30 seconds depending on your CPU...)
      ✓ Answer generated (18.45s)

======================================================================
Jawaban:
======================================================================
Hukum Newton kedua menyatakan bahwa percepatan suatu benda berbanding
lurus dengan gaya yang bekerja padanya dan berbanding terbalik dengan
massa benda tersebut. Secara matematis dapat ditulis: F = m × a

Contoh: Jika kamu mendorong meja dengan gaya lebih besar, meja akan
bergerak lebih cepat (percepatan lebih besar). Tetapi jika mejanya
lebih berat (massa lebih besar), untuk percepatan yang sama kamu perlu
gaya yang lebih besar.
======================================================================

Pertanyaan: exit
Terima kasih! Sampai jumpa.
```

**Or test with a single question**:
```bash
python scripts/3_test_qa.py "Apa itu fotosintesis?"
```

## Performance Expectations

### Desktop (4-core CPU, 16GB RAM)

- **Query embedding**: ~0.15s
- **Vector search**: ~0.08s
- **LLM inference**: 15-25s (Q8), 10-15s (Q4)
- **Total latency**: ~20-30s per question

### Laptop (2-core CPU, 8GB RAM)

- **Query embedding**: ~0.3s
- **Vector search**: ~0.1s
- **LLM inference**: 30-45s (Q4 recommended)
- **Total latency**: ~35-50s per question

### Storage

- **Database**: ~10MB per chapter (~100 chunks)
- **Models**: 7.5GB (Q8) or 4GB (Q4)
- **Embeddings model cache**: ~500MB

## Troubleshooting

### Issue: "Database not found"

**Solution**:
```bash
python scripts/1_init_schema.py
```

### Issue: "llama.cpp server is not running"

**Solution**:
```bash
# Check if server is running
curl http://127.0.0.1:8080/health

# If not, start server in separate terminal
cd /path/to/llama.cpp
./llama-server -m /path/to/models/lfm2-7b-q8_0.gguf --host 127.0.0.1 --port 8080
```

### Issue: "No PDF files found"

**Solution**:
```bash
# Check if textbooks directory exists
ls data/textbooks/

# Add PDF files with correct naming:
# subject_grade_chapterN.pdf
```

### Issue: "ModuleNotFoundError: No module named 'pycozo'"

**Solution**:
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Out of memory" during inference

**Solution**:
1. Use smaller quantization (Q4 instead of Q8)
2. Reduce context size in llama-server: `-c 2048`
3. Reduce number of threads: `--threads 2`

### Issue: Slow embedding generation

**Solution**:
```bash
# Install with GPU support (if available)
pip install sentence-transformers[gpu]
```

## Next Steps: Phase 2 GUI

After validating Phase 1 POC, the next phase will:

1. **PyQt6 GUI Application**
   - Chat interface with message history
   - Subject/grade filter
   - Dark mode for students
   - Progress indicators during LLM inference

2. **Background Processing**
   - Run LLM inference in separate thread
   - Non-blocking UI during answer generation
   - Cancel button for long-running queries

3. **Packaging**
   - PyInstaller for desktop distribution
   - Bundle CozoDB + LFM2 + embeddings
   - Single executable for Windows/Linux/macOS

4. **Android App**
   - Kotlin + Jetpack Compose
   - CozoDB Android library (cozo-lib-android)
   - LFM2 via LEAP SDK (2x faster than llama.cpp)

## Technical Notes

### Why CozoDB?

CozoDB provides **unified** relational-graph-vector database:
- **Vector search**: HNSW index for embeddings
- **Relational**: Chapter metadata, subjects, grades
- **Graph**: Prerequisites between concepts (future)
- **Embedded**: No server required, ~200MB SQLite file
- **Cross-platform**: Android, iOS, Desktop ready

**Alternative would require**:
- DuckDB (vector) + Neo4j (graph) + SQLite (relational)
- Multiple databases, complex sync, larger footprint

### Why Local-First?

1. **Zero latency**: No network requests, <3s response time
2. **Privacy**: Student data never leaves device
3. **Offline**: Works without internet connection
4. **Cost**: No cloud API fees ($0 vs $6,840/year Grok API)
5. **Ownership**: Students own their learning data

### Sync Strategy (Future)

When Cassandra 5.0 becomes available on FreeBSD:
- **Content distribution**: Admin publishes new chapters
- **Background sync**: Students pull updates (6-24hr frequency)
- **Conflict-free**: Content is read-only, no merge conflicts
- **Bandwidth-efficient**: Only download diffs

## License

This POC is part of the AI Teacher project. See main repository for license information.

## Support

For issues or questions about Phase 1 POC:
1. Check troubleshooting section above
2. Review logs from scripts
3. Verify llama.cpp server is running
4. Ensure PDF files are in correct format

## References

- [CozoDB Documentation](https://docs.cozodb.org/)
- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- [Sentence Transformers](https://www.sbert.net/)
- [PyCozo Python Client](https://github.com/cozodb/pycozo)
