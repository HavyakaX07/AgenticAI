"""
Device Resolver - NMS Device Identifier Lookup.

Resolves human-friendly device references to actual NMS device_ids
BEFORE payload construction. Supports three backends:

  BACKEND 1 - PostgreSQL (production)
      Set DB_BACKEND=postgres and DB_URL=postgresql://user:pass@host/db
      Table: nms_devices (device_id, display_name, ip, device_type,
                           category, brand, model, location)

  BACKEND 2 - SQLite (lightweight production / on-prem)
      Set DB_BACKEND=sqlite and SQLITE_PATH=/data/devices.db

  BACKEND 3 - Mock in-memory (POC / testing)
      Set DB_BACKEND=mock  OR leave DB_URL empty

Supported input types:
  - Brand/model name  : "scalance", "ruggedcom", "SCALANCE-X200"
  - IP address        : "172.16.122.190"
  - Device type       : "switch", "router", "firewall"
  - Device category   : "industrial switch", "ruggedized switch"
  - Partial name      : "scalance-x200", "rug-rs9"
  - Device ID (pass-through): "SCALANCE-X200-001"

SPECIAL INTENT KEYWORDS (auto-expand without asking user):
  - "all scalance"  / "all switches"    → expand to ALL matching devices
  - "any scalance"  / "any one ruggedcom" → pick FIRST matching device

CACHING MECHANISM:
  - All devices loaded into memory on startup
  - Cache refreshed every 15 minutes automatically
  - Lookups performed on in-memory cache (< 1ms)
  - Background refresh from database (zero query downtime)
"""
import logging
import os
import re
import asyncio
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Intent keywords ────────────────────────────────────────────────────────────
# When user says "all" or "any", we auto-resolve without asking for disambiguation
_ALL_KEYWORDS  = ["all", "every", "each", "entire", "whole"]
_ANY_KEYWORDS  = ["any", "any one", "anyone", "whichever", "first", "one of"]

# ── Regex helpers ──────────────────────────────────────────────────────────────
_IP_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")

# ── Cache configuration ────────────────────────────────────────────────────────
CACHE_REFRESH_INTERVAL = 900  # 15 minutes in seconds

# ── Device type keyword map ────────────────────────────────────────────────────
_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "switch":   ["switch", "switches", "sw"],
    "router":   ["router", "routers", "rt", "gateway"],
    "firewall": ["firewall", "fw", "security appliance"],
}

_BRAND_KEYWORDS: List[str] = [
    "scalance", "ruggedcom", "siemens", "cisco", "juniper", "aruba", "huawei",
]

# ── Resolution mode ────────────────────────────────────────────────────────────
class ResolutionMode(str, Enum):
    NORMAL   = "normal"    # default: single match → use it, multiple → ask user
    ALL      = "all"       # user said "all" → return every match
    ANY_ONE  = "any_one"   # user said "any" → return first match only


