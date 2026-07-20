# GATT Profile & Technical Map: OPPO Enco Buds3 Pro

* **Survey Timestamp:** 2026-07-18_18-53-37
* **Target Device MAC Address:** `42:8C:99:7A:6E:11`

| Handle | Type | UUID | Name / Purpose | Properties | Status | Value / Context | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0xA100 | Primary Service | `0000079a-d102-11e1-9b23-00025b00a5a5` | OPPO Custom Service (Fast Pairing/Ecosystem) | — | ⚠️ Proprietary | `—` | Vendor-specific endpoint. Requires protocol analysis. |
| 0xA101 | Characteristic | `0100079a-d102-11e1-9b23-00025b00a5a5` | Unknown Vendor Characteristic | WRITE-WITHOUT-RESPONSE, WRITE | ❓ Proprietary (Unmapped) | `Unreadable / No Read Perms` | Hypothesis: Custom payload/diagnostic channel. |
| 0xA103 | Descriptor | `00002901-0000-1000-8000-00805f9b34fb` | Characteristic User Description | READ/WRITE (Implicit) | ✅ Standard | `Hex: [0x437573746F6D20446174612050617468205258204461746100] | ASCII: "Custom Data Path RX Data"` | Adheres to official Bluetooth SIG Specifications. |
| 0xA104 | Characteristic | `0200079a-d102-11e1-9b23-00025b00a5a5` | Unknown Vendor Characteristic | READ, NOTIFY | ❓ Proprietary (Unmapped) | `0x019A0750A8063F00040198A049225655600008000001` | Hypothesis: Custom payload/diagnostic channel. |
| 0xA106 | Descriptor | `00002902-0000-1000-8000-00805f9b34fb` | Client Characteristic Configuration Descriptor (CCCD) | READ/WRITE (Implicit) | ✅ Standard | `0x0000` | Adheres to official Bluetooth SIG Specifications. |
| 0xA107 | Descriptor | `00002901-0000-1000-8000-00805f9b34fb` | Characteristic User Description | READ/WRITE (Implicit) | ✅ Standard | `Hex: [0x437573746F6D20446174612050617468205458204461746100] | ASCII: "Custom Data Path TX Data"` | Adheres to official Bluetooth SIG Specifications. |
| 0xA200 | Primary Service | `0000079c-d102-11e1-9b23-00025b00a5a5` | OPPO Proprietary Service (Audio Control/ANC/Gestures) | — | ⚠️ Proprietary | `—` | Vendor-specific endpoint. Requires protocol analysis. |
| 0xA201 | Characteristic | `0100079c-d102-11e1-9b23-00025b00a5a5` | Unknown Vendor Characteristic | READ, NOTIFY | ❓ Proprietary (Unmapped) | `⚠️ Bleak Error: (<BleakGATTProtocolErrorCode.VALUE_NOT_ALLOWED: 19>, 'GATT Protocol Error: Value Not Allowed')` | Hypothesis: Custom payload/diagnostic channel. |
| 0xA203 | Descriptor | `00002902-0000-1000-8000-00805f9b34fb` | Client Characteristic Configuration Descriptor (CCCD) | READ/WRITE (Implicit) | ✅ Standard | `0x0000` | Adheres to official Bluetooth SIG Specifications. |
| 0xA204 | Descriptor | `00002901-0000-1000-8000-00805f9b34fb` | Characteristic User Description | READ/WRITE (Implicit) | ✅ Standard | `N/A` | Adheres to official Bluetooth SIG Specifications. |
| 0x8000 | Primary Service | `0000fe2c-0000-1000-8000-00805f9b34fb` | Unknown Profile | — | ❓ Unknown | `—` | Unclassified GATT attribute. |
| 0x8006 | Characteristic | `fe2c1235-8366-4814-8eb0-01de32100bea` | Unknown Vendor Characteristic | WRITE, NOTIFY | ❓ Proprietary (Unmapped) | `Unreadable / No Read Perms` | Hypothesis: Custom payload/diagnostic channel. |
| 0x8008 | Descriptor | `00002902-0000-1000-8000-00805f9b34fb` | Client Characteristic Configuration Descriptor (CCCD) | READ/WRITE (Implicit) | ✅ Standard | `0x0000` | Adheres to official Bluetooth SIG Specifications. |
| 0x8009 | Characteristic | `fe2c1236-8366-4814-8eb0-01de32100bea` | Unknown Vendor Characteristic | WRITE | ❓ Proprietary (Unmapped) | `Unreadable / No Read Perms` | Hypothesis: Custom payload/diagnostic channel. |
| 0x800E | Characteristic | `fe2c123a-8366-4814-8eb0-01de32100bea` | Unknown Vendor Characteristic | READ, WRITE, NOTIFY | ❓ Proprietary (Unmapped) | `0x7F3B7EDC551BB1AF289D8B2042B6A3DE` | Hypothesis: Custom payload/diagnostic channel. |
| 0x8010 | Descriptor | `00002902-0000-1000-8000-00805f9b34fb` | Client Characteristic Configuration Descriptor (CCCD) | READ/WRITE (Implicit) | ✅ Standard | `0x0000` | Adheres to official Bluetooth SIG Specifications. |
| 0x8011 | Characteristic | `fe2c1239-8366-4814-8eb0-01de32100bea` | Unknown Vendor Characteristic | READ | ❓ Proprietary (Unmapped) | `0x010081` | Hypothesis: Custom payload/diagnostic channel. |
| 0x800B | Characteristic | `fe2c1237-8366-4814-8eb0-01de32100bea` | Unknown Vendor Characteristic | WRITE, NOTIFY | ❓ Proprietary (Unmapped) | `Unreadable / No Read Perms` | Hypothesis: Custom payload/diagnostic channel. |
| 0x800D | Descriptor | `00002902-0000-1000-8000-00805f9b34fb` | Client Characteristic Configuration Descriptor (CCCD) | READ/WRITE (Implicit) | ✅ Standard | `0x0000` | Adheres to official Bluetooth SIG Specifications. |
| 0x8003 | Characteristic | `fe2c1234-8366-4814-8eb0-01de32100bea` | Unknown Vendor Characteristic | WRITE, NOTIFY | ❓ Proprietary (Unmapped) | `Unreadable / No Read Perms` | Hypothesis: Custom payload/diagnostic channel. |
| 0x8005 | Descriptor | `00002902-0000-1000-8000-00805f9b34fb` | Client Characteristic Configuration Descriptor (CCCD) | READ/WRITE (Implicit) | ✅ Standard | `0x0000` | Adheres to official Bluetooth SIG Specifications. |
| 0x8001 | Characteristic | `fe2c1233-8366-4814-8eb0-01de32100bea` | Unknown Vendor Characteristic | READ | ❓ Proprietary (Unmapped) | `0x62956400` | Hypothesis: Custom payload/diagnostic channel. |
| 0xA000 | Primary Service | `01000100-0000-1000-8000-009078563412` | Unknown Vendor Characteristic | — | ❓ Proprietary (Unmapped) | `—` | Hypothesis: Custom payload/diagnostic channel. |
| 0xA001 | Characteristic | `03000300-0000-1000-8000-009278563412` | Unknown Vendor Characteristic | WRITE-WITHOUT-RESPONSE, WRITE | ❓ Proprietary (Unmapped) | `Unreadable / No Read Perms` | Hypothesis: Custom payload/diagnostic channel. |
| 0xA003 | Descriptor | `00002901-0000-1000-8000-00805f9b34fb` | Characteristic User Description | READ/WRITE (Implicit) | ✅ Standard | `Hex: [0x446174612050617468205258204461746100] | ASCII: "Data Path RX Data"` | Adheres to official Bluetooth SIG Specifications. |
| 0xA004 | Characteristic | `02000200-0000-1000-8000-009178563412` | Unknown Vendor Characteristic | NOTIFY | ❓ Proprietary (Unmapped) | `Unreadable / No Read Perms` | Hypothesis: Custom payload/diagnostic channel. |
| 0xA006 | Descriptor | `00002902-0000-1000-8000-00805f9b34fb` | Client Characteristic Configuration Descriptor (CCCD) | READ/WRITE (Implicit) | ✅ Standard | `0x0000` | Adheres to official Bluetooth SIG Specifications. |
| 0xA007 | Descriptor | `00002901-0000-1000-8000-00805f9b34fb` | Characteristic User Description | READ/WRITE (Implicit) | ✅ Standard | `Hex: [0x446174612050617468205458204461746100] | ASCII: "Data Path TX Data"` | Adheres to official Bluetooth SIG Specifications. |
| 0x0020 | Primary Service | `00001801-0000-1000-8000-00805f9b34fb` | Generic Attribute Service | — | ✅ Standard | `—` | Adheres to official Bluetooth SIG Specifications. |
| 0x0024 | Characteristic | `00002b29-0000-1000-8000-00805f9b34fb` | Unknown Profile | READ, WRITE | ❓ Unknown | `0x07` | Unclassified GATT attribute. |
| 0x0028 | Characteristic | `00002b2a-0000-1000-8000-00805f9b34fb` | Unknown Profile | READ | ❓ Unknown | `0x16AAEC8FFD09BF33DF582CC5362D7F0E` | Unclassified GATT attribute. |
| 0x0021 | Characteristic | `00002a05-0000-1000-8000-00805f9b34fb` | Service Changed | INDICATE | ✅ Standard | `Unreadable / No Read Perms` | Adheres to official Bluetooth SIG Specifications. |
| 0x0023 | Descriptor | `00002902-0000-1000-8000-00805f9b34fb` | Client Characteristic Configuration Descriptor (CCCD) | READ/WRITE (Implicit) | ✅ Standard | `0x0200` | Adheres to official Bluetooth SIG Specifications. |
| 0x0026 | Characteristic | `00002b3a-0000-1000-8000-00805f9b34fb` | Unknown Profile | READ | ❓ Unknown | `0x01` | Unclassified GATT attribute. |
