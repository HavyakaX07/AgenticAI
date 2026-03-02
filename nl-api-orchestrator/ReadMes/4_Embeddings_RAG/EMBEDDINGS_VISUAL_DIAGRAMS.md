# Embeddings & RAG - Visual Diagrams

## Complete Visual Guide to Embeddings, Vector Search & RAG

---

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NMS API ORCHESTRATOR SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐             │
│  │   User NL    │      │     RAG      │      │     LLM      │             │
│  │    Query     │ ───► │  Embedding   │ ───► │  Parameter   │             │
│  │              │      │  & Search    │      │  Extraction  │             │
│  └──────────────┘      └──────────────┘      └──────────────┘             │
│         │                      │                      │                     │
│         │                      │                      │                     │
│         ▼                      ▼                      ▼                     │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │              MCP Embed Server (Port 9001)                 │              │
│  │  • Model: BAAI/bge-small-en-v1.5 (ONNX)                  │              │
│  │  • FAISS Index: 13 capability vectors                    │              │
│  │  • Endpoints: /embed, /search, /health                   │              │
│  └──────────────────────────────────────────────────────────┘              │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │           Ollama LLM (Host: llama3.2:3b)                  │              │
│  │  • Runs on host machine (not Docker)                     │              │
│  │  • Extracts structured parameters                        │              │
│  └──────────────────────────────────────────────────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Embedding Generation Process

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TEXT → EMBEDDING TRANSFORMATION                          │
└─────────────────────────────────────────────────────────────────────────────┘

INPUT TEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Copy CLI credentials from scalance to ruggedcom"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: TOKENIZATION                                                        │
│ ─────────────────────────────────────────────────────────────────────────── │
│ Words → Token IDs                                                           │
│                                                                             │
│ "Copy"         → 2500                                                       │
│ "CLI"          → 8923                                                       │
│ "credentials"  → 5401                                                       │
│ "from"         → 1996                                                       │
│ "scalance"     → 23401                                                      │
│ "to"           → 2000                                                       │
│ "ruggedcom"    → 24500                                                      │
│                                                                             │
│ Result: [2500, 8923, 5401, 1996, 23401, 2000, 24500]                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: BERT ENCODER (12 Transformer Layers)                                │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│ Layer 1:  Token Embeddings → Self-Attention → Feed-Forward                 │
│           [7 tokens × 384 dims]                                             │
│           ↓                                                                 │
│ Layer 2:  Contextualized Representations                                    │
│           Each token "sees" other tokens                                    │
│           ↓                                                                 │
│ Layer 3-11: Progressive abstraction                                         │
│           Captures relationships: "from X to Y"                             │
│           ↓                                                                 │
│ Layer 12: Final hidden states                                               │
│           [7 tokens × 384 dims]                                             │
│                                                                             │
│ Example token: "scalance"                                                   │
│   Layer 1:  [0.12, 0.45, ...]  (word meaning)                              │
│   Layer 6:  [0.18, 0.52, ...]  (+ context: "device name")                  │
│   Layer 12: [0.23, 0.61, ...]  (+ full context: "source device")           │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: POOLING (Extract Sentence Representation)                           │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│ Take [CLS] token output (special token representing entire sentence)       │
│                                                                             │
│ [CLS] Layer 12: [0.234, -0.456, 0.789, 0.123, ..., -0.345]                │
│                                                                             │
│ Result: Single 384-dimensional vector                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: L2 NORMALIZATION                                                    │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│ Before: [0.234, -0.456, 0.789, ..., -0.345]                                │
│ Length: √(0.234² + (-0.456)² + ... + (-0.345)²) = 1.234                   │
│                                                                             │
│ Normalize: vector / length                                                  │
│                                                                             │
│ After:  [0.190, -0.369, 0.639, ..., -0.280]                                │
│ Length: 1.0 exactly ✅                                                      │
│                                                                             │
│ Why? Enables cosine similarity via simple dot product!                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
OUTPUT EMBEDDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[0.190, -0.369, 0.639, 0.100, ..., -0.280]  (384 floats, length=1.0)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 3. Text Enrichment Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│          FROM BASIC API NAME TO RICH SEMANTIC REPRESENTATION                │
└─────────────────────────────────────────────────────────────────────────────┘