# ══════════════════════════════════════════════════════════════════════════════
# POC Mock Device Database
# Mirrors device_list schema for testing without PostgreSQL
# ══════════════════════════════════════════════════════════════════════════════
_MOCK_DEVICES: List[Dict[str, Any]] = [
    {
        "device_id": "SCALANCE-X200-001",
        "device_name": "SCALANCE X200 #1",
        "device_type": "switch",
        "ip_address": "172.16.122.190",
        "mac": "00:1B:1B:01:22:90",
        "order_no": "6GK5200-8AS10-2AA3",
        "firmware": "v4.2.1",
        "sinec_hierarchy_name": "Plant Floor A",
        "is_blacklisted": False,
        "device_status": "online",
        "config_status": 1,
        "device_info": {"brand": "scalance", "model": "SCALANCE X200", "category": "industrial_switch"}
    },
    {
        "device_id": "SCALANCE-X200-002",
        "device_name": "SCALANCE X200 #2",
        "device_type": "switch",
        "ip_address": "172.16.122.191",
        "mac": "00:1B:1B:01:22:91",
        "order_no": "6GK5200-8AS10-2AA3",
        "firmware": "v4.2.1",
        "sinec_hierarchy_name": "Plant Floor B",
        "is_blacklisted": False,
        "device_status": "online",
        "config_status": 1,
        "device_info": {"brand": "scalance", "model": "SCALANCE X200", "category": "industrial_switch"}
    },
    {
        "device_id": "SCALANCE-XC200-001",
        "device_name": "SCALANCE XC200 Core",
        "device_type": "switch",
        "ip_address": "172.16.122.100",
        "mac": "00:1B:1B:01:21:00",
        "order_no": "6GK5200-8AS20-2AB2",
        "firmware": "v5.0.0",
        "sinec_hierarchy_name": "Server Room",
        "is_blacklisted": False,
        "device_status": "online",
        "config_status": 1,
        "device_info": {"brand": "scalance", "model": "SCALANCE XC200", "category": "industrial_switch"}
    },
    {
        "device_id": "RUGGEDCOM-RS900-001",
        "device_name": "RUGGEDCOM RS900 #1",
        "device_type": "switch",
        "ip_address": "172.16.122.200",
        "mac": "00:30:A7:01:22:00",
        "order_no": "RS900-24T-K1-A2-A2",
        "firmware": "v5.6.1",
        "sinec_hierarchy_name": "Substation A",
        "is_blacklisted": False,
        "device_status": "online",
        "config_status": 1,
        "device_info": {"brand": "ruggedcom", "model": "RUGGEDCOM RS900", "category": "ruggedized_switch"}
    },
    {
        "device_id": "RUGGEDCOM-RS900-002",
        "device_name": "RUGGEDCOM RS900 #2",
        "device_type": "switch",
        "ip_address": "172.16.122.201",
        "mac": "00:30:A7:01:22:01",
        "order_no": "RS900-24T-K1-A2-A2",
        "firmware": "v5.6.1",
        "sinec_hierarchy_name": "Substation B",
        "is_blacklisted": False,
        "device_status": "online",
        "config_status": 1,
        "device_info": {"brand": "ruggedcom", "model": "RUGGEDCOM RS900", "category": "ruggedized_switch"}
    },
    {
        "device_id": "RUGGEDCOM-RS416-001",
        "device_name": "RUGGEDCOM RS416 Gateway",
        "device_type": "router",
        "ip_address": "172.16.122.210",
        "mac": "00:30:A7:01:22:10",
        "order_no": "RS416V2-SERIAL-24-24-2TX",
        "firmware": "v5.5.0",
        "sinec_hierarchy_name": "Control Room",
        "is_blacklisted": False,
        "device_status": "online",
        "config_status": 1,
        "device_info": {"brand": "ruggedcom", "model": "RUGGEDCOM RS416", "category": "ruggedized_router"}
    },
    {
        "device_id": "FW-SIEMENS-001",
        "device_name": "Siemens Firewall #1",
        "device_type": "firewall",
        "ip_address": "10.0.0.1",
        "mac": "00:1B:1B:FE:00:01",
        "order_no": "6GK5615-0AA01-2AA2",
        "firmware": "v4.1.2",
        "sinec_hierarchy_name": "DMZ",
        "is_blacklisted": False,
        "device_status": "online",
        "config_status": 1,
        "device_info": {"brand": "siemens", "model": "SCALANCE S615", "category": "firewall"}
    },
    {
        "device_id": "RT-CORE-001",
        "device_name": "Core Router",
        "device_type": "router",
        "ip_address": "192.168.1.1",
        "mac": "00:1E:BD:C0:00:01",
        "order_no": "ISR4431/K9",
        "firmware": "17.6.1",
        "sinec_hierarchy_name": "Data Center",
        "is_blacklisted": False,
        "device_status": "online",
        "config_status": 1,
        "device_info": {"brand": "cisco", "model": "ISR 4431", "category": "core_router"}
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# SQL Schema (PostgreSQL & SQLite compatible)
# Matches production NMS device_list table structure
# ══════════════════════════════════════════════════════════════════════════════
CREATE_TABLE_SQL = """
-- PostgreSQL version (use JSONB for device_info)
CREATE TABLE IF NOT EXISTS device_list (
    device_id VARCHAR(100) PRIMARY KEY,
    is_blacklisted BOOLEAN DEFAULT FALSE,
    device_info JSONB,                    -- stores: {brand, model, category}
    device_status TEXT,
    device_name TEXT,
    device_type TEXT,
    ip_address TEXT,
    mac TEXT,
    order_no TEXT,
    firmware TEXT,
    sinec_hierarchy_name TEXT,
    config_status INT DEFAULT 0,
    updated_on BIGINT,
    mc_timestamp VARCHAR(100)
);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_device_list_ip ON device_list(ip_address);
CREATE INDEX IF NOT EXISTS idx_device_list_type ON device_list(device_type);
CREATE INDEX IF NOT EXISTS idx_device_list_name ON device_list(device_name);
CREATE INDEX IF NOT EXISTS idx_device_list_mac ON device_list(mac);

-- For JSONB queries on brand/model (PostgreSQL only)
CREATE INDEX IF NOT EXISTS idx_device_info_brand ON device_list
    USING GIN ((device_info->'brand'));
"""

# SQLite version (use JSON instead of JSONB)
CREATE_TABLE_SQL_SQLITE = """
CREATE TABLE IF NOT EXISTS device_list (
    device_id VARCHAR(100) PRIMARY KEY,
    is_blacklisted BOOLEAN DEFAULT 0,
    device_info TEXT,                     -- JSON string: {brand, model, category}
    device_status TEXT,
    device_name TEXT,
    device_type TEXT,
    ip_address TEXT,
    mac TEXT,
    order_no TEXT,
    firmware TEXT,
    sinec_hierarchy_name TEXT,
    config_status INTEGER DEFAULT 0,
    updated_on INTEGER,
    mc_timestamp VARCHAR(100)
);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_device_list_ip ON device_list(ip_address);
CREATE INDEX IF NOT EXISTS idx_device_list_type ON device_list(device_type);
CREATE INDEX IF NOT EXISTS idx_device_list_name ON device_list(device_name);
CREATE INDEX IF NOT EXISTS idx_device_list_mac ON device_list(mac);
"""

# Seed data for PostgreSQL
SEED_SQL_POSTGRES = """
INSERT INTO device_list
  (device_id, device_name, device_type, ip_address, mac, order_no, firmware,
   sinec_hierarchy_name, is_blacklisted, device_status, config_status, device_info,
   updated_on, mc_timestamp)
VALUES
  ('SCALANCE-X200-001', 'SCALANCE X200 #1', 'switch', '172.16.122.190', '00:1B:1B:01:22:90',
   '6GK5200-8AS10-2AA3', 'v4.2.1', 'Plant Floor A', FALSE, 'online', 1,
   '{"brand": "scalance", "model": "SCALANCE X200", "category": "industrial_switch"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text),

  ('SCALANCE-X200-002', 'SCALANCE X200 #2', 'switch', '172.16.122.191', '00:1B:1B:01:22:91',
   '6GK5200-8AS10-2AA3', 'v4.2.1', 'Plant Floor B', FALSE, 'online', 1,
   '{"brand": "scalance", "model": "SCALANCE X200", "category": "industrial_switch"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text),

  ('SCALANCE-XC200-001', 'SCALANCE XC200 Core', 'switch', '172.16.122.100', '00:1B:1B:01:21:00',
   '6GK5200-8AS20-2AB2', 'v5.0.0', 'Server Room', FALSE, 'online', 1,
   '{"brand": "scalance", "model": "SCALANCE XC200", "category": "industrial_switch"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text),

  ('RUGGEDCOM-RS900-001', 'RUGGEDCOM RS900 #1', 'switch', '172.16.122.200', '00:30:A7:01:22:00',
   'RS900-24T-K1-A2-A2', 'v5.6.1', 'Substation A', FALSE, 'online', 1,
   '{"brand": "ruggedcom", "model": "RUGGEDCOM RS900", "category": "ruggedized_switch"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text),

  ('RUGGEDCOM-RS900-002', 'RUGGEDCOM RS900 #2', 'switch', '172.16.122.201', '00:30:A7:01:22:01',
   'RS900-24T-K1-A2-A2', 'v5.6.1', 'Substation B', FALSE, 'online', 1,
   '{"brand": "ruggedcom", "model": "RUGGEDCOM RS900", "category": "ruggedized_switch"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text),

  ('RUGGEDCOM-RS416-001', 'RUGGEDCOM RS416 Gateway', 'router', '172.16.122.210', '00:30:A7:01:22:10',
   'RS416V2-SERIAL-24-24-2TX', 'v5.5.0', 'Control Room', FALSE, 'online', 1,
   '{"brand": "ruggedcom", "model": "RUGGEDCOM RS416", "category": "ruggedized_router"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text),

  ('FW-SIEMENS-001', 'Siemens Firewall #1', 'firewall', '10.0.0.1', '00:1B:1B:FE:00:01',
   '6GK5615-0AA01-2AA2', 'v4.1.2', 'DMZ', FALSE, 'online', 1,
   '{"brand": "siemens", "model": "SCALANCE S615", "category": "firewall"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text),

  ('RT-CORE-001', 'Core Router', 'router', '192.168.1.1', '00:1E:BD:C0:00:01',
   'ISR4431/K9', '17.6.1', 'Data Center', FALSE, 'online', 1,
   '{"brand": "cisco", "model": "ISR 4431", "category": "core_router"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text)
ON CONFLICT (device_id) DO NOTHING;
"""

# Seed data for SQLite
SEED_SQL_SQLITE = """
INSERT OR IGNORE INTO device_list
  (device_id, device_name, device_type, ip_address, mac, order_no, firmware,
   sinec_hierarchy_name, is_blacklisted, device_status, config_status, device_info,
   updated_on, mc_timestamp)
VALUES
  ('SCALANCE-X200-001', 'SCALANCE X200 #1', 'switch', '172.16.122.190', '00:1B:1B:01:22:90',
   '6GK5200-8AS10-2AA3', 'v4.2.1', 'Plant Floor A', 0, 'online', 1,
   '{"brand": "scalance", "model": "SCALANCE X200", "category": "industrial_switch"}',
   strftime('%s', 'now'), datetime('now')),

  ('SCALANCE-X200-002', 'SCALANCE X200 #2', 'switch', '172.16.122.191', '00:1B:1B:01:22:91',
   '6GK5200-8AS10-2AA3', 'v4.2.1', 'Plant Floor B', 0, 'online', 1,
   '{"brand": "scalance", "model": "SCALANCE X200", "category": "industrial_switch"}',
   strftime('%s', 'now'), datetime('now')),

  ('SCALANCE-XC200-001', 'SCALANCE XC200 Core', 'switch', '172.16.122.100', '00:1B:1B:01:21:00',
   '6GK5200-8AS20-2AB2', 'v5.0.0', 'Server Room', 0, 'online', 1,
   '{"brand": "scalance", "model": "SCALANCE XC200", "category": "industrial_switch"}',
   strftime('%s', 'now'), datetime('now')),

  ('RUGGEDCOM-RS900-001', 'RUGGEDCOM RS900 #1', 'switch', '172.16.122.200', '00:30:A7:01:22:00',
   'RS900-24T-K1-A2-A2', 'v5.6.1', 'Substation A', 0, 'online', 1,
   '{"brand": "ruggedcom", "model": "RUGGEDCOM RS900", "category": "ruggedized_switch"}',
   strftime('%s', 'now'), datetime('now')),

  ('RUGGEDCOM-RS900-002', 'RUGGEDCOM RS900 #2', 'switch', '172.16.122.201', '00:30:A7:01:22:01',
   'RS900-24T-K1-A2-A2', 'v5.6.1', 'Substation B', 0, 'online', 1,
   '{"brand": "ruggedcom", "model": "RUGGEDCOM RS900", "category": "ruggedized_switch"}',
   strftime('%s', 'now'), datetime('now')),

  ('RUGGEDCOM-RS416-001', 'RUGGEDCOM RS416 Gateway', 'router', '172.16.122.210', '00:30:A7:01:22:10',
   'RS416V2-SERIAL-24-24-2TX', 'v5.5.0', 'Control Room', 0, 'online', 1,
   '{"brand": "ruggedcom", "model": "RUGGEDCOM RS416", "category": "ruggedized_router"}',
   strftime('%s', 'now'), datetime('now')),

  ('FW-SIEMENS-001', 'Siemens Firewall #1', 'firewall', '10.0.0.1', '00:1B:1B:FE:00:01',
   '6GK5615-0AA01-2AA2', 'v4.1.2', 'DMZ', 0, 'online', 1,
   '{"brand": "siemens", "model": "SCALANCE S615", "category": "firewall"}',
   strftime('%s', 'now'), datetime('now')),

  ('RT-CORE-001', 'Core Router', 'router', '192.168.1.1', '00:1E:BD:C0:00:01',
   'ISR4431/K9', '17.6.1', 'Data Center', 0, 'online', 1,
   '{"brand": "cisco", "model": "ISR 4431", "category": "core_router"}',
   strftime('%s', 'now'), datetime('now'));
"""


# ══════════════════════════════════════════════════════════════════════════════
# DeviceResolver
# ══════════════════════════════════════════════════════════════════════════════

class DeviceResolver:
    """
    Resolves device references to NMS device_ids.

    Backends (set via constructor or environment variables):
        DB_BACKEND = "postgres" | "sqlite" | "mock"
        DB_URL     = "postgresql://user:pass@host:5432/nmsdb"   (postgres)
        SQLITE_PATH= "/data/devices.db"                          (sqlite)

    Usage:
        # POC / mock
        resolver = DeviceResolver()

        # SQLite (lightweight production)
        resolver = DeviceResolver(db_backend="sqlite", sqlite_path="/data/devices.db")

        # PostgreSQL (full production)
        resolver = DeviceResolver(db_backend="postgres", db_url="postgresql://...")
    """

    def __init__(
        self,
        db_backend: Optional[str]  = None,
        db_url:     Optional[str]  = None,
        sqlite_path: Optional[str] = None,
        # Legacy / POC compat
        nms_base_url: Optional[str] = None,
        token:        Optional[str] = None,
        use_mock:     bool = True,
    ):
        # Resolve backend from args → env → default (mock)
        self.db_backend  = (db_backend or os.getenv("DB_BACKEND", "mock")).lower()
        self.db_url      = db_url      or os.getenv("DB_URL", "")
        self.sqlite_path = sqlite_path or os.getenv("SQLITE_PATH", "/data/devices.db")
        self.token       = token

        # Legacy: if nms_base_url provided, use REST API mode
        self.nms_base_url = nms_base_url or os.getenv("NMS_DEVICE_API_URL", "")

        # Override backend based on legacy settings
        if self.db_backend == "mock" and self.nms_base_url:
            self.db_backend = "rest"
        if use_mock or (self.db_backend == "mock" and not self.db_url and not self.nms_base_url):
            self.db_backend = "mock"

        # DB connection pools (lazy-initialized)
        self._pg_pool  = None   # asyncpg pool (postgres)
        self._sqlite_db = None  # aiosqlite connection (sqlite)

        # In-memory cache for fast lookups
        self._cache: List[Dict[str, Any]] = []
        self._cache_timestamp: float = 0
        self._cache_lock = asyncio.Lock()
        self._refresh_task: Optional[asyncio.Task] = None

        logger.info(f"DeviceResolver initialized (backend={self.db_backend})")

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def initialize(self):
        """
        Initialize DB connection pool and load cache.
        Starts background task for periodic cache refresh.
        For mock backend this is a no-op.
        """
        if self.db_backend == "postgres":
            await self._init_postgres()
        elif self.db_backend == "sqlite":
            await self._init_sqlite()

        # Load initial cache from database
        await self._refresh_cache()
        logger.info(f"✓ Device cache loaded: {len(self._cache)} devices")

        # Start background refresh task (every 15 minutes)
        if self.db_backend in ["postgres", "sqlite"]:
            self._refresh_task = asyncio.create_task(self._cache_refresh_loop())
            logger.info(f"✓ Cache auto-refresh started (interval: {CACHE_REFRESH_INTERVAL}s)")

    async def close(self):
        """Close DB connections and stop background tasks."""
        # Stop refresh task
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Cache refresh task stopped")

        # Close database connections
        if self._pg_pool:
            await self._pg_pool.close()
        if self._sqlite_db:
            await self._sqlite_db.close()

    # ── Public resolve API ─────────────────────────────────────────────────────

    def detect_resolution_mode(self, query: str) -> ResolutionMode:
        """
        Detect if the original NL query contains ALL or ANY ONE intent keywords.

        Examples:
          "Trust all scalance devices"   → ResolutionMode.ALL
          "Copy from any ruggedcom"       → ResolutionMode.ANY_ONE
          "Copy from scalance to ruggedcom" → ResolutionMode.NORMAL

        This is called on the ORIGINAL query (before LLM extraction),
        not on individual device references.
        """
        q = query.lower()
        for kw in _ALL_KEYWORDS:
            if re.search(rf"\b{re.escape(kw)}\b", q):
                return ResolutionMode.ALL
        for kw in _ANY_KEYWORDS:
            if re.search(rf"\b{re.escape(kw)}\b", q):
                return ResolutionMode.ANY_ONE
        return ResolutionMode.NORMAL

    async def resolve(
        self,
        reference: str,
        mode: ResolutionMode = ResolutionMode.NORMAL,
    ) -> List[Dict[str, Any]]:
        """
        Resolve a single device reference to matching device records.

        Args:
            reference : IP, brand, type, partial name, or existing device_id
            mode      : NORMAL | ALL | ANY_ONE

        Returns:
            List of device dicts.
              NORMAL  → 1 device  (pass through)
                      → multiple  (caller decides: ask user OR auto-pick)
              ALL     → all matches (never triggers disambiguation)
              ANY_ONE → exactly [first_match] (never triggers disambiguation)
        """
        ref = reference.strip()
        if not ref:
            return []

        matches = await self._lookup(ref)

        if mode == ResolutionMode.ALL:
            # Return everything — caller will expand to all device IDs
            return matches

        if mode == ResolutionMode.ANY_ONE:
            # Return only first match — caller picks it without asking user
            return matches[:1]

        # NORMAL mode — return all matches; caller handles single vs multiple
        return matches

    async def resolve_many(
        self,
        references: List[str],
        mode: ResolutionMode = ResolutionMode.NORMAL,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Resolve multiple references, applying the same mode to each."""
        results: Dict[str, List[Dict[str, Any]]] = {}
        for ref in references:
            results[ref] = await self.resolve(ref, mode)
        return results

    # ── DB backends ────────────────────────────────────────────────────────────

    async def _lookup(self, reference: str) -> List[Dict[str, Any]]:
        """
        Route lookup to cache or fallback to database.
        Cache is used for postgres/sqlite backends for fast lookups.
        """
        # Use cache for postgres/sqlite (loaded in memory)
        if self.db_backend in ["postgres", "sqlite"] and self._cache:
            return self._cached_lookup(reference)

        # Fallback to direct database query if cache not ready
        if self.db_backend == "postgres":
            return await self._pg_lookup(reference)
        elif self.db_backend == "sqlite":
            return await self._sqlite_lookup(reference)
        elif self.db_backend == "rest":
            return await self._rest_lookup(reference)
        else:
            return _mock_lookup(reference)

    def _cached_lookup(self, reference: str) -> List[Dict[str, Any]]:
        """
        Perform lookup on in-memory cache.
        This is MUCH faster than database queries (< 1ms).

        Priority order:
          1. Exact device_id
          2. IP address
          3. Brand name
          4. Device type
          5. Partial name/model match
        """
        ref_lower = reference.lower()

        # 1. Exact device_id (case-insensitive)
        for device in self._cache:
            if device.get("device_id", "").lower() == ref_lower:
                return [device]

        # 2. IP address (exact match)
        if _IP_RE.match(reference):
            matches = [d for d in self._cache if d.get("ip_address") == reference]
            if matches:
                return matches

        # 3. Brand name (from device_info or flattened brand field)
        for brand in _BRAND_KEYWORDS:
            if brand in ref_lower:
                matches = [
                    d for d in self._cache
                    if d.get("brand", "").lower() == brand
                ]
                if matches:
                    return matches

        # 4. Device type
        for dtype, kws in _TYPE_KEYWORDS.items():
            if any(kw in ref_lower for kw in kws):
                matches = [
                    d for d in self._cache
                    if d.get("device_type", "").lower() == dtype
                ]
                if matches:
                    return matches

        # 5. Partial match on device_name or model
        matches = [
            d for d in self._cache
            if ref_lower in d.get("device_name", "").lower()
            or ref_lower in d.get("model", "").lower()
        ]
        return matches

    # ── Cache management ───────────────────────────────────────────────────────

    async def _refresh_cache(self):
        """
        Refresh cache by loading all devices from database.
        Called on startup and every 15 minutes.
        """
        async with self._cache_lock:
            try:
                logger.info("Refreshing device cache from database...")
                start_time = time.time()

                if self.db_backend == "postgres":
                    devices = await self._load_all_from_postgres()
                elif self.db_backend == "sqlite":
                    devices = await self._load_all_from_sqlite()
                else:
                    devices = _MOCK_DEVICES.copy()

                # Update cache atomically
                self._cache = devices
                self._cache_timestamp = time.time()

                elapsed = (time.time() - start_time) * 1000  # ms
                logger.info(
                    f"✓ Cache refreshed: {len(self._cache)} devices loaded "
                    f"(took {elapsed:.1f}ms, age: 0s)"
                )
            except Exception as e:
                logger.error(f"Failed to refresh cache: {e}", exc_info=True)
                # Keep existing cache if refresh fails

    async def _cache_refresh_loop(self):
        """
        Background task that refreshes cache every 15 minutes.
        Runs continuously until close() is called.
        """
        try:
            while True:
                await asyncio.sleep(CACHE_REFRESH_INTERVAL)

                # Calculate cache age
                cache_age = int(time.time() - self._cache_timestamp)
                logger.info(f"Cache refresh triggered (age: {cache_age}s)")

                await self._refresh_cache()
        except asyncio.CancelledError:
            logger.info("Cache refresh loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Cache refresh loop error: {e}", exc_info=True)

    async def _load_all_from_postgres(self) -> List[Dict[str, Any]]:
        """Load all active devices from PostgreSQL."""
        if not self._pg_pool:
            return []

        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT * FROM device_list
                       WHERE (is_blacklisted IS FALSE OR is_blacklisted IS NULL)
                       ORDER BY device_type, device_name"""
                )
                return [_pg_row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to load devices from PostgreSQL: {e}")
            return []

    async def _load_all_from_sqlite(self) -> List[Dict[str, Any]]:
        """Load all active devices from SQLite."""
        if not self._sqlite_db:
            return []

        try:
            async with self._sqlite_db.execute(
                """SELECT * FROM device_list
                   WHERE (is_blacklisted = 0 OR is_blacklisted IS NULL)
                   ORDER BY device_type, device_name"""
            ) as cursor:
                rows = await cursor.fetchall()
                return [_sqlite_row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to load devices from SQLite: {e}")
            return []

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            {
                "total_devices": int,
                "cache_age_seconds": int,
                "last_refresh": str (ISO timestamp),
                "backend": str
            }
        """
        from datetime import datetime

        cache_age = int(time.time() - self._cache_timestamp) if self._cache_timestamp > 0 else None
        last_refresh = (
            datetime.fromtimestamp(self._cache_timestamp).isoformat()
            if self._cache_timestamp > 0
            else None
        )

        return {
            "total_devices": len(self._cache),
            "cache_age_seconds": cache_age,
            "last_refresh": last_refresh,
            "backend": self.db_backend,
            "refresh_interval_seconds": CACHE_REFRESH_INTERVAL
        }

    # ── PostgreSQL ─────────────────────────────────────────────────────────────

    async def _init_postgres(self):
        """Initialize asyncpg connection pool."""
        try:
            import asyncpg  # noqa: F401 — optional dependency
            self._pg_pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,
                max_size=10,
                command_timeout=10,
            )
            logger.info(f"PostgreSQL pool connected: {self.db_url.split('@')[-1]}")
        except ImportError:
            logger.error(
                "asyncpg not installed. Run: pip install asyncpg\n"
                "Falling back to mock backend."
            )
            self.db_backend = "mock"
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}. Falling back to mock.")
            self.db_backend = "mock"

    async def _pg_lookup(self, reference: str) -> List[Dict[str, Any]]:
        """
        PostgreSQL lookup with priority order:
          1. Exact device_id
          2. IP address
          3. Brand name (from device_info JSONB)
          4. Device type
          5. Full-text partial match on device_name / device_info->>'model'

        Note: Filters out blacklisted devices automatically
        """
        if not self._pg_pool:
            return _mock_lookup(reference)

        ref_lower = reference.lower()
        try:
            async with self._pg_pool.acquire() as conn:
                # 1. Exact device_id (case-insensitive)
                rows = await conn.fetch(
                    """SELECT * FROM device_list
                       WHERE LOWER(device_id) = $1 AND (is_blacklisted IS FALSE OR is_blacklisted IS NULL)""",
                    ref_lower
                )
                if rows:
                    return [_pg_row_to_dict(r) for r in rows]

                # 2. IP address (exact match)
                if _IP_RE.match(reference):
                    rows = await conn.fetch(
                        """SELECT * FROM device_list
                           WHERE ip_address = $1 AND (is_blacklisted IS FALSE OR is_blacklisted IS NULL)""",
                        reference
                    )
                    if rows:
                        return [_pg_row_to_dict(r) for r in rows]

                # 3. Brand name (from JSONB device_info)
                for brand in _BRAND_KEYWORDS:
                    if brand in ref_lower:
                        rows = await conn.fetch(
                            """SELECT * FROM device_list
                               WHERE LOWER(device_info->>'brand') = $1
                               AND (is_blacklisted IS FALSE OR is_blacklisted IS NULL)""",
                            brand
                        )
                        if rows:
                            return [_pg_row_to_dict(r) for r in rows]

                # 4. Device type (exact match on device_type column)
                for dtype, kws in _TYPE_KEYWORDS.items():
                    if any(kw in ref_lower for kw in kws):
                        rows = await conn.fetch(
                            """SELECT * FROM device_list
                               WHERE LOWER(device_type) = $1
                               AND (is_blacklisted IS FALSE OR is_blacklisted IS NULL)""",
                            dtype
                        )
                        if rows:
                            return [_pg_row_to_dict(r) for r in rows]

                # 5. Partial match on device_name or model (JSONB)
                rows = await conn.fetch(
                    """SELECT * FROM device_list
                       WHERE (device_name ILIKE $1 OR device_info->>'model' ILIKE $1)
                       AND (is_blacklisted IS FALSE OR is_blacklisted IS NULL)""",
                    f"%{reference}%"
                )
                return [_pg_row_to_dict(r) for r in rows]

        except Exception as e:
            logger.error(f"PostgreSQL lookup failed for '{reference}': {e}")
            return []

    # ── SQLite ─────────────────────────────────────────────────────────────────

    async def _init_sqlite(self):
        """Initialize aiosqlite connection and create table if needed."""
        try:
            import aiosqlite  # noqa: F401 — optional dependency
            import os as _os
            _os.makedirs(_os.path.dirname(self.sqlite_path) or ".", exist_ok=True)
            self._sqlite_db = await aiosqlite.connect(self.sqlite_path)
            self._sqlite_db.row_factory = aiosqlite.Row
            # Create table + seed with mock data if empty
            await self._sqlite_db.executescript(CREATE_TABLE_SQL_SQLITE)
            await self._sqlite_db.executescript(SEED_SQL_SQLITE)
            await self._sqlite_db.commit()
            logger.info(f"SQLite connected: {self.sqlite_path}")
        except ImportError:
            logger.error(
                "aiosqlite not installed. Run: pip install aiosqlite\n"
                "Falling back to mock backend."
            )
            self.db_backend = "mock"
        except Exception as e:
            logger.error(f"SQLite init failed: {e}. Falling back to mock.")
            self.db_backend = "mock"

    async def _sqlite_lookup(self, reference: str) -> List[Dict[str, Any]]:
        """
        SQLite lookup — same priority as PostgreSQL.
        Uses JSON functions to query device_info field.
        Filters out blacklisted devices.
        """
        if not self._sqlite_db:
            return _mock_lookup(reference)

        ref_lower = reference.lower()
        try:
            # 1. Exact device_id
            async with self._sqlite_db.execute(
                """SELECT * FROM device_list
                   WHERE LOWER(device_id) = ? AND (is_blacklisted = 0 OR is_blacklisted IS NULL)""",
                (ref_lower,)
            ) as cursor:
                rows = await cursor.fetchall()
                if rows:
                    return [_sqlite_row_to_dict(r) for r in rows]

            # 2. IP address
            if _IP_RE.match(reference):
                async with self._sqlite_db.execute(
                    """SELECT * FROM device_list
                       WHERE ip_address = ? AND (is_blacklisted = 0 OR is_blacklisted IS NULL)""",
                    (reference,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    if rows:
                        return [_sqlite_row_to_dict(r) for r in rows]

            # 3. Brand name (extract from JSON device_info)
            import json
            for brand in _BRAND_KEYWORDS:
                if brand in ref_lower:
                    async with self._sqlite_db.execute(
                        """SELECT * FROM device_list
                           WHERE (is_blacklisted = 0 OR is_blacklisted IS NULL)"""
                    ) as cursor:
                        rows = await cursor.fetchall()
                        matches = []
                        for r in rows:
                            try:
                                info = json.loads(r["device_info"]) if r["device_info"] else {}
                                if info.get("brand", "").lower() == brand:
                                    matches.append(_sqlite_row_to_dict(r))
                            except:
                                pass
                        if matches:
                            return matches

            # 4. Device type
            for dtype, kws in _TYPE_KEYWORDS.items():
                if any(kw in ref_lower for kw in kws):
                    async with self._sqlite_db.execute(
                        """SELECT * FROM device_list
                           WHERE LOWER(device_type) = ? AND (is_blacklisted = 0 OR is_blacklisted IS NULL)""",
                        (dtype,)
                    ) as cursor:
                        rows = await cursor.fetchall()
                        if rows:
                            return [_sqlite_row_to_dict(r) for r in rows]

            # 5. Partial device_name or model match
            async with self._sqlite_db.execute(
                """SELECT * FROM device_list
                   WHERE (is_blacklisted = 0 OR is_blacklisted IS NULL)"""
            ) as cursor:
                rows = await cursor.fetchall()
                matches = []
                for r in rows:
                    try:
                        info = json.loads(r["device_info"]) if r["device_info"] else {}
                        name = (r["device_name"] or "").lower()
                        model = info.get("model", "").lower()
                        if ref_lower in name or ref_lower in model:
                            matches.append(_sqlite_row_to_dict(r))
                    except:
                        pass
                return matches

        except Exception as e:
            logger.error(f"SQLite lookup failed for '{reference}': {e}")
            return []

    # ── REST API (legacy NMS HTTP endpoint) ────────────────────────────────────

    async def _rest_lookup(self, reference: str) -> List[Dict[str, Any]]:
        """Call NMS REST API to resolve device reference."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.nms_base_url}/devices",
                    params={"search": reference},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                resp.raise_for_status()
                data = resp.json()
                # Expected: { "devices": [ { "device_id": "...", ... } ] }
                devices = data.get("devices", [])
                # Normalise keys to snake_case if API returns camelCase
                return [_normalise_keys(d) for d in devices]
        except Exception as e:
            logger.error(f"REST lookup failed for '{reference}': {e}")
            return []


# ══════════════════════════════════════════════════════════════════════════════
# Mock lookup (in-memory, no external dependency)
# ══════════════════════════════════════════════════════════════════════════════

def _mock_lookup(reference: str) -> List[Dict[str, Any]]:
    """
    Priority order:
      1. Exact device_id   (pass-through)
      2. IP address        (exact)
      3. Brand name        (all devices of that brand, from device_info)
      4. Device type       (all devices of that type)
      5. Partial name/model

    Filters out blacklisted devices.
    """
    ref_lower = reference.strip().lower()

    # Filter non-blacklisted devices
    active_devices = [d for d in _MOCK_DEVICES if not d.get("is_blacklisted", False)]

    # 1. Exact device_id
    for d in active_devices:
        if d["device_id"].lower() == ref_lower:
            return [d]

    # 2. IP
    if _IP_RE.match(reference.strip()):
        matches = [d for d in active_devices if d.get("ip_address") == reference.strip()]
        if matches:
            return matches

    # 3. Brand (from device_info JSONB)
    for brand in _BRAND_KEYWORDS:
        if brand in ref_lower:
            matches = [
                d for d in active_devices
                if d.get("device_info", {}).get("brand", "").lower() == brand
            ]
            if matches:
                return matches

    # 4. Device type
    for dtype, kws in _TYPE_KEYWORDS.items():
        if any(kw in ref_lower for kw in kws):
            matches = [d for d in active_devices if d.get("device_type", "").lower() == dtype]
            if matches:
                return matches

    # 5. Partial device_name / model (from device_info)
    matches = [
        d for d in active_devices
        if ref_lower in d.get("device_name", "").lower()
        or ref_lower in d.get("device_info", {}).get("model", "").lower()
    ]
    return matches


# ── Database row converters ───────────────────────────────────────────────────

def _pg_row_to_dict(row) -> Dict[str, Any]:
    """
    Convert PostgreSQL asyncpg.Record to dict.
    device_info is already parsed as dict (JSONB → Python dict automatically).
    """
    d = dict(row)
    # Flatten device_info for easier access (optional, preserves compatibility)
    if "device_info" in d and isinstance(d["device_info"], dict):
        info = d.pop("device_info")
        d["brand"] = info.get("brand", "")
        d["model"] = info.get("model", "")
        d["category"] = info.get("category", "")
    return d


def _sqlite_row_to_dict(row) -> Dict[str, Any]:
    """
    Convert SQLite aiosqlite.Row to dict.
    Parses device_info JSON string to dict.
    """
    import json
    d = dict(row)
    # Parse JSON string from device_info
    if "device_info" in d and isinstance(d["device_info"], str):
        try:
            info = json.loads(d["device_info"])
            d["brand"] = info.get("brand", "")
            d["model"] = info.get("model", "")
            d["category"] = info.get("category", "")
        except:
            d["brand"] = ""
            d["model"] = ""
            d["category"] = ""
    return d


# ── Key normaliser (camelCase → snake_case for REST responses) ─────────────────

def _normalise_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise API response keys to snake_case."""
    mapping = {
        "deviceId":    "device_id",
        "displayName": "display_name",
        "deviceName":  "device_name",
        "deviceType":  "device_type",
        "ipAddress":   "ip_address",
    }
    return {mapping.get(k, k): v for k, v in d.items()}

