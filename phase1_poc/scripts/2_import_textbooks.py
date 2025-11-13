#!/usr/bin/env python3
"""
Phase 1 POC - Script 2: Import Textbooks with TypeAgent Entity Extraction
==========================================================================

This script imports PDF textbooks into CozoDB with TypeAgent structured RAG:
1. Extracts text from PDF files
2. Chunks text into manageable pieces (~500 tokens)
3. Generates embeddings using sentence-transformers
4. Extracts entities using Grok API (TypeAgent approach)
5. Stores chunks, embeddings, and entities in CozoDB with inverted index

Usage:
    python scripts/2_import_textbooks.py

Place PDF files in ./data/textbooks/ with naming convention:
    {subject}_{grade}_chapter{number}.pdf

Examples:
    - matematika_7_chapter1.pdf
    - fisika_8_chapter2.pdf
    - kimia_9_chapter3.pdf
"""

import os
import sys
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from collections import defaultdict
from dotenv import load_dotenv

from pycozo import Client
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import numpy as np

# Import TypeAgent entity extractor
from typeagent import GrokEntityExtractor, Entity

# Load environment variables
load_dotenv()

# Configuration
COZODB_ENGINE = os.getenv('COZODB_ENGINE', 'sqlite')
COZODB_PATH = os.getenv('COZODB_PATH', './data/ai_teacher.db')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
EMBEDDING_DIM = int(os.getenv('EMBEDDING_DIMENSION', '768'))
TEXTBOOKS_DIR = './data/textbooks'

# TypeAgent configuration
ENABLE_TYPEAGENT = os.getenv('ENABLE_TYPEAGENT', 'true').lower() == 'true'
GROK_API_KEY = os.getenv('GROK_API_KEY', '')
GROK_API_URL = os.getenv('GROK_API_URL', 'https://api.x.ai/v1')
GROK_MODEL = os.getenv('GROK_MODEL', 'grok-2-1212')
ENTITY_EXTRACTION_TEMPERATURE = float(os.getenv('ENTITY_EXTRACTION_TEMPERATURE', '0.3'))

# Chunking parameters
CHUNK_SIZE = 500  # tokens (approximate)
CHUNK_OVERLAP = 50  # tokens overlap between chunks