API: copy_device_credentials
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BEFORE ENRICHMENT (Basic)
┌──────────────────────────────────────────────────────────────────┐
│ "copy_device_credentials: Copy credentials from source to dest" │
│                                                                  │
│ Length: 68 characters                                            │
│ Embedding: Generic, low information density                      │
└──────────────────────────────────────────────────────────────────┘

                            ↓ ENRICHMENT ↓

AFTER ENRICHMENT (3 Data Sources + Synonyms)
┌───────────────────────────────────────────────────────────────────────────┐
│ SOURCE 1: credential_api_schema_rag.json                                  │
│ ───────────────────────────────────────────────────────────────────────── │
│ • API Name: "copy_device_credentials"                                     │
│ • Description: "Copy credentials from one source device to multiple       │
│   destination devices. Supports copying SNMP read, SNMP write, and       │
│   CLI/SSH credentials selectively."                                       │
│ • Examples:                                                               │
│   - "Copy SNMP read credentials from device A to device B"               │
│   - "Copy CLI credentials from 192.168.1.1 to 192.168.1.2"              │
└───────────────────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────────────┐
│ SOURCE 2: credential_api_nlp_metadata.json                                │
│ ───────────────────────────────────────────────────────────────────────── │
│ • Primary Keywords: "copy", "replicate", "duplicate"                      │
│ • Secondary Keywords: "transfer", "migrate", "sync"                       │
│ • Sample Utterances:                                                      │
│   - "Copy credentials from {source} to {destinations}"                    │
│   - "Replicate auth data from {device_id} to {device_ids}"              │
│ • NLP Training Samples:                                                   │
│   - "copy snmp credentials from one device to another"                   │
│   - "replicate authentication data across devices"                        │
└───────────────────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────────────┐
│ SOURCE 3: credential_api_rag_training_examples.json                       │
│ ───────────────────────────────────────────────────────────────────────── │
│ • Real User Queries:                                                      │
│   - "Copy CLI credentials from scalance to ruggedcom"                    │
│   - "Copy SNMP read community from 172.16.122.190 to 172.16.122.200"   │
│   - "Replicate device authentication from switch A to switch B"          │
└───────────────────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────────────┐
│ CONTEXT ENRICHMENT (Synonyms & Domain Context)                            │
│ ───────────────────────────────────────────────────────────────────────── │
│ • Action Synonyms: "copy", "replicate", "duplicate", "transfer",         │
│   "migrate", "clone", "synchronize"                                       │
│ • Device Synonyms: "switch", "router", "firewall", "device",             │
│   "equipment", "node", "appliance"                                        │
│ • Credential Type Synonyms: "SNMP community", "CLI password",            │
│   "SSH key", "authentication", "credentials", "auth data"                 │
└───────────────────────────────────────────────────────────────────────────┘

                            ↓ FINAL RESULT ↓

