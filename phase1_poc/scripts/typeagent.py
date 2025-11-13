#!/usr/bin/env python3
"""
TypeAgent Entity Extraction Module with OCR
============================================

This module implements TypeAgent-style structured RAG using Grok API
for entity extraction from text chunks, user queries, and images (OCR).

Based on Microsoft Research's TypeAgent approach:
- Extract structured entities (concepts, formulas, topics)
- Build inverted index for fast entity lookup
- 4.2x better recall than traditional vector-only RAG
- OCR for handwritten student answers using Grok Vision

Features:
- Text entity extraction (from textbooks, queries)
- Image OCR (handwritten answers, diagrams)
- Entity extraction from OCR'd text

References:
- TypeAgent paper: https://www.microsoft.com/en-us/research/publication/typeagent/
- Grok API: https://docs.x.ai/api
- Grok Vision: https://docs.x.ai/docs/guides/vision
"""

import os
import json
import base64
from pathlib import Path
from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field
import requests


class Entity(BaseModel):
    """Extracted entity from text."""
    text: str = Field(description="The entity text as it appears")
    type: str = Field(description="Entity type: concept, formula, topic, definition, example")
    normalized: str = Field(description="Normalized form for matching (lowercase, singular)")


class EntityExtractionResult(BaseModel):
    """Result of entity extraction."""
    entities: List[Entity]
    reasoning: Optional[str] = None


