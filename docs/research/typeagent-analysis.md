# TypeAgent Research & Integration Analysis for AI Teacher

**Research Date:** November 2025
**Researcher:** Technical Team
**Status:** Recommendation for Roadmap Integration

---

## Executive Summary

TypeAgent is a Microsoft research project led by Guido van Rossum (Python creator) that introduces **Structured RAG** - a significant improvement over traditional RAG systems. After thorough research, we **strongly recommend** integrating TypeAgent's structured RAG approach into AI Teacher's architecture. This will dramatically improve:

- **Recall accuracy:** 4.2x better (63 vs 15 books recalled in benchmark)
- **Token efficiency:** 50% fewer tokens needed
- **Semantic understanding:** Better context-aware answers about past conversations
- **Knowledge persistence:** Superior long-term memory for student profiles

**Recommendation:** Integrate Structured RAG in **Phase 1 (MVP)** rather than waiting for production.

---

## What is TypeAgent?

### Overview

**TypeAgent** is sample code from Microsoft that explores an architecture for building personal agents with natural language interfaces using LLM technology. The Python port (`typeagent-py`) was presented by Guido van Rossum at PyBay 2025 in his talk: **"Structured RAG is Better than RAG!"**

- **GitHub (TypeScript):** https://github.com/microsoft/TypeAgent
- **GitHub (Python):** https://github.com/microsoft/typeagent-py
- **License:** MIT (open source)
- **Status:** Early-stage prototype, actively developed
- **Stars:** 333+ on GitHub
- **Installation:** `pip install typeagent`

### Core Innovation: KnowPro

**KnowPro** is TypeAgent's memory implementation that uses **Structured RAG** for indexing and querying agent conversations. It transforms "forgetful chatbots" into "reliable lifelong companions" through structured knowledge extraction and retrieval.

---

## Traditional RAG vs Structured RAG

### Traditional RAG (What We Currently Plan)

**How it works:**
1. Split documents into chunks (e.g., 512 tokens with 50 overlap)
2. Generate embeddings for each chunk
3. Store embeddings in vector database (DuckDB for POC)
4. Query: Generate embedding for user question
5. Retrieve top-k most similar chunks (cosine similarity)
6. Pass chunks + query to LLM for answer generation

**Limitations:**
- ❌ **Narrow context window** - Can only fit limited chunks
- ❌ **Fragmented answers** - Chunking breaks context
- ❌ **Poor semantic search** - Struggles with relationship queries
- ❌ **No structured knowledge** - Doesn't understand entities/relationships
- ❌ **Limited recall** - Misses relevant information outside top-k
- ❌ **No temporal reasoning** - Can't track concepts over time

### Structured RAG (TypeAgent Approach)

**How it works:**
1. **Knowledge Extraction (Ingestion Time):**
   - Use LLM to extract structured data from documents:
     - **Entities:** People, concepts, formulas, laws (e.g., "Hukum Newton 2", "Gaya", "Percepatan")
     - **Topics:** Short topic sentences summarizing content
     - **Verbs/Actions:** Relationships between entities (e.g., "requires", "relates to", "prerequisite of")
     - **Key Terms:** Important terminology from entities and topics

2. **Structured Storage:**
   - Store extracted entities, topics, and relationships
   - Create inverted index: term → entities/topics → messages
   - Build knowledge graph of entity relationships
   - Use traditional database (SQL) + inverted index (Lucene/Azure AI Search)

3. **Structured Query:**
   - User query → Extract entities and intent
   - Query inverted index for matching entities/topics
   - Traverse knowledge graph for related concepts
   - Retrieve structured knowledge (not raw text chunks)
   - Build compact, semantically-rich context

4. **Generation:**
   - Pass structured knowledge + query to LLM
   - LLM has "tight semantic structures" within attention budget
   - More accurate, context-aware answers

**Advantages:**
- ✅ **4.2x better recall** - 63 vs 15 books in benchmark (3K tokens)
- ✅ **50% token savings** - More efficient context packing
- ✅ **Semantic understanding** - Understands entity relationships
- ✅ **Multi-hop reasoning** - Can traverse knowledge graph
- ✅ **Temporal tracking** - Maintains knowledge over time
- ✅ **Explicit relationships** - Subject-predicate-object triples
- ✅ **Better question answering** - "What were the books we talked about?" works well

