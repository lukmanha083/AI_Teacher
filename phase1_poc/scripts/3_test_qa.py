#!/usr/bin/env python3
"""
Phase 1 POC - Script 3: Test Q&A with Hybrid Search
====================================================

This script tests the complete Q&A pipeline:
1. User asks a question in Indonesian
2. Generate embedding for the question
3. Perform vector similarity search in CozoDB
4. Retrieve top-k relevant chunks
5. Send chunks + question to LFM2 via llama.cpp
6. Display the answer

Usage:
    python scripts/3_test_qa.py

    Or with a specific question:
    python scripts/3_test_qa.py "Jelaskan hukum Newton kedua"

Requirements:
    - llama.cpp server must be running with LFM2 model
    - Start server: ./llama-server -m models/lfm2-7b-q8_0.gguf --host 127.0.0.1 --port 8080
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

from pycozo import Client
from sentence_transformers import SentenceTransformer
import requests
import json

# Load environment variables
load_dotenv()

# Configuration
COZODB_ENGINE = os.getenv('COZODB_ENGINE', 'sqlite')
COZODB_PATH = os.getenv('COZODB_PATH', './data/ai_teacher.db')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
MODEL_PATH = os.getenv('MODEL_PATH', './models/lfm2-7b-q8_0.gguf')

# llama.cpp server configuration
LLAMA_SERVER_URL = os.getenv('LLAMA_SERVER_URL', 'http://127.0.0.1:8080')
LLAMA_API_KEY = os.getenv('LLAMA_API_KEY', None)

# Search parameters
TOP_K = 3  # Number of chunks to retrieve


class LlamaServerClient:
    """Client for llama.cpp server (OpenAI-compatible API)."""

    def __init__(self, base_url: str = LLAMA_SERVER_URL, api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def health_check(self) -> bool:
        """Check if llama.cpp server is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Send chat completion request to llama.cpp server."""

        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            raise Exception(f"LLM API error: {response.status_code} - {response.text}")

        result = response.json()
        return result['choices'][0]['message']['content']


def vector_search(db: Client, query_embedding: List[float], k: int = TOP_K) -> List[Dict]:
    """
    Perform vector similarity search using HNSW index.

    Returns list of relevant chunks with metadata.
    """
    result = db.run("""
        ?[chapter_id, chunk_text, chunk_index, distance] :=
            ~embedding_ann_idx{
                query: $query_vector,
                k: $k | embedding_id, distance
            },
            *embedding{
                embedding_id,
                chapter_id,
                chunk_text,
                chunk_index
            }

        :order distance
    """, {
        'query_vector': query_embedding,
        'k': k
    })

    chunks = []
    for row in result['rows']:
        chapter_id, chunk_text, chunk_index, distance = row

        # Get chapter metadata
        chapter_result = db.run("""
            ?[subject, grade, chapter_number, title] :=
                *chapter{chapter_id, subject, grade, chapter_number, title},
                chapter_id = $chapter_id
        """, {'chapter_id': chapter_id})

        if len(chapter_result['rows']) > 0:
            subject, grade, chapter_number, title = chapter_result['rows'][0]

            chunks.append({
                'chapter_id': chapter_id,
                'subject': subject,
                'grade': grade,
                'chapter_number': chapter_number,
                'title': title,
                'chunk_text': chunk_text,
                'chunk_index': chunk_index,
                'distance': float(distance)
            })

    return chunks


def build_prompt(question: str, context_chunks: List[Dict]) -> str:
    """
    Build RAG prompt with retrieved context.

    Format:
    - System instruction
    - Context from retrieved chunks
    - User question
    """

    # Build context from chunks
    context = ""
    for i, chunk in enumerate(context_chunks, 1):
        context += f"\n--- Sumber {i}: {chunk['title']} (Kelas {chunk['grade']}) ---\n"
        context += chunk['chunk_text']
        context += "\n"

    # System instruction in Indonesian
    system_instruction = """Anda adalah AI Teacher yang membantu siswa SMP memahami materi STEM (Matematika, Fisika, Kimia, Biologi).

Tugas Anda:
1. Jawab pertanyaan siswa berdasarkan konteks yang diberikan
2. Jelaskan dengan bahasa yang mudah dipahami siswa SMP
3. Jika perlu, berikan contoh sederhana
4. Jika informasi tidak cukup dalam konteks, katakan dengan jujur

Konteks dari buku pelajaran:
{context}

