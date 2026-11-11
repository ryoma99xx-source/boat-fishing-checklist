"""Draws the タイラバカウンター icon (plain shapes, no photos): a tairaba head with a necktie and hook
on the site's night-navy ground. Writes public/tairaba/icon-512.png, icon-192.png, icon-180.png, favicon.png."""
import math, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'public', 'tairaba')
S = 1024  # draw large, then shrink

def font(size):
    for p in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def draw():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=200, fill=(11, 20, 34, 255))
    # necktie strands (behind the head): wavy ribbons streaming down-right
    for i, (col, off) in enumerate([((255, 122, 40), -70), ((232, 54, 72), 0), ((255, 178, 60), 70)]):
        pts = []
        for t in range(0, 101):
            u = t / 100
            x = 470 + off * 0.6 + u * 380
            y = 470 + off + u * 330 + math.sin(u * math.pi * 3 + i) * 34
            pts.append((x, y))
        d.line(pts, fill=col + (255,), width=46, joint='curve')
    # skirt (thin rubber strands)
    for k in range(9):
        a = math.radians(18 + k * 6)
        d.line([(470, 470), (470 + math.cos(a) * 330, 470 + math.sin(a) * 330)], fill=(255, 210, 120, 220), width=10)
    # head (sinker): red sphere with highlight and eye
    cx, cy, r = 400, 400, 210
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(214, 32, 52, 255))
    d.ellipse([cx - r + 40, cy - r + 30, cx - 10, cy - 30], fill=(244, 92, 102, 255))
    d.ellipse([cx - 70, cy - 40, cx + 50, cy + 80], fill=(255, 255, 255, 255))
    d.ellipse([cx - 35, cy - 5, cx + 25, cy + 55], fill=(20, 20, 24, 255))
    # hook: a gold arc under the skirt
    d.arc([620, 640, 860, 880], start=200, end=460, fill=(240, 200, 90, 255), width=26)
    d.polygon([(626, 700), (600, 640), (668, 676)], fill=(240, 200, 90, 255))
    # word mark
    f = font(118)
    d.text((S / 2, 930), 'TAIRABA', font=f, fill=(255, 255, 255, 255), anchor='ms')
    return im

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    big = draw()
    for name, px in [('icon-512.png', 512), ('icon-192.png', 192), ('icon-180.png', 180), ('favicon.png', 48)]:
        big.resize((px, px), Image.LANCZOS).save(os.path.join(OUT, name), optimize=True)
    print('ok')
