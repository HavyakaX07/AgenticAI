"""
Tool routing using LLM to select the appropriate tool and fill payload.
"""
import json
import logging
from typing import Dict, Any, List
import httpx
from openai import AsyncOpenAI

from .prompts import create_messages, LLM_RESPONSE_SCHEMA

logger = logging.getLogger(__name__)


class ToolRouter:
    """Routes queries to appropriate tools using LLM reasoning."""

    def __init__(self, openai_base_url: str, openai_api_key: str, model_name: str):
        """
        Initialize router.

        Args:
            openai_base_url: Base URL for OpenAI-compatible API
            openai_api_key: API key (can be dummy for local models)
            model_name: Model identifier
        """
        self.client = AsyncOpenAI(
            base_url=openai_base_url,
            api_key=openai_api_key
        )
        self.model_name = model_name
        logger.info(f"Initialized ToolRouter with model: {model_name}")

    async def check_health(self):
        """Check if LLM server is healthy."""
        try:
            # Try to list models as a health check
            await self.client.models.list()
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            raise

    async def route(self, query: str, capabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use LLM to select tool and fill payload.

        Args:
            query: User's natural language query
            capabilities: List of candidate capability cards

        Returns:
            Dict with decision, tool_name, payload, missing_fields, notes
        """
        try:
            messages = create_messages(query, capabilities)

            logger.info(f"Calling LLM with {len(capabilities)} candidate tools")

            # Call LLM with JSON mode if supported
            try:
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000,
                    response_format={"type": "json_object"}  # Force JSON output
                )
            except Exception as e:
                logger.warning(f"JSON mode not supported, falling back: {e}")
                # Fallback without response_format
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000
                )

            content = response.choices[0].message.content
            logger.debug(f"LLM response: {content}")

            # Parse JSON response
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Response content: {content}")
                # Try to repair JSON
                result = self._repair_json(content)

            # Add usage stats if available
            if hasattr(response, 'usage') and response.usage:
                result["usage"] = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }

            # Validate required fields
            if "decision" not in result:
                logger.warning("LLM response missing 'decision', defaulting to NONE")
                result["decision"] = "NONE"

            return result

        except Exception as e:
            logger.error(f"LLM routing failed: {e}", exc_info=True)
            # Return safe fallback
            return {
                "decision": "NONE",
                "notes": f"LLM routing error: {str(e)}"
            }

    def _repair_json(self, content: str) -> Dict[str, Any]:
        """
        Attempt to repair malformed JSON response.

        Args:
            content: Raw LLM response

        Returns:
            Parsed dict or fallback
        """
        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                try:
                    return json.loads(content[start:end].strip())
                except json.JSONDecodeError:
                    pass

        # Try to extract JSON object
        if "{" in content and "}" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            try:
                return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass

        logger.error(f"Could not repair JSON from: {content}")
        return {
            "decision": "NONE",
            "notes": "Failed to parse LLM response"
        }

