# TiKV Cloud Provider Analysis & LEAP Licensing Update

**Date:** November 2025
**Status:** CRITICAL EVALUATION - Managed TiKV vs Bare Metal
**Context:** User inquiry about TiDB Cloud pricing and LEAP licensing clarification

---

## Executive Summary

### LEAP Licensing - EXCELLENT NEWS! ✅

**Liquid AI LEAP is FREE until $10M annual revenue!**

This means we can use LFM2 + LEAP SDK without licensing costs for approximately **3-4 years**:

```
Year 1: ~10K users × $77.4/user/year = $774K revenue
Year 2: ~50K users × $77.4/user/year = $3.87M revenue
Year 3: ~100K users × $77.4/user/year = $7.74M revenue
Year 4: ~130K users = $10M revenue (licensing kicks in)
```

**Impact**: LEAP is approved for production use with zero licensing concerns until we hit 130,000 users!

---

## TiKV Cloud Providers

### Option 1: TiDB Cloud Starter (Serverless) ❌ NOT AVAILABLE IN JAKARTA

**The Problem**: TiDB Cloud Starter only available in 5 AWS regions:
- Oregon (us-west-2)
- Virginia (us-east-1)
- Tokyo (ap-northeast-1)
- **Singapore (ap-southeast-1)** ← Closest to Indonesia
- Frankfurt (eu-central-1)

**Jakarta NOT supported** for serverless tier.

**Free Tier** (per organization):
- 250M Request Units (RUs) per month
- 25GB row storage
- 25GB column storage

**Limitations for Our Use Case**:
- ❌ Not in Jakarta (latency to Singapore: 20-40ms)
- ❌ CozoDB cannot use TiDB Cloud Starter (SQL-only interface)
- ❌ Would need TiKV direct access (not available in Starter tier)

**Verdict**: Cannot use TiDB Cloud Starter - no raw TiKV access for CozoDB.

---

### Option 2: TiDB Cloud Dedicated ✅ Available in Jakarta

**What it is**: Traditional node-based pricing with full TiKV cluster management

**Available Regions**: Jakarta (ap-southeast-3) on AWS ✅

**Pricing** (AWS Jakarta region, estimated):

#### Compute Costs

**TiKV Nodes** (recommended: 8 vCPU, 64GB RAM):
- **$1.37 per hour per node**
- 3 nodes minimum for HA: $1.37 × 3 = **$4.11/hour**
- **Monthly**: $4.11 × 730 hours = **$3,000/month**
- **Annual**: **$36,000/year**

**PD Nodes** (lightweight, 2 vCPU, 8GB RAM):
- **~$0.25 per hour per node** (estimated)
- 3 nodes minimum: $0.25 × 3 = **$0.75/hour**
- **Monthly**: $0.75 × 730 = **$548/month**
- **Annual**: **$6,576/year**

#### Storage Costs

**TiKV Standard Storage**:
- **$0.000196 per GiB per hour**
- For 500GB: 500 × $0.000196 × 730 = **$71.54/month**
- **Annual**: **$858/year**

#### Total TiDB Cloud Dedicated Cost

```
Compute (TiKV): $36,000/year
Compute (PD): $6,576/year
Storage (500GB): $858/year
Data transfer: ~$600/year

Total: $44,034/year
```

**What You Get**:
- ✅ Fully managed TiKV cluster
- ✅ Automatic backups
- ✅ Monitoring & alerts
- ✅ High availability (3-node)
- ✅ Security patches
- ✅ 24/7 PingCAP support

**What You Don't Get**:
- ❌ Direct TiKV access for CozoDB (SQL interface only)
- ❌ Cannot connect CozoDB directly to TiDB Cloud

---

### Option 3: Self-Hosted TiKV on Cloud VPS

**Strategy**: Deploy TiKV ourselves on cloud VPS (DigitalOcean, Vultr, etc.)

**DigitalOcean Singapore** (closest to Indonesia):

**3× TiKV nodes** (CPU-Optimized 8 vCPU, 16GB RAM):
- $168/month × 3 = **$504/month**
- **Annual**: **$6,048/year**

**3× PD nodes** (General Purpose 2 vCPU, 4GB RAM):
- $42/month × 3 = **$126/month**
- **Annual**: **$1,512/year**

**Block Storage** (500GB):
- $50/month × 3 = **$150/month**
- **Annual**: **$1,800/year**

**Total**: **$9,360/year** + DevOps time

