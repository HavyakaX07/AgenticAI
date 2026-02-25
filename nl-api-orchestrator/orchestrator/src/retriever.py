"""
Capability retrieval using RAG (semantic embeddings + FAISS vector search).

Registry source: credential_api_schema_rag.json
Embedding enrichment is handled by the embed server which loads all three
registry files (schema_rag + nlp_metadata + rag_training_examples).
"""
import json
import logging
from typing import List, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class CapabilityRetriever:
    """Retrieves relevant NMS capabilities using embeddings and vector search."""

    def __init__(self, registry_path: str, embed_server_url: str):
        """
        Args:
            registry_path:    Path to credential_api_schema_rag.json
            embed_server_url: URL of the MCP embed server (handles all enrichment)
        """
        self.registry_path = registry_path
        self.embed_server_url = embed_server_url
        self.capabilities: List[Dict[str, Any]] = []
        self.capability_map: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Load capability cards from credential_api_schema_rag.json."""
        logger.info(f"Loading NMS capabilities from {self.registry_path}")

        with open(self.registry_path, 'r') as f:
            data = json.load(f)

        # schema_rag is a JSON array; capabilities.json was also an array – both work
        if isinstance(data, list):
            self.capabilities = data
        elif isinstance(data, dict):
            # In case it is wrapped in an object key
            self.capabilities = data.get("capabilities", list(data.values()))

        # Build name → capability card lookup
        self.capability_map = {cap["name"]: cap for cap in self.capabilities}

        logger.info(f"Loaded {len(self.capabilities)} NMS capability cards: "
                    f"{[c['name'] for c in self.capabilities]}")

    async def check_health(self):
        """Check if embed server is reachable."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.embed_server_url}/health",
                timeout=5.0
            )
            response.raise_for_status()

    async def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve the top-k most relevant NMS capabilities for a user query.

        Flow:
          1. Embed the query via the embed server (POST /embed)
          2. FAISS vector search for top-k similar capability vectors (POST /search)
          3. Map returned capability IDs back to full capability cards

        Args:
            query:  User natural language query
            top_k:  Number of candidates to return

        Returns:
            List of capability card dicts sorted by cosine similarity (best first)
        """
        try:
            async with httpx.AsyncClient() as client:
                # Step 1 – embed the user query
                embed_resp = await client.post(
                    f"{self.embed_server_url}/embed",
                    json={"text": query},
                    timeout=10.0
                )
                embed_resp.raise_for_status()
                query_vector = embed_resp.json()["vector"]

                # Step 2 – FAISS search
                search_resp = await client.post(
                    f"{self.embed_server_url}/search",
                    json={"vector": query_vector, "top_k": top_k},
                    timeout=10.0
                )
                search_resp.raise_for_status()
                search_results = search_resp.json()

            capability_ids = search_results.get("ids", [])
            scores         = search_results.get("scores", [])

            logger.info(f"RAG search results for '{query[:60]}':")
            for cap_id, score in zip(capability_ids, scores):
                logger.info(f"  {cap_id}: similarity={score:.4f}")

            # Step 3 – resolve IDs to full capability cards (preserving rank order)
            results = [
                self.capability_map[cap_id]
                for cap_id in capability_ids
                if cap_id in self.capability_map
            ]

            if not results:
                logger.warning("No capability cards matched the search result IDs – "
                               "returning fallback top-k")
                return self.capabilities[:top_k]

            return results

        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}", exc_info=True)
            logger.warning("Falling back to first-k capabilities")
            return self.capabilities[:top_k]

