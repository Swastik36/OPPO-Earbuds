"""
Direct BlueZ D-Bus control — operates on the OS-level Bluetooth pairing/link,
NOT the app's own RFCOMM control socket (see device.py / OppoDevice for that).

Use this only for administrative/troubleshooting actions: forcing a full
Bluetooth disconnect or reconnect of the earbuds at the system level, the
same thing a desktop Bluetooth settings panel would do. This will drop
audio (A2DP/HSP) too, not just this app's control channel.
"""
import logging

logger = logging.getLogger("oppo_control.bluetooth_control")


class BluetoothControlError(Exception):
    """Raised when a BlueZ D-Bus operation can't be completed."""
    pass


def _find_device_path(bus, mac_address: str) -> str:
    import dbus

    manager = dbus.Interface(
        bus.get_object("org.bluez", "/"),
        "org.freedesktop.DBus.ObjectManager"
    )
    objects = manager.GetManagedObjects()

    mac_suffix = "dev_" + mac_address.upper().replace(":", "_")
    for path, interfaces in objects.items():
        if "org.bluez.Device1" in interfaces and path.endswith(mac_suffix):
            return path

    raise BluetoothControlError(
        f"No BlueZ device object found for {mac_address}. "
        "Is it paired with this system at all?"
    )


def bt_disconnect(mac_address: str) -> None:
    """Force-disconnect the earbuds from this machine at the OS Bluetooth level.

    Blocking call — run via loop.run_in_executor from async code.
    """
    try:
        import dbus
    except ImportError as e:
        import sys
        logger.error(f"dbus import failed. sys.executable={sys.executable!r} sys.path={sys.path!r}")
        raise BluetoothControlError(
            f"Could not import dbus-python ({e}). If `pip`/your package manager "
            "reports it as already installed, this usually means the app's Python "
            "interpreter isn't the one the package was installed for — check "
            "`sys.executable` from inside the running app."
        ) from e

    try:
        bus = dbus.SystemBus()
        device_path = _find_device_path(bus, mac_address)
        device = dbus.Interface(bus.get_object("org.bluez", device_path), "org.bluez.Device1")
        device.Disconnect()
        logger.info(f"BlueZ: forced OS-level disconnect of {mac_address}")
    except BluetoothControlError:
        raise
    except Exception as e:
        raise BluetoothControlError(f"BlueZ disconnect failed: {e}") from e


def bt_connect(mac_address: str) -> None:
    """Force-reconnect the earbuds at the OS Bluetooth level.

    Blocking call — run via loop.run_in_executor from async code.
    """
    try:
        import dbus
    except ImportError as e:
        import sys
        logger.error(f"dbus import failed. sys.executable={sys.executable!r} sys.path={sys.path!r}")
        raise BluetoothControlError(
            f"Could not import dbus-python ({e}). If `pip`/your package manager "
            "reports it as already installed, this usually means the app's Python "
            "interpreter isn't the one the package was installed for — check "
            "`sys.executable` from inside the running app."
        ) from e

    try:
        bus = dbus.SystemBus()
        device_path = _find_device_path(bus, mac_address)
        device = dbus.Interface(bus.get_object("org.bluez", device_path), "org.bluez.Device1")
        device.Connect()
        logger.info(f"BlueZ: forced OS-level reconnect of {mac_address}")
    except BluetoothControlError:
        raise
    except Exception as e:
        raise BluetoothControlError(f"BlueZ connect failed: {e}") from e
