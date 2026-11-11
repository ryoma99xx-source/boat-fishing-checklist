"""タイラバカウンターのアイコン：オーナー提供の画像（tools/tairaba/icon-source.png）を縮小するだけ（切り抜き・加工なし）。
public/tairaba/icon-512.png, icon-192.png, icon-180.png, favicon.png を書き出す。"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'tairaba', 'icon-source.png')
OUT = os.path.join(HERE, '..', 'public', 'tairaba')

if __name__ == '__main__':
    im = Image.open(SRC).convert('RGB')
    for name, px in [('icon-512.png', 512), ('icon-192.png', 192), ('icon-180.png', 180), ('favicon.png', 48)]:
        im.resize((px, px), Image.LANCZOS).save(os.path.join(OUT, name), optimize=True)
    print('ok', im.size)
