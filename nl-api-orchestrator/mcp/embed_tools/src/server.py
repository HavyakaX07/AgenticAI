"""
MCP Embeddings & Vector Search Server.
Provides embedding and similarity search using SentenceTransformers and FAISS.
"""
import logging
import json
import os
from typing import List
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

# Configuration
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
REGISTRY_PATH = "/app/registry/capabilities.json"

# Global state
model = None
index = None
capability_ids = []
capability_texts = []


class EmbedRequest(BaseModel):
    """Request for embedding text."""
    text: str


class EmbedResponse(BaseModel):
    """Response with embedding vector."""
    vector: List[float]


class SearchRequest(BaseModel):
    """Request for similarity search."""
    vector: List[float]
    top_k: int = 3


class SearchResponse(BaseModel):
    """Response with search results."""
    ids: List[str]
    scores: List[float]


@app.on_event("startup")
async def startup_event():
    """Initialize model and build FAISS index."""
    global model, index, capability_ids, capability_texts

    logger.info(f"Loading embedding model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)
    logger.info("Model loaded successfully")

    # Load capabilities and build index
    logger.info(f"Loading capabilities from {REGISTRY_PATH}")
    try:
        with open(REGISTRY_PATH, 'r') as f:
            capabilities = json.load(f)

        logger.info(f"Loaded {len(capabilities)} capabilities")

        # Extract texts for embedding
        capability_ids = []
        capability_texts = []

        for cap in capabilities:
            cap_id = cap["name"]
            # Combine name, description, and examples for rich embedding
            text_parts = [
                cap["name"],
                cap["description"]
            ]

            # Add example queries
            if cap.get("examples"):
                for ex in cap["examples"]:
                    text_parts.append(ex.get("user", ""))

            text = " ".join(text_parts)

            capability_ids.append(cap_id)
            capability_texts.append(text)

        # Generate embeddings
        logger.info("Generating embeddings for capabilities...")
        embeddings = model.encode(capability_texts, show_progress_bar=False)
        embeddings = np.array(embeddings).astype('float32')

        # Build FAISS index
        dimension = embeddings.shape[1]
        logger.info(f"Building FAISS index with dimension {dimension}")
        index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)

        # Normalize vectors for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)

        logger.info(f"FAISS index built with {index.ntotal} vectors")

    except FileNotFoundError:
        logger.warning(f"Registry file not found: {REGISTRY_PATH}")
        logger.warning("Starting without pre-loaded capabilities")
    except Exception as e:
        logger.error(f"Failed to load capabilities: {e}", exc_info=True)
        raise


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": EMBED_MODEL,
        "capabilities_indexed": len(capability_ids)
    }


@app.post("/embed", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    """
    Generate embedding vector for text.

    Args:
        request: Text to embed

    Returns:
        Embedding vector
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not initialized")

    try:
        logger.info(f"Embedding text: {request.text[:100]}...")

        # Generate embedding
        embedding = model.encode([request.text], show_progress_bar=False)[0]
        vector = embedding.tolist()

        logger.info(f"Generated embedding with dimension {len(vector)}")
        return EmbedResponse(vector=vector)

    except Exception as e:
        logger.error(f"Embedding failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search for similar capabilities using vector similarity.

    Args:
        request: Query vector and top_k

    Returns:
        Top-k capability IDs and scores
    """
    if index is None or not capability_ids:
        raise HTTPException(status_code=503, detail="Index not initialized")

    try:
        logger.info(f"Searching for top {request.top_k} similar capabilities")

        # Convert query vector to numpy array and normalize
        query_vector = np.array([request.vector]).astype('float32')
        faiss.normalize_L2(query_vector)

        # Search
        scores, indices = index.search(query_vector, min(request.top_k, len(capability_ids)))

        # Get capability IDs
        result_ids = [capability_ids[idx] for idx in indices[0]]
        result_scores = scores[0].tolist()

        logger.info(f"Found results: {list(zip(result_ids, result_scores))}")

        return SearchResponse(
            ids=result_ids,
            scores=result_scores
        )

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)