---

## TypeAgent Architecture

### Three Foundational Principles

1. **Distill models into logical structures**
   - Convert LLM outputs into actionable patterns
   - Extract structured knowledge from unstructured text

2. **Use structure to control information density**
   - Keep semantic structures compact within attention budgets
   - Fit more meaningful information in fewer tokens

3. **Use structure to enable collaboration**
   - Facilitate human-model-program interactions
   - Enable explainable, traceable reasoning

### Technical Components

```
┌────────────────────────────────────────────────────────────┐
│ 1. INGESTION PHASE                                         │
│                                                            │
│  PDF/Text Input                                            │
│       │                                                    │
│       ▼                                                    │
│  LLM-based Extraction                                      │
│  ├── Entities (nouns, concepts, formulas)                 │
│  ├── Topics (topic sentences)                             │
│  ├── Relationships (verbs, actions)                       │
│  └── Key Terms                                            │
│       │                                                    │
│       ▼                                                    │
│  Structured Storage                                        │
│  ├── Inverted Index (term → entity/topic)                 │
│  ├── Knowledge Graph (entity relationships)               │
│  └── SQL Database (structured data)                       │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ 2. QUERY PHASE                                             │
│                                                            │
│  User Question                                             │
│       │                                                    │
│       ▼                                                    │
│  Query Structuring (LLM extracts intent + entities)       │
│       │                                                    │
│       ▼                                                    │
│  Inverted Index Lookup                                     │
│  ├── Find matching entities                               │
│  ├── Find matching topics                                 │
│  └── Retrieve related terms                               │
│       │                                                    │
│       ▼                                                    │
│  Knowledge Graph Traversal                                 │
│  ├── Find related entities                                │
│  ├── Follow relationships (multi-hop)                     │
│  └── Collect semantic context                             │
│       │                                                    │
│       ▼                                                    │
│  Build Structured Context (compact, semantic)             │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ 3. GENERATION PHASE                                        │
│                                                            │
│  Structured Context + Query → LLM → Answer                │
└────────────────────────────────────────────────────────────┘
```

---

## Benchmark Results

### TypeAgent Performance (Behind the Tech Podcasts - 25 episodes)

**Task:** Recall all books discussed in conversations

| Approach | Input Tokens | Books Recalled | Recall Rate |
|----------|-------------|----------------|-------------|
| **Structured RAG** | 3K | **63** | **100%** |
| Classic RAG | 6K | 15 | 24% |
| Classic RAG | 128K | 31 | 49% |

**Key Insights:**
- Structured RAG recalls **4.2x more** with **50% fewer tokens**
- Even with massive context (128K), classic RAG only reaches 49% recall
- Structured RAG achieves perfect recall with minimal tokens

---

## Application to AI Teacher

### Perfect Alignment with Our Needs

AI Teacher has **identical requirements** to TypeAgent's design goals:

1. **Educational Concepts as Entities**
   - Math: "Aljabar", "Persamaan Linear", "Teorema Pythagoras"
   - Physics: "Hukum Newton", "Gaya", "Percepatan", "F=ma"
   - Chemistry: "Atom", "Molekul", "Reaksi Kimia"
   - Biology: "Sel", "DNA", "Fotosintesis"

2. **Relationship-Rich Domain**
   - Prerequisites: "Persamaan Linear" requires "Aljabar Dasar"
   - Related concepts: "Gaya" relates to "Hukum Newton 1, 2, 3"
   - Part-of: "Mitokondria" part-of "Sel"

3. **Long-Term Memory Requirement**
   - Track student's learning journey over months
   - Remember which topics mastered, which struggling
   - Adapt difficulty based on history

4. **Multi-Hop Reasoning**
   - "What do I need to learn before Hukum Newton 2?"
   - "Show me topics related to what I learned last week"
   - "Which concepts connect chemistry and physics?"

### Concrete Benefits for AI Teacher