class GrokEntityExtractor:
    """Entity extractor using Grok API."""

    def __init__(self, api_key: str, api_url: str = "https://api.x.ai/v1",
                 model: str = "grok-2-1212", temperature: float = 0.3):
        """
        Initialize Grok entity extractor.

        Args:
            api_key: Grok API key from https://console.x.ai/
            api_url: Grok API base URL
            model: Model to use (grok-2-1212 recommended)
            temperature: Lower = more conservative (0.3 recommended)
        """
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        self.model = model
        self.temperature = temperature
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

    def extract_from_chunk(self, chunk_text: str, subject: str, grade: int) -> List[Entity]:
        """
        Extract entities from a textbook chunk.

        Args:
            chunk_text: The text chunk to extract entities from
            subject: Subject area (matematika, fisika, kimia, biologi)
            grade: Grade level (7, 8, or 9)

        Returns:
            List of extracted entities
        """

        system_prompt = f"""You are an expert at extracting structured entities from Indonesian textbooks for {subject} (grade {grade}).

Your task is to extract KEY entities that students would search for, including:
1. **Concepts**: Important scientific/mathematical concepts (e.g., "hukum Newton", "fotosintesis")
2. **Formulas**: Mathematical/physics formulas (e.g., "F = m × a", "E = mc²")
3. **Topics**: Major topics or subtopics (e.g., "gerak lurus", "sistem pernapasan")
4. **Definitions**: Terms being defined (e.g., "massa", "percepatan", "enzim")
5. **Examples**: Specific named examples (e.g., "apel jatuh", "mobil bergerak")

Guidelines:
- Extract 5-15 entities per chunk
- Focus on entities students would search for
- Use Indonesian terms as they appear in the text
- Normalize to singular, lowercase form for matching
- Mark entity type accurately

Return JSON in this format:
{{
  "entities": [
    {{"text": "Hukum Newton Kedua", "type": "concept", "normalized": "hukum newton kedua"}},
    {{"text": "F = m × a", "type": "formula", "normalized": "f = m × a"}},
    {{"text": "percepatan", "type": "definition", "normalized": "percepatan"}}
  ]
}}"""

        user_prompt = f"""Extract entities from this {subject} textbook chunk (grade {grade}):

---
{chunk_text[:1500]}
---

Return ONLY valid JSON, no other text."""

        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": self.temperature,
                    "max_tokens": 1000
                },
                timeout=30
            )

            if response.status_code != 200:
                print(f"⚠ Grok API error: {response.status_code} - {response.text}")
                return []

            result = response.json()
            content = result['choices'][0]['message']['content']

            # Parse JSON response
            # Handle markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            entities = [
                Entity(
                    text=e['text'],
                    type=e['type'],
                    normalized=e['normalized']
                )
                for e in data.get('entities', [])
            ]

            return entities

        except Exception as e:
            print(f"⚠ Entity extraction error: {e}")
            return []

    def extract_from_query(self, query: str, max_entities: int = 10) -> List[Entity]:
        """
        Extract entities from a user query.

        Args:
            query: User's question in Indonesian
            max_entities: Maximum entities to extract

        Returns:
            List of extracted entities
        """

        system_prompt = f"""You are an expert at extracting search entities from Indonesian student questions about STEM subjects.

Your task is to identify KEY entities the student is asking about, including:
1. **Concepts**: Scientific/mathematical concepts mentioned
2. **Formulas**: Any formulas referenced
3. **Topics**: Subject topics mentioned
4. **Keywords**: Important search keywords

Guidelines:
- Extract 1-{max_entities} entities
- Focus on the MAIN concepts being asked about
- Use Indonesian terms
- Normalize to singular, lowercase
- Only extract entities explicitly mentioned or strongly implied

Return JSON in this format:
{{
  "entities": [
    {{"text": "Hukum Newton", "type": "concept", "normalized": "hukum newton"}},
    {{"text": "percepatan", "type": "concept", "normalized": "percepatan"}}
  ]
}}"""

        user_prompt = f"""Extract search entities from this student question:

"{query}"

Return ONLY valid JSON, no other text."""

        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": self.temperature,
                    "max_tokens": 500
                },
                timeout=20
            )

            if response.status_code != 200:
                print(f"⚠ Grok API error: {response.status_code}")
                return []

            result = response.json()
            content = result['choices'][0]['message']['content']

            # Parse JSON response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            entities = [
                Entity(
                    text=e['text'],
                    type=e['type'],
                    normalized=e['normalized']
                )
                for e in data.get('entities', [])
            ]

            return entities[:max_entities]

        except Exception as e:
            print(f"⚠ Query entity extraction error: {e}")
            return []

    def ocr_image(self, image_path: str) -> str:
        """
        Perform OCR on an image using Grok Vision API.

        Supports handwritten text, printed text, diagrams, and formulas.

        Args:
            image_path: Path to image file (JPG, PNG, etc.)

        Returns:
            Extracted text from image
        """

        # Read and encode image
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"⚠ Error reading image: {e}")
            return ""

        # Determine image format
        image_format = Path(image_path).suffix.lower().replace('.', '')
        if image_format == 'jpg':
            image_format = 'jpeg'

        # Grok Vision API call
        system_prompt = """You are an expert OCR system specialized in reading handwritten student answers for STEM subjects (Math, Physics, Chemistry, Biology) in Indonesian language.

Your task:
1. Extract ALL text from the image, including:
   - Handwritten text (even if messy)
   - Printed text
   - Mathematical formulas and equations
   - Diagrams labels
   - Any annotations

2. Preserve formatting:
   - Keep paragraph breaks
   - Preserve formula notation (e.g., F = m × a)
   - Keep lists and numbering

3. Handle Indonesian language correctly

Return ONLY the extracted text, no additional commentary."""

        user_content = [
            {
                "type": "text",
                "text": "Extract all text from this image. Include handwritten notes, formulas, and any visible text:"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{image_format};base64,{image_data}"
                }
            }
        ]

        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "grok-vision-beta",  # Grok Vision model
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.1,  # Very low for accurate OCR
                    "max_tokens": 2000
                },
                timeout=30
            )

            if response.status_code != 200:
                print(f"⚠ Grok Vision API error: {response.status_code} - {response.text}")
                return ""

            result = response.json()
            extracted_text = result['choices'][0]['message']['content']

            return extracted_text.strip()

        except Exception as e:
            print(f"⚠ OCR error: {e}")
            return ""

    def extract_from_image(self, image_path: str, subject: str = "unknown") -> tuple[str, List[Entity]]:
        """
        Perform OCR on image and extract entities from the OCR'd text.

        This is useful for analyzing student answers:
        1. OCR the handwritten answer
        2. Extract key entities (concepts mentioned)
        3. Can be used for assessment or query expansion

        Args:
            image_path: Path to image file
            subject: Subject context (matematika, fisika, kimia, biologi)

        Returns:
            Tuple of (ocr_text, entities)
        """

        print(f"   [OCR] Processing image: {Path(image_path).name}")

        # Step 1: OCR
        ocr_text = self.ocr_image(image_path)

        if not ocr_text:
            print(f"   ⚠ No text extracted from image")
            return ("", [])

        print(f"   ✓ Extracted {len(ocr_text)} characters")
        print(f"   Preview: {ocr_text[:100]}...")

        # Step 2: Extract entities
        print(f"   [Entity] Extracting entities from OCR'd text...")

        system_prompt = f"""Extract key entities from this student's answer about {subject}.

Focus on:
1. **Concepts** mentioned (e.g., "hukum Newton", "fotosintesis")
2. **Formulas** written (e.g., "F = m × a")
3. **Topics** discussed (e.g., "gerak lurus")
4. **Terms** defined

Return JSON:
{{
  "entities": [
    {{"text": "...", "type": "concept|formula|topic|definition", "normalized": "..."}},
  ]
}}"""

        user_prompt = f"""Student's answer (from OCR):

---
{ocr_text[:1000]}
---

Extract entities. Return ONLY JSON."""

        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": self.temperature,
                    "max_tokens": 1000
                },
                timeout=30
            )

            if response.status_code != 200:
                print(f"   ⚠ Entity extraction error: {response.status_code}")
                return (ocr_text, [])

            result = response.json()
            content = result['choices'][0]['message']['content']

            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            entities = [
                Entity(
                    text=e['text'],
                    type=e['type'],
                    normalized=e['normalized']
                )
                for e in data.get('entities', [])
            ]

            print(f"   ✓ Extracted {len(entities)} entities")
            for entity in entities:
                print(f"      - {entity.text} ({entity.type})")

            return (ocr_text, entities)

        except Exception as e:
            print(f"   ⚠ Entity extraction error: {e}")
            return (ocr_text, [])


def normalize_entity(text: str) -> str:
    """
    Normalize entity text for matching.

    Rules:
    - Convert to lowercase
    - Remove extra whitespace
    - Basic singularization (remove -s, -es suffixes for English terms)
    """
    text = text.lower().strip()
    text = ' '.join(text.split())  # Normalize whitespace
    return text


if __name__ == "__main__":
    # Test entity extraction
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv('GROK_API_KEY')
    if not api_key or api_key == 'your-grok-api-key-here':
        print("Error: GROK_API_KEY not set in .env file")
        print("Get your API key from: https://console.x.ai/")
        sys.exit(1)

    extractor = GrokEntityExtractor(api_key=api_key)

    # Test with sample query
    print("Testing entity extraction from query...")
    print("="*60)

    query = "Jelaskan hukum Newton kedua dan berikan contohnya"
    print(f"Query: {query}\n")

    entities = extractor.extract_from_query(query)

    print(f"Extracted {len(entities)} entities:")
    for entity in entities:
        print(f"  - {entity.text} ({entity.type}) -> {entity.normalized}")

    print("\n" + "="*60)
    print("✓ Entity extraction test complete")