**Pros**:
- ✅ 79% cheaper than TiDB Cloud Dedicated ($9,360 vs $44,034)
- ✅ Full TiKV access for CozoDB
- ✅ Flexible configuration

**Cons**:
- ❌ Manual cluster management
- ❌ Need TiKV expertise
- ❌ Self-managed backups
- ❌ No official support (community only)

---

### Option 4: Bare Metal (OVHcloud Jakarta) - ORIGINAL PLAN

**3× Ryzen 5 7600X servers**:
- $90/month × 3 = **$270/month**
- **Annual**: **$3,240/year**

**Total**: **$3,240/year** + DevOps time

**Pros**:
- ✅ 93% cheaper than TiDB Cloud Dedicated
- ✅ 65% cheaper than cloud VPS
- ✅ Full control
- ✅ Better specs (6 cores, 64GB RAM vs 8 vCPU, 16GB)
- ✅ Local Jakarta latency

**Cons**:
- ❌ Manual everything
- ❌ Need DevOps expertise
- ❌ Physical hardware dependency

---

## CRITICAL ISSUE: CozoDB + Remote TiKV Performance

### The Problem

**From CozoDB documentation**:

> "The TiKV storage backend... is **orders of magnitude slower** than every other engine for graph traversals, due to the **significant network overhead**."

**What this means**:
- Local CozoDB (SQLite/RocksDB): **<50ms** graph queries
- Remote CozoDB (TiKV over network): **500-2000ms** graph queries (!!)

### Why This Happens

**Graph traversals require many round-trips**:

```
Example: Find prerequisites for "Hukum Newton 2"

Local (RocksDB):
  1. Lookup "Hukum Newton 2" node (5ms)
  2. Traverse edges to prerequisites (10ms)
  3. Fetch prerequisite nodes (15ms)
  Total: ~30ms, 1 local disk operation

Remote (TiKV cloud):
  1. Lookup "Hukum Newton 2" node (50ms network RTT)
  2. Traverse edges to prerequisites (50ms network RTT)
  3. Fetch prerequisite nodes (50ms network RTT)
  Total: ~150ms for simple query

Complex queries (3-hop traversal):
  - 5+ network round trips
  - Total: 500-1000ms (!!)
```

### The Dilemma

**If we use cloud TiKV**:
- ✅ No server management
- ❌ Graph queries are 10-30x slower (unacceptable UX!)

**If we use bare metal**:
- ✅ Fast local graph queries
- ❌ Must manage servers ourselves

---

## Recommended Architecture: Hybrid Approach

### Strategy: Local CozoDB + Periodic Sync

**Don't use remote TiKV for real-time queries!**

Instead:

```
┌─────────────────────────────────────────────┐
│         Mobile/Desktop Devices              │
│                                             │
│  CozoDB (SQLite/RocksDB) - LOCAL            │
│  - Instant graph queries (<50ms)            │
│  - Full offline capability                  │
│  - Periodic sync to server                  │
└──────────────────┬──────────────────────────┘
                   │
                   │ Sync every 6-24 hours
                   │ Upload: Student progress
                   │ Download: New content
                   │
┌──────────────────▼──────────────────────────┐
│         Central Server (Ubuntu)             │
│                                             │
│  CozoDB (TiKV backend) - AUTHORITATIVE      │
│  - Content authoring                        │
│  - Student analytics                        │
│  - Curriculum updates                       │
│  - NOT used for real-time queries           │
└─────────────────────────────────────────────┘
```

### Benefits

1. **Fast queries**: All student-facing queries are local (<50ms)
2. **Offline-first**: Students can study without internet
3. **Scalable**: Central TiKV stores all data, but not queried directly
4. **Cost-effective**: Can use smaller TiKV cluster (not for real-time load)

### Updated Use Cases

**Local CozoDB (SQLite/RocksDB)**:
- ✅ Student queries (real-time, <50ms)
- ✅ Graph traversals (prerequisites, related topics)
- ✅ Vector similarity search (textbook content)
- ✅ Student progress tracking

**Remote TiKV Cluster**:
- ✅ Content authoring (teachers add new material)
- ✅ Curriculum updates (push to all students)
- ✅ Analytics (aggregate student performance)
- ✅ Backup & disaster recovery
- ❌ NOT for real-time student queries

---

## Cost Comparison (10,000 Users)

### Option A: TiDB Cloud Dedicated (Jakarta)

```
TiKV compute: $36,000/year
PD compute: $6,576/year
Storage: $858/year
Support: INCLUDED

Total: $44,034/year
```

