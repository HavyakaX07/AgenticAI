# Embeddings & RAG - Quick Reference

## 🎯 Quick Overview

**System**: NMS API Orchestrator with RAG (Retrieval-Augmented Generation)  
**Model**: BAAI/bge-small-en-v1.5 (384-dimensional embeddings)  
**Vector DB**: FAISS IndexFlatIP (cosine similarity)  
**Performance**: 30ms RAG time, 33 req/sec throughput

---

## 🔑 Key Concepts (30-Second Version)

### What Are Embeddings?
Text → Numbers that capture meaning

```
"Copy credentials" → [0.23, -0.45, 0.78, ..., 0.12]  (384 floats)
```

### What Is RAG?
Retrieval-Augmented Generation = Search + LLM

```
User Query → Find Similar API (RAG) → Extract Parameters (LLM) → Call API
```

### What Is FAISS?
Fast vector similarity search library

```
Query Vector → Compare with 13 stored vectors → Return top-3 matches (< 10ms)
```

### What Is Cosine Similarity?
Measures angle between vectors (range: -1 to +1)

```
Similar vectors → close to 1.0
Opposite vectors → close to -1.0
```

---

## 📊 Architecture Flow

```
┌──────────────────────────────────────────────────────────────┐
│ USER QUERY: "Copy CLI credentials from scalance to ruggedcom"│
└──────────────────────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 1: Embed Query (20ms)                                   │
│ → [0.21, -0.43, 0.76, ..., 0.15]  (384 floats)              │
└──────────────────────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 2: FAISS Search (10ms)                                  │
│ → Top-3: [copy_device_credentials (0.89),                    │
│           get_device_detail (0.65),                          │
│           set_device_credentials (0.54)]                     │
└──────────────────────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 3: LLM Parameter Extraction (120ms)                     │
│ → {source: "scalance", destinations: ["ruggedcom"], cli: true}│
└──────────────────────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 4: Call API (85ms)                                      │
│ → POST /copyDeviceCredentials                                │
└──────────────────────────────────────────────────────────────┘
```

**Total Time**: ~287ms (RAG: 30ms = 10%)

---

## 🛠️ Technical Specs

| Component | Technology | Specs |
|-----------|-----------|-------|
| **Embedding Model** | BAAI/bge-small-en-v1.5 | 384 dims, 33M params, ONNX |
| **Vector Database** | FAISS IndexFlatIP | 13 vectors, 20 KB memory |
| **Similarity Metric** | Cosine Similarity | Dot product (L2-normalized) |
| **Framework** | fastembed + FastAPI | Python 3.11 |
| **Docker Image** | mcp-embed:latest | ~600 MB (vs ~2 GB PyTorch) |

---

## 📁 Data Sources (3-Way Enrichment)

Each API capability is enriched with:

1. **credential_api_schema_rag.json**
   - API name, description, examples
   - Input/output schemas

2. **credential_api_nlp_metadata.json**
   - Intent patterns, keywords
   - Sample utterances
   - NLP training samples
   - Action/device/credential synonyms

3. **credential_api_rag_training_examples.json**
   - Real user queries
   - Historical examples

**Result**: 500+ character rich text per API → High-quality embedding

---

## ⚡ Performance Metrics

| Metric | Value |
|--------|-------|
| **Embedding Time** | 20ms |
| **FAISS Search Time** | 10ms |
| **Total RAG Time** | 30ms |
| **Throughput** | 33 req/sec |
| **Memory Usage** | 200 MB (model) + 20 KB (index) |
| **Index Build Time** | 2-3 seconds (startup only) |

---

## 🔍 How Cosine Similarity Works

```python
# Example (simplified to 4 dimensions)
query_vec = [0.5, 0.8, -0.3, 0.1]   # User query
api_vec_1 = [0.52, 0.79, -0.25, 0.15]  # copy_device_credentials
api_vec_2 = [-0.6, 0.1, 0.8, -0.4]  # delete_device_credentials

# L2 normalize (make length = 1.0)
query_vec = normalize(query_vec)
api_vec_1 = normalize(api_vec_1)
api_vec_2 = normalize(api_vec_2)

# Cosine similarity = dot product (for normalized vectors)
sim_1 = dot_product(query_vec, api_vec_1)  # 0.992  ← Very similar!
sim_2 = dot_product(query_vec, api_vec_2)  # -0.234 ← Not similar

# Ranking: api_1 (0.992) > api_2 (-0.234)
```

---

## 🚀 Quick Start

### Test Embedding Endpoint

```bash
curl -X POST http://localhost:9001/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "Copy CLI credentials from device A to device B"}'
```

**Output**:
```json
{
  "vector": [0.234, -0.456, 0.789, ..., 0.123]  // 384 floats
}
```

### Test Search Endpoint

```bash
curl -X POST http://localhost:9001/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.234, -0.456, ..., 0.123],
    "top_k": 3
  }'
```

