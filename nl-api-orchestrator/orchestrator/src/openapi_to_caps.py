"""
Utility to convert OpenAPI spec to capability cards.
"""
import json
import yaml
import sys
import argparse
from typing import Dict, Any, List


def openapi_to_capabilities(openapi_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert OpenAPI spec to capability cards.

    Args:
        openapi_spec: Parsed OpenAPI specification

    Returns:
        List of capability cards
    """
    capabilities = []
    paths = openapi_spec.get("paths", {})
    base_url = ""

    # Extract base URL from servers
    if "servers" in openapi_spec and openapi_spec["servers"]:
        base_url = openapi_spec["servers"][0].get("url", "")

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.upper() not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                continue

            # Extract operation details
            operation_id = operation.get("operationId", f"{method}_{path.replace('/', '_')}")
            summary = operation.get("summary", "")
            description = operation.get("description", summary)

            # Build endpoint
            endpoint = f"{method.upper()} {base_url}{path}"

            # Extract request schema
            input_schema = {"type": "object", "properties": {}, "required": []}

            # Parameters (query, path, header)
            parameters = operation.get("parameters", [])
            for param in parameters:
                param_name = param.get("name")
                param_schema = param.get("schema", {"type": "string"})
                input_schema["properties"][param_name] = param_schema

                if param.get("required", False):
                    input_schema["required"].append(param_name)

            # Request body
            request_body = operation.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                json_content = content.get("application/json", {})
                body_schema = json_content.get("schema", {})

                # Merge body schema properties
                if "properties" in body_schema:
                    input_schema["properties"].update(body_schema["properties"])

                if "required" in body_schema:
                    input_schema["required"].extend(body_schema["required"])

            # Determine risk level (heuristic)
            risk = "low"
            if method.upper() in ["DELETE", "PUT"]:
                risk = "high"
            elif method.upper() in ["POST", "PATCH"]:
                risk = "medium"

            # Detect auth
            auth = "none"
            if "security" in operation or "security" in openapi_spec:
                auth = "bearer"  # Simplified

            # Create capability card
            capability = {
                "name": operation_id,
                "description": description or summary,
                "endpoint": endpoint,
                "auth": auth,
                "risk": risk,
                "input_schema": input_schema,
                "examples": []  # User must add examples manually
            }

            capabilities.append(capability)

    return capabilities


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert OpenAPI spec to capability cards"
    )
    parser.add_argument(
        "input",
        help="Path to OpenAPI YAML or JSON file"
    )
    parser.add_argument(
        "output",
        help="Path to output capabilities.json file"
    )

    args = parser.parse_args()

    # Load OpenAPI spec
    with open(args.input, 'r') as f:
        if args.input.endswith('.yaml') or args.input.endswith('.yml'):
            spec = yaml.safe_load(f)
        else:
            spec = json.load(f)

    # Convert
    capabilities = openapi_to_capabilities(spec)

    # Write output
    with open(args.output, 'w') as f:
        json.dump(capabilities, f, indent=2)

    print(f"Converted {len(capabilities)} operations to capability cards")
    print(f"Output written to: {args.output}")
    print("\nNote: Please review and add examples manually for better LLM performance.")


if __name__ == "__main__":
    main()

