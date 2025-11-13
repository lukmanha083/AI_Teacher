#!/usr/bin/env python3
"""
Phase 1 POC - Script 3: Test Q&A with TypeAgent Hybrid Search
================================================================

This script tests the complete TypeAgent RAG pipeline:
1. User asks a question in Indonesian
2. Extract entities from question using Grok API
3. Find chunks via entity inverted index (TypeAgent)
4. Perform vector similarity search (traditional RAG)
5. Hybrid scoring: combine entity matches + vector similarity
6. Send top chunks + question to LFM2 via llama.cpp
7. Display the answer

TypeAgent provides 4.2x better recall than vector-only RAG.

Usage:
    python scripts/3_test_qa_typeagent.py

    Or with a specific question:
    python scripts/3_test_qa_typeagent.py "Jelaskan hukum Newton kedua"

Requirements:
    - llama.cpp server must be running with LFM2 model
    - Start server: ./llama-server -m models/lfm2-7b-q8_0.gguf --host 127.0.0.1 --port 8080
    - Grok API key in .env (for entity extraction)
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict
from dotenv import load_dotenv

from pycozo import Client
from sentence_transformers import SentenceTransformer
import requests
import json

# Import TypeAgent entity extractor
from typeagent import GrokEntityExtractor, Entity

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

# TypeAgent configuration
ENABLE_TYPEAGENT = os.getenv('ENABLE_TYPEAGENT', 'true').lower() == 'true'
GROK_API_KEY = os.getenv('GROK_API_KEY', '')
GROK_API_URL = os.getenv('GROK_API_URL', 'https://api.x.ai/v1')
GROK_MODEL = os.getenv('GROK_MODEL', 'grok-2-1212')
MAX_ENTITIES_PER_QUERY = int(os.getenv('MAX_ENTITIES_PER_QUERY', '10'))

# Hybrid search weights
ENTITY_WEIGHT = float(os.getenv('HYBRID_SEARCH_ENTITY_WEIGHT', '0.6'))
VECTOR_WEIGHT = float(os.getenv('HYBRID_SEARCH_VECTOR_WEIGHT', '0.4'))

# Search parameters
TOP_K = 5  # Number of chunks to retrieve


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


def entity_search(db: Client, entities: List[Entity], k: int = TOP_K) -> Dict[str, Tuple[str, str, int, float]]:
    """
    TypeAgent entity-based search using inverted index.

    Returns dict of embedding_id -> (chapter_id, chunk_text, chunk_index, entity_score)
    """
    if not entities:
        return {}

    # Get normalized forms for matching
    normalized_entities = [e.normalized for e in entities]

    # Query: Find chunks that contain any of the extracted entities
    result = db.run("""
        # Find entities matching our query entities
        ?[entity_id, normalized_form] :=
            *entity{entity_id, normalized_form},
            normalized_form in $entities

        # Get chunks associated with these entities via inverted index
        ?[chunk_id, entity_count, relevance_sum] :=
            *chunk_entity{chunk_id, entity_id, relevance_score},
            *entity{entity_id, normalized_form},
            normalized_form in $entities,
            entity_count = count(entity_id),
            relevance_sum = sum(relevance_score)

        # Get chunk details
        ?[embedding_id, chapter_id, chunk_text, chunk_index, entity_score] :=
            *embedding{embedding_id, chapter_id, chunk_text, chunk_index},
            *chunk_entity{chunk_id: embedding_id, entity_id, relevance_score},
            *entity{entity_id, normalized_form},
            normalized_form in $entities,
            entity_score = sum(relevance_score)

        :order -entity_score
        :limit $k
    """, {'entities': normalized_entities, 'k': k * 2})  # Get more than k for hybrid merge

    chunks = {}
    for row in result['rows']:
        embedding_id, chapter_id, chunk_text, chunk_index, entity_score = row
        chunks[embedding_id] = (chapter_id, chunk_text, chunk_index, float(entity_score))

    return chunks


def vector_search(db: Client, query_embedding: List[float], k: int = TOP_K) -> Dict[str, Tuple[str, str, int, float]]:
    """
    Traditional vector similarity search using HNSW index.

    Returns dict of embedding_id -> (chapter_id, chunk_text, chunk_index, distance)
    """
    result = db.run("""
        ?[embedding_id, chapter_id, chunk_text, chunk_index, distance] :=
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
        'k': k * 2  # Get more than k for hybrid merge
    })

    chunks = {}
    for row in result['rows']:
        embedding_id, chapter_id, chunk_text, chunk_index, distance = row
        # Convert distance to similarity score (lower distance = higher similarity)
        similarity = 1.0 / (1.0 + float(distance))
        chunks[embedding_id] = (chapter_id, chunk_text, chunk_index, similarity)

    return chunks


