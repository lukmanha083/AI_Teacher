#!/usr/bin/env python3
"""
Phase 1 POC - Script 1: Initialize CozoDB Schema
================================================

This script initializes the CozoDB database with the schema needed for
the AI Teacher POC, including:
- Chapters table (relational data)
- Embeddings table (vector data)
- Concepts table (graph nodes)
- Prerequisites relation (graph edges)
- Entity tables (TypeAgent structured RAG)
- Inverted index (chunk_entity for fast entity lookup)
- HNSW vector index for similarity search

Usage:
    python scripts/1_init_schema.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pycozo import Client

# Load environment variables
load_dotenv()

# Configuration
COZODB_ENGINE = os.getenv('COZODB_ENGINE', 'sqlite')
COZODB_PATH = os.getenv('COZODB_PATH', './data/ai_teacher.db')
EMBEDDING_DIM = int(os.getenv('EMBEDDING_DIMENSION', '768'))
HNSW_M = int(os.getenv('HNSW_M', '16'))
HNSW_EF_CONSTRUCTION = int(os.getenv('HNSW_EF_CONSTRUCTION', '200'))
HNSW_DISTANCE = os.getenv('HNSW_DISTANCE', 'Cosine')


def init_cozodb_schema():
    """Initialize CozoDB schema with relations and indexes."""

    print(f"Initializing CozoDB with engine: {COZODB_ENGINE}")
    print(f"Database path: {COZODB_PATH}")

    # Ensure data directory exists
    Path(COZODB_PATH).parent.mkdir(parents=True, exist_ok=True)

    # Create CozoDB client
    db = Client(engine=COZODB_ENGINE, path=COZODB_PATH)

    print("\n1. Creating 'chapter' relation (relational data)...")
    result = db.run("""
        :create chapter {
            chapter_id: Uuid =>
            subject: String,
            grade: Int,
            chapter_number: Int,
            title: String,
            content: String,
            created_at: String
        }
    """)
    print(f"   ✓ Created 'chapter' relation: {result}")

    print("\n2. Creating 'embedding' relation (vector data)...")
    result = db.run(f"""
        :create embedding {{
            embedding_id: Uuid =>
            chapter_id: Uuid,
            chunk_text: String,
            chunk_index: Int,
            embedding: <F32; {EMBEDDING_DIM}>
        }}
    """)
    print(f"   ✓ Created 'embedding' relation: {result}")

    print("\n3. Creating 'concept' relation (graph nodes)...")
    result = db.run("""
        :create concept {
            concept_id: Uuid =>
            name: String,
            definition: String,
            subject: String,
            grade: Int
        }
    """)
    print(f"   ✓ Created 'concept' relation: {result}")

    print("\n4. Creating 'prerequisite' relation (graph edges)...")
    result = db.run("""
        :create prerequisite {
            from_concept: Uuid,
            to_concept: Uuid =>
            strength: Float
        }
    """)
    print(f"   ✓ Created 'prerequisite' relation: {result}")

    print("\n5. Creating 'chapter_concept' relation (links chapters to concepts)...")
    result = db.run("""
        :create chapter_concept {
            chapter_id: Uuid,
            concept_id: Uuid =>
        }
    """)
    print(f"   ✓ Created 'chapter_concept' relation: {result}")

    print("\n6. Creating 'entity' relation (TypeAgent structured RAG)...")
    result = db.run("""
        :create entity {
            entity_id: Uuid =>
            entity_text: String,
            entity_type: String,
            subject: String,
            normalized_form: String,
            frequency: Int
        }
    """)
    print(f"   ✓ Created 'entity' relation: {result}")

    print("\n7. Creating 'chunk_entity' relation (inverted index for entities)...")
    result = db.run("""
        :create chunk_entity {
            chunk_id: Uuid,
            entity_id: Uuid =>
            relevance_score: Float
        }
    """)
    print(f"   ✓ Created 'chunk_entity' relation: {result}")

    print("\n8. Creating 'entity_cooccurrence' relation (entity graph)...")
    result = db.run("""
        :create entity_cooccurrence {
            entity1_id: Uuid,
            entity2_id: Uuid =>
            cooccurrence_count: Int,
            pmi_score: Float
        }
    """)
    print(f"   ✓ Created 'entity_cooccurrence' relation: {result}")

    print("\n9. Creating HNSW index for vector similarity search...")
    result = db.run(f"""
        ::hnsw create embedding_ann_idx {{
            fields: [embedding],
            dim: {EMBEDDING_DIM},
            m: {HNSW_M},
            ef_construction: {HNSW_EF_CONSTRUCTION},
            distance: {HNSW_DISTANCE},
            extend_candidates: true,
            keep_pruned_connections: true
        }}
    """)
    print(f"   ✓ Created HNSW index 'embedding_ann_idx': {result}")

    print("\n10. Verifying schema...")
    result = db.run("::relations")
    relations = [row[0] for row in result['rows']]

    expected_relations = ['chapter', 'embedding', 'concept', 'prerequisite',
                         'chapter_concept', 'entity', 'chunk_entity', 'entity_cooccurrence']
    for rel in expected_relations:
        if rel in relations:
            print(f"   ✓ Relation '{rel}' exists")
        else:
            print(f"   ✗ Relation '{rel}' NOT FOUND")
            sys.exit(1)

    # Check for HNSW index
    result = db.run("::indices")
    indices = [row[0] for row in result['rows']]
    if 'embedding_ann_idx' in indices:
        print(f"   ✓ Index 'embedding_ann_idx' exists")
    else:
        print(f"   ✗ Index 'embedding_ann_idx' NOT FOUND")
        sys.exit(1)

    print("\n" + "="*60)
    print("✓ Schema initialization complete!")
    print("="*60)
    print("\nDatabase ready for Phase 1 POC testing.")
    print(f"Location: {COZODB_PATH}")
    print(f"Engine: {COZODB_ENGINE}")
    print("\nNext step: Run 'python scripts/2_import_textbooks.py'")


if __name__ == "__main__":
    try:
        init_cozodb_schema()
    except Exception as e:
        print(f"\n✗ Error during schema initialization: {e}", file=sys.stderr)
        sys.exit(1)
