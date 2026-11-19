"""Builds the public ティップラン用エギ catalog page (https://dragon-counter.cutlassfish.tokyo/egi-catalog/) and the same
catalog as a cutlassfish.tokyo article. Same structure and filters as the テンヤ catalog (tools/tenya_page.py), and the
same catalog.js (public/tenya-catalog/catalog.js, set up by data-tcat-* on the root).

    python3 tools/egi_page.py

Data: the ティップランカウンター egi catalog (tools/tipran/catalog.json → heads) and its cut photos
(tools/tipran/egi-images.json → public/tipran/egi/<id>.webp). Photos are only cut out and made smaller.
Output:
  public/egi-catalog/index.html
  wordpress/egi-catalog/{article.json, article.html, images/egi-collage.jpg}
釣れ筋・ランキングは、ティップランカウンターの釣果データがたまったら足す（今はなし）。"""
import hashlib, html, json, os, re, sys, unicodedata
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tenya_page as T

SITE = T.SITE
PUB = T.PUB
REPO = os.path.dirname(os.path.dirname(SITE))
OUT = os.path.join(PUB, 'egi-catalog')
AOUT = os.path.join(REPO, 'wordpress', 'egi-catalog')
URL = 'https://dragon-counter.cutlassfish.tokyo/egi-catalog/'
APP = 'https://dragon-counter.cutlassfish.tokyo/tipran/'
HOST = 'https://dragon-counter.cutlassfish.tokyo'
E = T.E
BTN = 'display:inline-block;font-size:14px;font-weight:700;padding:8px 14px;border-radius:8px;text-decoration:none;margin:0 6px 6px 0'


def zs(z):
    return '%g' % float(z)


def load():
    cat = json.load(open(os.path.join(HERE, 'tipran', 'catalog.json'), encoding='utf-8'))
    mp = json.load(open(os.path.join(HERE, 'tipran', 'egi-images.json'), encoding='utf-8'))
    plist, makers = [], []
    for r in cat['heads']:
        m, p = r['m'], r['s']
        if m not in makers:
            makers.append(m)
        o = r.get('o') or []
        z = sorted({float(x['z']) for x in o})
        sizes = ' '.join(zs(x) for x in z)
        wt = '・'.join('%s号%s' % (zs(x['z']), ' %sg' % zs(x['g']) if x.get('g') else '') for x in o)
        cols = []
        for c in r['c']:
            im = mp.get('%s|%s|%s' % (m, p, c))
            q = T.norm_q(' '.join([m, p, c, wt] + ['%s号' % zs(x) for x in z]))
            cols.append({'c': c, 'img': im['id'] if im else '', 'q': q, 'z': sizes})
        plist.append({'m': m, 'p': p, 'u': r.get('u', ''), 'note': r.get('note', ''), 'z': z, 'wt': wt, 'cols': cols})
    plist.sort(key=lambda r: (makers.index(r['m']), bool(r['note']), r['p']))
    global SINKERS
    SINKERS = [r for r in cat.get('skirts', []) if (r['m'], r['s']) not in PAGE_HIDE_SINKERS]
    return cat.get('v', ''), plist, makers


SINKERS = []
# カタログのページ・記事には載せないシンカー（オーナー指示 2026-11-20。アプリのカタログには残る）
PAGE_HIDE_SINKERS = {('ダイワ', 'アゴリグシンカー3'), ('第一精工', 'エギタス')}


def wtxt(w):
    w = [float(x) for x in w]
    return '・'.join(zs(x) for x in w) + 'g'


