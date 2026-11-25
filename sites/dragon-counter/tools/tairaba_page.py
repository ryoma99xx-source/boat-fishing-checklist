"""タイラバのヘッド・ネクタイ（＋スカート）のカタログを、ツールのサイトのページと cutlassfish.tokyo の記事にする。
オーナー指示 2026-11-23：テンヤ（tools/tenya_page.py）・エギ（tools/egi_page.py）と同じ作り・更新のしかたで。

ネクタイが2,521色とエギの約4倍あり、記事1本の上限（1MB）に入らないので、ページも記事も2つに分ける（オーナーが選んだ形）。
  ページ：https://dragon-counter.cutlassfish.tokyo/tairaba-catalog/        ヘッド（全色の写真）＋スカート
          https://dragon-counter.cutlassfish.tokyo/tairaba-catalog/ties/   ネクタイ（全色の写真）
  記事  ：ヘッド・スカートの記事（全色の写真）
          ネクタイの記事（製品ごとに代表の写真1枚と、色の名前の一覧。全色の写真はページへ）
絞り込み・検索はテンヤ・エギと同じ catalog.js（/tenya-catalog/catalog.js、data-tcat-* で設定）。

    python3 tools/tairaba_page.py            ページ2つと記事2本のファイルを作る
    python3 tools/tairaba_page.py --push     ＋公開中の記事2本の本文とアイキャッチを差し替える（WP_USER / WP_APP_PASSWORD が要る）

データ：タイラバカウンターのカタログ（tools/tairaba/catalog.json）と写真（tools/tairaba/images.json → public/tairaba/img/<id>.webp）。
写真は切り抜きと縮小だけ。カタログを足したら（tairaba_catalog.py・tairaba_images.py のあと）、これを動かして DEPLOY を更新する。
"""
import hashlib, json, os, re, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tenya_page as T
import tairaba_shapes as SH   # 形の写真（製品ごとに1枚）

SITE, PUB = T.SITE, T.PUB
REPO = os.path.dirname(os.path.dirname(SITE))
E = T.E
HOST = 'https://dragon-counter.cutlassfish.tokyo'
APP = HOST + '/tairaba/'
APP_ART = 'https://cutlassfish.tokyo/article/tairaba-counter/'
PAGES = {'head': ('tairaba-catalog', HOST + '/tairaba-catalog/'), 'tie': ('tairaba-catalog/ties', HOST + '/tairaba-catalog/ties/')}
AOUT = {'head': os.path.join(REPO, 'wordpress', 'tairaba-head-catalog'), 'tie': os.path.join(REPO, 'wordpress', 'tairaba-tie-catalog')}
POSTS = os.path.join(REPO, 'wordpress', 'tairaba-catalog-posts.json')   # 記事の ID とアイキャッチ {kind: {post_id, sha256, media_id}}
BTN = 'display:inline-block;font-size:14px;font-weight:700;padding:8px 14px;border-radius:8px;text-decoration:none;margin:0 6px 6px 0'
NOLINK = {'フリマアプリ系'}   # 店のリンクを付けないメーカー（決まった商品名がない）
CAT_ART = {'head': 'https://cutlassfish.tokyo/article/tairaba-head-catalog/', 'tie': 'https://cutlassfish.tokyo/article/tairaba-tie-catalog/'}


def zs(z):
    return '%g' % float(z)


def load():
    cat = json.load(open(os.path.join(HERE, 'tairaba', 'catalog.json'), encoding='utf-8'))
    mp = json.load(open(os.path.join(HERE, 'tairaba', 'images.json'), encoding='utf-8'))
    shp = SH.load()
    hp = os.path.join(HERE, 'tairaba', 'images-hold.json')
    hold = set(json.load(open(hp, encoding='utf-8'))['keys']) if os.path.exists(hp) else set()
    out = {}
    for kind, key in (('head', 'heads'), ('tie', 'ties'), ('skirt', 'skirts')):
        plist, makers = [], []
        for r in cat[key]:
            m, p = r['m'], r['s']
            if m not in makers:
                makers.append(m)
            w = sorted({float(x) for x in (r.get('w') or [])})
            wt = ('%s〜%sg（%d種）' % (zs(w[0]), zs(w[-1]), len(w)) if len(w) > 1 else '%sg' % zs(w[0])) if w else ''
            info = [x for x in ([('タングステン（TG）' if r.get('mat') == 'TG' else r.get('mat', '')), r.get('type', '')] if kind == 'head' else [r.get('sh', '')]) if x]
            cols = []
            for c in r['c']:
                k = '%s|%s|%s|%s' % (key, m, p, c)
                im = mp.get(k) if k not in hold else None
                q = T.norm_q(' '.join([m, p, c] + info + ['%sg' % zs(x) for x in w]))
                cols.append({'c': c, 'img': im['id'] if im else '', 'q': q, 'z': ' '.join(zs(x) for x in w)})
            plist.append({'shape': (shp.get('%s|%s|%s' % (key, m, p)) or {}).get('id', ''), 'm': m, 'p': p, 'u': r.get('u', ''), 'tg': r.get('mat') == 'TG', 'w': w, 'wt': wt, 'info': info, 'cols': cols})
        # ページ・記事のメーカーの順は、写真のある色の割合が高い順（低いほど下）。同じ割合ならアプリの順。オーナー指示 2026-11-23（アプリの順は変えない）
        rate = {m: (lambda cs: sum(1 for c in cs if c['img']) / max(1, len(cs)))([c for r in plist if r['m'] == m for c in r['cols']]) for m in makers}
        makers = sorted(makers, key=lambda m: (-round(rate[m], 4), makers.index(m)))
        plist.sort(key=lambda r: makers.index(r['m']))
        out[kind] = (plist, makers)
    return cat.get('v', ''), out