ENRICHED TEXT (500+ characters)
┌───────────────────────────────────────────────────────────────────────────┐
│ copy_device_credentials . Copy credentials from one source device to      │
│ multiple destination devices. Supports copying SNMP read, SNMP write,    │
│ and CLI/SSH credentials. Copy SNMP read credentials from device A to     │
│ device B . Copy CLI credentials from 192.168.1.1 to 192.168.1.2 .       │
│ copy replicate duplicate transfer migrate . Copy credentials from        │
│ {source} to {destinations} . Replicate auth data from device-001 to     │
│ device-002 . copy snmp credentials from one device to another .         │
│ replicate authentication data across devices . Copy CLI credentials      │
│ from scalance to ruggedcom . Copy SNMP read community from              │
│ 172.16.122.190 to 172.16.122.200 . network switch router firewall       │
│ device equipment node . SNMP community CLI password SSH key              │
│ authentication credentials auth data                                      │
│                                                                          │
│ Length: 538 characters ✅                                                 │
│ Embedding: Rich, high information density ✅                              │
└───────────────────────────────────────────────────────────────────────────┘
```

**Result**: 8x more text, 10x more semantic information!

---

## 4. FAISS Index Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FAISS IndexFlatIP MEMORY LAYOUT                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│ IndexFlatIP Configuration                                                  │
│ ───────────────────────────────────────────────────────────────────────── │
│ Type:       Flat (no compression, 100% accuracy)                          │
│ Metric:     Inner Product (dot product for cosine similarity)             │
│ Dimension:  384                                                           │
│ Count:      13 vectors                                                    │
│ Memory:     13 × 384 × 4 bytes (float32) = 19,968 bytes ≈ 20 KB          │
└───────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│ Stored Vectors (L2-normalized)                                            │
│ ───────────────────────────────────────────────────────────────────────── │
│                                                                           │
│ Index 0:  copy_device_credentials                                         │
│   Vector: [0.234, -0.456, 0.789, 0.123, ..., -0.345]                     │
│   Length: 1.0 ✅                                                           │
│                                                                           │
│ Index 1:  get_device_detail_credentials                                   │
│   Vector: [0.123, 0.567, -0.234, 0.789, ..., 0.456]                      │
│   Length: 1.0 ✅                                                           │
│                                                                           │
│ Index 2:  set_bulk_device_credentials                                     │
│   Vector: [-0.345, 0.234, 0.567, -0.123, ..., 0.789]                     │
│   Length: 1.0 ✅                                                           │
│                                                                           │
│ ... (10 more vectors)                                                     │
│                                                                           │
│ Index 12: get_https_port                                                  │
│   Vector: [0.567, -0.123, 0.345, 0.234, ..., -0.567]                     │
│   Length: 1.0 ✅                                                           │
└───────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│ Capability ID Mapping                                                      │
│ ───────────────────────────────────────────────────────────────────────── │
│ capability_ids = [                                                        │
│   "copy_device_credentials",          # Index 0                           │
│   "get_device_detail_credentials",    # Index 1                           │
│   "set_bulk_device_credentials",      # Index 2                           │
│   "set_device_credentials",           # Index 3                           │
│   "get_default_device_credentials",   # Index 4                           │
│   "delete_device_credentials",        # Index 5                           │
│   "get_all_device_credentials",       # Index 6                           │
│   "check_role_rights_credentials",    # Index 7                           │
│   "view_decrypted_password",          # Index 8                           │
│   "trust_device_credentials",         # Index 9                           │
│   "untrust_device_credentials",       # Index 10                          │
│   "get_https_certificate",            # Index 11                          │
│   "get_https_port"                    # Index 12                          │
│ ]                                                                         │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Vector Similarity Search Algorithm

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FAISS SEARCH: QUERY → TOP-K RESULTS                      │
└─────────────────────────────────────────────────────────────────────────────┘

USER QUERY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Copy CLI credentials from scalance to ruggedcom"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Embed Query                                                         │
│ ─────────────────────────────────────────────────────────────────────────── │
│ POST /embed                                                                 │
│   Input: "Copy CLI credentials from scalance to ruggedcom"                 │
│   Output: [0.210, -0.430, 0.760, ..., 0.150]  (384 dims)                  │
│   Time: 20ms                                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: L2 Normalize Query Vector                                           │
│ ─────────────────────────────────────────────────────────────────────────── │
│ query_vec = [0.210, -0.430, 0.760, ..., 0.150]                             │
│ length = √(0.210² + (-0.430)² + ... + 0.150²) = 1.234                     │
│                                                                             │
│ normalized = query_vec / length                                             │
│            = [0.170, -0.348, 0.616, ..., 0.122]                            │
│ new_length = 1.0 ✅                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Compute Similarity Scores (Dot Product)                             │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│ For each stored vector v_i in FAISS index:                                  │
│   score_i = dot_product(query_vec, v_i)                                    │
│           = Σ(query_vec[j] × v_i[j])  for j=0 to 383                      │
│                                                                             │
│ Since both are L2-normalized (length=1.0):                                  │
│   score_i = cosine_similarity(query_vec, v_i)                              │
│                                                                             │
│ ───────────────────────────────────────────────────────────────────────────│
│ Index 0 (copy_device_credentials):                                          │
│   vec_0 = [0.234, -0.456, 0.789, ..., -0.345]                              │
│   score_0 = (0.170×0.234) + (-0.348×-0.456) + ... + (0.122×-0.345)        │
│           = 0.0398 + 0.1587 + ... + (-0.0421)                              │
│           = 0.8923 ✅ HIGH SCORE!                                           │
│                                                                             │
│ Index 1 (get_device_detail_credentials):                                    │
│   vec_1 = [0.123, 0.567, -0.234, ..., 0.456]                               │
│   score_1 = 0.6543                                                          │
│                                                                             │
│ Index 2 (set_bulk_device_credentials):                                      │
│   vec_2 = [-0.345, 0.234, 0.567, ..., 0.789]                               │
│   score_2 = 0.5421                                                          │
│                                                                             │
│ ... (compute for all 13 vectors)                                            │
│                                                                             │
│ Index 5 (delete_device_credentials):                                        │
│   vec_5 = [-0.789, 0.123, -0.456, ..., 0.234]                              │
│   score_5 = -0.2341  ← NEGATIVE (opposite direction)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Sort by Score (Descending)                                          │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│ All Scores:                                                                 │
│   Index 0:  0.8923  ← Best match!                                          │
│   Index 1:  0.6543                                                          │
│   Index 2:  0.5421                                                          │
│   Index 3:  0.4567                                                          │
│   Index 4:  0.3421                                                          │
│   Index 5: -0.2341  ← Opposite meaning                                     │
│   ... (rest)                                                                │
│                                                                             │
│ Sorted (descending):                                                        │
│   [0, 1, 2, 3, 4, ...]                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: Return Top-K (K=3)                                                  │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│ Top 3 Indices: [0, 1, 2]                                                    │
│ Top 3 Scores:  [0.8923, 0.6543, 0.5421]                                    │
│                                                                             │
│ Map to Capability IDs:                                                      │
│   capability_ids[0] = "copy_device_credentials"     (score: 0.8923)        │
│   capability_ids[1] = "get_device_detail_credentials" (score: 0.6543)      │
│   capability_ids[2] = "set_bulk_device_credentials" (score: 0.5421)        │
│                                                                             │
│ Time: 10ms                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
SEARCH RESULT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "ids": ["copy_device_credentials", "get_device_detail_credentials", 
          "set_bulk_device_credentials"],
  "scores": [0.8923, 0.6543, 0.5421]
}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 6. Cosine Similarity Visualization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VECTOR SPACE (Simplified to 2D)                          │
└─────────────────────────────────────────────────────────────────────────────┘

    Dimension 2 (Y-axis)
         ▲
         │
    1.0  │                    ● copy_device_credentials
         │                   /│\
         │                  / │ \
         │                 /  │  \
         │                /   │   \
    0.5  │               /    │    \
         │              /     │     \
         │             /      │      \  ● get_device_detail
         │            /       │       \
    0.0  │───────────/────────●────────\────────────────► Dimension 1
         │          /    Query Vector    \              (X-axis)
         │         /                      \
   -0.5  │        /                        \
         │       /                          \
         │      /                            \
   -1.0  │     ● delete_device_credentials    \
         │
        -1.0  -0.5   0.0   0.5   1.0

LEGEND:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
● Query Vector: "Copy CLI credentials"
● copy_device_credentials:   Angle ≈ 30°  → cos(30°) ≈ 0.89  ✅ Very similar
● get_device_detail:         Angle ≈ 50°  → cos(50°) ≈ 0.64  ✅ Somewhat similar
● delete_device_credentials: Angle ≈ 160° → cos(160°) ≈ -0.94 ❌ Opposite!

COSINE SIMILARITY RANGES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 +1.0  ────────  Identical (0° angle)
  0.9  ────────  Very Similar
  0.7  ────────  Similar
  0.5  ────────  Somewhat Similar
  0.0  ────────  Unrelated (90° angle)
 -0.5  ────────  Somewhat Opposite
 -1.0  ────────  Completely Opposite (180° angle)
```