def sinker_photos(r, article):
    """色ごとの写真（無い色は名前だけ）。色ごとの写真が無い色があれば、製品全体の写真を先に1枚"""
    p = os.path.join(HERE, 'tipran', 'sinker-images.json')
    mp = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    get = lambda c: (mp.get('%s|%s|%s' % (r['m'], r['s'], c)) or {}).get('id', '')
    cols = r.get('c') or []
    items = [(c, get(c)) for c in cols]
    whole = get('')
    if whole and (not cols or any(not i for _, i in items)):
        items = [('（製品の写真）' if cols else '', whole)] + [(c, i) for c, i in items if i] + [(c, '') for c, i in items if not i]
    if not any(i for _, i in items):
        return ''
    src = (lambda i: '%s/tipran/sinker/%s.webp' % (HOST, i)) if article else (lambda i: '/tipran/sinker/%s.webp' % i)
    if article:
        figs = ''.join('<figure style="margin:0;border:1px solid #1f2d42;border-radius:8px;overflow:hidden;background:#101c2e">%s<figcaption style="padding:6px 8px;font-size:13px;line-height:1.4;color:#eef3f8">%s</figcaption></figure>'
                       % ('<img src="%s" alt="%s %s" width="240" height="180" loading="lazy" style="display:block;width:100%%;height:auto;aspect-ratio:4/3;object-fit:contain;background:#fff">' % (src(i), E(r['s']), E(c)) if i else '<div style="aspect-ratio:4/3;background:#fff;color:#889;display:flex;align-items:center;justify-content:center;font-size:12px">写真なし</div>', E(c or r['s']))
                       for c, i in items)
        return '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin:10px 0 0">%s</div>' % figs
    figs = ''.join('<figure class="cl">%s<figcaption><b>%s</b></figcaption></figure>'
                   % ('<img src="%s" alt="%s %s" loading="lazy" decoding="async" width="240" height="180">' % (src(i), E(r['s']), E(c)) if i else '<div class="noimg">写真なし</div>', E(c or r['s']))
                   for c, i in items)
    return '<div class="grid">%s</div>' % figs


def sinker_html(article=False):
    """シンカー（増し錘）の一覧。写真はないので、製品ごとに重さ・色・メーカーのページと探すボタンを並べる（絞り込みの外）"""
    makers = []
    for r in SINKERS:
        if r['m'] not in makers:
            makers.append(r['m'])
    out = []
    for m in makers:
        rs = [r for r in SINKERS if r['m'] == m]
        out.append('<h3 style="margin:22px 0 6px">%s</h3>' % E(m) if article else '<h3 class="sk-mk">%s</h3>' % E(m))
        for r in rs:
            rr = {'m': r['m'], 'p': r['s'], 'u': r.get('u', '')}
            k = re.sub(r'\s+', ' ', '%s %s' % (r['m'], r['s'])).strip()
            cw = r.get('cw') or {}
            cols = r.get('c') or []
            if cw and cols:
                lim = []
                for ci, c in enumerate(cols):
                    ws = [w for w, idx in cw.items() if ci in idx]
                    if len(ws) < len(cw):
                        lim.append('%s（%s）' % (c, wtxt(sorted(ws, key=float))))
                    else:
                        lim.append(c)
                ctext = '・'.join(lim)
            else:
                ctext = '・'.join(cols)
            note = r.get('note', '')
            if article:
                out.append('<div style="border:1px solid #1f2d42;border-radius:10px;padding:12px 14px;margin:0 0 12px;background:#0b1422;color:#eef3f8">'
                           '<p style="margin:0 0 4px;font-weight:700;font-size:16px">%s</p><p style="margin:0 0 4px;font-size:14px">重さ：%s</p>%s%s<p style="margin:8px 0 0">%s</p>%s</div>'
                           % (E(r['s']), E(wtxt(r['w'])), '<p style="margin:0 0 4px;font-size:14px">色：%s</p>' % E(ctext) if ctext else '',
                              '<p style="margin:0;font-size:13px;color:#9cabbd">%s</p>' % E(note) if note else '', links_html(rr, small=False, kwd=k), sinker_photos(r, True)))
            else:
                out.append('<section class="pd sk"><h2><small>%s</small>%s</h2><p class="meta">重さ：%s</p>%s%s<p class="links">%s<a class="buy az" href="%s" target="_blank" rel="nofollow sponsored noopener">Amazonで探す</a><a class="buy rk" href="%s" target="_blank" rel="nofollow sponsored noopener">楽天で探す</a><a class="buy yh" href="%s" target="_blank" rel="nofollow sponsored noopener">Yahoo!で探す</a></p>%s</section>'
                           % (E(r['m']), E(r['s']), E(wtxt(r['w'])), '<p class="meta">色：%s</p>' % E(ctext) if ctext else '', '<p class="meta" style="font-size:13px">%s</p>' % E(note) if note else '',
                              '<a class="off" href="%s" target="_blank" rel="noopener">メーカーのページ ↗</a>' % E(rr['u']) if rr['u'] else '',
                              E(T.amazon(k)), E(T.rakuten(k)), E(T.yahoo(k)), sinker_photos(r, False)))
    return makers, '\n'.join(out)


