# OPPO Enco Buds3 Pro Control Protocol (RFCOMM DLCI 30)

Through reverse-engineering the Android **HeyMelody** app Bluetooth snoop log, we discovered that the app communicates with the earbuds using **Bluetooth Classic RFCOMM DLCI 30** (Serial Port Profile) instead of BLE GATT for runtime controls when connected to Android.

The communication uses a custom packet framing format starting with sync byte `0xAA`.

---

## 1. Frame Structure

Every command frame follows this binary format:

| Byte Index | Field | Description |
| :--- | :--- | :--- |
| `0` | **Sync Byte** | Always `0xAA` |
| `1` | **Length** | Number of bytes following this length byte |
| `2 - 3` | **Sequence / Session** | Always `0x00 00` |
| `4` | **Command Group** | Identifies the subsystem (e.g., EQ, Game Mode, Battery) |
| `5` | **Command ID** | `0x01` = Read, `0x04` = Write, `0x05` = Notify. Responses set the MSB (e.g., `0x81` = Read Resp, `0x84` = Write Resp) |
| `6` | **Transaction Seq ID** | Monotonically increasing ID matching requests and responses |
| `7+` | **Payload** | Variable-length parameter payload |

---

## 2. Feature Command Mappings

### A. Battery Status Reporting
*   **Command Group:** `0x05` (Status Read / Response)
*   **Query Command:**
    *   **TX (Request):** `AA 07 00 00 05 01 [Seq] 00 00`
    *   **RX (Response):** `AA 20 00 00 05 81 [Seq] 19 00 00 03 [Battery CSV String]`

#### Battery CSV Payload Format:
The payload begins with `03` (representing 3 device records: Left Bud, Right Bud, Charging Case), followed by an ASCII CSV string:
`[Device_ID],[Charging_State],[Battery_Value]`

*   **Device ID:** `1` = Left Bud, `2` = Right Bud, `3` = Charging Case.
*   **Charging State:** `2` = Charging, `1` = Discharging.
*   **Battery Value:**
    *   If **Discharging**: The value represents the exact battery percentage (e.g. `85` for `85%`).
*   If **Charging**: The value is offset by `100` (e.g., `118` represents charging at `18%`; `102` represents charging at `2%`).

*Example value from log:* `1,2,118,2,2,118,3,2,102` decodes to:
*   Left earbud: Charging, 18% battery.
*   Right earbud: Charging, 18% battery.
*   Charging case: Charging, 2% battery.

---

### B. Sound Master EQ (Audio Effects)
*   **Command Group:** `0x06` (Write Control), `0x0F` (Status Read / Response), `0x04` (Status Notification)
*   **Property ID (inside payload):** `0x01`

#### Commands:
*   **Read Current EQ:**
    *   **TX (Request):** `AA 07 00 00 0F 01 [Seq] 00 00`
    *   **RX (Response):** `AA 09 00 00 0F 81 [Seq] 02 00 00 [Value]`
*   **Write EQ Preset:**
    *   **TX (Write):** `AA 08 00 00 06 04 [Seq] 01 00 [Value]`
    *   **RX (Ack):** `AA 08 00 00 06 84 [Seq] 01 00 00`
*   **State Changed Notification:**
    *   **RX (Push):** `AA 08 00 00 04 05 00 01 00 [Value]`

#### EQ Values:
*   `0x00`: **Original / Balanced**
*   `0x01`: **Bass Boost**
*   `0x02`: **Clear Vocals**

---

### C. Game Mode (Low Latency)
*   **Command Group:** `0x03` (Write / Notify Control), `0x0D` (Status Read / Response)
*   **Parameter ID (inside payload):** `0x28`

#### Commands:
*   **Read Current Settings (Multiple Parameters Query):**
    *   **TX (Request):** `AA 0E 00 00 0D 01 [Seq] 07 00 06 05 11 06 1B 27 28` (queries 7 parameters, including `0x28` Game Mode)
    *   **RX (Response):** `AA 15 00 00 0D 81 [Seq] 0E 00 00 ... 28 [Value]` (contains key-value pairs, where parameter `0x28` has the trailing `Value` byte)
*   **Write Game Mode:**
    *   **TX (Write):** `AA 09 00 00 03 04 [Seq] 02 00 28 [Value]`
    *   **RX (Ack):** `AA 08 00 00 03 84 [Seq] 01 00 00`
