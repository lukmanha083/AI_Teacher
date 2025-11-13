#!/usr/bin/env python3
"""
Phase 1 POC - Script 4: Analyze Student Answers with OCR
=========================================================

This script uses Grok Vision API to:
1. OCR handwritten student answers from images
2. Extract entities from the OCR'd text
3. Compare with expected entities from the question
4. Provide analysis and feedback

Use cases:
- Assessment: Check if student mentioned key concepts
- Query expansion: Use student's terminology for better search
- Feedback: Identify what student understood vs missed

Usage:
    python scripts/4_analyze_student_answer.py <image_path> [subject]

Examples:
    python scripts/4_analyze_student_answer.py student_answer.jpg fisika
    python scripts/4_analyze_student_answer.py homework.png matematika

Supported image formats:
- JPG/JPEG
- PNG
- WebP
- BMP

Requirements:
- Grok API key in .env (for Vision OCR)
- Image of student's handwritten or printed answer
"""

import os
import sys
from pathlib import Path
from typing import List, Set
from dotenv import load_dotenv

from pycozo import Client
from typeagent import GrokEntityExtractor, Entity

# Load environment variables
load_dotenv()

# Configuration
COZODB_ENGINE = os.getenv('COZODB_ENGINE', 'sqlite')
COZODB_PATH = os.getenv('COZODB_PATH', './data/ai_teacher.db')
GROK_API_KEY = os.getenv('GROK_API_KEY', '')
GROK_API_URL = os.getenv('GROK_API_URL', 'https://api.x.ai/v1')
GROK_MODEL = os.getenv('GROK_MODEL', 'grok-2-1212')


def find_related_entities(db: Client, student_entities: List[Entity], subject: str) -> List[Entity]:
    """
    Find entities in database that match student's answer.

    This helps us understand what the student got right.
    """
    if not student_entities:
        return []

    # Get normalized forms
    normalized_forms = [e.normalized for e in student_entities]

    # Query database for matching entities
    result = db.run("""
        ?[entity_id, entity_text, entity_type, frequency] :=
            *entity{entity_id, entity_text, entity_type, subject, normalized_form, frequency},
            subject = $subject,
            normalized_form in $entities

        :order -frequency
    """, {
        'subject': subject,
        'entities': normalized_forms
    })

    matched_entities = []
    for row in result['rows']:
        entity_id, entity_text, entity_type, frequency = row
        # Find corresponding student entity
        for student_entity in student_entities:
            if student_entity.normalized in [entity_text.lower(), entity_text]:
                matched_entities.append(Entity(
                    text=entity_text,
                    type=entity_type,
                    normalized=student_entity.normalized
                ))
                break

    return matched_entities


def analyze_answer(image_path: str, subject: str, db: Client, extractor: GrokEntityExtractor):
    """
    Analyze student answer from image.

    Process:
    1. OCR the image
    2. Extract entities from OCR'd text
    3. Compare with database entities
    4. Provide feedback
    """

    print("="*70)
    print("Student Answer Analysis")
    print("="*70)
    print(f"Image: {Path(image_path).name}")
    print(f"Subject: {subject}")
    print("="*70)

    # Step 1: OCR + Entity Extraction
    print("\n[Step 1] OCR and Entity Extraction")
    print("-"*70)

    ocr_text, student_entities = extractor.extract_from_image(image_path, subject)

    if not ocr_text:
        print("\n✗ Failed to extract text from image")
        print("Possible reasons:")
        print("  - Image is blurry or low quality")
        print("  - Handwriting is illegible")
        print("  - Image format not supported")
        print("  - Grok API error")
        return

    # Display OCR'd text
    print(f"\n📄 Extracted Text ({len(ocr_text)} characters):")
    print("-"*70)
    print(ocr_text)
    print("-"*70)

    if not student_entities:
        print("\n⚠ No entities extracted from answer")
        print("Student may have written general text without specific concepts.")
        return

    # Display extracted entities
    print(f"\n🔍 Extracted {len(student_entities)} entities:")
    for i, entity in enumerate(student_entities, 1):
        print(f"  {i}. {entity.text} ({entity.type})")

    # Step 2: Match with database
    print(f"\n[Step 2] Matching with Knowledge Base")
    print("-"*70)

    matched_entities = find_related_entities(db, student_entities, subject)

    if matched_entities:
        print(f"\n✓ Found {len(matched_entities)} matches in knowledge base:")
        for i, entity in enumerate(matched_entities, 1):
            print(f"  {i}. {entity.text} ({entity.type})")
    else:
        print("\n⚠ No matches found in knowledge base")
        print("This could mean:")
        print("  - Student used different terminology")
        print("  - Student answered off-topic")
        print("  - Knowledge base doesn't cover this content yet")

    # Step 3: Analysis
    print(f"\n[Step 3] Analysis")
    print("-"*70)

    # Coverage analysis
    student_normalized = set(e.normalized for e in student_entities)
    matched_normalized = set(e.normalized for e in matched_entities)

    coverage = len(matched_normalized) / len(student_normalized) if student_normalized else 0

    print(f"\n📊 Coverage: {coverage*100:.1f}%")
    print(f"   - Student mentioned: {len(student_entities)} entities")
    print(f"   - Matched with curriculum: {len(matched_entities)} entities")

    # What student got right
    if matched_normalized:
        print(f"\n✅ Concepts student understood:")
        for entity in matched_entities:
            print(f"   - {entity.text}")

    # What might be missing
    unmatched = student_normalized - matched_normalized
    if unmatched:
        print(f"\n❓ Entities not in curriculum (might be incorrect or need review):")
        for normalized in unmatched:
            # Find original entity
            for entity in student_entities:
                if entity.normalized == normalized:
                    print(f"   - {entity.text} ({entity.type})")
                    break

    # Step 4: Recommendations
    print(f"\n[Step 4] Recommendations")
    print("-"*70)

    if coverage >= 0.8:
        print("\n🌟 Excellent! Student demonstrates strong understanding.")
        print("   Mentioned most key concepts accurately.")
    elif coverage >= 0.5:
        print("\n👍 Good! Student has basic understanding.")
        print("   Some concepts mentioned, but may need review.")
    elif coverage >= 0.3:
        print("\n⚠ Needs improvement. Student has partial understanding.")
        print("   Missing several key concepts.")
    else:
        print("\n❌ Needs significant review. Low concept coverage.")
        print("   Student may need to re-study this topic.")

    # Suggest related material
    if matched_entities:
        print("\n💡 Suggested review materials:")
        print("   Run Q&A with these topics:")
        for entity in matched_entities[:3]:  # Top 3
            print(f"     python scripts/3_test_qa.py \"Jelaskan tentang {entity.text}\"")

    print("\n" + "="*70)