---

## 7. Complete RAG Pipeline Timeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              END-TO-END REQUEST FLOW WITH TIMINGS                           │
└─────────────────────────────────────────────────────────────────────────────┘

Total Time: 287ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

0ms ───────────────────────────────────────────────────────────────────► 287ms
│                                                                            │
├─ 0-1ms ──────► Request Parsing                                             │
│                                                                            │
├─ 1-31ms ─────► RAG: Embedding + Vector Search                              │
│    │                                                                       │
│    ├─ 1-21ms ────► POST /embed (20ms)                                     │
│    │               Query → 384-dim vector                                  │
│    │                                                                       │
│    └─ 21-31ms ───► POST /search (10ms)                                    │
│                    FAISS similarity search                                 │
│                    Result: top-3 APIs with scores                          │
│                                                                            │
├─ 31-151ms ───► LLM: Parameter Extraction (120ms) ← BOTTLENECK             │
│                Ollama llama3.2:3b                                          │
│                Extract: {source, destinations, cli: true}                  │
│                                                                            │
├─ 151-156ms ──► Device Resolution (5ms or <1ms with cache)                 │
│                Lookup device IDs from PostgreSQL/cache                     │
│                                                                            │
├─ 156-171ms ──► OPA Policy Check (15ms)                                    │
│                Verify permissions + risk level                             │
│                                                                            │
├─ 171-256ms ──► MCP API Call (85ms)                                        │
│                POST /copyDeviceCredentials                                 │
│                                                                            │
└─ 256-287ms ──► Response Formatting (31ms)                                 │
                 JSON serialization + logging                                │

