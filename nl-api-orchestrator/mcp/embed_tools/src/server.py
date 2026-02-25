"""
MCP Embeddings & Vector Search Server.
Provides embedding and similarity search using SentenceTransformers and FAISS.

Embedding text is enriched from THREE sources:
  1. credential_api_schema_rag.json    – API name, description, examples
  2. credential_api_nlp_metadata.json  – intent patterns, sample utterances,
                                         nlp training samples, entity/action
                                         synonyms, workflow descriptions
  3. credential_api_rag_training_examples.json – real user queries per API
"""
import logging
import json
import os
from typing import List, Dict
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import faiss

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MCP Embeddings Server",
    description="Embeddings and vector search service",
    version="1.0.0"
)

# ── Configuration ──────────────────────────────────────────────────────────────
EMBED_MODEL   = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
REGISTRY_DIR  = os.getenv("REGISTRY_DIR", "/app/registry")

# File paths (all mounted into the same registry directory)
SCHEMA_RAG_PATH    = os.path.join(REGISTRY_DIR, "credential_api_schema_rag.json")
NLP_METADATA_PATH  = os.path.join(REGISTRY_DIR, "credential_api_nlp_metadata.json")
TRAINING_EX_PATH   = os.path.join(REGISTRY_DIR, "credential_api_rag_training_examples.json")

# ── Global state ───────────────────────────────────────────────────────────────
model: SentenceTransformer = None
index: faiss.Index          = None
capability_ids:   List[str] = []
capability_texts: List[str] = []


# ── Pydantic models ────────────────────────────────────────────────────────────
class EmbedRequest(BaseModel):
    text: str

class EmbedResponse(BaseModel):
    vector: List[float]

class SearchRequest(BaseModel):
    vector: List[float]
    top_k: int = 3