def kw(r, kind):
    p = re.sub(r'[（(]([^）)]*)[）)]', r' \1 ', r['p'])
    return re.sub(r'\s+', ' ', '%s %s %s' % (r['m'], p, 'タイラバ' if kind != 'tie' or 'ネクタイ' not in p else '')).strip()


def photo(i, article):
    return ('%s/tairaba/img/%s.webp' % (HOST, i)) if article else '/tairaba/img/%s.webp' % i


def fig_attrs(r, c, fid):
    # 検索の文字は製品の data-pq ＋色の名前（catalog.js が組み立てる）。ページを軽くするため色ごとには持たない
    return 'data-tcat-c="1"%s' % (' data-z="%s"' % E(c['z']) if c['z'] else '')


def prod_attrs(r):
    pq = T.norm_q(' '.join([r['m'], r['p']] + r['info'] + ['%sg' % zs(x) for x in r['w']]))
    return 'data-tcat-p="1" data-m="%s" data-mj="%s" data-name="%s" data-pq="%s"%s' % (E(r['m']), E(r['m']), E(r['p']), E(pq), ' data-tg="1"' if r['tg'] else '')


def meta(r):
    return '・'.join([x for x in r['info']] + ([('重さ ' + r['wt'])] if r['wt'] else []) + ['%d色' % len(r['cols'])])


ROOTS = {'head': 'data-tcat="1" data-tcat-noun="ヘッド" data-tcat-unit="g" data-tcat-ph="検索（例：TG オレンジ 80、ダイワ ケイムラ）" data-tcat-nonew="1" data-tcat-norank="1"',
         'tie': 'data-tcat="1" data-tcat-noun="ネクタイ" data-tcat-ph="検索（例：カーリー ゼブラ、ジャッカル グロー）" data-tcat-nonew="1" data-tcat-norank="1"',
         'skirt': 'data-tcat="1" data-tcat-noun="スカート" data-tcat-ph="検索（例：ダイワ グロー）" data-tcat-nonew="1" data-tcat-norank="1"'}


def shop_links(r, kind, page=True, small=False):
    if r['m'] in NOLINK:
        return ''
    k = kw(r, kind)
    if page:
        return ('<a class="off" href="%s" target="_blank" rel="noopener">メーカーのページ ↗</a>' % E(r['u']) if r['u'] else '') + \
            '<a class="buy az" href="%s" target="_blank" rel="nofollow sponsored noopener">Amazonで探す</a><a class="buy rk" href="%s" target="_blank" rel="nofollow sponsored noopener">楽天で探す</a><a class="buy yh" href="%s" target="_blank" rel="nofollow sponsored noopener">Yahoo!で探す</a>' % (E(T.amazon(k)), E(T.rakuten(k)), E(T.yahoo(k)))
    if small == 'cls':   # ネクタイの記事：見た目は catalog.js の .tcat-b（記事を1MB以下にするため）
        x = '<a href="%s" target="_blank" rel="noopener" class="tcat-b mk">メーカーのページ</a>' % E(r['u']) if r['u'] else ''
        return x + ''.join('<a href="%s" target="_blank" rel="nofollow sponsored noopener" class="tcat-b %s">%sで探す</a>' % (E(u), c, n) for u, c, n in ((T.amazon(k), 'az', 'Amazon'), (T.rakuten(k), 'rk', '楽天'), (T.yahoo(k), 'yh', 'Yahoo!')))
    b = BTN + (';font-size:13px;padding:6px 10px' if small else '')
    x = '<a href="%s" target="_blank" rel="noopener" style="%s;border:1px solid #99a;color:inherit">メーカーのページ</a>' % (E(r['u']), b) if r['u'] and not small else ''
    x += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#f3a847;color:#111 !important">Amazonで探す</a>' % (E(T.amazon(k)), b)
    x += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#bf0000;color:#fff !important">楽天で探す</a>' % (E(T.rakuten(k)), b)
    x += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#ff0033;color:#fff !important">Yahoo!で探す</a>' % (E(T.yahoo(k)), b)
    return x


def shape_fig(r, article):
    """形の写真（色ごとの写真が色見本だけの製品に、全体が写った写真を1枚）。オーナー指示 2026-11-25"""
    if not r.get('shape'):
        return ''
    return ('<figure style="margin:0 0 12px;max-width:420px"><img src="%s" alt="%s の形" loading="lazy" style="display:block;width:100%%;height:auto;max-height:260px;object-fit:contain;background:#fff;border-radius:10px">'
            '<figcaption style="font-size:12px;opacity:.75;margin-top:4px">形（色は下の写真）</figcaption></figure>' % (photo(r['shape'], article), E(r['p'])))


