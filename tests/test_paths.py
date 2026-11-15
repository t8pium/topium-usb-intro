from pathlib import Path
import pytest
from topium_usb_intro.explorer import UnsafeFolder, safe_relative_directory, folders_to_open
from topium_usb_intro.models import Profile


def test_accept_valid_folder(tmp_path):
    (tmp_path / "Projects" / "Data").mkdir(parents=True)
    assert safe_relative_directory(tmp_path, "Projects\\Data") == (tmp_path / "Projects" / "Data").resolve()


@pytest.mark.parametrize("relative", ["..", "../outside", "Projects/../../outside", "/etc", 
                                      r"C:\\Windows", r"\\\\server\\share", "X:private", "", "Projects:ads"])
def test_reject_unsafe_paths(tmp_path, relative):
    with pytest.raises((UnsafeFolder, ValueError)):
        safe_relative_directory(tmp_path, relative)


def test_reject_symlink_outside_volume(tmp_path):
    inside = tmp_path / "vol"
    outside = tmp_path / "private"
    inside.mkdir()
    outside.mkdir()
    try:
        (inside / "link").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(UnsafeFolder):
        safe_relative_directory(inside, "link")


def test_root_only(tmp_path):
    p = Profile(name="USB", disk_pnp_id="ABC", volume_serial="DEF", volume_guid="")
    assert folders_to_open(p, tmp_path) == [tmp_path.resolve()]


def test_multi_folder_only_existing_and_unique(tmp_path):
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    p = Profile(name="USB", disk_pnp_id="ABC", volume_serial="DEF", volume_guid="",
                folder_mode="multiple", folders=["one", "missing", "one", "two"])
    assert folders_to_open(p, tmp_path) == [(tmp_path / "one").resolve(), (tmp_path / "two").resolve()]


def test_first_valid_folder(tmp_path):
    (tmp_path / "two").mkdir()
    p = Profile(name="USB", disk_pnp_id="ABC", volume_serial="DEF", volume_guid="",
                folder_mode="first", folders=["missing", "two"])
    assert folders_to_open(p, tmp_path) == [(tmp_path / "two").resolve()]
