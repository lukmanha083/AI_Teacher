# Sync Strategy: 10,000 CozoDB Clients ↔ Cassandra

**Date:** November 2025
**Status:** ARCHITECTURE DESIGN
**Context:** User asked about syncing 10K local CozoDB with Cassandra using Kafka

---

## Executive Summary

### User's Question

> "How do we sync thousands of local CozoDB (10,000 users) with Cassandra? Using event-driven Apache Kafka? If Kafka is needed, should we wait for FreeBSD to port Cassandra 5.0 or build from source?"

### Short Answer

**You DON'T need Kafka for 10,000 users!**

- Simple **REST API + polling** is sufficient for 10K users
- Kafka adds complexity without benefits at this scale
- Cassandra CDC + Kafka makes sense at 100K-1M users
- **FreeBSD decision**: Use **Cassandra 4.x** from ports (stable) OR migrate to Ubuntu for Cassandra 5.0

---

## Part 1: Do We Need Kafka?

### Kafka: What It's For

**Apache Kafka** is for:
- **High-throughput event streaming** (millions of events/sec)
- **Real-time push notifications** (sub-second latency)
- **Complex event processing** (stream joins, aggregations)
- **Massive scale** (100K-10M+ clients)

### Our Use Case: Content Distribution

**What we're syncing**:
- Textbook content updates (teachers add chapters)
- Student progress upload (daily aggregation)
- Frequency: Every 6-24 hours
- Scale: 10,000 users

**Key insight**: This is **NOT real-time!**

Students don't need new content in milliseconds. Hours or even days is fine for educational content updates.

### Kafka: Overkill for Our Scale

| Metric | Our Needs | Kafka Designed For | Verdict |
|--------|-----------|-------------------|---------|
| **Scale** | 10K users | 100K-10M users | Overkill |
| **Latency** | Hours (6-24hr sync) | Milliseconds | Overkill |
| **Throughput** | ~100 req/sec | 1M+ events/sec | Overkill |
| **Complexity** | Simple content dist. | Stream processing | Overkill |
| **Operations** | Want simple | Needs expertise | Overkill |

**Verdict**: **DON'T use Kafka for 10K users**

Use Kafka when you hit 100K+ users or need sub-second push updates.

---

## Part 2: Simple Sync Strategy (Recommended)

### Architecture: Pull-Based REST API

```
┌─────────────────────────────────────────────┐
│  Mobile/Desktop (10,000 devices)            │
│  CozoDB (SQLite) - Local                    │
│                                             │
│  Every 6-24 hours:                          │
│  1. Check for content updates (HTTP GET)    │
│  2. Download new content if available       │
│  3. Upload student progress (HTTP POST)     │
└──────────────┬──────────────────────────────┘
               │
               │ HTTPS (REST API)
               │ Simple poll-based sync
               │
┌──────────────▼──────────────────────────────┐
│  Sync API Server (FreeBSD/Ubuntu)           │
│  - FastAPI / Flask Python app               │
│  - Checks Cassandra for updates             │
│  - Writes student progress to Cassandra     │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  Cassandra 4.x/5.0 (3-node cluster)         │
│  - textbooks table                          │
│  - embeddings table                         │
│  - knowledge_graph table                    │
│  - student_progress table                   │
│  - sync_metadata table (version tracking)   │
└─────────────────────────────────────────────┘
```

### Why Pull-Based is Better

**Pull-Based (Client polls server)**:
- ✅ Simple to implement
- ✅ Client controls when to sync (WiFi-only, battery-aware)
- ✅ Scales to 10K users easily
- ✅ No persistent connections
- ✅ Works offline (queue changes, sync when online)

**Push-Based (Server pushes to client)**:
- ❌ Requires persistent connections (WebSocket, SSE, or push service)
- ❌ More complex server infrastructure
- ❌ Battery drain on mobile
- ❌ Not needed for 6-24 hour sync frequency

**Verdict**: Pull-based is perfect for content distribution!

