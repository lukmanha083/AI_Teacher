#!/usr/bin/env python3
"""
Phase 1 POC - Script 2: Import Textbooks and Generate Embeddings
=================================================================

This script imports PDF textbooks into CozoDB:
1. Extracts text from PDF files
2. Chunks text into manageable pieces (~500 tokens)
3. Generates embeddings using sentence-transformers
4. Stores chunks and embeddings in CozoDB

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
from typing import List, Tuple
from dotenv import load_dotenv

from pycozo import Client
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import numpy as np

# Load environment variables
load_dotenv()

# Configuration
COZODB_ENGINE = os.getenv('COZODB_ENGINE', 'sqlite')
COZODB_PATH = os.getenv('COZODB_PATH', './data/ai_teacher.db')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
EMBEDDING_DIM = int(os.getenv('EMBEDDING_DIMENSION', '768'))
TEXTBOOKS_DIR = './data/textbooks'

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


def import_textbook(pdf_path: str, db: Client, embedding_model: SentenceTransformer):
    """Import a single textbook PDF into CozoDB."""

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

    # Import each textbook
    print("\nStarting import process...")
    print("="*60)

    success_count = 0
    error_count = 0

    for pdf_path in pdf_files:
        try:
            import_textbook(str(pdf_path), db, embedding_model)
            success_count += 1
        except Exception as e:
            print(f"\n✗ Error importing {pdf_path.name}: {e}")
            error_count += 1

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

    if success_count > 0:
        print("\nNext step: Run 'python scripts/3_test_qa.py' to test Q&A")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nImport interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