def cards_page(plist, kind, pre):
    out = []
    for pi, r in enumerate(plist):
        cols = []
        for ci, c in enumerate(r['cols']):
            img = ('<img src="%s" alt="%s %s" loading="lazy" decoding="async" width="240" height="180">' % (photo(c['img'], False), E(r['p']), E(c['c']))) if c['img'] else '<div class="noimg">写真なし</div>'
            cols.append('<figure class="cl" %s>%s<figcaption><b>%s</b></figcaption></figure>' % (fig_attrs(r, c, '%s-%d-%d' % (pre, pi, ci)), img, E(c['c'])))
        out.append('<section class="pd" id="%s-%d" %s>\n <h2><small>%s</small>%s</h2>\n <p class="meta">%s</p>\n <p class="links" data-tcat-links="1">%s</p>\n %s<div class="grid">%s</div>\n</section>'
                   % (pre, pi, prod_attrs(r), E(r['m']), E(r['p']), E(meta(r)), shop_links(r, kind), shape_fig(r, False), ''.join(cols)))
    return '\n'.join(out)


def head_tpl():
    t = re.sub(r'\}\}', '}', re.sub(r'\{\{', '{', T.TPL))
    return t[:t.index('<body>')]


def app_box():
    return ('<section class="box app-box">\n <div class="app-head"><img src="/tairaba/icon-192.png" alt="" width="64" height="64"><div><b>タイラバカウンター</b><small>マダイの釣果記録アプリ（無料・登録なし）</small></div></div>\n'
            ' <p>タイラバカウンターは釣果を数えるアプリですが、<b>持っているヘッド・ネクタイの管理</b>もできます。このページと同じリストを持っているので、写真を見ながら持っているものを登録しておけます。'
            'その中から選んでおけば、釣れたときにボタンを押すだけで「どのヘッドとネクタイで、何時に釣れたか」が残ります。</p>\n'
            ' <ul><li>このページと同じリストから、持っているヘッド・ネクタイ・スカートを写真で登録</li><li>よく使うものだけの「一軍リスト」を作れる</li><li>竿・リール（ベイト・電動）もカタログから登録</li><li>釣り場を選ぶと、潮回りと満潮・干潮が自動で入る</li><li>出方（巻き／フォール）・巻きの速さ・アタリの位置も残せる</li></ul>\n'
            ' <div class="app-btns"><a class="btn" href="/tairaba/">タイラバカウンターを開く</a><a class="btn sub" href="%s">使い方の記事を読む</a></div>\n</section>' % APP_ART)


FOOT = ('<footer>\n <p>写真はメーカーや販売店の製品写真を切り抜いたものです。写真のない色もあります。</p>\n'
        ' <p>Amazonのアソシエイトとして、このサイトは適格販売により収入を得ています。</p>\n <p><a href="https://cutlassfish.tokyo/">東京湾の魚・釣り（cutlassfish.tokyo）</a></p>\n</footer>')