def photo(i):
    return '%s/tipran/egi/%s.webp' % (HOST, i)


def kw(r):
    return re.sub(r'\s+', ' ', '%s %s エギ' % (r['m'], re.sub(r'[（(]([^）)]*)[）)]', r' \1 ', r['p']))).strip()


def fig_attrs(r, c, fid):
    return 'id="%s" data-tcat-c="1" data-k="%s" data-cn="%s" data-z="%s" data-q="%s"' % (
        fid, E('%s|%s|%s' % (r['m'], r['p'], c['c'])), E(c['c']), E(c['z']), E(c['q']))


def prod_attrs(r):
    return 'data-tcat-p="1" data-m="%s" data-mj="%s" data-name="%s"' % (E(r['m']), E(r['m']), E(r['p']))


def zrange(r):
    z = r['z']
    if not z:
        return ''
    return '%s号' % zs(z[0]) if len(z) == 1 else '%s〜%s号' % (zs(z[0]), zs(z[-1]))


ROOT = 'data-tcat="1" data-tcat-noun="エギ" data-tcat-ph="検索（例：ケイムラ 3.5、ダイワ 夜光）" data-tcat-nonew="1" data-tcat-norank="1"'


def page(v, plist, makers):
    ncol = sum(len(r['cols']) for r in plist)
    sizes = sorted({z for r in plist for z in r['z']})
    cards = []
    for pi, r in enumerate(plist):
        k = kw(r)
        cols = []
        for ci, c in enumerate(r['cols']):
            img = ('<img src="/tipran/egi/%s.webp" alt="%s %s" loading="lazy" decoding="async" width="240" height="180">' % (c['img'], E(r['p']), E(c['c']))) if c['img'] else '<div class="noimg">写真なし</div>'
            cols.append('<figure class="cl" %s>%s<figcaption><b>%s</b></figcaption></figure>' % (fig_attrs(r, c, 'c-%d-%d' % (pi, ci)), img, E(c['c'])))
        cards.append('''<section class="pd" id="p-%d" %s>
 <h2><small>%s</small>%s</h2>
 <p class="meta">%s・%d色%s</p>
 <p class="links" data-tcat-links="1">%s<a class="buy az" href="%s" target="_blank" rel="nofollow sponsored noopener">Amazonで探す</a><a class="buy rk" href="%s" target="_blank" rel="nofollow sponsored noopener">楽天で探す</a><a class="buy yh" href="%s" target="_blank" rel="nofollow sponsored noopener">Yahoo!で探す</a></p>
 <div class="grid">%s</div>
</section>''' % (pi, prod_attrs(r), E(r['m']), E(r['p']), E(r['wt'] or zrange(r)), len(r['cols']),
                 '・' + E(r['note']) if r['note'] else '',
                 '<a class="off" href="%s" target="_blank" rel="noopener">メーカーのページ ↗</a>' % E(r['u']) if r['u'] else '',
                 E(T.amazon(k)), E(T.rakuten(k)), E(T.yahoo(k)), ''.join(cols)))
    desc = 'ティップラン用エギの全カラーを写真で一覧。ダイワ・シマノ・ヤマシタなど%dメーカー%d製品・%d色を、号数・メーカーで絞り込み、色の名前で検索できます。釣果記録アプリ「ティップランカウンター」のエギカタログと同じデータです。' % (len(makers), len(plist), ncol)
    s = TPL
    for a, b in [('{title}', 'ティップラン用エギ・シンカー カタログ｜エギ%dメーカー・%d色を写真で比較' % (len(makers), ncol)), ('{desc}', E(desc)), ('{url}', URL),
                 ('{lead}', '主要%dメーカーのティップラン用エギ %d製品・%d色を写真で一覧にしました。号数・メーカーで絞り込めて、色や製品の名前で検索できます。ページの下には、シンカー（増し錘）%d製品も載せています。' % (len(makers), len(plist), ncol, len(SINKERS))),
                 ('{upd}', E(v)), ('{zlist}', '・'.join(zs(z) + '号' for z in sizes)), ('{cards}', '\n'.join(cards)), ('{root}', ROOT),
                 ('{sklead}', 'エギの下に付けて重さを足すシンカーです。%dメーカー・%d製品。色によって出ている重さが違うものは、色の後ろに重さを書いています。' % (len(sinker_html()[0]), len(SINKERS))),
                 ('{sinkers}', sinker_html()[1]),
                 ('{js}', hashlib.sha256(open(os.path.join(PUB, 'tenya-catalog', 'catalog.js'), 'rb').read()).hexdigest()[:10])]:
        s = s.replace(a, b)
    return s