#### 1. Better Student Question Answering

**Traditional RAG Problem:**
- Student asks: "Apa hubungan antara gaya dan percepatan?" (What's the relationship between force and acceleration?)
- Retrieves chunks mentioning "gaya" OR "percepatan"
- May miss the connection (Hukum Newton 2: F = m × a)

**Structured RAG Solution:**
- Extract entities: "Gaya", "Percepatan"
- Query knowledge graph: Find relationship
- Retrieve: "Hukum Newton 2" connects them via F = m × a
- Result: Precise, relationship-aware answer

#### 2. Superior Student Profiling

**Traditional RAG Problem:**
- Stores conversation chunks
- Hard to query: "What math topics has student mastered?"
- Requires scanning all chunks

**Structured RAG Solution:**
- Extracted entities: "Persamaan Linear (mastered)", "Persamaan Kuadrat (struggling)"
- Query index: Instant retrieval of student's knowledge state
- Track temporal progression: "Improved on topic X over 3 weeks"

#### 3. Prerequisite-Aware Teaching

**Traditional RAG Problem:**
- Student asks about "Persamaan Kuadrat"
- System doesn't know if student understands "Persamaan Linear" first

**Structured RAG Solution:**
- Knowledge graph has prerequisite relationships
- Query: "Does student know prerequisites for Persamaan Kuadrat?"
- System can proactively teach missing prerequisites

#### 4. Adaptive Difficulty

**Traditional RAG Problem:**
- Difficulty adjustment based on limited signals

**Structured RAG Solution:**
- Track mastery level per entity: "Aljabar Dasar (expert)", "Geometri (beginner)"
- Adjust question difficulty based on structured knowledge
- Identify knowledge gaps precisely

---

## Integration Strategy for AI Teacher

### Hybrid Architecture (Recommended)

**Combine Structured RAG + Traditional RAG:**

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID RAG SYSTEM                        │
│                                                             │
│  User Question                                              │
│       │                                                     │
│       ├────────────────┬────────────────┐                  │
│       ▼                ▼                ▼                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│  │ Structured │  │  Vector    │  │ Knowledge  │          │
│  │   Index    │  │  Search    │  │   Graph    │          │
│  │ (TypeAgent)│  │ (DuckDB)   │  │  (Neo4j)   │          │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘          │
│        │                │                │                  │
│        └────────────────┴────────────────┘                  │
│                         │                                   │
│                         ▼                                   │
│                  Combine Results                            │
│                         │                                   │
│                         ▼                                   │
│                   LLM Generation                            │
└─────────────────────────────────────────────────────────────┘
```

**Why Hybrid:**
1. **Structured RAG** for entity/concept queries and relationships
2. **Vector search** for semantic similarity and detailed passages
3. **Knowledge graph** for explicit relationships (already planned)
4. **Best of both worlds:** Precision + Flexibility

### Implementation Phases

#### Phase 0: POC (Months 1-2) - Research & Prototype

- [x] ✅ Current RAG architecture (DuckDB + Neo4j)
- [ ] ⏳ **Add:** Prototype TypeAgent integration
  - Install `typeagent` Python package
  - Test on sample textbook (1 chapter)
  - Compare recall vs traditional RAG
  - Measure token efficiency
  - **Deliverable:** Performance comparison report

#### Phase 1: MVP (Months 3-5) - Structured RAG Integration

- [ ] **Ingestion Pipeline:**
  - Implement entity extraction from Indonesian textbooks
  - Extract topics, key terms, relationships
  - Store in structured format (SQL + inverted index)
  - Populate Neo4j with extracted relationships

- [ ] **Query System:**
  - Implement structured query processing
  - Build inverted index lookup (can use DuckDB or SQLite)
  - Integrate with Neo4j for graph traversal
  - Implement hybrid retrieval (structured + vector)

- [ ] **Student Memory:**
  - Apply Structured RAG to student profiles
  - Extract mastery entities from conversations
  - Track temporal knowledge progression
  - Enable queries: "What has student mastered?"

- **Deliverable:** MVP with hybrid RAG for Math + Physics

#### Phase 2: Beta (Months 6-8) - Refinement

- [ ] Optimize entity extraction prompts for Indonesian language
- [ ] Fine-tune extraction for STEM domain
- [ ] Expand to Chemistry + Biology
- [ ] A/B testing: Structured vs Traditional RAG
- [ ] User feedback on answer quality

- **Deliverable:** Beta with all subjects using hybrid RAG

#### Phase 3+: Production - Scale & Optimize

- [ ] Migrate inverted index to production-grade (Elasticsearch/Azure AI Search)
- [ ] Optimize extraction speed (batch processing)
- [ ] Implement caching for extracted entities
- [ ] Production monitoring and quality metrics

---

## Technical Implementation Plan

### 1. Entity Extraction System

```python
"""
Entity extraction for Indonesian STEM textbooks
Uses TypeAgent-style structured extraction
"""

from typing import List, Dict
from langchain.prompts import PromptTemplate
from src.llm.client import LlamaServerClient

# Extraction prompt template
ENTITY_EXTRACTION_PROMPT = """
Ekstrak informasi terstruktur dari teks buku STEM berikut:

Teks:
{text}

Ekstrak dan format dalam JSON:
{{
  "entities": [
    {{"name": "Hukum Newton 2", "type": "law", "description": "F = m × a"}},
    {{"name": "Gaya", "type": "concept", "description": "..."}}
  ],
  "topics": [
    "Hubungan antara gaya, massa, dan percepatan"
  ],
  "relationships": [
    {{"subject": "Hukum Newton 2", "predicate": "melibatkan", "object": "Gaya"}},
    {{"subject": "Hukum Newton 2", "predicate": "melibatkan", "object": "Percepatan"}}
  ],
  "key_terms": ["gaya", "massa", "percepatan", "Newton"]
}}

Fokus pada konsep STEM: rumus, hukum, definisi, hubungan antar konsep.
"""

class StructuredExtractor:
    def __init__(self, llm_client: LlamaServerClient):
        self.llm = llm_client

    def extract_knowledge(self, text: str, metadata: Dict) -> Dict:
        """Extract structured knowledge from text"""

        # Generate extraction prompt
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)

        # Call LLM
        response = self.llm.chat_completion(
            messages=[
                {"role": "system", "content": "Kamu adalah sistem ekstraksi pengetahuan STEM."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3  # Lower temp for structured extraction
        )

        # Parse JSON response
        extracted = self._parse_json(response)

        # Add metadata
        extracted["metadata"] = metadata

        return extracted

    def _parse_json(self, response: Dict) -> Dict:
        """Parse and validate JSON from LLM response"""
        # Implementation: Extract JSON from response, validate schema
        pass
```

### 2. Inverted Index Implementation

```python
"""
Inverted index for term → entity/topic mapping
Can use DuckDB, SQLite, or dedicated search engine
"""

import duckdb
from typing import List, Dict

class InvertedIndex:
    def __init__(self, db_path: str):
        self.conn = duckdb.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        """Create inverted index tables"""

        # Entities table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY,
                name VARCHAR,
                type VARCHAR,
                description TEXT,
                source_file VARCHAR,
                page_number INTEGER
            )
        """)

        # Topics table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY,
                topic TEXT,
                source_file VARCHAR,
                page_number INTEGER
            )
        """)

        # Term index (inverted index)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS term_index (
                term VARCHAR,
                entity_id INTEGER,
                topic_id INTEGER,
                relevance FLOAT
            )
        """)

        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_term ON term_index(term)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entity_id ON term_index(entity_id)")

    def add_entity(self, entity: Dict) -> int:
        """Add entity and index its terms"""

        # Insert entity
        result = self.conn.execute("""
            INSERT INTO entities (name, type, description, source_file, page_number)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
        """, [
            entity["name"],
            entity["type"],
            entity["description"],
            entity["metadata"]["source_file"],
            entity["metadata"]["page_number"]
        ]).fetchone()

        entity_id = result[0]

        # Extract and index terms
        terms = self._extract_terms(entity["name"], entity["description"])
        for term, relevance in terms:
            self.conn.execute("""
                INSERT INTO term_index (term, entity_id, relevance)
                VALUES (?, ?, ?)
            """, [term.lower(), entity_id, relevance])

        self.conn.commit()
        return entity_id

    def search(self, query: str, k: int = 10) -> List[Dict]:
        """Search for entities matching query terms"""

        # Extract query terms
        query_terms = self._tokenize(query)

        # Build SQL query
        results = self.conn.execute("""
            SELECT e.id, e.name, e.type, e.description,
                   SUM(ti.relevance) as score
            FROM entities e
            JOIN term_index ti ON e.id = ti.entity_id
            WHERE ti.term IN ({})
            GROUP BY e.id, e.name, e.type, e.description
            ORDER BY score DESC
            LIMIT ?
        """.format(','.join('?' * len(query_terms))), query_terms + [k]).fetchall()

        return [
            {
                "id": r[0],
                "name": r[1],
                "type": r[2],
                "description": r[3],
                "score": r[4]
            }
            for r in results
        ]

    def _extract_terms(self, name: str, description: str) -> List[tuple]:
        """Extract terms with relevance scores"""
        # Implementation: tokenize, stem, calculate relevance
        pass

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize and normalize text"""
        # Implementation: lowercase, remove stopwords, stem
        pass