def page_html(kind, v, D):
    js = hashlib.sha256(open(os.path.join(PUB, 'tenya-catalog', 'catalog.js'), 'rb').read()).hexdigest()[:10]
    hp, hm = D['head']; tp, tm = D['tie']; sp, sm = D['skirt']
    nh, nt, ns = (sum(len(r['cols']) for r in x) for x in (hp, tp, sp))
    if kind == 'head':
        title = 'タイラバのヘッド カタログ｜%dメーカー・%d色を写真で比較' % (len(hm), nh)
        desc = 'タイラバのヘッドの全カラーを写真で一覧。%dメーカー%d製品・%d色を、重さ・メーカー・素材（タングステン）で絞り込み、色の名前で検索できます。スカート%d製品も。釣果記録アプリ「タイラバカウンター」と同じデータです。' % (len(hm), len(hp), nh, len(sp))
        body = ('<p class="eyebrow">TAIRABA CATALOG</p>\n<h1>タイラバ ヘッド・スカート カタログ</h1>\n'
                '<p class="lead">%dメーカーのタイラバのヘッド %d製品・%d色を写真で一覧にしました。重さ・メーカー・素材（タングステンだけ）で絞り込めて、色や製品の名前で検索できます。ページの下には、スカート %d製品も載せています。</p>\n'
                '<p class="note">ネクタイは <a href="/tairaba-catalog/ties/"><b>ネクタイのカタログ</b></a>（%dメーカー・%d色）へ。色の名前・重さはメーカーの表記です。%s 時点。最新の情報はメーカーのページで確かめてください。'
                '完成品（ヘッドにネクタイ・針が付いたもの）も、ヘッドの色で載せています。</p>\n'
                '<span class="pr">PR：このページはアフィリエイト広告（Amazon・楽天・Yahoo!ショッピング）を利用しています</span>\n'
                '<p class="note" style="margin-top:12px"><a href="#skirts">スカートの一覧へ ↓</a></p>\n<div %s>\n<div data-tcat-bar="1"></div>\n\n%s\n</div>\n'
                '<h2 id="skirts" style="font-size:22px;margin:32px 0 4px">スカート</h2>\n<p class="note">ネクタイと一緒に付けて、ボリュームやアピールを足すパーツです。%dメーカー・%d製品。</p>\n<div %s>\n<div data-tcat-bar="1"></div>\n%s\n</div>\n'
                % (len(hm), len(hp), nh, len(sp), len(tm), nt, E(v), ROOTS['head'], cards_page(hp, 'head', 'h'), len(sm), len(sp), ROOTS['skirt'], cards_page(sp, 'skirt', 's')))
    else:
        title = 'タイラバのネクタイ カタログ｜%dメーカー・%d色を写真で比較' % (len(tm), nt)
        desc = 'タイラバのネクタイの全カラーを写真で一覧。%dメーカー%d製品・%d色を、メーカーで絞り込み、形（カーリー・ストレートなど）や色の名前で検索できます。釣果記録アプリ「タイラバカウンター」と同じデータです。' % (len(tm), len(tp), nt)
        body = ('<p class="eyebrow">TAIRABA CATALOG</p>\n<h1>タイラバ ネクタイ カタログ</h1>\n'
                '<p class="lead">%dメーカーのタイラバのネクタイ %d製品・%d色を写真で一覧にしました。メーカーで絞り込めて、形（カーリー・ストレートなど）や色・製品の名前で検索できます。</p>\n'
                '<p class="note">ヘッドとスカートは <a href="/tairaba-catalog/"><b>ヘッドのカタログ</b></a>（%dメーカー・%d色）へ。色の名前はメーカーの表記です。%s 時点。最新の情報はメーカーのページで確かめてください。'
                'ネクタイとスカート・針がセットになった替えユニットも載せています。</p>\n'
                '<span class="pr">PR：このページはアフィリエイト広告（Amazon・楽天・Yahoo!ショッピング）を利用しています</span>\n<div %s>\n<div data-tcat-bar="1"></div>\n\n%s\n</div>\n'
                % (len(tm), len(tp), nt, len(hm), nh, E(v), ROOTS['tie'], cards_page(tp, 'tie', 't')))
    url = PAGES[kind][1]
    s = head_tpl().replace('{title}', E(title)).replace('{desc}', E(desc)).replace('{url}', url)
    s += ('<body>\n<div class="wrap">\n<header class="top"><a href="https://cutlassfish.tokyo/">東京湾の魚・釣り</a><a class="app" href="/tairaba/">タイラバカウンター</a></header>\n'
          + body + '\n' + app_box() + '\n\n' + FOOT + '\n</div>\n<script src="/tenya-catalog/catalog.js?v=%s" defer></script>\n</body>\n</html>\n' % js)
    return s


def collage(kind, plist, path, nmk, ncol):
    """1080x1350：写真を上下に並べ、真ん中に題名の帯（写真は並べて縮小するだけ）。エギと同じ形"""
    by = {}
    for r in plist:
        cs = [c['img'] for c in r['cols'] if c['img']]
        if cs and r['m'] not in NOLINK:
            by.setdefault(r['m'], []).append(cs)
    pics, k = [], 0
    while len(pics) < 24 and any(by.values()):
        for m in list(by):
            if by[m] and len(pics) < 24:
                cs = by[m].pop(0); pics.append(cs[k % len(cs)]); k += 1
    W, H, cols, th, band = 1080, 1350, 4, 180, 270
    cw = W // cols
    im = Image.new('RGB', (W, H), (6, 10, 17))
    for n, i in enumerate(pics):
        row = n // cols
        y = row * th + (band if row >= 3 else 0)
        p = Image.open(os.path.join(PUB, 'tairaba', 'img', i + '.webp')).convert('RGBA')
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
    d.rectangle([0, y0, W, y0 + 5], fill=(229, 57, 109)); d.rectangle([0, y0 + band - 5, W, y0 + band], fill=(229, 57, 109))

    def centre(text, font, y, fill, spacing=0):
        w = d.textlength(text, font=font) + spacing * (len(text) - 1)
        x = (W - w) / 2
        for ch in text:
            d.text((x, y), ch, font=font, fill=fill); x += d.textlength(ch, font=font) + spacing
    centre('TAIRABA CATALOG', en, y0 + 26, (240, 120, 160), 8)
    centre('タイラバ %s カタログ' % ('ヘッド' if kind == 'head' else 'ネクタイ'), jp(72), y0 + 70, (238, 243, 248))
    centre('%dメーカー・%d色を写真で一覧' % (nmk, ncol), jp(42), y0 + 182, (227, 164, 59))
    im.save(path, 'JPEG', quality=88)


def app_lead():
    return ('<div style="display:flex;gap:12px;align-items:center;border:1px solid #44566e;border-radius:12px;padding:12px 14px;margin:20px 0">'
            '<a href="%s" style="flex:0 0 56px;width:56px;display:block"><img src="%sicon-192.png" alt="タイラバカウンター" width="56" height="56" style="width:56px;min-width:56px;max-width:none;height:56px;border-radius:12px;display:block;object-fit:cover"></a>'
            '<div style="font-size:14px;line-height:1.6;flex:1 1 0;min-width:0">このカタログは、マダイの釣果記録アプリ<a href="%s"><b>タイラバカウンター</b></a>のカタログと同じです。持っているヘッド・ネクタイを写真で登録でき、どれで釣れたかをボタン1つで残せます。<a href="#tc-app">くわしくは下で ↓</a></div></div>' % (APP, APP, APP))