**Problems**:
- ❌ Cannot connect CozoDB directly (SQL interface only)
- ❌ Would need to use TiDB SQL, rewrite all Datalog queries
- ❌ Loses CozoDB benefits (unified vector+graph)

**Verdict**: NOT COMPATIBLE with our architecture

---

### Option B: Cloud VPS (DigitalOcean Singapore) + TiKV

```
Infrastructure: $9,360/year
DevOps (15 hrs/month × $50): $9,000/year
Monitoring: $240/year
Backups: $600/year

Total: $19,200/year
```

**Network Latency**:
- Jakarta → Singapore: 20-40ms
- Student devices never query TiKV directly (local CozoDB)
- Only sync traffic (acceptable latency)

**Pros**:
- ✅ 56% cheaper than TiDB Cloud Dedicated
- ✅ Full CozoDB compatibility
- ✅ Managed compute (DigitalOcean handles hardware)

**Cons**:
- ❌ Manual TiKV cluster management
- ❌ Requires DevOps expertise

---

### Option C: Bare Metal (OVHcloud Jakarta) + TiKV

```
Infrastructure: $3,240/year
DevOps (15 hrs/month × $50): $9,000/year
Monitoring: $240/year
Backups: $600/year

Total: $13,080/year
```

**Network Latency**:
- Local Jakarta (0-5ms between servers)
- Students never query TiKV directly (local CozoDB)

**Pros**:
- ✅ 70% cheaper than TiDB Cloud Dedicated
- ✅ 32% cheaper than cloud VPS
- ✅ Full CozoDB compatibility
- ✅ Local Jakarta (best latency)
- ✅ Better hardware specs

**Cons**:
- ❌ Manual everything
- ❌ Physical hardware dependency

---

### Option D: REVISED - Skip TiKV Entirely (For Now)

**Radical simplification for first 10K users**:

```
Mobile/Desktop: CozoDB (SQLite) - LOCAL

Sync Server: PostgreSQL + pgvector
  - Stores: textbook content, student progress
  - Vector search: pgvector extension
  - Simple, proven, cheap
  - Cost: $100/month DigitalOcean = $1,200/year
```

**Rationale**:
1. TiKV is overkill for 10K users
2. PostgreSQL handles 10K users easily
3. Graph queries happen locally (CozoDB SQLite)
4. Only sync data needs centralization
5. Migrate to TiKV when we hit 50K+ users

**Cost**:
```
PostgreSQL VPS: $1,200/year
DevOps (5 hrs/month × $50): $3,000/year
Monitoring: $240/year
Backups: $300/year

Total: $4,740/year
```

**Savings**: $39,294/year vs TiDB Cloud Dedicated (89% cheaper!)

---

## Final Recommendation

### Phase 0-2 (Months 1-8, <500 users): Development

**Architecture**:
- Local: CozoDB (SQLite) on Ubuntu
- Sync: Simple PostgreSQL
- Cost: **~$1,200/year**

**Why**: Focus on product, not infrastructure

---

### Phase 3-4 (Months 9-18, 500-10K users): Production Launch

**Architecture**:
- Local: CozoDB (SQLite) on mobile/desktop
- Sync: PostgreSQL + pgvector on DigitalOcean
- Cost: **~$4,740/year**

**Why**:
- PostgreSQL handles 10K users easily
- 89% cheaper than TiDB Cloud
- Simple operations (proven tech)
- Fast iteration

---

### Phase 5 (Month 19+, 10K-100K users): Scale to TiKV

**When to migrate**:
- PostgreSQL struggles (>50K users)
- Need multi-region (Jakarta + Singapore)
- Analytics queries slow down

**Architecture**:
- Local: CozoDB (SQLite) on mobile/desktop
- Sync: CozoDB (TiKV backend) on bare metal
- Cost: **~$13,080/year**

**Why**:
- Bare metal 70% cheaper than TiDB Cloud
- Full CozoDB compatibility
- Scales to 200K+ users

---

## Updated Cost Summary

| Phase | Users | Database | Annual Cost | Per User |
|-------|-------|----------|-------------|----------|
| **POC** | <500 | PostgreSQL (DO) | $1,200 | $2.40 |
| **Launch** | 10K | PostgreSQL (DO) | $4,740 | $0.47 |
| **Scale** | 50K | TiKV bare metal | $13,080 | $0.26 |
| **Enterprise** | 200K | TiKV bare metal | $18,000 | $0.09 |

