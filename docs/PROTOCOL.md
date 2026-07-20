# RFCOMM OPPO Protocol Specification
**Version 1.0**  
**Author:** OPPO Linux Companion Community  
**Status:** Released Public Reference  

This document serves as the definitive reference specification for the proprietary Bluetooth Classic application-layer control protocol used by the OPPO, OnePlus, and Realme family of wireless earbuds (the protocol driving the official *HeyMelody* mobile application).

---

## 1. Transport Layer

The protocol operates over classic Bluetooth stream sockets using the RFCOMM transport profile:
*   **Service Name:** SPP (Serial Port Profile)
*   **SPP UUID:** `00001107-D102-11E1-9B23-00025B00A5A5`
*   **RFCOMM Channel:** Fixed to **Server Channel 15** (DLCI 30).
*   **Negotiation:** No custom initialization handshake is required. Sockets accept command envelopes immediately upon link establishment.

---

## 2. Framing & Envelope Structures

Communication utilizes two layers: an outer **`OPOv1` Link Layer** wrapping an inner **`Packet` Application Layer**.

```text
+-------------------+----------------------------+-----------------------+
|  SOF Byte (0xAA)  | Link Length (Varint 1-N B) | Link Header (2 Bytes) |
+-------------------+----------------------------+-----------------------+
|                                                                        |
|  +--------------------+------------------------+--------------------+  |
|  |  Command (LE 2 B)  |  Sequence ID (U8 1 B)  |  PayLen (LE 2 B)   |  |
|  +--------------------+------------------------+--------------------+  |
|  |                                                                  |  |
|  |  Payload Bytes (PayLen Bytes...)                                 |  |
|  |                                                                  |  |
|  +------------------------------------------------------------------+  |
|                                                                        |
+------------------------------------------------------------------------+
```

### 2.1 Outer `OPOv1` Link Envelope
1.  **SOF (Start of Frame) [1 Byte]:** Constant byte `0xAA`.
2.  **Link Length [Variable 1-N Bytes]:** A 7-bit Little Endian Varint representing the size of the remaining bytes in the frame.
    *   *Calculation:* For each byte, the lower 7 bits represent value bits, and the MSB (bit 7) is a continuation flag. If bit 7 is `1`, read the next byte and shift it left by 7 bits.
    *   *Length Scope:* Varint length includes the 2-byte Link Header + the entire inner packet, but excludes the SOF and Varint length bytes themselves.
    *   *Single-Byte Note:* For all standard telemetry query and control payloads (which are under 128 bytes in length), the Varint encoding fits into a **single byte** (since the continuation MSB bit remains `0`). It only expands to multiple bytes for bulk transfers like firmware block pushes.

3.  **Link Header [2 Bytes]:** Constant padding bytes `0x00 0x00` indicating an unfragmented connection session frame.

### 2.2 Inner Application Packet
1.  **Command Word [2 Bytes - Little Endian]:** Identifies the subsystem and operation.
    *   **Upper Byte (Command Class):**
        *   `0x01`: Query / Read Request
        *   `0x04`: Control / Write Command
        *   `0x05`: Push Notification / Telemetry Status update
        *   `0x81`: Query Response (MSB set high for acknowledgment)
        *   `0x84`: Write Response / Acknowledgment
    *   **Lower Byte (Feature Space):**
        *   `0x03`: Game Mode
        *   `0x04`: Active Noise Cancellation (ANC)
        *   `0x05`: Battery Telemetry Reporting
        *   `0x06`: Sound Master EQ Control
        *   `0x07`: Firmware Version
        *   `0x08`: Touch Gestures Map
        *   `0x27`: Prompt Tone Volume Write
        *   `0x30`: Prompt Tone Volume Read
        *   `0x0F`: EQ Status Read Space
2.  **Sequence ID [1 Byte]:** Transaction counter used to pair requests and responses. Values range from `0x00` to `0xFE`. Sequence ID `0xFF` or `0x00` is reserved for unsolicited status events pushed from the device.
3.  **Payload Length [2 Bytes - Little Endian]:** Specifies the size of the following payload arguments.
4.  **Payload [Variable Length]:** Parameter-specific argument bytes.

---

## 3. Core Features & Payload Map

### 3.1 Battery Telemetry
*   **Query Command:** `0x0105` (`05 01` in LE)
*   **Response Command:** `0x8105` (`05 81` in LE) or `0x8106`

