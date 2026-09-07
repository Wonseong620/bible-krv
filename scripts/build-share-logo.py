"""Render the site's existing arch/cross wordmark as a share image."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SCALE = 3
image = Image.new('RGB', (1200*SCALE, 630*SCALE), '#faf9f5')
draw = ImageDraw.Draw(image)
def box(coords): return tuple(int(v*SCALE) for v in coords)
title = ImageFont.truetype('/System/Library/Fonts/Supplemental/AppleMyungjo.ttf', 82*SCALE)
subtitle = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 25*SCALE)
width = draw.textlength('말씀 곁에', font=title)/SCALE
group_width = 112 + 34 + width
left = (1200-group_width)/2
# Same pine arch and equal-arm cross as the existing header's brand-mark.
draw.rounded_rectangle(box((left,245,left+112,385)), radius=56*SCALE, fill='#244d43')
draw.rectangle(box((left,301,left+112,379)), fill='#244d43')
draw.rounded_rectangle(box((left,369,left+112,385)), radius=6*SCALE, fill='#244d43')
cx,cy = left+56,310
draw.line(box((cx-23,cy,cx+23,cy)), fill='#faf9f5', width=4*SCALE)
draw.line(box((cx,cy-23,cx,cy+23)), fill='#faf9f5', width=4*SCALE)
x = left+146
draw.text((x*SCALE,247*SCALE), '말씀 곁에', font=title, fill='#262f2b', anchor='lt')
draw.text((x*SCALE,352*SCALE), '성경 고민상담소', font=subtitle, fill='#69706a', anchor='lt')
image.resize((1200,630), Image.Resampling.LANCZOS).save(ROOT/'share-logo-v1.png', optimize=True)
print(ROOT/'share-logo-v1.png')
