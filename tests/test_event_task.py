"""Tests for declarative event triggered Task Scheduler setup (no Windows mutation)."""
from xml.etree import ElementTree as ET
import pytest

from topium_usb_intro.event_task import build_task_xml, NS, PNP_GUID
from topium_usb_intro.models import Profile
from topium_usb_intro.event_match import event_matches_profile, should_play, normalized_id


def test_task_xml_has_only_event_trigger_and_runs_as_interactive_user():
    src = build_task_xml("S-1-5-21-1000-2000-3000-1001", r"C:\TOPIUM\intro.exe",
                         '--on-connect --event-device-id "$(deviceId)"')
    root = ET.fromstring(src)
    def find(path):
        result = root.find(path, {"t": NS})
        assert result is not None
        return result
    assert find("t:Triggers/t:EventTrigger/t:Enabled").text == "true"
    query = find("t:Triggers/t:EventTrigger/t:Subscription").text
    assert "EventID=6416" in query
    assert "ClassName" in query and "DiskDrive" in query
    assert "Security" in query
    assert find("t:Triggers/t:EventTrigger/t:ValueQueries/t:Value").text == (
        "Event/EventData/Data[@Name='DeviceId']")
    assert find("t:Principals/t:Principal/t:UserId").text.endswith("-1001")
    assert find("t:Principals/t:Principal/t:LogonType").text == "InteractiveToken"
    assert find("t:Principals/t:Principal/t:RunLevel").text == "LeastPrivilege"
    assert find("t:Settings/t:MultipleInstancesPolicy").text == "IgnoreNew"
    assert find("t:Actions/t:Exec/t:Command").text == r"C:\TOPIUM\intro.exe"
    assert '"$(deviceId)"' in find("t:Actions/t:Exec/t:Arguments").text
    assert not root.findall(".//t:BootTrigger", {"t": NS})
    assert not root.findall(".//t:LogonTrigger", {"t": NS})


def test_invalid_launcher_refused():
    with pytest.raises(ValueError):
        build_task_xml("S-1-5-5", "intro.exe", "--on-connect")
    with pytest.raises(ValueError):
        build_task_xml("not-a-sid", r"C:\program.exe", "")


def test_event_id_match_independent_of_case_and_drive_letter():
    profile = Profile(name="USB", disk_pnp_id=r"SCSI\Disk&Ven_Seagate\ABC123",
                      volume_serial="AB1234", volume_guid="")
    assert event_matches_profile(r"scsi\disk&ven_seagate\abc123", profile)
    assert not event_matches_profile(r"SCSI\Disk&Ven_Seagate\OTHER", profile)
    assert not event_matches_profile("", profile)
    assert normalized_id("  FOO\\ ") == "foo"


def test_debounce_window():
    assert not should_play(104, 100)
    assert should_play(105, 100)
    assert should_play(120, 100)
    assert not should_play(99, 100)


def test_pnp_auditing_guid_is_explicit():
    assert PNP_GUID.casefold() == "{0cce9248-69ae-11d9-bed3-505054503030}"