def tpl():
    """The テンヤ page's look, with the words, the app box and the script set up for egi."""
    t = T.TPL.replace('{{', '{{').replace('}}', '}}')
    t = re.sub(r'\{\{', '{', t)
    t = re.sub(r'\}\}', '}', t)
    head = t[:t.index('<body>')]
    head = head.replace('{title}', '{title}')
    body = '''<body>
<div class="wrap">
<header class="top"><a href="https://cutlassfish.tokyo/">東京湾の魚・釣り</a><a class="app" href="/tipran/">ティップランカウンター</a></header>
<p class="eyebrow">EGI CATALOG</p>
<h1>ティップラン用エギ・シンカー カタログ</h1>
<p class="lead">{lead}</p>
<p class="note"><b style="color:var(--ink)">号数は {zlist}</b>のエギを載せています。色の名前・号数・重さはメーカーの表記です。{upd} 時点。最新の情報はメーカーのページで確かめてください。エギは種類がとても多いので、まだ載っていない製品・色もあります。</p>
<span class="pr">PR：このページはアフィリエイト広告（Amazon・楽天・Yahoo!ショッピング）を利用しています</span>

<p class="note" style="margin-top:12px"><a href="#sinkers">シンカー（増し錘）の一覧へ ↓</a></p>
<div {root}>
<div data-tcat-bar="1"></div>

{cards}
</div>

<h2 id="sinkers" style="font-size:22px;margin:32px 0 4px">シンカー（増し錘）</h2>
<p class="note">{sklead}</p>
{sinkers}

<section class="box app-box">
 <div class="app-head"><img src="/tipran/icon-192.png" alt="" width="64" height="64"><div><b>ティップランカウンター</b><small>アオリイカの釣果記録アプリ（無料・登録なし）</small></div></div>
 <p>ティップランカウンターは釣果を数えるアプリですが、<b>持っているエギの管理</b>もできます。このページと同じエギのリストを持っているので、写真を見ながら持っているエギを登録しておけます。その中から選んでおけば、釣れたときにボタンを押すだけで「どのエギで、何時に釣れたか」が残ります。</p>
 <ul><li>このページと同じリストから、持っているエギを写真で登録</li><li>シンカー・竿・リール（ベイトも）もカタログから登録</li><li>釣り場を選ぶと、潮回りと満潮・干潮が自動で入る</li><li>アタリ・バラシ・釣れた時刻を、ボタン1つで記録</li><li>記録はスマホの中に保存。アプリとしてホーム画面にも置ける</li></ul>
 <div class="app-btns"><a class="btn" href="/tipran/">ティップランカウンターを開く</a><a class="btn sub" href="https://cutlassfish.tokyo/article/tipran-counter/">使い方の記事を読む</a></div>
</section>

<footer>
 <p>写真はメーカーや販売店の製品写真を切り抜いたものです。写真のない色もあります。</p>
 <p>Amazonのアソシエイトとして、このサイトは適格販売により収入を得ています。</p>
 <p><a href="https://cutlassfish.tokyo/">東京湾の魚・釣り（cutlassfish.tokyo）</a></p>
</footer>
</div>
<script src="/tenya-catalog/catalog.js?v={js}" defer></script>
</body>
</html>
'''
    return head + body