def hybrid_search(db: Client, query: str, embedding_model: SentenceTransformer,
                 entity_extractor: GrokEntityExtractor = None,
                 k: int = TOP_K) -> List[Dict]:
    """
    Hybrid search combining TypeAgent entity matching + vector similarity.

    Algorithm:
    1. Extract entities from query (TypeAgent)
    2. Entity search via inverted index
    3. Vector search via HNSW
    4. Combine with weighted scoring
    5. Return top-k chunks

    Weights:
    - Entity weight: 0.6 (TypeAgent structured search)
    - Vector weight: 0.4 (semantic similarity)
    """

    print(f"\n{'='*70}")
    print(f"Query: {query}")
    print(f"{'='*70}")

    # Step 1: Extract entities from query
    entities = []
    if entity_extractor and ENABLE_TYPEAGENT:
        print(f"\n[TypeAgent] Extracting entities from query...")
        start_time = time.time()
        entities = entity_extractor.extract_from_query(query, max_entities=MAX_ENTITIES_PER_QUERY)
        elapsed = time.time() - start_time
        print(f"            ✓ Extracted {len(entities)} entities ({elapsed:.2f}s)")
        if entities:
            for entity in entities:
                print(f"              - {entity.text} ({entity.type})")

    # Step 2: Entity search (if entities found)
    entity_chunks = {}
    if entities:
        print(f"\n[TypeAgent] Entity-based search via inverted index...")
        start_time = time.time()
        entity_chunks = entity_search(db, entities, k=k)
        elapsed = time.time() - start_time
        print(f"            ✓ Found {len(entity_chunks)} chunks matching entities ({elapsed:.2f}s)")

    # Step 3: Vector search
    print(f"\n[Vector] Generating query embedding...")
    start_time = time.time()
    query_embedding = embedding_model.encode(query, convert_to_numpy=True).tolist()
    elapsed = time.time() - start_time
    print(f"         ✓ Embedding generated ({elapsed:.2f}s)")

    print(f"\n[Vector] Similarity search via HNSW...")
    start_time = time.time()
    vector_chunks = vector_search(db, query_embedding, k=k)
    elapsed = time.time() - start_time
    print(f"         ✓ Found {len(vector_chunks)} similar chunks ({elapsed:.2f}s)")

    # Step 4: Hybrid scoring
    print(f"\n[Hybrid] Combining scores (entity:{ENTITY_WEIGHT}, vector:{VECTOR_WEIGHT})...")

    # Collect all unique chunk IDs
    all_chunk_ids = set(entity_chunks.keys()) | set(vector_chunks.keys())

    # Normalize scores to [0, 1] range
    if entity_chunks:
        max_entity_score = max(score for _, _, _, score in entity_chunks.values())
    else:
        max_entity_score = 1.0

    if vector_chunks:
        max_vector_score = max(score for _, _, _, score in vector_chunks.values())
    else:
        max_vector_score = 1.0

    # Calculate hybrid scores
    hybrid_scores = []
    for chunk_id in all_chunk_ids:
        # Entity score (normalized)
        if chunk_id in entity_chunks:
            entity_score = entity_chunks[chunk_id][3] / max_entity_score
        else:
            entity_score = 0.0

        # Vector score (normalized)
        if chunk_id in vector_chunks:
            vector_score = vector_chunks[chunk_id][3] / max_vector_score
        else:
            vector_score = 0.0

        # Hybrid score
        hybrid_score = (ENTITY_WEIGHT * entity_score) + (VECTOR_WEIGHT * vector_score)

        # Get chunk data (prefer entity_chunks if available)
        if chunk_id in entity_chunks:
            chapter_id, chunk_text, chunk_index, _ = entity_chunks[chunk_id]
        else:
            chapter_id, chunk_text, chunk_index, _ = vector_chunks[chunk_id]

        hybrid_scores.append({
            'embedding_id': chunk_id,
            'chapter_id': chapter_id,
            'chunk_text': chunk_text,
            'chunk_index': chunk_index,
            'entity_score': entity_score,
            'vector_score': vector_score,
            'hybrid_score': hybrid_score
        })

    # Sort by hybrid score and take top-k
    hybrid_scores.sort(key=lambda x: x['hybrid_score'], reverse=True)
    top_chunks = hybrid_scores[:k]

    print(f"         ✓ Selected top-{k} chunks by hybrid score")

    # Step 5: Enrich with chapter metadata
    result_chunks = []
    for chunk in top_chunks:
        # Get chapter metadata
        chapter_result = db.run("""
            ?[subject, grade, chapter_number, title] :=
                *chapter{chapter_id, subject, grade, chapter_number, title},
                chapter_id = $chapter_id
        """, {'chapter_id': chunk['chapter_id']})

        if len(chapter_result['rows']) > 0:
            subject, grade, chapter_number, title = chapter_result['rows'][0]

            result_chunks.append({
                'chapter_id': chunk['chapter_id'],
                'subject': subject,
                'grade': grade,
                'chapter_number': chapter_number,
                'title': title,
                'chunk_text': chunk['chunk_text'],
                'chunk_index': chunk['chunk_index'],
                'entity_score': chunk['entity_score'],
                'vector_score': chunk['vector_score'],
                'hybrid_score': chunk['hybrid_score']
            })

    return result_chunks