**Previous (TiDB Cloud Dedicated)**: $44,034/year for 10K users = $4.40/user

**New (PostgreSQL → TiKV)**: $4,740/year for 10K users = $0.47/user

**Savings**: **$39,294/year (89% cheaper!)**

---

## Why This Works

### The Key Insight

**Students never query the central database directly!**

All queries happen on local CozoDB:
- "Jelaskan hukum Newton kedua" → Local graph + vector search
- "Apa itu fotosintesis?" → Local textbook content
- "Lihat progress saya" → Local student data

**Central database only for**:
- Syncing new content (daily/weekly)
- Uploading student progress (daily)
- Analytics queries (not time-sensitive)
- Backup & disaster recovery

### Performance Characteristics

**User-facing queries** (local CozoDB):
- Graph traversal: 10-50ms
- Vector search: 30-80ms
- Total latency: <100ms ✅

**Background sync** (PostgreSQL/TiKV):
- Frequency: Every 6-24 hours
- Latency: 200-1000ms (acceptable, not user-facing)
- Bandwidth: ~5MB/device/day

### Scalability Path

**Phase 3-4 (10K users)**:
- PostgreSQL on DigitalOcean
- Cost: $4,740/year
- Operations: Simple (managed)

**Phase 5 (50K+ users)**:
- Migrate to TiKV bare metal
- Cost: $13,080/year
- Operations: Medium (need TiKV expert)

**Migration effort**: 2-3 weeks (data export/import)

---

## Action Items

### Immediate (This Week)

- [x] ✅ Confirm LEAP free until $10M revenue
- [ ] Test PostgreSQL + pgvector with 15K document embeddings
- [ ] Prototype CozoDB (SQLite) sync to PostgreSQL
- [ ] Benchmark local CozoDB graph query performance

### Month 1 (POC)

- [ ] Deploy PostgreSQL on DigitalOcean ($12/month)
- [ ] Implement sync protocol (CozoDB → PostgreSQL)
- [ ] Test with 100 beta users
- [ ] Measure sync bandwidth and frequency

### Month 9 (Production)

- [ ] Launch with PostgreSQL backend
- [ ] Monitor performance and capacity
- [ ] Plan TiKV migration (if needed at 50K users)

### Month 19 (Scale to TiKV)

- [ ] Order OVHcloud Jakarta bare metal servers
- [ ] Deploy TiKV cluster (Ubuntu 24.04)
- [ ] Migrate from PostgreSQL to TiKV
- [ ] Test with 50K+ users

---

## Summary

### Key Decisions

1. **LEAP Licensing**: ✅ FREE until $10M revenue (~130K users)

2. **TiDB Cloud**: ❌ NOT RECOMMENDED
   - $44,034/year for 10K users
   - Cannot connect CozoDB directly
   - Would need to rewrite all queries to SQL

3. **Cloud TiKV**: ❌ NOT RECOMMENDED for real-time queries
   - Graph queries are 10-30x slower over network
   - Acceptable only for background sync

4. **Recommended Path**:
   - **Now-10K users**: PostgreSQL + pgvector ($4,740/year)
   - **50K+ users**: TiKV bare metal ($13,080/year)
   - **Never**: TiDB Cloud Dedicated (too expensive, incompatible)

### Cost Savings

| Solution | Annual Cost | Savings vs TiDB Cloud |
|----------|-------------|----------------------|
| **PostgreSQL (Launch)** | $4,740 | **$39,294 (89%)** |
| **TiKV Bare Metal (Scale)** | $13,080 | **$30,954 (70%)** |
| TiKV Cloud VPS | $19,200 | $24,834 (56%) |
| TiDB Cloud Dedicated | $44,034 | Baseline |

### The Winning Architecture

```
Mobile/Desktop:
  CozoDB (SQLite) - Local, fast (<50ms queries)
    ↓
  Sync every 6-24 hours
    ↓
Central Server:
  PostgreSQL (0-10K users) → TiKV (50K+ users)
  - Content distribution
  - Student progress aggregation
  - Analytics
```

**Why it works**:
- ✅ Fast (local queries)
- ✅ Cheap (simple PostgreSQL for most users)
- ✅ Scalable (migrate to TiKV when needed)
- ✅ Offline-first (students can study without internet)

---

**Status**: ✅ RECOMMENDATION COMPLETE

**Next Decision**: Approve PostgreSQL-first approach for launch?
