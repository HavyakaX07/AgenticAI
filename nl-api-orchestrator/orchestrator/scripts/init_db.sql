-- =============================================================================
-- NMS Device Registry - PostgreSQL Initialization Script
-- =============================================================================
-- This script creates the device_list table and populates it with mock data
-- for testing the Device Resolver with PostgreSQL backend.
--
-- Schema matches production NMS device_list table structure.
-- Automatically executed when PostgreSQL container starts for the first time.
-- =============================================================================

-- Create the device_list table
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

-- Create indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_device_list_ip ON device_list(ip_address);
CREATE INDEX IF NOT EXISTS idx_device_list_type ON device_list(device_type);
CREATE INDEX IF NOT EXISTS idx_device_list_name ON device_list(device_name);
CREATE INDEX IF NOT EXISTS idx_device_list_mac ON device_list(mac);

-- GIN index for JSONB queries on brand/model (PostgreSQL specific)
CREATE INDEX IF NOT EXISTS idx_device_info_brand ON device_list
    USING GIN ((device_info->'brand'));

-- =============================================================================
-- Seed Mock Device Data
-- =============================================================================

INSERT INTO device_list
  (device_id, device_name, device_type, ip_address, mac, order_no, firmware,
   sinec_hierarchy_name, is_blacklisted, device_status, config_status, device_info,
   updated_on, mc_timestamp)
VALUES
  -- SCALANCE Devices (Industrial Switches)
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

  -- RUGGEDCOM Devices (Ruggedized Switches & Routers)
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

  -- Other Devices (Firewall & Router)
  ('FW-SIEMENS-001', 'Siemens Firewall #1', 'firewall', '10.0.0.1', '00:1B:1B:FE:00:01',
   '6GK5615-0AA01-2AA2', 'v4.1.2', 'DMZ', FALSE, 'online', 1,
   '{"brand": "siemens", "model": "SCALANCE S615", "category": "firewall"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text),

  ('RT-CORE-001', 'Core Router', 'router', '192.168.1.1', '00:1E:BD:C0:00:01',
   'ISR4431/K9', '17.6.1', 'Data Center', FALSE, 'online', 1,
   '{"brand": "cisco", "model": "ISR 4431", "category": "core_router"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text),

  -- Additional test devices (mixed brands and types)
  ('SCALANCE-XR500-001', 'SCALANCE XR500 Layer3', 'switch', '172.16.122.150', '00:1B:1B:01:21:50',
   '6GK5500-0AA10-2AA3', 'v5.2.0', 'Distribution Layer', FALSE, 'online', 1,
   '{"brand": "scalance", "model": "SCALANCE XR500", "category": "industrial_switch"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text),

  ('RUGGEDCOM-RSG920-001', 'RUGGEDCOM RSG920', 'switch', '172.16.122.220', '00:30:A7:01:22:20',
   'RSG920P-4GC-4GE-2SFP', 'v6.0.0', 'Substation C', FALSE, 'online', 1,
   '{"brand": "ruggedcom", "model": "RUGGEDCOM RSG920", "category": "ruggedized_switch"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text),

  -- Blacklisted device (for testing filter logic)
  ('SCALANCE-X200-999', 'SCALANCE X200 Retired', 'switch', '172.16.122.199', '00:1B:1B:01:22:99',
   '6GK5200-8AS10-2AA3', 'v3.9.0', 'Decommissioned', TRUE, 'offline', 0,
   '{"brand": "scalance", "model": "SCALANCE X200", "category": "industrial_switch"}'::jsonb,
   EXTRACT(EPOCH FROM NOW())::bigint, NOW()::text)

ON CONFLICT (device_id) DO NOTHING;

-- =============================================================================
-- Verification Query (optional - for manual testing)
-- =============================================================================
-- SELECT device_id, device_name, device_type, ip_address,
--        device_info->>'brand' as brand, device_info->>'model' as model
-- FROM device_list
-- WHERE is_blacklisted = FALSE
-- ORDER BY device_type, device_name;