#### Dual-Format Telemetry Representation
Depending on the firmware generation, battery telemetry is reported in one of two formats:

1.  **ASCII CSV Format (Modern - e.g. Enco Buds3 Pro):**
    *   Payload starts with a 4-byte header: `0x19 0x00 0x00 0x03` (25 bytes payload length, 3 records).
    *   Followed by an ASCII CSV string: `[Device_ID],[Charging_State],[Battery_Value]`
        *   **Device ID:** `1` = Left, `2` = Right, `3` = Case
        *   **Charging State:** `1` = Discharging, `2` = Charging
        *   **Battery Value:** Percent level (if charging, offset by +100).
*   *Example CSV:* `1,2,118,2,2,118,3,2,102` (Left: 18% Charging, Right: 18% Charging, Case: 2% Charging).

2.  **Packed Binary Format (Legacy):**
    *   `payload[0]`: Padding status.
    *   `payload[1]`: Count of records (usually 3).
    *   Subsequent 2-byte tuples: `[battery_id] [battery_info]`
        *   `battery_id`: `1` = Left, `2` = Right, `3` = Case
        *   `battery_info`: bit 7 is charging flag; bits 0-6 represent battery percentage.

---

### 3.2 Firmware Version
*   **Query Command:** `0x0107` (`07 01` in LE) or `0x0105`
*   **Response Command:** `0x8107` (`07 81` in LE) or `0x8105`

#### Dual-Format Firmware Representation
1.  **Binary Format (Modern):**
    *   `payload[0]`: Count of records (`0x06`).
    *   `payload[3:8]`: 5 version bytes parsed directly (e.g. `2.1.1.2.1`).
2.  **ASCII CSV Format (Legacy):**
    *   Decoded payload yields a CSV string listing version types: `[part_id],[type],[version]`.

---

### 3.3 Sound Master Equalizer
*   **Query Command:** `0x010F` (`0F 01` in LE)
*   **Write Command:** `0x0406` (`06 04` in LE)
*   **Response/Ack:** `0x810F` / `0x8406`

#### EQ Presets
*   `0x00`: Original (Balanced tuning)
*   `0x01`: Bass Boost
*   `0x02`: Clear Vocals (Vocals enhancement)

*   **EQ Write Payload:** `0x01 0x00 [preset_idx]` (3 bytes).
*   **EQ Read Response Payload:** `0x02 0x00 0x00 [preset_idx]` (4 bytes).

---

### 3.4 Low-Latency Game Mode
*   **Query Command:** `0x010D` (`0D 01` in LE - Batch feature query)
*   **Write Command:** `0x0403` (`03 04` in LE - Write feature switch)

*   **Game Mode Write Payload:** `0x02 0x00 0x28 [status]` where `status` is `0x01` (ON) or `0x00` (OFF).
*   **Game Mode Read Response Payload:** Search for status byte tuple `0x28 [status]`.

---

### 3.5 Touch Gesture Remapping
*   **Query Command:** `0x0108` (`08 01` in LE)
*   **Write Command:** `0x0401` (`01 04` in LE)

*   **Gesture Config Record (4 Bytes):** `[earbud_id] [action_type] [trigger_id] [function_id]`
    *   **earbud_id:** `1` = Left Bud, `2` = Right Bud
    *   **action_type:** `1` = Basic Tap, `6` = Custom Swipe/Long-press
    *   **trigger_id:** `1` = Single, `2` = Double, `3` = Triple, `4` = Long Press, `5` = Double & Hold, `6` = Slide
    *   **function_id:** `0` = None, `1` = Play/Pause, `5` = Prev Track, `6` = Next Track, `0x0B` = Volume-, `0x0C` = Volume+, `0x1C`/`0x1D` = Game Mode Toggle
*   **Write Payload:** `<count:1> [gesture_records...]` (Count of 4-byte records to write).

---

### 3.6 Find My Earbuds (Ringing Alert)
*   **Write Command:** `0x0400` (`00 04` in LE)
*   **Ack:** `0x8400`

*   **Ringing Payload:** `[status]`
    *   `0x01`: Start ringing alert tone on the earbuds.
    *   `0x00`: Stop ringing alert tone.

---

### 3.7 Prompt Sound Volume
*   **Query Command:** `0x0130` (`30 01` in LE)
*   **Write Command:** `0x0427` (`27 04` in LE)

*   **Volume Payload:** `[volume_byte]` (Value between `0` and `100` representing percentage).