---

## Part 3: Sync Protocol Design

### 3.1 Version Tracking

**Cassandra table**:

```cql
CREATE TABLE sync_metadata (
    content_type TEXT,        -- 'textbook', 'embedding', 'graph'
    version BIGINT,           -- Incremented on each change
    last_updated TIMESTAMP,
    change_summary MAP<TEXT, TEXT>,
    PRIMARY KEY (content_type)
);

-- Example data
INSERT INTO sync_metadata (content_type, version, last_updated)
VALUES ('textbook', 42, toTimestamp(now()));
```

**Client tracks**:

```python
# Stored in local CozoDB
CREATE TABLE sync_state (
    content_type TEXT PRIMARY KEY,
    last_synced_version INT,
    last_sync_time TIMESTAMP
);
```

### 3.2 Sync Flow: Check for Updates

**Client → Server**:

```http
GET /api/v1/sync/check
Headers:
  Authorization: Bearer <jwt_token>
  X-Client-Version: 1.0.0

Body (JSON):
{
  "student_id": "uuid-1234",
  "current_versions": {
    "textbook": 38,
    "embedding": 40,
    "graph": 35
  }
}
```

**Server → Client**:

```json
{
  "updates_available": true,
  "new_versions": {
    "textbook": 42,
    "embedding": 45,
    "graph": 38
  },
  "changes": {
    "textbook": ["chapter_uuid_1", "chapter_uuid_2"],
    "embedding": ["Added 500 new embeddings for Physics"],
    "graph": ["Added 20 new concept relationships"]
  },
  "estimated_download_size_mb": 15
}
```

### 3.3 Download Content Updates

**Client → Server** (if updates available):

```http
GET /api/v1/sync/download/textbook?from_version=38&to_version=42
Headers:
  Authorization: Bearer <jwt_token>
```

**Server → Client** (streaming response):

```json
{
  "version": 42,
  "content_type": "textbook",
  "changes": [
    {
      "operation": "INSERT",
      "chapter_id": "uuid-5678",
      "subject": "Physics",
      "grade": 9,
      "title": "Hukum Newton Ketiga",
      "content": "...",
      "embeddings": [/* array of vectors */],
      "knowledge_graph": {
        "concepts": [...],
        "relationships": [...]
      }
    },
    {
      "operation": "UPDATE",
      "chapter_id": "uuid-1234",
      "changes": {
        "content": "Updated explanation of Newton's Second Law..."
      }
    },
    {
      "operation": "DELETE",
      "chapter_id": "uuid-9999"
    }
  ]
}
```

### 3.4 Upload Student Progress

**Client → Server** (daily or when online):

```http
POST /api/v1/sync/upload/progress
Headers:
  Authorization: Bearer <jwt_token>

Body:
{
  "student_id": "uuid-1234",
  "progress_data": {
    "chapters_completed": ["uuid-5678", "uuid-7890"],
    "questions_answered": 45,
    "correct_answers": 38,
    "study_time_minutes": 120,
    "last_active": "2025-11-13T10:30:00Z",
    "subjects_studied": {
      "Physics": 60,
      "Math": 60
    }
  },
  "sync_timestamp": "2025-11-13T12:00:00Z"
}
```

**Server → Client**:

```json
{
  "success": true,
  "progress_saved": true,
  "server_timestamp": "2025-11-13T12:00:05Z"
}
```

### 3.5 Conflict Resolution

**Strategy**: **Last Write Wins (LWW)** with server timestamp

