"""
Capability retrieval using RAG (embeddings + vector search).
"""
import json
import logging
from typing import List, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class CapabilityRetriever:
    """Retrieves relevant capabilities using embeddings and vector search."""

    def __init__(self, registry_path: str, embed_server_url: str):
        """
        Initialize retriever.

        Args:
            registry_path: Path to capabilities.json
            embed_server_url: URL of the MCP embed server
        """
        self.registry_path = registry_path
        self.embed_server_url = embed_server_url
        self.capabilities: List[Dict[str, Any]] = []
        self.capability_map: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Load capabilities from registry."""
        logger.info(f"Loading capabilities from {self.registry_path}")

        with open(self.registry_path, 'r') as f:
            self.capabilities = json.load(f)

        # Create name -> capability mapping
        self.capability_map = {cap["name"]: cap for cap in self.capabilities}

        logger.info(f"Loaded {len(self.capabilities)} capabilities")

    async def check_health(self):
        """Check if embed server is healthy."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.embed_server_url}/health",
                timeout=5.0
            )
            response.raise_for_status()

    async def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve top-k most relevant capabilities for a query.

        Args:
            query: User's natural language query
            top_k: Number of capabilities to return

        Returns:
            List of capability cards sorted by relevance
        """
        try:
            # Get embedding for query
            async with httpx.AsyncClient() as client:
                # Embed query
                embed_response = await client.post(
                    f"{self.embed_server_url}/embed",
                    json={"text": query},
                    timeout=10.0
                )
                embed_response.raise_for_status()
                query_vector = embed_response.json()["vector"]

                # Search for similar capabilities
                search_response = await client.post(
                    f"{self.embed_server_url}/search",
                    json={"vector": query_vector, "top_k": top_k},
                    timeout=10.0
                )
                search_response.raise_for_status()
                search_results = search_response.json()

            # Get capability cards for the results
            capability_ids = search_results.get("ids", [])
            scores = search_results.get("scores", [])

            logger.info(f"Retrieved {len(capability_ids)} capabilities with scores: {scores}")

            # Return capabilities in order of relevance
            results = []
            for cap_id in capability_ids:
                if cap_id in self.capability_map:
                    results.append(self.capability_map[cap_id])

            return results

        except Exception as e:
            logger.error(f"Failed to retrieve capabilities: {e}", exc_info=True)
            # Fallback: return all capabilities if retrieval fails
            logger.warning("Falling back to returning all capabilities")
            return self.capabilities[:top_k]

