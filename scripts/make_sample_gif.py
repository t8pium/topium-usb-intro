"""Generate an original paletted GIF with true transparent exterior (no assets needed)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def make(output: Path) -> None:
    width, height = 440, 200
    palette = [
        (0, 0, 0),       # 0 transparent outside the rounded panel
        (18, 25, 42),    # 1 panel
        (60, 170, 255),  # 2 outline
        (223, 240, 255), # 3 main text
        (100, 215, 255), # 4 subtitle
        (75, 200, 255),  # 5 loading line
    ]
    flat = [channel for color in palette for channel in color] + [0] * (768 - len(palette) * 3)
    font = ImageFont.load_default()
    frames: list[Image.Image] = []
    for i in range(15):
        image = Image.new("P", (width, height), color=0)
        image.putpalette(flat)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, width - 8, height - 8), radius=32,
                               fill=1, outline=2, width=3)
        draw.text((42, 55), "T O P I U M", fill=3, font=font, stroke_width=1)
        if i >= 3:
            draw.text((42, 98), "USB CONNECTED", fill=4, font=font)
        draw.rounded_rectangle((42, 138, 42 + int((width - 84) * (i + 1) / 15), 149),
                               radius=4, fill=5)
        frames.append(image)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(output, format="GIF", save_all=True, append_images=frames[1:],
                   duration=[90] * len(frames), loop=0, disposal=2,
                   transparency=0, optimize=False)
    print(output)


if __name__ == "__main__":
    make(Path(__file__).resolve().parents[1] /
         "src/topium_usb_intro/assets/sample_intro.gif")