class SearchResponse(BaseModel):
    ids:    List[str]
    scores: List[float]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_json(path: str):
    """Load JSON file – returns None if file missing."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"File not found – skipping: {path}")
        return None
    except Exception as e:
        logger.error(f"Failed to parse {path}: {e}")
        return None


def _build_nlp_lookup(nlp_meta: dict) -> Dict[str, dict]:
    """
    Build a lookup keyed by api_mapping name from the NLP metadata file.

    Returns: { "copy_device_credentials": { intent_obj }, ... }
    """
    lookup: Dict[str, dict] = {}
    if not nlp_meta:
        return lookup

    intent_patterns = nlp_meta.get("intent_patterns", {})
    for intent_name, intent_obj in intent_patterns.items():
        api_name = intent_obj.get("api_mapping", "")
        if api_name:
            lookup[api_name] = intent_obj

    return lookup


def _build_training_lookup(training_data) -> Dict[str, List[str]]:
    """
    Build a lookup of real user queries keyed by selected_api name.

    Returns: { "copy_device_credentials": ["Copy SNMP …", "replicate …"], ... }
    """
    lookup: Dict[str, List[str]] = {}
    if not training_data:
        return lookup

    examples = []
    if isinstance(training_data, dict):
        # Nested: { "rag_training_dataset": { "examples": [...] } }
        examples = (
            training_data.get("rag_training_dataset", {}).get("examples", [])
            or training_data.get("examples", [])
        )
    elif isinstance(training_data, list):
        examples = training_data

    for ex in examples:
        api_name = ex.get("selected_api", "")
        query    = ex.get("user_query", "")
        if api_name and query:
            lookup.setdefault(api_name, []).append(query)

    return lookup


def _build_nlp_training_lookup(nlp_meta: dict) -> Dict[str, List[str]]:
    """
    Extract training samples from nlp_metadata → nlp_training_data.intents.

    Returns: { "copy_device_credentials": ["copy snmp credentials …", ...] }
    """
    lookup: Dict[str, List[str]] = {}
    if not nlp_meta:
        return lookup

    # nlp_training_data.intents[].intent  →  matched via intent_patterns api_mapping
    intent_to_api: Dict[str, str] = {}
    for _intent_name, obj in nlp_meta.get("intent_patterns", {}).items():
        intent_key = _intent_name           # e.g. "COPY_CREDENTIALS"
        api_name   = obj.get("api_mapping", "")
        if api_name:
            intent_to_api[intent_key] = api_name

    for item in nlp_meta.get("nlp_training_data", {}).get("intents", []):
        intent_key = item.get("intent", "")
        samples    = item.get("training_samples", [])
        api_name   = intent_to_api.get(intent_key, "")
        if api_name and samples:
            lookup.setdefault(api_name, []).extend(samples)

    return lookup


def _build_capability_text(
    cap:                  dict,
    nlp_lookup:           Dict[str, dict],
    training_lookup:      Dict[str, List[str]],
    nlp_training_lookup:  Dict[str, List[str]],
    action_synonyms:      Dict[str, List[str]],
    device_synonyms:      List[str],
    cred_type_synonyms:   Dict[str, List[str]],
) -> str:
    """
    Build a rich text representation of a single capability by combining:
      • API name + description  (schema_rag)
      • primary & secondary keywords  (nlp_metadata intent_patterns)
      • sample_utterances  (nlp_metadata intent_patterns)
      • nlp training samples  (nlp_metadata nlp_training_data)
      • real RAG training user queries  (rag_training_examples)
      • schema_rag example user queries
      • action synonym expansion
      • domain context: device_synonyms, credential_type_synonyms
    """
    api_name = cap.get("name", "")
    parts: List[str] = []

    # ── 1. Core schema fields ──────────────────────────────────────────────────
    parts.append(api_name)
    parts.append(cap.get("description", ""))

    # Schema examples (user queries only)
    for ex in cap.get("examples", []):
        user_q = ex.get("user", "")
        if user_q:
            parts.append(user_q)

    # ── 2. NLP metadata – intent patterns ─────────────────────────────────────
    intent_obj = nlp_lookup.get(api_name, {})
    if intent_obj:
        # Primary + secondary keywords
        keywords = (
            intent_obj.get("primary_keywords", [])
            + intent_obj.get("secondary_keywords", [])
        )
        if keywords:
            parts.append(" ".join(keywords))

        # Sample utterances (strip template placeholders for cleaner embedding)
        for utt in intent_obj.get("sample_utterances", []):
            # Replace {placeholder} with generic stand-ins so the sentence is grammatical
            clean_utt = (
                utt.replace("{source}", "device-001")
                   .replace("{destinations}", "device-002 device-003")
                   .replace("{device_id}", "device-001")
                   .replace("{device_ids}", "device-001 device-002")
                   .replace("{location}", "building A")
            )
            parts.append(clean_utt)

        # Expand action synonyms for primary keywords
        for kw in intent_obj.get("primary_keywords", []):
            synonyms = action_synonyms.get(kw, [])
            if synonyms:
                parts.append(" ".join(synonyms))

    # ── 3. NLP metadata – training samples ────────────────────────────────────
    for sample in nlp_training_lookup.get(api_name, []):
        parts.append(sample)

    # ── 4. RAG training examples – real user queries ──────────────────────────
    for query in training_lookup.get(api_name, []):
        parts.append(query)

    # ── 5. Domain context ─────────────────────────────────────────────────────
    # Device synonyms enrich any capability that talks about devices
    if device_synonyms:
        parts.append("network " + " ".join(device_synonyms))

    # Credential type synonyms relevant to this API
    for cred_type, synonyms in cred_type_synonyms.items():
        if cred_type.lower() in api_name.lower() or cred_type.lower() in cap.get("description", "").lower():
            parts.extend(synonyms)

    # Deduplicate while preserving order
    seen = set()
    unique_parts: List[str] = []
    for p in parts:
        p_stripped = p.strip()
        if p_stripped and p_stripped not in seen:
            seen.add(p_stripped)
            unique_parts.append(p_stripped)

    combined = " . ".join(unique_parts)
    logger.debug(f"[{api_name}] embedding text ({len(combined)} chars): {combined[:200]}…")
    return combined


# ── Startup ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize model and build FAISS index enriched with NLP metadata."""
    global model, index, capability_ids, capability_texts

    # ── Load model ─────────────────────────────────────────────────────────────
    logger.info(f"Loading embedding model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)
    logger.info("Model loaded successfully")

    # ── Load all registry files ────────────────────────────────────────────────
    logger.info("Loading registry files …")
    capabilities  = _load_json(SCHEMA_RAG_PATH)   or []
    nlp_meta      = _load_json(NLP_METADATA_PATH)  or {}
    training_data = _load_json(TRAINING_EX_PATH)   or {}

    if not capabilities:
        logger.warning("No capabilities loaded – starting without pre-built index")
        return

    logger.info(f"  schema_rag       : {len(capabilities)} capabilities")
    logger.info(f"  nlp_metadata     : {len(nlp_meta.get('intent_patterns', {}))} intents")

    # ── Build lookup tables from NLP metadata ──────────────────────────────────
    nlp_lookup          = _build_nlp_lookup(nlp_meta)
    training_lookup     = _build_training_lookup(training_data)
    nlp_training_lookup = _build_nlp_training_lookup(nlp_meta)

    # Context-enrichment data
    context             = nlp_meta.get("context_enrichment", {})
    action_synonyms     = context.get("action_synonyms", {})
    device_synonyms     = context.get("device_synonyms", [])
    cred_type_synonyms  = context.get("credential_type_synonyms", {})

    logger.info(f"  action_synonyms  : {len(action_synonyms)} entries")
    logger.info(f"  nlp_training_lookup : {sum(len(v) for v in nlp_training_lookup.values())} samples")
    logger.info(f"  training_lookup  : {sum(len(v) for v in training_lookup.values())} examples")

    # ── Build rich embedding texts ─────────────────────────────────────────────
    capability_ids    = []
    capability_texts  = []

    for cap in capabilities:
        api_name = cap.get("name", "")
        if not api_name:
            continue

        text = _build_capability_text(
            cap,
            nlp_lookup,
            training_lookup,
            nlp_training_lookup,
            action_synonyms,
            device_synonyms,
            cred_type_synonyms,
        )

        capability_ids.append(api_name)
        capability_texts.append(text)
        logger.info(f"  ✓ built text for [{api_name}] – {len(text)} chars")

    # ── Generate embeddings ────────────────────────────────────────────────────
    logger.info(f"Generating embeddings for {len(capability_texts)} capabilities …")
    embeddings = model.encode(capability_texts, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype="float32")

    # ── Build FAISS index (cosine similarity via inner product on L2-normalised vecs)
    dimension = embeddings.shape[1]
    logger.info(f"Building FAISS IndexFlatIP  dim={dimension}")
    index = faiss.IndexFlatIP(dimension)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    logger.info(f"✓ FAISS index ready – {index.ntotal} vectors indexed")


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": EMBED_MODEL,
        "capabilities_indexed": len(capability_ids),
        "registry_sources": {
            "schema_rag":        SCHEMA_RAG_PATH,
            "nlp_metadata":      NLP_METADATA_PATH,
            "training_examples": TRAINING_EX_PATH,
        }
    }


@app.post("/embed", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    """Generate embedding vector for a text string."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not initialized")
    try:
        logger.info(f"Embedding: {request.text[:100]}…")
        embedding = model.encode([request.text], show_progress_bar=False)[0]
        return EmbedResponse(vector=embedding.tolist())
    except Exception as e:
        logger.error(f"Embedding failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search for the most similar capabilities using cosine similarity."""
    if index is None or not capability_ids:
        raise HTTPException(status_code=503, detail="Index not initialized")
    try:
        query_vec = np.array([request.vector], dtype="float32")
        faiss.normalize_L2(query_vec)
        scores, indices = index.search(
            query_vec, min(request.top_k, len(capability_ids))
        )
        result_ids    = [capability_ids[i] for i in indices[0]]
        result_scores = scores[0].tolist()
        logger.info(f"Search results: {list(zip(result_ids, result_scores))}")
        return SearchResponse(ids=result_ids, scores=result_scores)
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)

