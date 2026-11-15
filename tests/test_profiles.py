import json
import pytest
from topium_usb_intro.profiles import AppConfig, load_config, save_config


def test_default_config_when_missing(tmp_path):
    assert load_config(tmp_path / "missing.json").profiles == []


def test_atomic_persistence(profile, tmp_path):
    path = tmp_path / "app" / "config.json"
    original = AppConfig(profiles=[profile], autostart=True)
    save_config(original, path)
    new = load_config(path)
    assert new.to_dict() == original.to_dict()
    assert not list(path.parent.glob("*.tmp"))


def test_reject_unknown_config_version(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"version": 99}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)


def test_reject_duplicate_profile_id(profile, tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"version": 1, "profiles": [profile.to_dict(), profile.to_dict()]}))
    with pytest.raises(ValueError):
        load_config(path)
