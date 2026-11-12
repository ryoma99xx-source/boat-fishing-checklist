"""ティップランカウンターの仮アイコン（図形だけで描く。オーナーの画像が来たら差し替える）。
public/tipran/icon-512.png, icon-192.png, icon-180.png, favicon.png を書き出す。
オーナー提供の画像 tools/tipran/icon-source.png があれば、それを縮小するだけにする。"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'public', 'tipran')
SRC = os.path.join(HERE, 'tipran', 'icon-source.png')
S = 1024

def font(size):
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def draw():
    im = Image.new('RGB', (S, S), (11, 20, 34))
    d = ImageDraw.Draw(im)
    # egi body (tilted), cloth stripes, eye, fins and the hook crown
    body = Image.new('RGBA', (S, S), (0, 0, 0, 0)); b = ImageDraw.Draw(body)
    b.ellipse([200, 420, 820, 600], fill=(240, 120, 40, 255))
    for x in range(260, 780, 70):
        b.line([(x, 430), (x + 40, 590)], fill=(255, 190, 90, 255), width=18)
    b.polygon([(800, 470), (900, 420), (900, 600), (800, 550)], fill=(240, 200, 90, 255))
    b.ellipse([250, 470, 320, 540], fill=(255, 255, 255, 255)); b.ellipse([270, 490, 305, 525], fill=(20, 20, 24, 255))
    b.polygon([(420, 590), (480, 690), (540, 595)], fill=(255, 150, 60, 255))
    for k in range(-2, 3):
        b.line([(890, 510), (960, 510 + k * 35)], fill=(220, 220, 230, 255), width=10)
    body = body.rotate(18, center=(S / 2, S / 2), resample=Image.BICUBIC)
    im.paste(body, (0, 0), body)
    f = font(120)
    d.text((S / 2, 230), 'TIPRUN', font=f, fill=(255, 255, 255), anchor='ms')
    d.text((S / 2, 930), 'COUNTER', font=font(96), fill=(63, 200, 196), anchor='ms')
    return im

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    big = Image.open(SRC).convert('RGB') if os.path.exists(SRC) else draw()
    for name, px in [('icon-512.png', 512), ('icon-192.png', 192), ('icon-180.png', 180), ('favicon.png', 48)]:
        big.resize((px, px), Image.LANCZOS).save(os.path.join(OUT, name), optimize=True)
    print('ok')
