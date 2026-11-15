from topium_usb_intro.state import SessionTracker


def test_initial_media_does_not_trigger():
    t = SessionTracker()
    assert t.observe({"a"}) == []
    assert t.present == {"a"}


def test_initial_trigger_opt_in():
    t = SessionTracker()
    assert t.observe({"a"}, allow_initial=True) == ["a"]


def test_duplicate_event_debounced():
    t = SessionTracker()
    assert t.observe(set()) == []
    assert t.observe({"a"}) == ["a"]
    assert t.observe({"a"}) == []
    assert t.observe({"a"}) == []


def test_single_missed_scan_does_not_falsely_reconnect():
    t = SessionTracker()
    t.observe(set())
    assert t.observe({"a"}) == ["a"]
    assert t.observe(set()) == []
    assert t.observe({"a"}) == []


def test_confirmed_removal_and_reconnection():
    t = SessionTracker()
    t.observe(set())
    assert t.observe({"a"}) == ["a"]
    assert t.observe(set(), confirmed_removal=True) == []
    assert t.observe({"a"}) == ["a"]


def test_two_missing_scans_release_session():
    t = SessionTracker()
    t.observe(set())
    t.observe({"a"})
    t.observe(set())
    t.observe(set())
    assert t.observe({"a"}) == ["a"]


def test_rebaseline_never_triggers():
    t = SessionTracker()
    t.rebaseline({"a"})
    assert t.observe({"a", "b"}) == ["b"]


def test_many_profiles_independent():
    t = SessionTracker()
    t.observe({"a"})
    assert t.observe({"a", "b", "c"}) == ["b", "c"]
    assert t.observe({"a", "b", "c"}) == []