def parse_filename(filename: str) -> Tuple[str, int, int]:
    """
    Parse filename to extract subject, grade, and chapter number.

    Expected format: {subject}_{grade}_chapter{number}.pdf
    Example: matematika_7_chapter1.pdf -> ('matematika', 7, 1)
    """
    try:
        name = filename.replace('.pdf', '')
        parts = name.split('_')

        subject = parts[0]
        grade = int(parts[1])

        # Extract chapter number from "chapter{N}"
        chapter_part = parts[2]
        chapter_number = int(chapter_part.replace('chapter', ''))

        return subject, grade, chapter_number
    except Exception as e:
        raise ValueError(f"Invalid filename format: {filename}. Expected format: subject_grade_chapterN.pdf") from e


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    print(f"   Extracting text from {pdf_path}...")
    reader = PdfReader(pdf_path)

    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    return text.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks.

    Note: This is a simple word-based chunking. For production, consider:
    - Sentence boundary detection
    - Semantic chunking
    - Token-aware chunking
    """
    words = text.split()
    chunks = []

    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        start = end - overlap

    return chunks


def generate_embeddings(texts: List[str], model: SentenceTransformer) -> np.ndarray:
    """Generate embeddings for a list of texts."""
    print(f"   Generating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    return embeddings


def import_textbook(pdf_path: str, db: Client, embedding_model: SentenceTransformer,
                   entity_extractor: Optional[GrokEntityExtractor] = None):
    """Import a single textbook PDF into CozoDB with optional entity extraction."""

    filename = Path(pdf_path).name
    print(f"\nProcessing: {filename}")
    print("="*60)

    # Parse filename
    subject, grade, chapter_number = parse_filename(filename)
    print(f"   Subject: {subject}")
    print(f"   Grade: {grade}")
    print(f"   Chapter: {chapter_number}")

    # Extract text
    text = extract_text_from_pdf(pdf_path)
    print(f"   Extracted {len(text)} characters")

    if len(text) < 100:
        print(f"   ⚠ Warning: Text too short, skipping this file")
        return

    # Chunk text
    chunks = chunk_text(text)
    print(f"   Created {len(chunks)} chunks")

    if len(chunks) == 0:
        print(f"   ⚠ Warning: No chunks created, skipping this file")
        return

    # Generate embeddings
    embeddings = generate_embeddings(chunks, embedding_model)
    print(f"   Generated embeddings with shape: {embeddings.shape}")

    # Create chapter record
    chapter_id = str(uuid.uuid4())
    title = f"{subject.capitalize()} - Chapter {chapter_number}"
    created_at = datetime.now().isoformat()

    print(f"   Inserting chapter record...")
    result = db.run("""
        ?[chapter_id, subject, grade, chapter_number, title, content, created_at] <- [
            [$chapter_id, $subject, $grade, $chapter_number, $title, $content, $created_at]
        ]
        :put chapter {
            chapter_id => subject, grade, chapter_number, title, content, created_at
        }
    """, {
        'chapter_id': chapter_id,
        'subject': subject,
        'grade': grade,
        'chapter_number': chapter_number,
        'title': title,
        'content': text[:1000],  # Store first 1000 chars as preview
        'created_at': created_at
    })
    print(f"   ✓ Chapter inserted: {chapter_id}")

    # Insert embeddings
    print(f"   Inserting {len(chunks)} embeddings...")
    embedding_rows = []

    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        embedding_id = str(uuid.uuid4())
        embedding_rows.append([
            embedding_id,
            chapter_id,
            chunk,
            idx,
            embedding.tolist()
        ])

    # Batch insert embeddings
    result = db.run("""
        ?[embedding_id, chapter_id, chunk_text, chunk_index, embedding] <- $rows
        :put embedding {
            embedding_id => chapter_id, chunk_text, chunk_index, embedding
        }
    """, {'rows': embedding_rows})

    print(f"   ✓ Inserted {len(embedding_rows)} embeddings")

    # Extract entities using TypeAgent (if enabled)
    if entity_extractor and ENABLE_TYPEAGENT:
        print(f"\n   Extracting entities using Grok API...")

        # Entity deduplication: entity_normalized -> (entity_id, entity_obj, chunks)
        entity_map: Dict[str, Tuple[str, Entity, List[str]]] = {}
        chunk_entities = []  # For chunk_entity relation

        for idx, (chunk, embedding_id) in enumerate(zip(chunks, [row[0] for row in embedding_rows])):
            # Extract entities from chunk
            entities = entity_extractor.extract_from_chunk(chunk, subject, grade)

            if entities:
                print(f"      Chunk {idx+1}/{len(chunks)}: extracted {len(entities)} entities")

                for entity in entities:
                    # Deduplicate by normalized form
                    if entity.normalized not in entity_map:
                        entity_id = str(uuid.uuid4())
                        entity_map[entity.normalized] = (entity_id, entity, [embedding_id])
                    else:
                        entity_id, _, chunk_ids = entity_map[entity.normalized]
                        chunk_ids.append(embedding_id)
                        entity_map[entity.normalized] = (entity_id, entity, chunk_ids)

                    # Add to chunk_entity inverted index
                    chunk_entities.append([
                        embedding_id,
                        entity_id,
                        1.0  # relevance score (can be refined later)
                    ])

        # Insert unique entities
        if entity_map:
            entity_rows = []
            for normalized, (entity_id, entity, chunk_ids) in entity_map.items():
                entity_rows.append([
                    entity_id,
                    entity.text,
                    entity.type,
                    subject,
                    normalized,
                    len(chunk_ids)  # frequency
                ])

            result = db.run("""
                ?[entity_id, entity_text, entity_type, subject, normalized_form, frequency] <- $rows
                :put entity {
                    entity_id => entity_text, entity_type, subject, normalized_form, frequency
                }
            """, {'rows': entity_rows})

            print(f"   ✓ Inserted {len(entity_rows)} unique entities")

            # Insert chunk_entity inverted index
            if chunk_entities:
                result = db.run("""
                    ?[chunk_id, entity_id, relevance_score] <- $rows
                    :put chunk_entity {
                        chunk_id, entity_id => relevance_score
                    }
                """, {'rows': chunk_entities})

                print(f"   ✓ Inserted {len(chunk_entities)} chunk-entity mappings")
        else:
            print(f"   ⚠ No entities extracted from this textbook")

    print(f"✓ Successfully imported {filename}")


def main():
    """Main import process."""

    print("="*60)
    print("Phase 1 POC - Textbook Import")
    print("="*60)

    # Check if database exists
    if not Path(COZODB_PATH).exists():
        print(f"\n✗ Error: Database not found at {COZODB_PATH}")
        print("Please run 'python scripts/1_init_schema.py' first")
        sys.exit(1)

    # Check textbooks directory
    if not Path(TEXTBOOKS_DIR).exists():
        print(f"\n✗ Error: Textbooks directory not found: {TEXTBOOKS_DIR}")
        print("Please create the directory and add PDF files")
        sys.exit(1)

    # Find PDF files
    pdf_files = list(Path(TEXTBOOKS_DIR).glob('*.pdf'))
    if len(pdf_files) == 0:
        print(f"\n✗ Error: No PDF files found in {TEXTBOOKS_DIR}")
        print("\nExpected filename format: subject_grade_chapterN.pdf")
        print("Examples:")
        print("  - matematika_7_chapter1.pdf")
        print("  - fisika_8_chapter2.pdf")
        print("  - kimia_9_chapter3.pdf")
        sys.exit(1)

    print(f"\nFound {len(pdf_files)} PDF file(s) to import")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")

    # Initialize CozoDB
    print(f"\nConnecting to CozoDB at {COZODB_PATH}...")
    db = Client(engine=COZODB_ENGINE, path=COZODB_PATH)

    # Load embedding model
    print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
    print("(This may take a few minutes on first run...)")
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"✓ Model loaded. Embedding dimension: {EMBEDDING_DIM}")

    # Initialize entity extractor (TypeAgent)
    entity_extractor = None
    if ENABLE_TYPEAGENT:
        if not GROK_API_KEY or GROK_API_KEY == 'your-grok-api-key-here':
            print("\n⚠ Warning: GROK_API_KEY not set, skipping entity extraction")
            print("To enable TypeAgent structured RAG:")
            print("  1. Get API key from: https://console.x.ai/")
            print("  2. Add to .env file: GROK_API_KEY=your-key-here")
            ENABLE_TYPEAGENT = False
        else:
            print(f"\nInitializing TypeAgent entity extractor...")
            print(f"  Model: {GROK_MODEL}")
            print(f"  Temperature: {ENTITY_EXTRACTION_TEMPERATURE}")
            entity_extractor = GrokEntityExtractor(
                api_key=GROK_API_KEY,
                api_url=GROK_API_URL,
                model=GROK_MODEL,
                temperature=ENTITY_EXTRACTION_TEMPERATURE
            )
            print(f"✓ Entity extractor ready (TypeAgent structured RAG enabled)")
    else:
        print("\n✓ TypeAgent disabled, using vector-only RAG")

    # Import each textbook
    print("\nStarting import process...")
    print("="*60)

    success_count = 0
    error_count = 0

    for pdf_path in pdf_files:
        try:
            import_textbook(str(pdf_path), db, embedding_model, entity_extractor)
            success_count += 1
        except Exception as e:
            print(f"\n✗ Error importing {pdf_path.name}: {e}")
            error_count += 1
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "="*60)
    print("Import Summary")
    print("="*60)
    print(f"✓ Successfully imported: {success_count} file(s)")
    if error_count > 0:
        print(f"✗ Failed to import: {error_count} file(s)")

    # Show database stats
    result = db.run("?[count(embedding_id)] := *embedding{embedding_id}")
    total_embeddings = result['rows'][0][0]

    result = db.run("?[count(chapter_id)] := *chapter{chapter_id}")
    total_chapters = result['rows'][0][0]

    print(f"\nDatabase Statistics:")
    print(f"  - Total chapters: {total_chapters}")
    print(f"  - Total embeddings: {total_embeddings}")

    if ENABLE_TYPEAGENT and entity_extractor:
        result = db.run("?[count(entity_id)] := *entity{entity_id}")
        total_entities = result['rows'][0][0]

        result = db.run("?[count(chunk_id)] := *chunk_entity{chunk_id, entity_id}")
        total_chunk_entities = result['rows'][0][0]

        print(f"  - Total entities (TypeAgent): {total_entities}")
        print(f"  - Total chunk-entity mappings: {total_chunk_entities}")

    if success_count > 0:
        print("\nNext step: Run 'python scripts/3_test_qa.py' to test Q&A")
        if ENABLE_TYPEAGENT and entity_extractor:
            print("(TypeAgent structured RAG is enabled for improved recall)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nImport interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