Sekarang jawab pertanyaan siswa dengan jelas dan akurat."""

    prompt = system_instruction.format(context=context)
    return prompt


def answer_question(question: str, db: Client, embedding_model: SentenceTransformer, llm_client: LlamaServerClient):
    """
    Complete Q&A pipeline:
    1. Generate query embedding
    2. Vector search for relevant chunks
    3. Build RAG prompt
    4. Get answer from LLM
    """

    print("\n" + "="*70)
    print(f"Pertanyaan: {question}")
    print("="*70)

    # Step 1: Generate query embedding
    print("\n[1/4] Generating query embedding...")
    start_time = time.time()
    query_embedding = embedding_model.encode(question, convert_to_numpy=True).tolist()
    elapsed = time.time() - start_time
    print(f"      ✓ Embedding generated ({elapsed:.2f}s)")

    # Step 2: Vector search
    print(f"\n[2/4] Searching for relevant context (top-{TOP_K})...")
    start_time = time.time()
    relevant_chunks = vector_search(db, query_embedding, k=TOP_K)
    elapsed = time.time() - start_time
    print(f"      ✓ Found {len(relevant_chunks)} relevant chunks ({elapsed:.2f}s)")

    if len(relevant_chunks) == 0:
        print("\n✗ No relevant context found in database")
        return

    # Display retrieved chunks
    print("\n      Retrieved context:")
    for i, chunk in enumerate(relevant_chunks, 1):
        print(f"      [{i}] {chunk['title']} (Kelas {chunk['grade']}) - Distance: {chunk['distance']:.4f}")
        print(f"          Preview: {chunk['chunk_text'][:100]}...")

    # Step 3: Build prompt
    print("\n[3/4] Building RAG prompt...")
    prompt = build_prompt(question, relevant_chunks)
    print(f"      ✓ Prompt built ({len(prompt)} chars)")

    # Step 4: Get answer from LLM
    print("\n[4/4] Generating answer from LFM2...")
    print("      (This may take 10-30 seconds depending on your CPU...)")
    start_time = time.time()

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": question}
    ]

    try:
        answer = llm_client.chat_completion(messages, max_tokens=512, temperature=0.7)
        elapsed = time.time() - start_time
        print(f"      ✓ Answer generated ({elapsed:.2f}s)")

        # Display answer
        print("\n" + "="*70)
        print("Jawaban:")
        print("="*70)
        print(answer)
        print("="*70)

    except Exception as e:
        print(f"\n✗ Error generating answer: {e}")


def interactive_mode(db: Client, embedding_model: SentenceTransformer, llm_client: LlamaServerClient):
    """Interactive Q&A mode."""

    print("\n" + "="*70)
    print("Interactive Q&A Mode")
    print("="*70)
    print("Type your questions in Indonesian. Type 'exit' or 'quit' to stop.")
    print("="*70)

    while True:
        try:
            question = input("\nPertanyaan: ").strip()

            if question.lower() in ['exit', 'quit', 'keluar']:
                print("\nTerima kasih! Sampai jumpa.")
                break

            if not question:
                print("⚠ Please enter a question")
                continue

            answer_question(question, db, embedding_model, llm_client)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"\n✗ Error: {e}")


def main():
    """Main Q&A test process."""

    print("="*70)
    print("Phase 1 POC - Q&A Testing")
    print("="*70)

    # Check if database exists
    if not Path(COZODB_PATH).exists():
        print(f"\n✗ Error: Database not found at {COZODB_PATH}")
        print("Please run 'python scripts/1_init_schema.py' first")
        sys.exit(1)

    # Check if llama.cpp server is running
    print(f"\nChecking llama.cpp server at {LLAMA_SERVER_URL}...")
    llm_client = LlamaServerClient(LLAMA_SERVER_URL, LLAMA_API_KEY)

    if not llm_client.health_check():
        print(f"\n✗ Error: llama.cpp server is not running")
        print(f"\nPlease start the server first:")
        print(f"  ./llama-server -m {MODEL_PATH} --host 127.0.0.1 --port 8080")
        print(f"\nOr if using a different model path, update .env file")
        sys.exit(1)

    print(f"✓ llama.cpp server is running")

    # Initialize CozoDB
    print(f"\nConnecting to CozoDB at {COZODB_PATH}...")
    db = Client(engine=COZODB_ENGINE, path=COZODB_PATH)

    # Check if database has data
    result = db.run("?[count(embedding_id)] := *embedding{embedding_id}")
    total_embeddings = result['rows'][0][0]

    if total_embeddings == 0:
        print(f"\n✗ Error: Database is empty (no embeddings found)")
        print("Please run 'python scripts/2_import_textbooks.py' first")
        sys.exit(1)

    print(f"✓ Database connected ({total_embeddings} embeddings)")

    # Load embedding model
    print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
    print("(This may take a few minutes on first run...)")
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"✓ Model loaded")

    # Check if question provided as argument
    if len(sys.argv) > 1:
        question = ' '.join(sys.argv[1:])
        answer_question(question, db, embedding_model, llm_client)
    else:
        # Interactive mode
        interactive_mode(db, embedding_model, llm_client)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