def app_section():
    return ('<h2 id="tc-app"><span class="en">APP</span>どのタイラバで釣れたかを残すなら「タイラバカウンター」</h2>\n'
            '<p><a href="%s"><b>タイラバカウンター</b></a>は、マダイの釣果を時間と一緒に記録するアプリです。<b>持っているヘッド・ネクタイの管理</b>もできます。このページと同じリストをアプリの中に持っているので、写真を見ながら持っているものを登録しておけます。</p>\n'
            '<p>その中から使うものを選んでおけば、釣れたときにボタンを押すだけで「どのヘッドとネクタイで、何時に、どんな潮で釣れたか」が残ります。無料で、登録もいりません。</p>\n'
            '<ul><li>このページと同じリストから、持っているヘッド・ネクタイ・スカートを写真で登録</li><li>よく使うものだけの「一軍リスト」を作れる</li><li>竿・リール（ベイト・電動）もカタログから登録</li><li>釣り場を選ぶと、潮回りと満潮・干潮が自動で入る</li><li>出方（巻き／フォール）・巻きの速さ・アタリの位置も残せる</li></ul>\n'
            '<p style="text-align:center;margin:20px 0"><a href="%s" style="display:inline-block;background:#e5396d;color:#ffffff !important;font-size:17px;font-weight:700;padding:14px 28px;border-radius:8px;text-decoration:none;margin:6px">タイラバカウンターを開く →</a>'
            '<a href="%s" style="display:inline-block;border:2px solid #e5396d;color:inherit;font-size:16px;font-weight:700;padding:12px 22px;border-radius:8px;text-decoration:none;margin:6px">使い方の記事を読む</a></p>' % (APP, APP, APP_ART))


FIG = 'margin:0;border:1px solid #1f2d42;border-radius:8px;overflow:hidden;background:#101c2e;color:#eef3f8;position:relative'
CAP = 'padding:6px 8px;font-size:13px;line-height:1.4;color:#eef3f8'
IMGST = 'display:block;width:100%;height:auto;aspect-ratio:4/3;object-fit:contain;background:#fff'


def art_photo_block(plist, makers, kind, pre, mkh=True):
    body = []
    for mi, m in enumerate(makers):
        rs = [r for r in plist if r['m'] == m]
        blk = ['<div data-tcat-mkb="%s">' % E(m)]
        if mkh:
            blk.append('<h2 id="%s-mk-%d"><span class="en">MAKER</span>%s</h2>\n<p>%d製品・%d色</p>' % (pre, mi, E(m), len(rs), sum(len(r['cols']) for r in rs)))
        else:
            blk.append('<h3 style="margin:22px 0 6px">%s</h3>' % E(m))
        for r in rs:
            pi = plist.index(r)
            figs = []
            for ci, c in enumerate(r['cols']):
                img = '<img src="%s" alt="%s %s" width="240" height="180" loading="lazy" style="%s">' % (photo(c['img'], True), E(r['p']), E(c['c']), IMGST) if c['img'] else ''
                figs.append('<figure %s style="%s">%s<figcaption style="%s">%s</figcaption></figure>' % (fig_attrs(r, c, '%s-%d-%d' % (pre, pi, ci)), FIG, img, CAP, E(c['c'])))
            blk.append('<div %s>\n<h3 id="%s-%d">%s</h3>\n<p>%s</p>\n<p data-tcat-links="1">%s</p>\n%s<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;margin:0 0 28px">%s</div>\n</div>'
                       % (prod_attrs(r), pre, pi, E(r['p']), E(meta(r)), shop_links(r, kind, page=False), shape_fig(r, True), ''.join(figs)))
        blk.append('</div>')
        body.append('\n'.join(blk))
    return '\n'.join(body)


def art_tie_block(plist, makers):
    """ネクタイの記事：製品ごとに代表の写真1枚と、色の名前のチップ（チップも絞り込み・検索の対象）。全色の写真はページへ"""
    body = []
    for mi, m in enumerate(makers):
        rs = [r for r in plist if r['m'] == m]
        blk = ['<div data-tcat-mkb="%s">' % E(m), '<h2 id="t-mk-%d"><span class="en">MAKER</span>%s</h2>\n<p>%d製品・%d色</p>' % (mi, E(m), len(rs), sum(len(r['cols']) for r in rs))]
        for r in rs:
            pi = plist.index(r)
            rep = r.get('shape') or next((c['img'] for c in r['cols'] if c['img']), '')
            chips = ''.join('<span data-tcat-c>%s</span>' % E(c['c']) for c in r['cols'])
            img = '<img src="%s" alt="%s" width="240" height="180" loading="lazy" style="%s;border-radius:8px">' % (photo(rep, True), E(r['p']), IMGST) if rep else ''
            blk.append('<div %s style="margin:0 0 26px">\n<h3 id="t-%d">%s</h3>\n<p>%s</p>\n<div style="display:grid;grid-template-columns:minmax(110px,160px) 1fr;gap:12px;align-items:start">%s<div>%s</div></div>\n'
                       '<p data-tcat-links="1" style="margin:10px 0 0"><a href="%s#t-%d" target="_blank" rel="noopener" class="tcat-b all">全色の写真を見る</a>%s</p>\n</div>'
                       % (prod_attrs(r), pi, E(r['p']), E(meta(r)), img or '<div></div>', chips, PAGES['tie'][1], pi, shop_links(r, 'tie', page=False, small='cls')))
        blk.append('</div>')
        body.append('\n'.join(blk))
    return '\n'.join(body)


