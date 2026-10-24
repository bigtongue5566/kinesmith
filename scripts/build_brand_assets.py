"""Generate Kinesmith's original geometric icon without models or external artwork."""

from pathlib import Path

from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
image = Image.new("RGB", (1024, 1024), "#102c32")
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((100, 100, 924, 924), radius=190, fill="#153b42")
draw.line((330, 285, 330, 740), fill="#f1efe5", width=88)
draw.line((365, 515, 655, 285), fill="#f1efe5", width=86)
draw.line((386, 500, 680, 740), fill="#ffb454", width=86)
for x, y, radius in ((692, 256, 34), (766, 208, 22), (822, 177, 12)):
    draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill="#64d9c5")
(root / "assets").mkdir(exist_ok=True)
image.save(root / "assets/icon.png", optimize=True)