def main():
    """Main analysis process."""

    if len(sys.argv) < 2:
        print("Usage: python scripts/4_analyze_student_answer.py <image_path> [subject]")
        print("\nExamples:")
        print("  python scripts/4_analyze_student_answer.py student_answer.jpg fisika")
        print("  python scripts/4_analyze_student_answer.py homework.png matematika")
        print("\nSupported subjects: matematika, fisika, kimia, biologi")
        sys.exit(1)

    image_path = sys.argv[1]
    subject = sys.argv[2] if len(sys.argv) > 2 else "unknown"

    # Validate image path
    if not Path(image_path).exists():
        print(f"✗ Error: Image not found: {image_path}")
        sys.exit(1)

    # Validate image format
    valid_formats = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']
    if Path(image_path).suffix.lower() not in valid_formats:
        print(f"✗ Error: Unsupported image format: {Path(image_path).suffix}")
        print(f"Supported formats: {', '.join(valid_formats)}")
        sys.exit(1)

    # Check Grok API key
    if not GROK_API_KEY or GROK_API_KEY == 'your-grok-api-key-here':
        print("✗ Error: GROK_API_KEY not set in .env")
        print("\nThis feature requires Grok Vision API for OCR.")
        print("To enable:")
        print("  1. Get API key from: https://console.x.ai/")
        print("  2. Add to .env file: GROK_API_KEY=your-key-here")
        sys.exit(1)

    # Check database exists
    if not Path(COZODB_PATH).exists():
        print(f"⚠ Warning: Database not found at {COZODB_PATH}")
        print("Running in standalone mode (no entity matching with curriculum)")
        db = None
    else:
        print(f"✓ Database connected: {COZODB_PATH}")
        db = Client(engine=COZODB_ENGINE, path=COZODB_PATH)

    # Initialize extractor
    print(f"✓ Initializing Grok Vision OCR...")
    extractor = GrokEntityExtractor(
        api_key=GROK_API_KEY,
        api_url=GROK_API_URL,
        model=GROK_MODEL
    )

    # Analyze
    if db:
        analyze_answer(image_path, subject, db, extractor)
    else:
        # Standalone mode (just OCR + entity extraction)
        print("\n[Standalone Mode] OCR + Entity Extraction Only")
        print("-"*70)
        ocr_text, entities = extractor.extract_from_image(image_path, subject)

        if ocr_text:
            print(f"\n📄 Extracted Text:")
            print("-"*70)
            print(ocr_text)
            print("-"*70)

            if entities:
                print(f"\n🔍 Extracted {len(entities)} entities:")
                for i, entity in enumerate(entities, 1):
                    print(f"  {i}. {entity.text} ({entity.type})")
        else:
            print("\n✗ Failed to extract text from image")


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