# ネクタイの記事の冒頭に出す更新のお知らせ（新しいものを上に）
TIE_UPDATES = [
    ('2026/11/25', 'ネクタイに<b>17メーカー</b>を追加しました。アブガルシア・オーナー・クレージーオーシャン・アクティブ、関西のササラボ・BRIZM・UROKODO・ヌーテック・AZZURO・剣屋・イグレイ、釣具店のタカミヤ・ガラパゴス、遊漁船発のクレイジーコレクション、ワーム系のソルトウォーターボーイズ・バレーヒル、そしてダイソー。いまは<b>%(nm)dメーカー・%(np)d製品・%(nc)d色</b>です。'),
]


def article(kind, v, D):
    hp, hm = D['head']; tp, tm = D['tie']; sp, sm = D['skirt']
    nh, nt, ns = (sum(len(r['cols']) for r in x) for x in (hp, tp, sp))
    a = []
    if kind == 'head':
        title = 'タイラバのヘッド カタログ｜%dメーカー・%d色を写真で一覧（スカートも）' % (len(hm), nh)
        a.append('<p class="lead">「タイラバのヘッド、メーカーも色も多すぎてよくわからん」「このヘッド、この重さでこんな色あったっけ？」と思っても、メーカーのページを行ったり来たりして探すのは面倒です。'
                 'そこで、タイラバのヘッドを<strong>メーカー・製品ごとに、全部の色を写真で一覧</strong>にしました。%dメーカー・%d製品・%d色です。記事の後半には、スカート %d製品の一覧もあります。釣果記録アプリ「タイラバカウンター」のカタログと同じデータです。</p>' % (len(hm), len(hp), nh, len(sp)))
        a.append('<p><small>※この記事には、Amazon・楽天市場・Yahoo!ショッピングへのアフィリエイトリンク（広告）が含まれます。</small></p>')
        a.append(app_lead())
        a.append('<p>ネクタイは、別の記事 <a href="%s"><b>タイラバのネクタイ カタログ</b></a>（%dメーカー・%d色）にまとめています。</p>' % (CAT_ART['tie'], len(tm), nt))
        a.append('<h2><span class="en">HOW</span>このカタログの見方</h2>')
        a.append('<ul><li>製品ごとに、素材（鉛・タングステン）と形、出ている重さ、色の数、メーカーのページ、Amazon・楽天・Yahoo!ショッピングで探すボタンを並べています。</li>'
                 '<li>写真の下は色の名前です。色の名前・重さはメーカーの表記のままです。写真はメーカーや販売店の製品写真を切り抜いたものです。</li>'
                 '<li>ヘッドにネクタイ・針が付いた完成品も、ヘッドの色で載せています。重さによって出ていない色がある製品もあるので、買う前にメーカーのページで確かめてください。</li>'
                 '<li><b>まだ載っていない製品・色もあります。</b>見つけたら少しずつ足していきます。</li></ul>')
        a.append('<p><b>一覧の上で、重さ・メーカー・素材（タングステンだけ）で絞り込み、色や製品の名前で検索できます。</b>「TG オレンジ 80」「ダイワ ケイムラ」のように、空白で区切って続けて入れると、全部に当てはまるものだけが残ります。数字だけ（「80」「80g」）は重さです。</p>')
        a.append('<h2><span class="en">WORDS</span>ヘッドを選ぶときによく出てくる言葉</h2>')
        a.append('<ul><li><b>鉛とタングステン（TG）</b>：タングステンは鉛より重い金属なので、同じ重さでもヘッドが小さくなります。潮の抵抗を受けにくく、底をとりやすいのが良いところ。値段は高めです。</li>'
                 '<li><b>遊動式と固定式</b>：遊動式はヘッドが糸の上を動き、魚が食ったときにヘッドの重さが伝わりにくい形。固定式はヘッドとネクタイ・針が一緒に動きます。</li>'
                 '<li><b>ケイムラ</b>：紫外線が当たると青白く光る塗装。<b>グロー（夜光）</b>：光をためて暗いところで光る塗装。</li>'
                 '<li><b>ゴールド・アカキン・オレンジ</b>：マダイ向けで定番の色です。濁りや深さで、明るい色・暗い色を使い分けます。</li></ul>')
        a.append(app_section())
        a.append('<p><a href="#skirts">スカートの一覧へ ↓</a></p>')
        a.append('<h2><span class="en">CATALOG</span>ヘッドの一覧</h2>')
        a.append('<div %s>\n<div data-tcat-bar="1"></div>\n%s\n</div>' % (ROOTS['head'], art_photo_block(hp, hm, 'head', 'h')))
        a.append('<h2 id="skirts"><span class="en">SKIRT</span>スカートの一覧</h2>')
        a.append('<p>ネクタイと一緒に付けて、ボリュームやアピールを足すパーツです。%dメーカー・%d製品。ヘッドと同じように、メーカーで絞り込み、色や製品の名前で検索できます。</p>' % (len(sm), len(sp)))
        a.append('<div %s>\n<div data-tcat-bar="1"></div>\n%s\n</div>' % (ROOTS['skirt'], art_photo_block(sp, sm, 'skirt', 's', mkh=False)))
        excerpt = 'ダイワ・シマノ・ジャッカルなど%dメーカーのタイラバのヘッド%d製品・%d色を、写真で一覧にしました。重さ・メーカー・素材（タングステン）で絞り込めて、色や製品の名前で検索できます。スカート%d製品も載せています。釣果記録アプリ「タイラバカウンター」と同じデータです。' % (len(hm), len(hp), nh, len(sp))
        ncol, nmk, plist = nh, len(hm), hp
    else:
        for d_, txt in TIE_UPDATES:   # オーナー指示 2026-11-25：冒頭に UPDATE のラベルで更新内容を書く
            a.append('<div style="border:2px solid #e3a43b;border-radius:12px;padding:10px 14px;margin:0 0 18px;background:rgba(227,164,59,.08)"><span style="display:inline-block;background:#e3a43b;color:#03161c;font-weight:700;font-size:12px;letter-spacing:.12em;padding:2px 8px;border-radius:6px;margin-right:8px">UPDATE</span><b>%s</b><br>%s</div>' % (E(d_), txt % {'nm': len(tm), 'np': len(tp), 'nc': nt}))
        title = 'タイラバのネクタイ カタログ｜%dメーカー・%d色を一覧（写真はツールのページで）' % (len(tm), nt)
        a.append('<p class="lead">タイラバのネクタイは、形も色も数えきれないほどあります。「あのカーリー、オレンジゼブラあったっけ？」と思っても、メーカーのページで探すのは大変です。'
                 'そこで、タイラバのネクタイを<strong>メーカー・製品ごとに、全部の色の名前を一覧</strong>にしました。%dメーカー・%d製品・%d色です。釣果記録アプリ「タイラバカウンター」のカタログと同じデータです。</p>' % (len(tm), len(tp), nt))
        a.append('<p><small>※この記事には、Amazon・楽天市場・Yahoo!ショッピングへのアフィリエイトリンク（広告）が含まれます。</small></p>')
        a.append('<p style="text-align:center;margin:18px 0"><a href="%s" style="display:inline-block;background:#41c9c6;color:#03161c !important;font-size:17px;font-weight:700;padding:14px 26px;border-radius:8px;text-decoration:none">全色の写真はこちら（ネクタイのカタログ） →</a></p>' % PAGES['tie'][1])
        a.append(app_lead())
        a.append('<p>ヘッドとスカートは、別の記事 <a href="%s"><b>タイラバのヘッド カタログ</b></a>（%dメーカー・%d色）にまとめています。</p>' % (CAT_ART['head'], len(hm), nh))
        a.append('<h2><span class="en">HOW</span>このカタログの見方</h2>')
        a.append('<ul><li>ネクタイは%d色と数がとても多いので、この記事では製品ごとに<b>代表の写真1枚と、色の名前の一覧</b>にしています。全部の色の写真は、各製品の「全色の写真を見る」から、ツールのページで見られます。</li>'
                 '<li>色の名前はメーカーの表記のままです。写真はメーカーや販売店の製品写真を切り抜いたものです。</li>'
                 '<li>ネクタイとスカート・針がセットになった替えユニットも、ネクタイとして載せています。</li>'
                 '<li><b>まだ載っていない製品・色もあります。</b>見つけたら少しずつ足していきます。</li></ul>' % nt)
        a.append('<p><b>一覧の上で、メーカーで絞り込み、形や色・製品の名前で検索できます。</b>「カーリー ゼブラ」「ジャッカル グロー」のように、空白で区切って続けて入れると、全部に当てはまるものだけが残ります。</p>')
        a.append('<h2><span class="en">WORDS</span>ネクタイを選ぶときによく出てくる言葉</h2>')
        a.append('<ul><li><b>カーリー</b>：先がくるっと巻いた形。巻くとヒラヒラと大きく動きます。<b>ストレート</b>：まっすぐな細い形。動きは控えめで、食いが渋いときに使う人も多い形です。</li>'
                 '<li><b>ツイン・ダブル・マルチ</b>：1本の根元から2本以上に分かれている形や、太さ・長さの違うものを組み合わせたもの。</li>'
                 '<li><b>ゼブラ</b>：縞模様。<b>ラメ・フレーク</b>：細かいキラキラが入った素材。</li>'
                 '<li><b>ケイムラ</b>：紫外線が当たると青白く光る素材。<b>グロー（夜光）</b>：光をためて暗いところで光る素材。</li></ul>')
        a.append(app_section())
        a.append('<h2><span class="en">CATALOG</span>ネクタイの一覧</h2>')
        a.append('<div %s>\n<div data-tcat-bar="1"></div>\n%s\n</div>' % (ROOTS['tie'], art_tie_block(tp, tm)))
        excerpt = 'ダイワ・シマノ・ジャッカルなど%dメーカーのタイラバのネクタイ%d製品・%d色を一覧にしました。メーカーで絞り込めて、形（カーリー・ストレート）や色の名前で検索できます。全色の写真はツールのページで見られます。釣果記録アプリ「タイラバカウンター」と同じデータです。' % (len(tm), len(tp), nt)
        ncol, nmk, plist = nt, len(tm), tp
    a.append('<p><small>%s 時点の内容です。価格や在庫は各ショップで確かめてください。Amazonのアソシエイトとして、このサイトは適格販売により収入を得ています。</small></p>' % E(v))
    out = AOUT[kind]
    os.makedirs(os.path.join(out, 'images'), exist_ok=True)
    img = '%s-collage.jpg' % kind
    collage(kind, plist, os.path.join(out, 'images', img), nmk, ncol)
    art = {'version': 1, 'title': title, 'excerpt': excerpt,
           'images': [{'id': 'collage', 'file': 'images/' + img, 'alt': 'タイラバの%sの写真を並べたもの' % ('ヘッド' if kind == 'head' else 'ネクタイ')}], 'featured_image': 'collage'}
    html_ = '\n\n'.join(a) + '\n'
    open(os.path.join(out, 'article.html'), 'w', encoding='utf-8').write(html_)
    json.dump(art, open(os.path.join(out, 'article.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('article %s: %s  %d KB' % (kind, title, len(html_.encode()) // 1024))


def main():
    v, D = load()
    for kind in ('head', 'tie'):
        d = os.path.join(PUB, PAGES[kind][0])
        os.makedirs(d, exist_ok=True)
        s = page_html(kind, v, D)
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(s)
        plist = D[kind][0]
        print('page %s: %d products, %d colours, %d with photo, %d KB' % (kind, len(plist), sum(len(r['cols']) for r in plist), sum(1 for r in plist for c in r['cols'] if c['img']), len(s.encode()) // 1024))
        article(kind, v, D)


def push():
    """公開中（または下書き）の記事2本を、いまのカタログで差し替える。エギの egi_page.push と同じ。記事の ID は wordpress/tairaba-catalog-posts.json"""
    import shutil, subprocess, tempfile
    if not os.environ.get('WP_USER') or not os.environ.get('WP_APP_PASSWORD'):
        print('記事の更新はできませんでした：環境変数 WP_USER / WP_APP_PASSWORD がありません（カタログのページは更新済み）'); return 1
    cf = os.path.join(REPO, 'wordpress', 'article-pack', 'cfpack.py')
    posts = json.load(open(POSTS, encoding='utf-8')) if os.path.exists(POSTS) else {}
    rc = 0
    for kind in ('head', 'tie'):
        info = posts.get(kind) or {}
        if not info.get('post_id'):
            print('記事の ID がありません（%s）。最初は cfpack.py upload で下書きを作り、%s に post_id を入れる' % (kind, POSTS)); rc = 1; continue
        out = AOUT[kind]
        art = json.load(open(os.path.join(out, 'article.json'), encoding='utf-8'))
        body = open(os.path.join(out, 'article.html'), encoding='utf-8').read()
        img = os.path.join(out, 'images', '%s-collage.jpg' % kind)
        sha = hashlib.sha256(open(img, 'rb').read()).hexdigest()
        same = info.get('sha256') == sha and info.get('media_id')
        done = False
        for n in range(6):
            with tempfile.TemporaryDirectory() as d:
                os.makedirs(os.path.join(d, 'images'))
                a2 = dict(art)
                if same:
                    a2['images'] = []; a2['featured_image'] = 'media:%d' % info['media_id']
                else:
                    shutil.copyfile(img, os.path.join(d, 'images', os.path.basename(img)))
                json.dump(a2, open(os.path.join(d, 'article.json'), 'w', encoding='utf-8'), ensure_ascii=False)
                open(os.path.join(d, 'article.html'), 'w', encoding='utf-8').write(' ' * n + body)
                z = os.path.join(d, 'pack.zip')
                b = subprocess.run([sys.executable, cf, 'build', d, '-o', z], capture_output=True, text=True)
                if b.returncode:
                    print('記事パックを作れませんでした:', (b.stdout + b.stderr)[-300:]); rc = 1; break
                r = subprocess.run([sys.executable, cf, 'update', str(info['post_id']), z, '--allow-published'], capture_output=True, text=True)
            o = r.stdout + r.stderr
            if r.returncode == 0:
                if not same:
                    m = re.search(r'"collage":\s*(\d+)', r.stdout)
                    if m:
                        info.update({'sha256': sha, 'media_id': int(m.group(1))}); posts[kind] = info
                        json.dump(posts, open(POSTS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                print('記事を更新しました: %s post %d' % (kind, info['post_id'])); done = True; break
            if 'HTTP 403' not in o:
                print('記事の更新に失敗しました:', o[-300:]); rc = 1; break
        if not done and rc == 0:
            print('記事の更新に失敗しました：ファイアウォール（SiteGuard）に6回断られました'); rc = 1
    return rc


if __name__ == '__main__':
    main()
    if '--push' in sys.argv:
        sys.exit(push())