BREAKDOWN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Request Parsing:      1ms    (0.3%)
RAG (Embedding+Search): 30ms  (10.5%)  ← Our Focus
LLM Inference:        120ms  (41.8%)  ← Bottleneck
Device Resolution:    5ms    (1.7%)
OPA Policy:           15ms   (5.2%)
MCP API Call:         85ms   (29.6%)
Response Format:      31ms   (10.8%)
────────────────────────────────────────
TOTAL:                287ms  (100%)

KEY INSIGHT: RAG is only 10.5% of total time, highly optimized! 🚀
```

---

## 8. Startup: Index Building Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MCP EMBED SERVER STARTUP SEQUENCE                        │
└─────────────────────────────────────────────────────────────────────────────┘

Container Start (t=0)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Load Embedding Model (500ms)                                        │
│ ─────────────────────────────────────────────────────────────────────────── │
│ model = TextEmbedding("BAAI/bge-small-en-v1.5")                            │
│                                                                             │
│ • Check cache: /app/model_cache/                                            │
│   └─ First run: Download 120 MB ONNX model (1-2 min)                       │
│   └─ Subsequent runs: Load from cache (500ms) ✅                            │
│ • Initialize ONNX Runtime                                                   │
│ • Warm up model (test inference)                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Load Registry Files (50ms)                                          │
│ ─────────────────────────────────────────────────────────────────────────── │
│ capabilities = load_json("credential_api_schema_rag.json")                 │
│   → 13 API definitions                                                      │
│                                                                             │
│ nlp_meta = load_json("credential_api_nlp_metadata.json")                   │
│   → Intent patterns, keywords, sample utterances                            │
│   → Action/device/credential synonyms                                       │
│   → NLP training samples                                                    │
│                                                                             │
│ training_data = load_json("credential_api_rag_training_examples.json")     │
│   → Real user queries per API                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Build Enriched Texts (100ms)                                        │
│ ─────────────────────────────────────────────────────────────────────────── │
│ For each of 13 capabilities:                                                │
│   text = _build_capability_text(                                            │
│     cap,                          # API definition                          │
│     nlp_lookup,                   # Intent patterns                         │
│     training_lookup,              # Real queries                            │
│     nlp_training_lookup,          # NLP samples                             │
│     action_synonyms,              # "copy", "replicate", ...                │
│     device_synonyms,              # "switch", "router", ...                 │
│     cred_type_synonyms            # "SNMP", "CLI", ...                     │
│   )                                                                         │
│                                                                             │
│ Result: 13 texts, avg 500+ chars each                                       │
│ Total: ~7,000 characters                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Generate Embeddings (1000ms)                                        │
│ ─────────────────────────────────────────────────────────────────────────── │
│ embeddings = model.embed(capability_texts)                                  │
│                                                                             │
│ • Batch operation: All 13 texts processed together                          │
│ • ONNX Runtime inference                                                    │
│ • Output: numpy array (13, 384) dtype=float32                              │
│                                                                             │
│ Time breakdown:                                                             │
│   Tokenization:   100ms                                                     │
│   BERT inference: 800ms  (12 layers × 13 texts)                            │
│   Pooling:        100ms                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: Build FAISS Index (50ms)                                            │
│ ─────────────────────────────────────────────────────────────────────────── │
│ dimension = 384                                                             │
│ index = faiss.IndexFlatIP(dimension)                                        │
│                                                                             │
│ faiss.normalize_L2(embeddings)  # L2 normalize for cosine similarity       │
│ index.add(embeddings)            # Add all 13 vectors                       │
│                                                                             │
│ Result:                                                                     │
│   • 13 vectors stored in flat array                                         │
│   • Total memory: 20 KB                                                     │
│   • Ready for search queries                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                ↓
Server Ready (t=1.7 seconds)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOG OUTPUT:
─────────────────────────────────────────────────────────────────────────────
INFO - Loading embedding model via fastembed (ONNX): BAAI/bge-small-en-v1.5
INFO - Model loaded successfully
INFO - Loading registry files …
INFO -   schema_rag       : 13 capabilities
INFO -   nlp_metadata     : 13 intents
INFO -   action_synonyms  : 8 entries
INFO -   nlp_training_lookup : 52 samples
INFO -   training_lookup  : 39 examples
INFO - Generating embeddings for 13 capabilities …
INFO - Building FAISS IndexFlatIP  dim=384
INFO - ✓ FAISS index ready – 13 vectors indexed
```

