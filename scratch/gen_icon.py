from PIL import Image, ImageDraw, ImageFont
import os

img = Image.new("RGBA", (512, 512), (6, 4, 1, 255))
draw = ImageDraw.Draw(img)

# Outer glowing rings
draw.ellipse((20, 20, 492, 492), outline=(255, 179, 0, 180), width=6)
draw.ellipse((40, 40, 472, 472), outline=(255, 111, 0, 120), width=3)
draw.ellipse((60, 60, 452, 452), outline=(255, 215, 0, 80), width=2)

# Central stylized U
# Left arm
draw.rounded_rectangle((156, 140, 196, 310), radius=10, fill=(255, 179, 0, 255))
# Right arm
draw.rounded_rectangle((316, 140, 356, 310), radius=10, fill=(255, 179, 0, 255))
# Bottom arc
draw.arc((156, 230, 356, 370), start=0, end=180, fill=(255, 179, 0, 255), width=40)

# Inner core glow
draw.ellipse((240, 240, 272, 272), fill=(255, 249, 196, 255))

out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "icon.png")
img.save(out_path, "PNG")
print(f"Generated {out_path}")
