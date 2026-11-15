from dataclasses import replace
import pytest
from topium_usb_intro.models import Profile, same_device, choose_matches


def test_exact_match(profile, usb):
    assert same_device(profile, usb)


def test_changed_drive_letter_keeps_identity(profile, usb):
    assert same_device(profile, replace(usb, mount_point="Z:\\"))


def test_other_usb_drive_rejected(profile, usb):
    assert not same_device(profile, replace(usb, disk_pnp_id="USBSTOR\\NOT_THIS_DISK"))
    assert not same_device(profile, replace(usb, volume_serial="00000000"))


def test_unregistered_fixed_internal_drive_rejected(profile, usb):
    assert not same_device(profile, replace(usb, bus_type="SATA"))


def test_no_generic_label_matching(profile, usb):
    assert not same_device(profile, replace(usb, disk_pnp_id="", volume_serial="", label="TOPIUM DRIVE"))


def test_disable(profile, usb):
    profile.enabled = False
    assert not same_device(profile, usb)


def test_requires_unique_device_identifier(usb):
    with pytest.raises(ValueError):
        Profile.from_volume(replace(usb, disk_pnp_id=""))
    with pytest.raises(ValueError):
        Profile.from_volume(replace(usb, volume_serial="", volume_guid=""))
    with pytest.raises(ValueError):
        Profile.from_volume(replace(usb, bus_type="SATA"))


def test_fallback_to_guid_when_serial_missing(usb):
    adjusted = replace(usb, volume_serial="")
    p = Profile.from_volume(adjusted)
    assert same_device(p, adjusted)
    assert not same_device(p, replace(adjusted, volume_guid="other"))


def test_ambiguous_matches_fail_closed(profile, usb):
    duplicates = [usb, replace(usb, mount_point="F:\\")]
    assert choose_matches([profile], duplicates) == {}


def test_profile_json_round_trip(profile):
    restored = Profile.from_dict(profile.to_dict())
    assert restored.to_dict() == profile.to_dict()
