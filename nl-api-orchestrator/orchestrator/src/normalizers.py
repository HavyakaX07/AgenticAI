"""
Payload normalization utilities.
Normalizes common synonyms and formats before validation.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Priority normalization map
PRIORITY_MAP = {
    "asap": "urgent",
    "critical": "urgent",
    "crit": "urgent",
    "emergency": "urgent",
    "high priority": "high",
    "hi": "high",
    "low priority": "low",
    "lo": "low",
    "normal": "medium",
    "med": "medium",
    "moderate": "medium",
}

# Status normalization map
STATUS_MAP = {
    "active": "open",
    "new": "open",
    "pending": "in_progress",
    "in progress": "in_progress",
    "working": "in_progress",
    "done": "closed",
    "resolved": "closed",
    "completed": "closed",
    "finished": "closed",
}


def normalize_payload(payload: Dict[str, Any], capability: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize payload values based on capability schema.

    Args:
        payload: Raw payload from LLM
        capability: Capability card with schema

    Returns:
        Normalized payload
    """
    normalized = payload.copy()
    schema = capability.get("input_schema", {})
    properties = schema.get("properties", {})

    # Normalize priority field
    if "priority" in properties and "priority" in normalized:
        original = normalized["priority"]
        if isinstance(original, str):
            lower_val = original.lower().strip()
            if lower_val in PRIORITY_MAP:
                normalized["priority"] = PRIORITY_MAP[lower_val]
                logger.debug(f"Normalized priority: {original} → {normalized['priority']}")

    # Normalize status field
    if "status" in properties and "status" in normalized:
        original = normalized["status"]
        if isinstance(original, str):
            lower_val = original.lower().strip()
            if lower_val in STATUS_MAP:
                normalized["status"] = STATUS_MAP[lower_val]
                logger.debug(f"Normalized status: {original} → {normalized['status']}")

    # Trim string fields
    for field, value in normalized.items():
        if isinstance(value, str):
            normalized[field] = value.strip()

    # Remove None values for optional fields
    required_fields = schema.get("required", [])
    normalized = {
        k: v for k, v in normalized.items()
        if v is not None or k in required_fields
    }

    return normalized


def add_synonym(mapping: Dict[str, str], synonym: str, canonical: str):
    """
    Add a custom synonym mapping.

    Args:
        mapping: The mapping dict to update (PRIORITY_MAP or STATUS_MAP)
        synonym: The synonym to add
        canonical: The canonical value to map to
    """
    mapping[synonym.lower()] = canonical
    logger.info(f"Added synonym mapping: {synonym} → {canonical}")