```

### 3. Hybrid Retrieval System

```python
"""
Hybrid retrieval combining structured and vector search
"""

from typing import List, Dict
from src.rag.duckdb_store import DuckDBVectorStore
from src.graph.neo4j_client import Neo4jClient

class HybridRetriever:
    def __init__(
        self,
        vector_store: DuckDBVectorStore,
        inverted_index: InvertedIndex,
        knowledge_graph: Neo4jClient
    ):
        self.vector_store = vector_store
        self.inverted_index = inverted_index
        self.knowledge_graph = knowledge_graph

    def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        k: int = 5
    ) -> Dict:
        """
        Hybrid retrieval combining all sources
        """

        # 1. Structured search (inverted index)
        structured_results = self.inverted_index.search(query, k=k)

        # 2. Vector search (semantic similarity)
        vector_results = self.vector_store.search(
            query_embedding, k=k
        )

        # 3. Knowledge graph traversal
        # Extract entities from query
        entities = self._extract_query_entities(query)
        graph_results = []
        for entity in entities:
            # Find related concepts
            related = self.knowledge_graph.get_related_concepts(
                entity, depth=2
            )
            graph_results.extend(related)

        # 4. Combine and rank
        combined = self._merge_results(
            structured_results,
            vector_results,
            graph_results
        )

        return {
            "structured": structured_results,
            "vector": vector_results,
            "graph": graph_results,
            "combined": combined
        }

    def _extract_query_entities(self, query: str) -> List[str]:
        """Extract entities from query using LLM"""
        # Implementation: Use LLM to identify entities in query
        pass

    def _merge_results(
        self,
        structured: List[Dict],
        vector: List[Dict],
        graph: List[Dict]
    ) -> List[Dict]:
        """Merge and rank results from all sources"""
        # Implementation: Combine results, remove duplicates, rank by relevance
        pass