def build_prompt(question: str, context_chunks: List[Dict]) -> str:
    """
    Build RAG prompt with retrieved context.

    Format:
    - System instruction
    - Context from retrieved chunks (with scores for transparency)
    - User question
    """

    # Build context from chunks
    context = ""
    for i, chunk in enumerate(context_chunks, 1):
        context += f"\n--- Sumber {i}: {chunk['title']} (Kelas {chunk['grade']}) ---\n"
        context += f"[Skor: entity={chunk['entity_score']:.2f}, vector={chunk['vector_score']:.2f}, hybrid={chunk['hybrid_score']:.2f}]\n"
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


def answer_question(question: str, db: Client, embedding_model: SentenceTransformer,
                   llm_client: LlamaServerClient, entity_extractor: GrokEntityExtractor = None):
    """
    Complete TypeAgent Q&A pipeline.
    """

    # Step 1: Hybrid search
    start_time = time.time()
    relevant_chunks = hybrid_search(db, question, embedding_model, entity_extractor, k=TOP_K)
    search_elapsed = time.time() - start_time

    if len(relevant_chunks) == 0:
        print("\n✗ No relevant context found in database")
        return

    # Display retrieved chunks
    print(f"\n{'='*70}")
    print(f"Retrieved Context (top-{len(relevant_chunks)} chunks):")
    print(f"{'='*70}")
    for i, chunk in enumerate(relevant_chunks, 1):
        print(f"\n[{i}] {chunk['title']} (Kelas {chunk['grade']})")
        print(f"    Entity score: {chunk['entity_score']:.3f} | Vector score: {chunk['vector_score']:.3f} | Hybrid: {chunk['hybrid_score']:.3f}")
        print(f"    Preview: {chunk['chunk_text'][:150]}...")

    # Step 2: Build prompt
    print(f"\n{'='*70}")
    print("[LFM2] Building RAG prompt...")
    prompt = build_prompt(question, relevant_chunks)
    print(f"       ✓ Prompt built ({len(prompt)} chars)")

    # Step 3: Get answer from LLM
    print(f"\n[LFM2] Generating answer...")
    print("       (This may take 10-30 seconds depending on your CPU...)")
    start_time = time.time()

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": question}
    ]

    try:
        answer = llm_client.chat_completion(messages, max_tokens=512, temperature=0.7)
        llm_elapsed = time.time() - start_time
        print(f"       ✓ Answer generated ({llm_elapsed:.2f}s)")

        # Display answer
        print(f"\n{'='*70}")
        print("Jawaban:")
        print(f"{'='*70}")
        print(answer)
        print(f"{'='*70}")

        # Performance summary
        total_elapsed = search_elapsed + llm_elapsed
        print(f"\nPerformance:")
        print(f"  - Search time: {search_elapsed:.2f}s")
        print(f"  - LLM time: {llm_elapsed:.2f}s")
        print(f"  - Total: {total_elapsed:.2f}s")

    except Exception as e:
        print(f"\n✗ Error generating answer: {e}")