---

## 9. Memory & Performance Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│           PYTORCH vs ONNX: WHY WE CHOSE FASTEMBED                           │
└─────────────────────────────────────────────────────────────────────────────┘

OPTION 1: sentence-transformers (PyTorch)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌──────────────────────────────────────────────────────────────────────┐
│ Dependencies                                                          │
│ • torch==2.2.0 (187 MB wheel)                                        │
│ • transformers                                                        │
│ • sentence-transformers                                               │
│ Total: ~250 MB                                                        │
└──────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────┐
│ Docker Image Size: ~2 GB                                             │
│ Build Time: 15-20 min (PyTorch compile)                              │
│ Runtime Memory: ~1 GB                                                 │
│ Inference Time: 100ms per query                                      │
└──────────────────────────────────────────────────────────────────────┘

OPTION 2: fastembed (ONNX Runtime) ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌──────────────────────────────────────────────────────────────────────┐
│ Dependencies                                                          │
│ • onnxruntime (50 MB)                                                │
│ • fastembed                                                           │
│ Total: ~70 MB                                                         │
└──────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────┐
│ Docker Image Size: ~600 MB ✅ (3x smaller)                           │
│ Build Time: 2-3 min ✅ (6x faster)                                   │
│ Runtime Memory: ~200 MB ✅ (5x smaller)                              │
│ Inference Time: 80ms per query ✅ (1.25x faster)                     │
└──────────────────────────────────────────────────────────────────────┘

COMPARISON CHART
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Docker Image Size:
PyTorch:  ████████████████████  (2000 MB)
ONNX:     ██████                (600 MB) ✅

Build Time:
PyTorch:  ████████████████████  (15 min)
ONNX:     ███                   (2 min) ✅

Memory Usage:
PyTorch:  ████████████████████  (1000 MB)
ONNX:     ████                  (200 MB) ✅

Inference Speed:
PyTorch:  ████████████████████  (100 ms)
ONNX:     ████████████████      (80 ms) ✅

VERDICT: ONNX wins on ALL metrics! 🏆
```

---

## Summary

✅ **Complete visual reference** for embeddings & RAG system  
✅ **Detailed diagrams** of every step in the pipeline  
✅ **Memory layouts** and data structures explained  
✅ **Performance comparisons** with clear visualizations  
✅ **Timeline breakdowns** showing where time is spent  
✅ **Interview-ready** visual aids for presentations  

**Use these diagrams to explain the system to anyone!** 🎨

