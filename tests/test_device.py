import asyncio

import pytest

from oppo_control.device import OppoDevice
from oppo_control.devices import EncoBuds3ProProfile
from oppo_control.exceptions import OppoError


def test_anc_raises_on_hardware_without_anc():
    """A stub must not report success for unsupported hardware."""
    device = OppoDevice("00:00:00:00:00:00")
    device.profile = EncoBuds3ProProfile

    with pytest.raises(OppoError):
        asyncio.run(device.set_anc_mode("on"))