TPL = None


def links_html(r, small=False, kwd=None):
    k = kwd or kw(r)
    b = BTN + (';font-size:13px;padding:6px 10px' if small else '')
    x = ''
    if r['u'] and not small:
        x += '<a href="%s" target="_blank" rel="noopener" style="%s;border:1px solid #99a;color:inherit">メーカーのページ</a>' % (E(r['u']), b)
    x += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#f3a847;color:#111 !important">Amazonで探す</a>' % (E(T.amazon(k)), b)
    x += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#bf0000;color:#fff !important">楽天で探す</a>' % (E(T.rakuten(k)), b)
    x += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#ff0033;color:#fff !important">Yahoo!で探す</a>' % (E(T.yahoo(k)), b)
    return x


def collage(plist, path, nmk, ncol):
    """1080x1350 for Instagram: egi photos above and below a title band (photos only arranged and made smaller)."""
    src = os.path.join(PUB, 'tipran', 'egi')
    by = {}
    for r in plist:
        if r['note']:
            continue
        cs = [c['img'] for c in r['cols'] if c['img']]
        if cs:
            by.setdefault(r['m'], []).append(cs)
    pics, k = [], 0
    while len(pics) < 24 and any(by.values()):
        for m in list(by):
            if by[m] and len(pics) < 24:
                cs = by[m].pop(0)
                pics.append(cs[k % len(cs)]); k += 1
    W, H, cols, th, band = 1080, 1350, 4, 180, 270
    cw = W // cols
    im = Image.new('RGB', (W, H), (6, 10, 17))
    for n, i in enumerate(pics):
        row = n // cols
        y = row * th + (band if row >= 3 else 0)
        p = Image.open(os.path.join(src, i + '.webp')).convert('RGBA')
        p.thumbnail((cw - 16, th - 12), Image.LANCZOS)
        tile = Image.new('RGBA', (cw - 8, th - 8), (255, 255, 255, 255))
        tile.alpha_composite(p, ((tile.width - p.width) // 2, (tile.height - p.height) // 2))
        im.paste(tile.convert('RGB'), ((n % cols) * cw + 4, y + 4))
    d = ImageDraw.Draw(im)
    fd = os.path.join(HERE, 'fonts')
    jp = lambda z: ImageFont.truetype(os.path.join(fd, 'NotoSansJP-Bold.ttf'), z)
    en = ImageFont.truetype(os.path.join(fd, 'BarlowCondensed-SemiBold.ttf'), 40)
    y0 = 3 * th
    d.rectangle([0, y0, W, y0 + band], fill=(11, 20, 34))
    d.rectangle([0, y0, W, y0 + 5], fill=(65, 201, 198)); d.rectangle([0, y0 + band - 5, W, y0 + band], fill=(65, 201, 198))

    def centre(text, font, y, fill, spacing=0):
        w = d.textlength(text, font=font) + spacing * (len(text) - 1)
        x = (W - w) / 2
        for ch in text:
            d.text((x, y), ch, font=font, fill=fill); x += d.textlength(ch, font=font) + spacing
    centre('EGI CATALOG', en, y0 + 26, (65, 201, 198), 8)
    centre('ティップラン用エギ カタログ', jp(72), y0 + 70, (238, 243, 248))
    centre('%dメーカー・%d色を写真で一覧' % (nmk, ncol), jp(42), y0 + 182, (227, 164, 59))
    im.save(path, 'JPEG', quality=88)


def article(v, plist, makers):
    ncol = sum(len(r['cols']) for r in plist)
    body = []
    for mi, m in enumerate(makers):
        rs = [r for r in plist if r['m'] == m]
        blk = ['<div data-tcat-mkb="%s">' % E(m), '<h2 id="mk-%d"><span class="en">MAKER</span>%s</h2>\n<p>%d製品・%d色</p>' % (mi, E(m), len(rs), sum(len(r['cols']) for r in rs))]
        for r in rs:
            pi = plist.index(r)
            figs = []
            for ci, c in enumerate(r['cols']):
                img = ('<img src="%s" alt="%s %s" width="240" height="180" loading="lazy" style="display:block;width:100%%;height:auto;aspect-ratio:4/3;object-fit:contain;background:#fff">' % (photo(c['img']), E(r['p']), E(c['c']))) if c['img'] else ''
                figs.append('<figure %s style="margin:0;border:1px solid #1f2d42;border-radius:8px;overflow:hidden;background:#101c2e;color:#eef3f8;position:relative">%s'
                            '<figcaption style="padding:6px 8px;font-size:13px;line-height:1.4;color:#eef3f8">%s</figcaption></figure>' % (fig_attrs(r, c, 'c-%d-%d' % (pi, ci)), img, E(c['c'])))
            blk.append('<div %s>\n<h3 id="tp-%d">%s</h3>\n<p>%s・%d色%s</p>\n<p data-tcat-links="1">%s</p>\n<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;margin:0 0 28px">%s</div>\n</div>'
                       % (prod_attrs(r), pi, E(r['p']), E(r['wt'] or zrange(r)), len(r['cols']), '・' + E(r['note']) if r['note'] else '', links_html(r), ''.join(figs)))
        blk.append('</div>')
        body.append('\n'.join(blk))
    a = []
    a.append('<p class="lead">「このエギ、ほかにどんな色があったっけ？」と思っても、メーカーのページを行ったり来たりして探すのは面倒です。そこで、ティップラン用のエギを<strong>メーカー・製品ごとに、全部の色を写真で一覧</strong>にしました。%dメーカー・%d製品・%d色です。記事の後半には、シンカー（増し錘）%d製品の一覧もあります。釣果記録アプリ「ティップランカウンター」のカタログと同じデータです。</p>' % (len(makers), len(plist), ncol, len(SINKERS)))
    a.append('<p><small>※この記事には、Amazon・楽天市場・Yahoo!ショッピングへのアフィリエイトリンク（広告）が含まれます。</small></p>')
    a.append('<div style="display:flex;gap:12px;align-items:center;border:1px solid #44566e;border-radius:12px;padding:12px 14px;margin:20px 0">'
             '<a href="%s" style="flex:0 0 56px;width:56px;display:block"><img src="%sicon-192.png" alt="ティップランカウンター" width="56" height="56" style="width:56px;min-width:56px;max-width:none;height:56px;border-radius:12px;display:block;object-fit:cover"></a>'
             '<div style="font-size:14px;line-height:1.6;flex:1 1 0;min-width:0">このカタログは、アオリイカの釣果記録アプリ<a href="%s"><b>ティップランカウンター</b></a>のエギカタログと同じです。持っているエギを写真で登録でき、どのエギで釣れたかをボタン1つで残せます。<a href="#tp-app">くわしくは下で ↓</a></div></div>' % (APP, APP, APP))
    a.append('<h2><span class="en">HOW</span>このカタログの見方</h2>')
    a.append('<ul><li>製品ごとに、号数と重さ、色の数、メーカーのページ、Amazon・楽天・Yahoo!ショッピングで探すボタンを並べています。</li>'
             '<li>写真の下は色の名前です。色の名前・号数・重さはメーカーの表記のままです。写真はメーカーや販売店の製品写真を切り抜いたものです。</li>'
             '<li>メーカーごとに、今の製品 → 旧モデル（生産終了）の順です。旧モデルも、在庫や手持ちで見かけるので載せています。</li>'
             '<li><b>エギはテンヤよりずっと種類が多く、まだ載っていない製品・色もあります。</b>見つけたら少しずつ足していきます。</li></ul>')
    a.append('<p><b>一覧の上で、号数・メーカーで絞り込み、色や製品の名前で検索できます。</b>「ケイムラ 3.5」「ダイワ 夜光」のように、空白で区切って続けて入れると、全部に当てはまるものだけが残ります。</p>')
    a.append('<h2><span class="en">WORDS</span>色の名前によく出てくる言葉</h2>')
    a.append('<ul><li><b>夜光・グロー</b>：光をためて、暗いところで光る塗装・下地。</li>'
             '<li><b>ケイムラ</b>：紫外線が当たると青白く光る塗装・下地。</li>'
             '<li><b>赤テープ・金テープ・ホロ</b>：布の下に貼ってある下地のシート。「赤-○○」のように、下地と布の色を並べた名前が多いです。</li>'
             '<li><b>杉・縞</b>：布の柄（杉の葉のような柄、縞模様）。</li></ul>')
    a.append('<h2 id="tp-app"><span class="en">APP</span>どのエギで釣れたかを残すなら「ティップランカウンター」</h2>')
    a.append('<p><a href="%s"><b>ティップランカウンター</b></a>は、アオリイカの釣果を時間と一緒に記録するアプリです。<b>持っているエギの管理</b>もできます。このページと同じエギのリストをアプリの中に持っているので、写真を見ながら持っているエギを登録しておけます。</p>' % APP)
    a.append('<p>その中から使うエギを選んでおけば、釣れたときにボタンを押すだけで「どのエギで、何時に、どんな潮で釣れたか」が残ります。無料で、登録もいりません。</p>')
    a.append('<ul><li>このページと同じリストから、持っているエギを写真で登録</li><li>シンカー・竿・リール（ベイトも）もカタログから登録</li><li>釣り場を選ぶと、潮回りと満潮・干潮が自動で入る</li><li>アタリ・バラシ・釣れた時刻を、ボタン1つで記録</li><li>記録はスマホの中に保存。ホーム画面に置けばアプリのように使える</li></ul>')
    a.append('<p style="text-align:center;margin:20px 0"><a href="%s" style="display:inline-block;background:#41c9c6;color:#03161c !important;font-size:17px;font-weight:700;padding:14px 28px;border-radius:8px;text-decoration:none;margin:6px">ティップランカウンターを開く →</a>'
             '<a href="https://cutlassfish.tokyo/article/tipran-counter/" style="display:inline-block;border:2px solid #41c9c6;color:inherit;font-size:16px;font-weight:700;padding:12px 22px;border-radius:8px;text-decoration:none;margin:6px">使い方の記事を読む</a></p>' % APP)
    a.append('<p><a href="#sinkers">シンカー（増し錘）の一覧へ ↓</a></p>')
    a.append('<h2><span class="en">CATALOG</span>エギの一覧</h2>')
    a.append('<div %s>\n<div data-tcat-bar="1"></div>\n%s\n</div>' % (ROOT, '\n'.join(body)))
    smk, shtml = sinker_html(article=True)
    a.append('<h2 id="sinkers"><span class="en">SINKER</span>シンカー（増し錘）の一覧</h2>')
    a.append('<p>エギの下に付けて重さを足すシンカーです。%dメーカー・%d製品。色によって出ている重さが違うものは、色の後ろに重さを書いています。</p>' % (len(smk), len(SINKERS)))
    a.append(shtml)
    a.append('<p><small>%s 時点の内容です。価格や在庫は各ショップで確かめてください。Amazonのアソシエイトとして、このサイトは適格販売により収入を得ています。</small></p>' % E(v))
    art = {'version': 1,
           'title': 'ティップラン用エギ・シンカー カタログ｜エギ%dメーカー・%d色を写真で一覧' % (len(makers), ncol),
           'excerpt': 'ダイワ・シマノ・ヤマシタなど%dメーカーのティップラン用エギ%d製品・%d色を、写真で一覧にしました。号数・メーカーで絞り込めて、色や製品の名前で検索できます。シンカー（増し錘）%d製品も載せています。釣果記録アプリ「ティップランカウンター」と同じデータです。' % (len(makers), len(plist), ncol, len(SINKERS)),
           'images': [{'id': 'egi-collage', 'file': 'images/egi-collage.jpg', 'alt': 'ティップラン用エギの写真を並べたもの'}],
           'featured_image': 'egi-collage'}
    os.makedirs(os.path.join(AOUT, 'images'), exist_ok=True)
    collage(plist, os.path.join(AOUT, 'images', 'egi-collage.jpg'), len(makers), ncol)
    open(os.path.join(AOUT, 'article.html'), 'w', encoding='utf-8').write('\n\n'.join(a) + '\n')
    json.dump(art, open(os.path.join(AOUT, 'article.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('article:', art['title'], sum(len(x) for x in a) // 1024, 'KB')


def main():
    global TPL
    TPL = tpl()
    v, plist, makers = load()
    os.makedirs(OUT, exist_ok=True)
    s = page(v, plist, makers)
    open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(s)
    print(len(plist), 'products,', sum(len(r['cols']) for r in plist), 'colours,', sum(1 for r in plist for c in r['cols'] if c['img']), 'with photo,', len(s) // 1024, 'KB')
    article(v, plist, makers)


POST_ID = 1420   # エギ・シンカーカタログの記事（https://cutlassfish.tokyo/article/tipran-egi-catalog/）
FEAT = os.path.join(AOUT, 'featured.json')   # いま記事に付いているアイキャッチ {sha256, media_id}


def push():
    """記事の本文とアイキャッチを、いまのカタログで差し替える（公開中ならそのまま公開中）。テンヤの tenya_article.push と同じ。
    環境変数 WP_USER / WP_APP_PASSWORD が要る（値は表示しない）。SiteGuard に断られたら先頭に空白を足して送り直す"""
    import re as _re, shutil, subprocess, tempfile
    if not os.environ.get('WP_USER') or not os.environ.get('WP_APP_PASSWORD'):
        print('記事の更新はできませんでした：環境変数 WP_USER / WP_APP_PASSWORD がありません（カタログのページは更新済み）'); return 1
    cf = os.path.join(REPO, 'wordpress', 'article-pack', 'cfpack.py')
    art = json.load(open(os.path.join(AOUT, 'article.json'), encoding='utf-8'))
    body = open(os.path.join(AOUT, 'article.html'), encoding='utf-8').read()
    img = os.path.join(AOUT, 'images', 'egi-collage.jpg')
    sha = hashlib.sha256(open(img, 'rb').read()).hexdigest()
    feat = json.load(open(FEAT, encoding='utf-8')) if os.path.exists(FEAT) else {}
    same = feat.get('sha256') == sha and feat.get('media_id')
    for n in range(6):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'images'))
            a2 = dict(art)
            if same:
                a2['images'] = []; a2['featured_image'] = 'media:%d' % feat['media_id']
            else:
                shutil.copyfile(img, os.path.join(d, 'images', 'egi-collage.jpg'))
            json.dump(a2, open(os.path.join(d, 'article.json'), 'w', encoding='utf-8'), ensure_ascii=False)
            open(os.path.join(d, 'article.html'), 'w', encoding='utf-8').write(' ' * n + body)
            z = os.path.join(d, 'pack.zip')
            b = subprocess.run([sys.executable, cf, 'build', d, '-o', z], capture_output=True, text=True)
            if b.returncode:
                print('記事パックを作れませんでした:', (b.stdout + b.stderr)[-300:]); return 1
            r = subprocess.run([sys.executable, cf, 'update', str(POST_ID), z, '--allow-published'], capture_output=True, text=True)
        out = r.stdout + r.stderr
        if r.returncode == 0:
            if not same:
                m = _re.search(r'"egi-collage":\s*(\d+)', r.stdout)
                if m:
                    json.dump({'sha256': sha, 'media_id': int(m.group(1))}, open(FEAT, 'w', encoding='utf-8'))
            print('記事を更新しました: post %d' % POST_ID); return 0
        if 'HTTP 403' not in out:
            print('記事の更新に失敗しました:', out[-300:]); return 1
    print('記事の更新に失敗しました：ファイアウォール（SiteGuard）に6回断られました'); return 1


if __name__ == '__main__':
    main()
    if '--push' in sys.argv:
        sys.exit(push())