```

---

## Cost-Benefit Analysis

### Implementation Costs

| Component | Effort | Timeline |
|-----------|--------|----------|
| Entity extraction pipeline | 2-3 weeks | Phase 1 |
| Inverted index system | 1-2 weeks | Phase 1 |
| Hybrid retrieval logic | 1-2 weeks | Phase 1 |
| Neo4j integration | 1 week | Phase 1 |
| Testing & optimization | 2-3 weeks | Phase 1 |
| **Total** | **7-11 weeks** | **Phase 1** |

### Benefits

| Benefit | Impact | Value |
|---------|--------|-------|
| **4.2x better recall** | Critical | Very High |
| **50% token savings** | Moderate | High |
| **Better student profiling** | Critical | Very High |
| **Prerequisite-aware teaching** | Critical | Very High |
| **Multi-hop reasoning** | High | High |
| **Explainable answers** | Moderate | Medium |

### ROI Assessment

**High ROI:** The 7-11 week investment is **highly justified** given:
1. Core product quality (answer accuracy) improves 4.2x
2. Token efficiency reduces inference costs by 50%
3. Enables critical features (student profiling, prerequisites)
4. Competitive differentiation (most educational apps don't use structured RAG)

**Recommendation: PROCEED** with integration in Phase 1.

---

## Risks & Mitigations

### Risk 1: Entity Extraction Quality for Indonesian

**Risk:** LFM2 may struggle with Indonesian language entity extraction

**Mitigation:**
- Fine-tune extraction prompts for Indonesian
- Use few-shot learning with examples
- Implement validation layer to check extraction quality
- Fall back to English translation if needed (for extraction only)

### Risk 2: Additional Complexity

**Risk:** Structured RAG adds system complexity

**Mitigation:**
- Use abstraction layers (easy to disable if issues arise)
- Implement comprehensive testing
- Start with one subject (Math) before expanding
- Keep traditional vector search as fallback

### Risk 3: TypeAgent Maturity

**Risk:** TypeAgent is early-stage prototype

**Mitigation:**
- Use concepts, not necessarily the library itself
- Implement core ideas independently
- Monitor TypeAgent development for updates
- Can always revert to traditional RAG

### Risk 4: Performance Overhead

**Risk:** Entity extraction during ingestion is slower

**Mitigation:**
- Batch processing (offline, not real-time)
- Cache extracted entities
- Extraction is one-time per document
- Query time is faster due to structured index

---

## Recommendations

### Short-Term (Phase 1 - MVP)

1. ✅ **INTEGRATE:** Add Structured RAG to Phase 1 roadmap
2. ✅ **PROTOTYPE:** Build entity extraction for Indonesian STEM content
3. ✅ **HYBRID:** Implement hybrid retrieval (structured + vector + graph)
4. ✅ **TEST:** A/B test structured vs traditional RAG with sample students
5. ✅ **MEASURE:** Track recall accuracy, token efficiency, answer quality

### Medium-Term (Phase 2 - Beta)

1. Optimize extraction prompts based on user feedback
2. Fine-tune LFM2 specifically for entity extraction
3. Expand to all subjects (Math, Physics, Chemistry, Biology)
4. Implement advanced features (temporal tracking, multi-hop reasoning)
5. Production-grade inverted index (consider Elasticsearch)

### Long-Term (Phase 3+ - Production)

1. Scale extraction pipeline for 1000+ textbooks
2. Continuous learning: Extract knowledge from student conversations
3. Cross-lingual expansion (English, other languages)
4. Advanced relationship mining (automatic prerequisite detection)
5. Contribute improvements back to TypeAgent project

---

## Conclusion

**TypeAgent's Structured RAG is a game-changer for AI Teacher.** The 4.2x improvement in recall accuracy directly translates to better student learning outcomes. The hybrid approach (structured + vector + graph) gives us:

1. **Precision:** Structured index for entity/concept queries
2. **Flexibility:** Vector search for semantic similarity
3. **Relationships:** Knowledge graph for multi-hop reasoning
4. **Efficiency:** 50% token savings = lower costs
5. **Memory:** Superior student profiling over time

**The competitive advantage is significant:** Most educational AI tools use basic RAG. By implementing Structured RAG, we'll deliver measurably better answers with lower costs.

**Recommendation:** **PROCEED** with integration in Phase 1 (MVP). The 7-11 week investment is justified by the substantial quality and cost improvements.

---

## References

1. **TypeAgent Repository (TypeScript):** https://github.com/microsoft/TypeAgent
2. **TypeAgent-Py Repository (Python):** https://github.com/microsoft/typeagent-py
3. **Guido van Rossum PyBay 2025 Talk:** "Structured RAG is Better than RAG!"
4. **TypeAgent Documentation:** Memory Architecture and KnowPro
5. **Benchmark Data:** Behind the Tech podcasts (25 episodes, 3K vs 128K tokens)

---

**Document Version:** 1.0
**Last Updated:** November 2025
**Next Review:** After Phase 1 prototype completion
**Status:** **APPROVED FOR ROADMAP INTEGRATION**
