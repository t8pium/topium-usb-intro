import pytest
from topium_usb_intro.models import UsbVolume, Profile

@pytest.fixture
def usb():
    return UsbVolume(
        disk_pnp_id=r"USBSTOR\DISK&VEN_ACME&PROD_PORTABLE\ABC123",
        disk_serial="ABC123", disk_model="ACME Drive", volume_serial="DEADBEEF",
        volume_guid="\\\\?\\Volume{1234-5678}\\", mount_point="E:\\", disk_index=5,
        bus_type="USB", label="TOPIUM DRIVE",
    )

@pytest.fixture
def profile(usb):
    return Profile.from_volume(usb)