**Why**:
- Student progress is append-only (new chapters completed, new questions answered)
- No conflicting updates (student can't "uncomplete" a chapter)
- Server timestamp is source of truth

**Edge case**: Student uses app on multiple devices

```python
# Server-side conflict resolution
def save_progress(student_id, progress_data, client_timestamp):
    # Get existing progress
    existing = cassandra.execute(
        "SELECT * FROM student_progress WHERE student_id = ?",
        [student_id]
    )

    # Merge: Union of completed chapters, sum of metrics
    merged_chapters = set(existing.chapters_completed) | set(progress_data.chapters_completed)
    merged_questions = existing.questions_answered + progress_data.questions_answered
    merged_study_time = existing.study_time_minutes + progress_data.study_time_minutes

    # Save merged progress with server timestamp
    cassandra.execute("""
        INSERT INTO student_progress (student_id, chapters_completed, questions_answered, study_time_minutes, last_updated)
        VALUES (?, ?, ?, ?, toTimestamp(now()))
    """, [student_id, merged_chapters, merged_questions, merged_study_time])

    return {"success": True}
```

---

## Part 4: Performance Analysis

### 4.1 Load Calculation (10,000 users)

**Assumptions**:
- 10,000 active users
- Sync frequency: Every 12 hours (2x/day)
- Sync duration: 5 minutes
- Users distributed evenly

**Requests per day**:
```
10,000 users × 2 syncs/day = 20,000 syncs/day
20,000 syncs/day ÷ 86,400 seconds = 0.23 requests/second average
```

**Peak load** (if 10% sync simultaneously):
```
1,000 users syncing over 5 minutes
1,000 users ÷ 300 seconds = 3.3 requests/second
```

**Server capacity needed**:
- **Sync API server**: 1 server handles 100+ req/sec easily
- **Cassandra**: 3-node cluster handles 10K+ reads/sec

**Verdict**: **Massively over-provisioned** - we can handle 100K users with this architecture!

### 4.2 Bandwidth Calculation

**Content download** (per user, per sync):
- Textbook updates: 5MB (if new chapter added)
- Embedding updates: 10MB (500 embeddings × 768 dims × 4 bytes = 1.5MB, compressed to ~10MB)
- Graph updates: 1MB
- **Total**: ~16MB per sync (worst case, if all content updated)

**Progress upload** (per user, per sync):
- JSON payload: ~10KB

**Total bandwidth** (worst case, all users sync in 1 day):
```
Download: 10,000 users × 16MB = 160GB/day
Upload: 10,000 users × 10KB = 100MB/day
Total: ~160GB/day = 6.7GB/hour = 1.8MB/sec average
```

**OVHcloud Jakarta**: 1 Gbit/s = 125 MB/sec

**Verdict**: Uses only **1.4% of available bandwidth** - plenty of headroom!

### 4.3 Storage Growth

**Per user storage**:
- Textbooks: 200MB (all subjects, all grades)
- Embeddings: 500MB (15K chunks × 768 dims × 4 bytes = 46MB per subject × 4 subjects = 184MB)
- Knowledge graph: 50MB (JSON relationships)
- **Total**: ~750MB per user (local CozoDB)

**Cassandra storage** (3-node cluster, RF=3):
- Textbooks: 2GB (shared across all users)
- Embeddings: 5GB (shared)
- Knowledge graph: 1GB (shared)
- Student progress: 10K users × 1MB = 10GB
- **Total**: ~18GB × 3 replicas = 54GB

**OVHcloud Jakarta**: 1TB per server × 3 = 3TB total

**Verdict**: Uses only **1.8% of available storage** - can scale to 500K users!

---

## Part 5: Kafka-Based Sync (Advanced, Not Needed Now)

### When to Use Kafka

**Upgrade to Kafka when**:
- Users > 100,000
- Need real-time push (<1 second latency)
- Want event-driven architecture (trigger actions on content changes)
- Need stream processing (analytics on sync events)

### Kafka + Cassandra CDC Architecture

```
┌─────────────────────────────────────────────┐
│  Admin adds new textbook chapter            │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  Cassandra 5.0 with CDC enabled             │
│  INSERT INTO textbooks (...)                │
└──────────────┬──────────────────────────────┘
               │
               │ Cassandra CDC
               │ (Change Data Capture)
               ▼
┌─────────────────────────────────────────────┐
│  Apache Kafka Topic: "textbook-updates"     │
│  Event: {chapter_id, operation: "INSERT"}   │
└──────────────┬──────────────────────────────┘
               │
               │ Kafka Consumer
               ▼
┌─────────────────────────────────────────────┐
│  Push Notification Service                  │
│  → Send to 10,000 devices via FCM/APNs      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  Mobile/Desktop receives push:              │
│  "New Physics chapter available!"           │
│  → Trigger background sync                  │
└─────────────────────────────────────────────┘
```

### Cost Comparison

**Simple REST API** (10K users):
- Sync API server: $100/month (DigitalOcean)
- Cassandra: $270/month (OVHcloud 3× bare metal)
- **Total**: $370/month = $4,440/year

**Kafka + CDC** (10K users):
- Kafka cluster: $300/month (3 nodes)
- Sync API server: $100/month
- Cassandra with CDC: $270/month
- Push notification service: $50/month
- **Total**: $720/month = $8,640/year

**Verdict**: Kafka costs **2x more** for no benefit at 10K users!

---

## Part 6: FreeBSD vs Ubuntu Decision

### Research Findings

#### Apache Kafka on FreeBSD

**Availability**: ✅ Available as `net/kafka` port (v3.5.0)

**Stability**: ❌ **NOT RECOMMENDED**
- Known issues with FreeBSD + ZFS + Kafka
- Open JIRA issue: KAFKA-6679
- Developers recommend "stay far away from Kafka on FreeBSD"
- Primarily tested on Linux

**Verdict**: **Don't run Kafka on FreeBSD in production**

#### Cassandra 5.0 on FreeBSD

**Port availability**: ❌ Only `cassandra4` port (v4.0.8)
- Cassandra 5.0 not yet in FreeBSD ports tree
- Would need to build from source

**Building from source**:
- ✅ Requires Java 17 (available on FreeBSD)
- ✅ Build with Ant: `ant build`
- ⚠️ No FreeBSD-specific documentation
- ⚠️ Known JVM compatibility issues (historical)
- ⚠️ Not officially tested/supported

**Verdict**: **Risky** - possible but unsupported

#### Cassandra 4.x on FreeBSD

**Port availability**: ✅ `cassandra4` port (v4.0.8) stable

**What you lose**:
- ❌ No native vector search (must use external plugin)
- ❌ No Cassandra 5.0 improvements (UCS, SAI, etc.)
- ❌ Accord ACID transactions (not in 5.0 either, but coming)

**What you keep**:
- ✅ Stable, tested on FreeBSD
- ✅ Proven reliability
- ✅ Easy install: `pkg install cassandra4`
- ✅ Wide column store (can store vectors as BLOBs)
- ✅ Horizontal scalability

**Verdict**: **Works, but limited** - acceptable compromise for FreeBSD

### Recommendation: Three Options

#### Option A: Cassandra 4.x on FreeBSD (Pragmatic)

**Pros**:
- ✅ Stay on FreeBSD (preferred OS)
- ✅ Stable port (v4.0.8)
- ✅ Simple install
- ✅ Horizontal scalability
- ✅ Can use jails, ZFS, pf firewall

**Cons**:
- ❌ No native vector search
- ❌ Must store vectors as BLOBs
- ❌ Manual vector similarity search (slower)

**Workaround for vectors**:
```cql
-- Store embeddings as BLOB
CREATE TABLE embeddings (
    embedding_id UUID PRIMARY KEY,
    chapter_id UUID,
    chunk_text TEXT,
    embedding BLOB  -- 768 floats × 4 bytes = 3072 bytes
);

-- Vector search must happen in application layer
-- (fetch candidates, compute cosine similarity in Python)
```

**When to choose**: You strongly prefer FreeBSD and can accept slower vector search

---

#### Option B: Build Cassandra 5.0 from Source on FreeBSD (Experimental)

**Steps**:

```bash
# Install Java 17
pkg install openjdk17

# Set JAVA_HOME
export JAVA_HOME=/usr/local/openjdk17

# Clone Cassandra 5.0
git clone https://github.com/apache/cassandra.git
cd cassandra
git checkout cassandra-5.0

# Build with Ant
ant build

# Run Cassandra
bin/cassandra -f
```

**Pros**:
- ✅ Native vector search
- ✅ Stay on FreeBSD
- ✅ Latest features

**Cons**:
- ❌ Unsupported configuration
- ❌ Potential JVM issues
- ❌ No official FreeBSD testing
- ❌ Must maintain custom build
- ❌ Upgrade path unclear

**When to choose**: You're willing to take risks and maintain custom builds

---

#### Option C: Ubuntu 24.04 with Cassandra 5.0 (Recommended)

**Pros**:
- ✅ Native vector search (critical!)
- ✅ Official support
- ✅ Easy install (apt/binary)
- ✅ Well-tested configuration
- ✅ Can use LXC containers (similar to jails)
- ✅ ZFS on Linux (works great)

**Cons**:
- ❌ Must leave FreeBSD
- ❌ Learn Ubuntu operations

**Migration effort**: 2-3 weeks
- Setup Ubuntu servers
- Install Cassandra 5.0
- Configure LXC containers
- Migrate data from dev PostgreSQL

**When to choose**: You want production-ready, supported setup

---

### My Recommendation

**Use Option C: Ubuntu 24.04 + Cassandra 5.0**

**Rationale**:
1. **Native vector search is critical** - 10-100x faster than manual search
2. **Official support matters** - less risk, easier troubleshooting
3. **Ubuntu is proven** - Cassandra runs on Ubuntu at Netflix, Apple, Instagram
4. **LXC containers ≈ jails** - similar isolation
5. **Future-proof** - easier to adopt new Cassandra features (Accord, etc.)

**Compromise**: If FreeBSD is non-negotiable, use **Option A (Cassandra 4.x)** and accept slower vector search. Migrate to Ubuntu when vector search becomes a bottleneck.

---

## Part 7: Implementation Roadmap

### Phase 0: POC (Months 1-2)

**Database**: PostgreSQL on FreeBSD
- Simple, fast to prototype
- Focus on product, not infrastructure

**Sync**: Hardcoded content, no sync yet
- Local CozoDB only
- Test with 10-50 users

---

### Phase 1: MVP (Months 3-5)

**Database**: Migrate to Cassandra
- **If FreeBSD**: Use Cassandra 4.x from ports
- **If Ubuntu**: Use Cassandra 5.0 (recommended)

**Sync**: Implement simple REST API
```python
# sync_api.py
from fastapi import FastAPI
from cassandra.cluster import Cluster

app = FastAPI()
cluster = Cluster(['cassandra1', 'cassandra2', 'cassandra3'])
session = cluster.connect('ai_teacher')

@app.get("/api/v1/sync/check")
async def check_updates(current_versions: dict):
    # Check Cassandra for new versions
    server_versions = session.execute(
        "SELECT content_type, version FROM sync_metadata"
    )

    updates = {}
    for row in server_versions:
        if row.version > current_versions.get(row.content_type, 0):
            updates[row.content_type] = row.version

    return {"updates_available": len(updates) > 0, "new_versions": updates}

@app.get("/api/v1/sync/download/{content_type}")
async def download_content(content_type: str, from_version: int):
    # Fetch changes from Cassandra
    changes = session.execute("""
        SELECT * FROM content_changes
        WHERE content_type = ? AND version > ?
    """, [content_type, from_version])

    return {"changes": list(changes)}

@app.post("/api/v1/sync/upload/progress")
async def upload_progress(student_id: str, progress_data: dict):
    # Save to Cassandra
    session.execute("""
        INSERT INTO student_progress (student_id, chapters_completed, questions_answered, study_time_minutes)
        VALUES (?, ?, ?, ?)
    """, [student_id, progress_data["chapters_completed"], ...])

    return {"success": True}
```

**Deploy**: 1 sync API server (DigitalOcean $100/month or bare metal)

---

### Phase 2: Beta (Months 6-8)

**Scale**: Test with 500 users

**Monitor**:
- Sync frequency (how often do users sync?)
- Download sizes (how much data per sync?)
- API latency (is REST API fast enough?)
- Cassandra load (CPU, disk I/O)

**Optimize**:
- Add caching (Redis) if needed
- Compress sync payloads (gzip)
- Batch content updates (daily digest)

---

### Phase 3: Production (Month 9+)

**Scale**: 10,000 users

**Infrastructure**:
- 3× Cassandra nodes (bare metal)
- 2× Sync API servers (load balanced)
- 1× Redis cache (optional)

**Monitoring**:
- Prometheus + Grafana
- Alert on sync failures
- Track sync latency p95/p99

---

### Phase 4: Scale (100K+ users)

**When REST API becomes bottleneck**, migrate to Kafka:

1. Enable Cassandra CDC
2. Deploy Kafka cluster (3 brokers)
3. Stream changes to Kafka topics
4. Implement push notifications (FCM/APNs)
5. Clients subscribe to updates

**Cost**: ~$8,640/year (2x current cost)

**Benefit**: Real-time push, sub-second latency

---

## Summary

### Key Decisions

1. **Sync Strategy**: **Simple REST API** (pull-based)
   - No Kafka needed for 10K users
   - Kafka at 100K+ users or when real-time push required

2. **Sync Frequency**: **Every 6-24 hours** (client-controlled)
   - Background sync when on WiFi
   - User can manually trigger sync

3. **Conflict Resolution**: **Last Write Wins** with server timestamp
   - Student progress is append-only (no conflicts)
   - Multiple devices: merge progress (union of completed chapters)

4. **FreeBSD vs Ubuntu**:
   - **Recommended**: **Ubuntu 24.04 + Cassandra 5.0** (native vector search)
   - **Acceptable**: FreeBSD + Cassandra 4.x (if FreeBSD non-negotiable)
   - **Not recommended**: Build Cassandra 5.0 from source on FreeBSD (unsupported)

5. **Kafka**: **NOT NOW**
   - Overkill for 10K users
   - Add at 100K+ users
   - FreeBSD Kafka has stability issues (use Ubuntu if deploying Kafka)

### Cost Summary (10,000 users)

**Simple REST API Sync**:
```
Cassandra (3 nodes): $3,240/year
Sync API server: $1,200/year
Monitoring: $240/year
Total: $4,680/year
```

**Kafka-based Sync** (not needed):
```
Cassandra: $3,240/year
Kafka (3 brokers): $3,600/year
Sync API server: $1,200/year
Push service: $600/year
Total: $8,640/year (85% more expensive!)
```

**Verdict**: Start with REST API, migrate to Kafka at 100K+ users

---

## Next Steps

**This Week**:
- [ ] Decide: FreeBSD (Cassandra 4.x) or Ubuntu (Cassandra 5.0)?
- [ ] Setup Cassandra cluster (3 nodes)
- [ ] Create sync_metadata table

**Month 3** (MVP):
- [ ] Implement sync REST API (FastAPI)
- [ ] Create sync_state table in local CozoDB
- [ ] Test sync with 10 beta users

**Month 9** (Production):
- [ ] Deploy production Cassandra cluster
- [ ] Load test sync API (simulate 10K users)
- [ ] Monitor sync performance

**Month 12+** (Scale):
- [ ] If approaching 100K users, research Kafka migration
- [ ] If vector search slow on Cassandra 4.x, migrate to Ubuntu + Cassandra 5.0

---

**Status**: ✅ SYNC STRATEGY COMPLETE

**Recommendation**: Start with simple REST API, NO Kafka for 10K users

**FreeBSD Decision**: Your call - I recommend Ubuntu for native vector search