**Output**:
```json
{
  "ids": ["copy_device_credentials", "get_device_detail_credentials", "set_device_credentials"],
  "scores": [0.89, 0.65, 0.54]
}
```

### Check Health

```bash
curl http://localhost:9001/health
```

**Output**:
```json
{
  "status": "ok",
  "model": "BAAI/bge-small-en-v1.5",
  "capabilities_indexed": 13
}
```

---

## 📝 Interview Cheat Sheet

### Q: What embeddings model do you use?
**A**: "BAAI/bge-small-en-v1.5, a 384-dimensional transformer model. It's small (120 MB ONNX), fast (20ms), and high-quality (MTEB 55.7)."

### Q: Why not use OpenAI embeddings?
**A**: "Cost, privacy, and control. We host locally using fastembed + ONNX. No API calls, no data sent externally, zero cost."

### Q: How does chunking work?
**A**: "We don't split documents. Each API capability is one chunk, enriched with 3 data sources: schema, NLP metadata, and training examples. This creates a rich 500+ char text per API."

### Q: What vector database do you use?
**A**: "FAISS IndexFlatIP for exact cosine similarity search. It's fast (< 10ms for 13 vectors), accurate (100%), and battle-tested (Facebook, Pinterest use it)."

### Q: How do you measure similarity?
**A**: "Cosine similarity via L2-normalized dot product. Measures vector angle (direction), not magnitude. Range: -1 (opposite) to +1 (identical)."

### Q: Can you scale to 10,000 APIs?
**A**: "Yes! For 1K-10K vectors, we'd use IndexIVFFlat (inverted file). For 10K+, IndexHNSW (graph-based). FAISS handles billions of vectors."

### Q: How long does RAG take?
**A**: "30ms total (20ms embedding + 10ms search). That's only 10% of our 287ms request time. LLM is the bottleneck (120ms)."

---

## 🎓 Key Formulas

### Cosine Similarity
```
           A · B
cos(θ) = ─────────
         |A| × |B|

For L2-normalized vectors (|A| = |B| = 1):
cos(θ) = A · B  (simple dot product)
```

### L2 Normalization
```
       v
v̂ = ─────
     |v|

Where |v| = √(v₁² + v₂² + ... + vₙ²)
```

### Dot Product
```
A · B = a₁b₁ + a₂b₂ + ... + aₙbₙ
```

---

## 🔧 Optimization Techniques

1. **ONNX Runtime**: 2x faster than PyTorch, 3x smaller image
2. **L2 Normalization**: Pre-compute at index time → faster search
3. **Batch Embedding**: Process all 13 capabilities at once (5x faster)
4. **Pre-Built Index**: Build once on startup, search many times
5. **IndexFlatIP**: Exact search (no approximation) for small datasets

---

## 📈 Scaling Guide

| Scale | Vectors | Index Type | Search Time | Accuracy |
|-------|---------|-----------|-------------|----------|
| **Small** | < 1K | IndexFlatIP ✅ | < 10ms | 100% |
| **Medium** | 1K-100K | IndexIVFFlat | < 50ms | ~95% |
| **Large** | 100K-1M | IndexHNSW | < 100ms | ~99% |
| **Huge** | 1M+ | IndexIVFPQ + GPU | < 200ms | ~90% |

**Our system**: 13 capabilities → IndexFlatIP is perfect!

---

## 🐛 Debugging

### Check Embedding Model Loaded
```bash
docker-compose logs mcp-embed | grep "Loading embedding model"
```

### Check Index Built
```bash
docker-compose logs mcp-embed | grep "FAISS index ready"
```

### View Similarity Scores
```bash
docker-compose logs orchestrator | grep "similarity"
```

### Test Direct Embedding
```bash
curl -X POST http://localhost:9001/embed -d '{"text": "test"}' | jq '.vector | length'
# Output: 384
```

---

## 📚 Further Reading

- **Full Guide**: `EMBEDDINGS_COMPLETE_GUIDE.md` (50+ pages)
- **FAISS Docs**: https://github.com/facebookresearch/faiss
- **BGE Model**: https://huggingface.co/BAAI/bge-small-en-v1.5
- **fastembed**: https://github.com/qdrant/fastembed
- **MTEB Benchmark**: https://github.com/embeddings-benchmark/mteb

---

## ✅ Summary

| What | How | Why |
|------|-----|-----|
| **Embeddings** | BAAI/bge-small (384 dims) | Semantic search, not keywords |
| **Enrichment** | 3 data sources merged | Rich context per API |
| **Vector DB** | FAISS IndexFlatIP | Fast, accurate, scalable |
| **Similarity** | Cosine (dot product) | Direction > magnitude for text |
| **Performance** | 30ms RAG (10% total) | Optimized with ONNX + cache |

**Status**: Production-ready, well-documented, interview-ready! 🚀

