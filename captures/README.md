# OPPO Enco Buds3 Pro Capture Library

This directory contains the raw ground-truth Bluetooth logs captured during reverse engineering.

---

## 1. Ground Truth Log File

### `btsnoop_hci.log`
*   **Description:** Captures the full connection sequence of the earbuds, including battery polling, touch gesture configuration queries, firmware version verification, and a sequence of EQ preset updates and Game Mode toggles.
*   **Datalink Type:** HCI UART / HCI USB (1001/1002) with 1-byte UART packet type prepended.

---

## 2. Capturing Procedures on Android (Honor/MagicOS)

To capture live Bluetooth traffic:
1.  Open the device dialing screen and input `*#*#2846579#*#*` to open the **ProjectMenu**.
2.  Navigate to **Background Settings** ➔ **Log Settings** ➔ Enable **AP Log** and **Bluetooth Log**.
3.  Reboot the device.
4.  Open the **HeyMelody** application and perform the target actions (e.g. toggle ANC, EQ, or Game Mode).
5.  Extract the log via ADB:
    ```bash
    adb pull /data/log/bt/btsnoop_hci_20260718_193712.log btsnoop_hci.log
    ```

---

## 3. Capturing Procedures on Linux

To capture live Bluetooth traffic on Linux:
1.  Run the system-wide Bluetooth monitor to write raw HCI packets to a PCAPNG log:
    ```bash
    sudo btmon -w captures/rfcomm_negotiation.pcapng
    ```
2.  Optionally, bind a virtual RFCOMM serial interface to monitor transport traffic:
    ```bash
    sudo rfcomm connect 0 60:55:56:22:49:A0 15
    ```
3.  Open Wireshark and attach to the virtual `bluetooth0` or RFCOMM interface to inspect multiplexed DLCI frames.