*   **State Changed Notification:**
    *   **RX (Push):** `AA 0B 00 00 03 05 00 04 00 01 28 [Value] 01`

#### Game Mode Values:
*   `0x00`: **OFF**
*   `0x01`: **ON**

---

### D. Firmware Version Information
*   **Command Group:** `0x07` (or `0x09`)
*   **Query Command:**
    *   **TX (Request):** `AA 07 00 00 07 01 [Seq] 00 00`
    *   **RX (Response):** `AA 0D 00 00 07 81 [Seq] 06 00 00 02 01 01 02 01`

#### Version Payload Format:
The payload ends in 5 bytes representing the parsed version levels:
*   `02 01 01 02 01` ➔ Firmware version: `2.1.1.2.1`

---

### E. Touch Gesture Configuration Matrix
*   **Command Group:** `0x08` (Read / Response)
*   **Query Command:**
    *   **TX (Request):** `AA 09 00 00 08 01 [Seq] 02 00 02 03`
    *   **RX (Response):** `AA 69 00 00 08 81 [Seq] 62 00 00 18 01 01 ...`

#### Gesture Matrix Format:
The response contains `18` (hex, which is 24 records) followed by 24 records of **4 bytes** each:
`[Earbud_ID] [Action_Type] [Gesture_Trigger_ID] [Function_Action_ID]`

#### Mappings:
1.  **Earbud ID (Byte 0):** `01` = Left, `02` = Right
2.  **Action Type (Byte 1):** `01` = Basic Touch, `06` = Custom Swipe/Long-press
3.  **Gesture Trigger ID (Byte 2):**
    *   `01`: Single Tap
    *   `02`: Double Tap
    *   `03`: Triple Tap
    *   `04`: Long Press
    *   `05`: Double Tap & Hold
    *   `06`: Slide
4.  **Function Action ID (Byte 3):**
    *   `00`: No Action
    *   `01`: Play / Pause
    *   `05`: Previous Track
    *   `06`: Next Track
    *   `0B` or `0C`: Volume Control
    *   `1C` or `1D`: Game Mode Toggle

---

## 3. Real-Time Telemetry Updates (Group 0x04)

During live operations (e.g., when the HeyMelody app is open and you take buds in or out of the case), the earbuds push real-time telemetry packets to the phone on **Command Group `0x04`** and **Command ID `0x02`** (Write / Notify).

The general frame layout is:
`AA [frame_len] 00 00 04 02 [seq_id] [payload_len_L] [payload_len_H] [payload...]`

The payload structure has a unified format:
`[report_type] [item_count] [id_1] [val_1] [id_2] [val_2] ...`

### A. Real-Time Battery Levels Update
*   **Payload Length:** `08 00` (8 bytes)
*   **Actual Payload:** `01 03 01 [Left_Value] 02 [Right_Value] 03 [Case_Value]`
    *   `01`: Report Type (Battery Levels)
    *   `03`: Number of items (3)
    *   `01 [Left_Value]`: Left Bud battery percentage (e.g., `5A` = 90%)
    *   `02 [Right_Value]`: Right Bud battery percentage (e.g., `5A` = 90%)
    *   `03 [Case_Value]`: Case battery percentage (e.g., `64` = 100%, or `00` if case is closed/uncommunicating)

### B. Real-Time Charging Status Update
*   **Payload Length:** `08 00` (8 bytes)
*   **Actual Payload:** `02 03 01 [Left_Charging] 02 [Right_Charging] 03 [Case_Charging]`
    *   `02`: Report Type (State Info)
    *   `03`: Number of items (3)
    *   `01 [Left_Charging]`: Left bud charging status
    *   `02 [Right_Charging]`: Right bud charging status
    *   `03 [Case_Charging]`: Case charging status
*   **Status Mappings:**
    *   `0x00`: Discharging / None
    *   `0x01`: Charging
    *   `0x02`: Full
    *   `0x04`: Connected to USB power (USB/Powered)

### C. Real-Time Placement / Wearing Status Update
*   **Payload Length:** `06 00` (6 bytes)
*   **Actual Payload:** `02 02 01 [Left_Placement] 02 [Right_Placement]`
    *   `02`: Report Type (State Info)
    *   `02`: Number of items (2)
    *   `01 [Left_Placement]`: Left bud placement status
    *   `02 [Right_Placement]`: Right bud placement status
*   **Status Mappings:**
    *   `0x00`: **In-Case**
    *   `0x01`: **Out-of-Case** (Active/Worn)
