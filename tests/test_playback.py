import pytest
from PIL import Image
from topium_usb_intro.gif_frames import load_one_cycle


def test_infinite_loop_gif_decodes_exactly_one_cycle(tmp_path):
    path = tmp_path / "forever.gif"
    a = Image.new("RGB", (12, 12), "red")
    b = Image.new("RGB", (12, 12), "blue")
    a.save(path, format="GIF", save_all=True, append_images=[b], duration=[80, 120], loop=0)
    frames = load_one_cycle(path)
    assert len(frames) == 2
    assert [f.duration_ms for f in frames] == [80, 120]
    assert frames[0].rgba != frames[1].rgba


def test_bad_file_fallback_signal_for_ui(tmp_path):
    path = tmp_path / "broken.gif"
    path.write_bytes(b"hello")
    with pytest.raises(ValueError):
        load_one_cycle(path)


def test_reject_oversized_gif(tmp_path):
    path = tmp_path / "big.gif"
    Image.new("RGB", (2048, 2048), "red").save(path)
    with pytest.raises(ValueError):
        load_one_cycle(path)


def test_loaded_sample_gif():
    from importlib.resources import files
    path = files("topium_usb_intro").joinpath("assets/sample_intro.gif")
    frames = load_one_cycle(str(path))
    assert len(frames) >= 2
    assert sum(f.duration_ms for f in frames) >= 200
