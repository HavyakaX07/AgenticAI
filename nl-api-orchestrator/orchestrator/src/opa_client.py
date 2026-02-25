"""
OPA (Open Policy Agent) client.
Checks policies before executing tools.
"""
import logging
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)


class OPAClient:
    """Client for OPA policy engine."""

    def __init__(self, opa_url: str):
        """
        Initialize OPA client.

        Args:
            opa_url: URL of OPA policy endpoint (e.g., http://mcp-policy:8181/v1/data/policy/allow)
        """
        self.opa_url = opa_url.rstrip('/')

        # Validate URL format
        if "/v1/data/" not in self.opa_url:
            logger.warning(f"OPA URL may be incomplete: {self.opa_url}. Expected format: http://host:port/v1/data/package/rule")

        logger.info(f"Initialized OPAClient with URL: {self.opa_url}")

    async def check_health(self):
        """Check if OPA server is healthy."""
        # Extract base URL (remove /v1/data/policy/allow)
        base_url = self.opa_url.split("/v1/data")[0]
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/health",
                timeout=5.0
            )
            response.raise_for_status()

    async def check_policy(self, policy_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an action is allowed by policy.

        Args:
            policy_input: Input for policy evaluation with keys:
                - payload: The tool payload
                - tool: Tool name
                - risk: Risk level
                - confirmed: User confirmation flag
                - user: User identifier

        Returns:
            Dict with 'allow' (bool) and optional 'reason' (str)
        """
        logger.info(f"Checking policy for tool: {policy_input.get('tool')}, risk: {policy_input.get('risk')}")
        logger.debug(f"Policy check URL: {self.opa_url}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.opa_url,
                    json={"input": policy_input},
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()

                # OPA can return two formats:
                # 1. Specific rule query: {"result": true/false} - boolean
                # 2. Package query: {"result": {"allow": true, "reason": "..."}} - object

                policy_result = result.get("result", {})

                # Handle boolean result (when querying /v1/data/policy/allow directly)
                if isinstance(policy_result, bool):
                    allow = policy_result
                    reason = "Policy evaluation complete"
                    logger.info(f"Policy decision (boolean): allow={allow}")
                # Handle object result (when querying /v1/data/policy)
                elif isinstance(policy_result, dict):
                    allow  = policy_result.get("allow", False)
                    # NMS policy returns deny_reason (singular string) not reason
                    reason = (
                        policy_result.get("deny_reason")
                        or policy_result.get("reason", "")
                    )
                    logger.info(f"Policy decision (object): allow={allow}, reason={reason}")
                else:
                    # Unexpected format
                    logger.warning(f"Unexpected policy result format: {type(policy_result)}, value: {policy_result}")
                    allow = False
                    reason = f"Unexpected policy result format: {type(policy_result)}"

                return {
                    "allow": allow,
                    "reason": reason
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Policy check HTTP error: {e.response.status_code} for URL {self.opa_url}")
            logger.error(f"Response body: {e.response.text}")
            return {
                "allow": False,
                "reason": f"Policy check error: {e.response.status_code} {e.response.reason_phrase}"
            }
        except Exception as e:
            logger.error(f"Policy check failed: {e}", exc_info=True)
            # Fail-closed: deny if policy check fails
            return {
                "allow": False,
                "reason": f"Policy check error: {str(e)}"
            }