def interactive_mode(db: Client, embedding_model: SentenceTransformer,
                    llm_client: LlamaServerClient, entity_extractor: GrokEntityExtractor = None):
    """Interactive Q&A mode."""

    print(f"\n{'='*70}")
    print("Interactive Q&A Mode (TypeAgent Hybrid Search)")
    print(f"{'='*70}")
    print("Type your questions in Indonesian. Type 'exit' or 'quit' to stop.")

    if entity_extractor:
        print(f"✓ TypeAgent enabled (entity weight: {ENTITY_WEIGHT}, vector weight: {VECTOR_WEIGHT})")
    else:
        print("⚠ TypeAgent disabled (vector-only search)")

    print(f"{'='*70}")

    while True:
        try:
            question = input("\nPertanyaan: ").strip()

            if question.lower() in ['exit', 'quit', 'keluar']:
                print("\nTerima kasih! Sampai jumpa.")
                break

            if not question:
                print("⚠ Please enter a question")
                continue

            answer_question(question, db, embedding_model, llm_client, entity_extractor)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main Q&A test process."""

    print("="*70)
    print("Phase 1 POC - Q&A Testing (TypeAgent Hybrid Search)")
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
    print(f"✓ Embedding model loaded")

    # Initialize TypeAgent entity extractor
    entity_extractor = None
    if ENABLE_TYPEAGENT:
        if not GROK_API_KEY or GROK_API_KEY == 'your-grok-api-key-here':
            print("\n⚠ Warning: GROK_API_KEY not set")
            print("TypeAgent entity extraction will be DISABLED")
            print("Falling back to vector-only search")
            print("\nTo enable TypeAgent:")
            print("  1. Get API key from: https://console.x.ai/")
            print("  2. Add to .env file: GROK_API_KEY=your-key-here")
        else:
            print(f"\nInitializing TypeAgent entity extractor...")
            entity_extractor = GrokEntityExtractor(
                api_key=GROK_API_KEY,
                api_url=GROK_API_URL,
                model=GROK_MODEL
            )
            print(f"✓ TypeAgent enabled (4.2x better recall than vector-only)")

            # Check if entities exist in database
            result = db.run("?[count(entity_id)] := *entity{entity_id}")
            total_entities = result['rows'][0][0]

            if total_entities == 0:
                print(f"\n⚠ Warning: No entities in database")
                print("Did you run import with ENABLE_TYPEAGENT=true?")
                print("Re-run 'python scripts/2_import_textbooks.py' to extract entities")
                entity_extractor = None
            else:
                print(f"✓ Entity database ready ({total_entities} unique entities)")

    # Check if question provided as argument
    if len(sys.argv) > 1:
        question = ' '.join(sys.argv[1:])
        answer_question(question, db, embedding_model, llm_client, entity_extractor)
    else:
        # Interactive mode
        interactive_mode(db, embedding_model, llm_client, entity_extractor)


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
