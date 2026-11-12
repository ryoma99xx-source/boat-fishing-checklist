"""Builds the public タチウオテンヤ catalog page (https://dragon-counter.cutlassfish.tokyo/tenya-catalog/).

    python3 tools/tenya_page.py

Same data as the app's tenya catalog, so the page follows every monthly catalog update:
  public/catalog-all.json   all items {m,p,z,c,s} (written by catalog_add.py)
  public/index.html         TENYA_CAT products (official page URL, 替えヘッド flag)
  public/catalog-extra.json monthly additions (URL, flag)
  public/tenya/index.json   which items have a photo (photos are the app's own cut photos)
Output:
  public/tenya-catalog/index.html     the page (text is in the HTML, so search engines can read it)
  public/tenya-catalog/rank-map.json  item id → "maker|product|colour", read by public/tenya-rank.php
Affiliate links are search links per product (Amazon / 楽天). The IDs below are the ones that appear in every
public affiliate link anyway; they are not secrets."""
import ast, hashlib, html, json, os, re, sys, unicodedata, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
PUB = os.path.join(SITE, 'public')
OUT = os.path.join(PUB, 'tenya-catalog')
URL = 'https://dragon-counter.cutlassfish.tokyo/tenya-catalog/'
AMAZON_TAG = '3pdpenguinfis-22'
RAKUTEN_ID = '596849ef.4c28cf8e.596849f0.7ddddc88'
VC_SID, VC_PID = '3780817', '892726662'   # バリューコマース（Yahoo!ショッピング）。「高額釣具をいちばんお得に買う」記事と同じ
JP = {'DAIWA': 'ダイワ', 'SHIMANO': 'シマノ', 'HAYABUSA': 'ハヤブサ', 'JACKALL': 'ジャッカル', 'START': 'スタート',
      'OWNER': 'オーナー', 'Major Craft': 'メジャークラフト', 'DUO': 'デュオ', 'PRO MARINE': 'プロマリン',
      'YAMASHITA': 'ヤマシタ', 'がまかつ': 'がまかつ', 'マルシン漁具': 'マルシン漁具'}
ORDER = list(JP)
E = lambda x: html.escape(str(x), quote=True)


def fnv(s):
    """Same id as the app: fnv(`${m}|${p}|${z}|${c}`), FNV-1a over UTF-16 code units, base 36."""
    h = 0x811c9dc5
    b = s.encode('utf-16-le')
    for i in range(0, len(b), 2):
        h ^= b[i] | (b[i + 1] << 8)
        h = (h * 0x01000193) & 0xffffffff
    d, n = '0123456789abcdefghijklmnopqrstuvwxyz', ''
    while True:
        h, r = divmod(h, 36)
        n = d[r] + n
        if not h:
            return 'k' + n


def zs(z):
    return '%g' % float(z)


def search_kw(m, p):
    p = re.sub(r'[（(]([^）)]*)[）)]', r' \1 ', p)
    return re.sub(r'\s+', ' ', '%s %s' % (JP.get(m, m), p)).strip()


def amazon(kw):
    return 'https://www.amazon.co.jp/s?k=%s&tag=%s' % (urllib.parse.quote_plus(kw), AMAZON_TAG)


def yahoo(kw):
    u = 'https://shopping.yahoo.co.jp/search?p=%s' % urllib.parse.quote(kw)
    return 'https://ck.jp.ap.valuecommerce.com/servlet/referral?sid=%s&pid=%s&vc_url=%s' % (VC_SID, VC_PID, urllib.parse.quote(u, safe=''))


def rakuten(kw):
    u = 'https://search.rakuten.co.jp/search/mall/%s/' % urllib.parse.quote(kw)
    q = urllib.parse.quote(u, safe='')
    return 'https://hb.afl.rakuten.co.jp/hgc/%s/?pc=%s&m=%s' % (RAKUTEN_ID, q, q)


def load():
    s = open(os.path.join(PUB, 'index.html'), encoding='utf-8').read()
    cat = json.loads(re.search(r'const TENYA_CAT=(\{.*?\});\n', s, re.S).group(1))
    abbr = ast.literal_eval(re.search(r'const ABBR=(\{.*?\});', s, re.S).group(1))
    info = {(m, p): {'u': u, 'h': bool(h)} for m, p, u, h in cat['products']}
    ex = json.load(open(os.path.join(PUB, 'catalog-extra.json'), encoding='utf-8'))
    added = {}
    for x in ex['items']:
        info.setdefault((x['m'], x['p']), {'u': x.get('u', ''), 'h': bool(x.get('h'))})
        if x.get('a'):
            added[(x['m'], x['p'], zs(x['z']), x['c'])] = x['a']
    allc = json.load(open(os.path.join(PUB, 'catalog-all.json'), encoding='utf-8'))
    ti = json.load(open(os.path.join(PUB, 'tenya', 'index.json'), encoding='utf-8'))
    return allc, info, set(ti['ids']), ti.get('v', ''), abbr, added


def tenya_abbr(p, abbr):
    """Same short name as the app's tenyaAbbr (searchable there, so searchable here too)."""
    if p in abbr:
        return abbr[p]
    m = re.search(r'[（(]([A-Z]{2,3}\d{3,4})[)）]', p)
    if m:
        return m.group(1)
    rest = re.sub(r'船タチウオテンヤ|船太刀魚テンヤ|タチウオ専用テンヤ|太刀魚テンヤ|タチウオテンヤ|テンヤ|サーベルマスター', ' ', p).strip()
    lat = re.findall(r'[A-Za-zβ]+', rest)
    return ' '.join(lat)[:10] if lat else re.sub(r'\s+', '', rest)[:4]


def norm_q(x):
    """The app's normQ: NFKC, lower case, ひらがな → カタカナ."""
    x = unicodedata.normalize('NFKC', str(x)).lower()
    return ''.join(chr(ord(ch) + 0x60) if '\u3041' <= ch <= '\u3096' else ch for ch in x)


def build():
    allc, info, photos, pv, abbr, added = load()
    prods, rmap = {}, {}
    for it in allc['items']:
        m, p, z, c, st = it['m'], it['p'], it['z'], it['c'], it.get('s', '')
        i = fnv('%s|%s|%s|%s' % (m, p, zs(z), c))
        pr = prods.setdefault((m, p), {'m': m, 'p': p, 'cols': {}, 'z': set(), **info.get((m, p), {'u': '', 'h': False})})
        col = pr['cols'].setdefault(c, {'c': c, 'z': [], 'img': '', 's': set(), 'a': ''})
        col['z'].append(float(z)); pr['z'].add(float(z))
        if st:
            col['s'].add(st)
        col['a'] = max(col['a'], added.get((m, p, zs(z), c), ''))
        if not col['img'] and i in photos:
            col['img'] = i
        rmap[i] = '%s|%s|%s' % (m, p, c)
    for pr in prods.values():
        for col in pr['cols'].values():
            col['q'] = norm_q(' '.join([pr['m'], JP.get(pr['m'], ''), pr['p'], tenya_abbr(pr['p'], abbr)] + [zs(z) + '号' for z in sorted(set(col['z']))]
                                       + [col['c']] + sorted(col['s'])))
    plist = sorted(prods.values(), key=lambda r: (ORDER.index(r['m']) if r['m'] in ORDER else 99, '旧型' in r['p'], r['h'], r['p']))  # 今の製品 → 替えヘッド → 旧型
    return allc, plist, rmap, pv


def fig_attrs(r, c, fid):
    """The marks catalog.js reads (same on the tool page and in the article)."""
    return ('id="%s" data-tcat-c="1" data-k="%s" data-cn="%s" data-z="%s" data-q="%s"%s%s'
            % (fid, E('%s|%s|%s' % (r['m'], r['p'], c['c'])), E(c['c']), ' '.join(zs(z) for z in sorted(set(c['z']))), E(c['q']),
               ' data-a="%s"' % E(c['a']) if c['a'] else '', ' data-st="%s"' % E(' '.join(sorted(c['s']))) if c['s'] else ''))


def is_tg(p):
    """タングステン（TG）の製品。アプリの isTG と同じ見分け方"""
    return bool(re.search(r'(^|[^A-Za-z])TG([^A-Za-z]|$)|タングステン', p))


def prod_attrs(r):
    return 'data-tcat-p="1" data-m="%s" data-mj="%s" data-name="%s"%s' % (E(r['m']), E(JP.get(r['m'], r['m'])), E(r['p']), ' data-tg="1"' if is_tg(r['p']) else '')


def page(allc, plist, pv):
    ncol = sum(len(r['cols']) for r in plist)
    makers = [m for m in ORDER if any(r['m'] == m for r in plist)]
    sizes = sorted({z for r in plist for z in r['z']})
    cards = []
    for pi, r in enumerate(plist):
        zl = sorted(r['z'])
        zr = '%s号' % zs(zl[0]) if len(zl) == 1 else '%s〜%s号' % (zs(zl[0]), zs(zl[-1]))
        kw = search_kw(r['m'], r['p'])
        cols = []
        for ci, c in enumerate(r['cols'].values()):
            zz = '・'.join(zs(z) for z in sorted(set(c['z']))) + '号'
            badge = ''.join('<span class="bd">%s</span>' % E(s) for s in sorted(c['s']))
            img = ('<img src="/tenya/%s.webp%s" alt="%s %s" loading="lazy" decoding="async" width="240" height="180">'
                   % (c['img'], '?v=' + urllib.parse.quote(pv) if pv else '', E(r['p']), E(c['c']))) if c['img'] else '<div class="noimg">写真なし</div>'
            cols.append('<figure class="cl" %s>%s<figcaption><b>%s</b><small>%s</small>%s</figcaption></figure>'
                        % (fig_attrs(r, c, 'c-%d-%d' % (pi, ci)), img, E(c['c']), zz, badge))
        cards.append('''<section class="pd" id="p-%d" %s>
 <h2><small>%s</small>%s</h2>
 <p class="meta">%s・%d色%s</p>
 <p class="links" data-tcat-links="1">%s<a class="buy az" href="%s" target="_blank" rel="nofollow sponsored noopener">Amazonで探す</a><a class="buy rk" href="%s" target="_blank" rel="nofollow sponsored noopener">楽天で探す</a><a class="buy yh" href="%s" target="_blank" rel="nofollow sponsored noopener">Yahoo!で探す</a></p>
 <div class="grid">%s</div>
</section>''' % (pi, prod_attrs(r), E(JP.get(r['m'], r['m'])), E(r['p']), zr, len(r['cols']),
                 '・替えヘッド' if r['h'] else '',
                 '<a class="off" href="%s" target="_blank" rel="noopener">メーカーのページ ↗</a>' % E(r['u']) if r['u'] else '',
                 E(amazon(kw)), E(rakuten(kw)), E(yahoo(kw)), ''.join(cols)))
    upd = allc.get('updated', '')
    desc = '船タチウオテンヤの全カラーを写真で一覧。ダイワ・シマノ・ハヤブサなど%dメーカー%d製品・%d色を、号数・色で絞り込めます。釣果記録アプリ「ドラゴンカウンター」のテンヤカタログと同じデータで毎月更新。' % (len(makers), len(plist), ncol)
    return TPL.format(
        title='船タチウオテンヤ カタログ｜%dメーカー・%d色を写真で比較' % (len(makers), ncol), desc=E(desc), url=URL,
        lead='主要%dメーカーの船タチウオテンヤ %d製品・%d色（号数違いまで数えると%d種類）を写真で一覧にしました。号数・新商品・タングステン・メーカーで絞り込めて、色や製品の名前で検索できます。' % (len(makers), len(plist), ncol, len(allc['items'])),
        upd=E(upd), zlist='・'.join(zs(z) + '号' for z in sizes), cards='\n'.join(cards),
        js=hashlib.sha256(open(os.path.join(OUT, 'catalog.js'), 'rb').read()).hexdigest()[:10])


TPL = '''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}"><meta property="og:image" content="https://dragon-counter.cutlassfish.tokyo/og.png"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#060a11">
<link rel="icon" href="/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600&family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{{--tcat-bg:rgba(6,10,17,.96);--tcat-line:#1f2d42;--tcat-chip:#0b1422;--tcat-field:#101c2e;--tcat-ink:#eef3f8;--tcat-muted:#9cabbd;--tcat-on:#41c9c6;--tcat-on-ink:#03161c;--tcat-ts-line:#1f2d42;--bg:#060a11;--surface:#0b1422;--surface2:#101c2e;--line:#1f2d42;--ink:#eef3f8;--muted:#9cabbd;--teal:#41c9c6;--amber:#e3a43b;--pink:#e5577f;--r:14px;
 --f-body:"Noto Sans JP","Hiragino Sans","Hiragino Kaku Gothic ProN",system-ui,sans-serif;--f-num:"Barlow Condensed","Noto Sans JP",system-ui,sans-serif}}
*{{box-sizing:border-box}}html{{-webkit-text-size-adjust:100%}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--f-body);font-size:16px;line-height:1.6}}
a{{color:var(--teal)}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 16px 48px}}
header.top{{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:14px 0;border-bottom:1px solid var(--line)}}
header.top a{{color:var(--ink);text-decoration:none;font-weight:700;letter-spacing:.04em}}
header.top .app{{font-size:14px;color:var(--teal);border:1px solid var(--teal);border-radius:999px;padding:4px 12px;white-space:nowrap}}
.eyebrow{{font-family:var(--f-num);letter-spacing:.24em;color:var(--teal);font-size:14px;margin:22px 0 0}}
h1{{font-size:26px;line-height:1.35;margin:4px 0 10px}}
.lead{{color:var(--ink);margin:0 0 6px}}.note{{color:var(--muted);font-size:13px;margin:0}}
.pr{{display:inline-block;font-size:12px;color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:2px 8px;margin:10px 0 0}}
.box{{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:14px;margin:18px 0}}
.box h2{{font-size:18px;margin:0 0 10px}}
.rk-cols{{display:grid;grid-template-columns:1fr;gap:16px}}@media(min-width:760px){{.rk-cols{{grid-template-columns:1fr 1fr}}}}
.rk-cols h3{{font-size:15px;margin:0 0 6px;color:var(--teal)}}
.filters{{position:sticky;top:0;z-index:5;background:rgba(6,10,17,.94);backdrop-filter:blur(6px);padding:10px 0;border-bottom:1px solid var(--line)}}
.chips{{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}}.chips::-webkit-scrollbar{{display:none}}
.chip{{flex:none;min-height:38px;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);font:inherit;font-size:14px}}
.chip.on{{background:var(--teal);border-color:var(--teal);color:#03161c;font-weight:700}}
.frow{{display:flex;gap:8px;margin-top:8px}}
.frow select,.frow input{{min-height:40px;border-radius:10px;border:1px solid var(--line);background:var(--surface2);color:var(--ink);font:inherit;font-size:16px;padding:6px 10px}}
.szc .chip{{min-width:64px}}.frow input{{flex:1;min-width:0}}
.count{{color:var(--muted);font-size:13px;margin:8px 0 0}}
.pd{{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:14px;margin:14px 0}}
.pd h2{{font-size:18px;line-height:1.4;margin:0}}.pd h2 small{{display:block;font-size:13px;color:var(--teal);font-weight:500}}
.meta{{color:var(--muted);font-size:14px;margin:2px 0 8px}}
.links{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}}
.links a{{display:inline-flex;align-items:center;min-height:38px;padding:6px 14px;border-radius:10px;font-size:14px;font-weight:700;text-decoration:none}}
.off{{border:1px solid var(--line);color:var(--ink)!important;font-weight:500!important}}
.buy.az{{background:#f3a847;color:#111}}.buy.rk{{background:#bf0000;color:#fff}}.buy.yh{{background:#ff0033;color:#fff}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}@media(min-width:600px){{.grid{{grid-template-columns:repeat(4,minmax(0,1fr))}}}}
.cl{{margin:0;background:var(--surface2);border:1px solid var(--line);border-radius:10px;overflow:hidden;scroll-margin-top:140px}}
.cl img,.cl .noimg{{display:block;width:100%;height:auto;aspect-ratio:4/3;object-fit:contain;background:#fff}}
.noimg{{display:flex!important;align-items:center;justify-content:center;color:#889;font-size:12px}}
.cl figcaption{{padding:6px 8px 8px;font-size:13px;line-height:1.35}}.cl b{{display:block;font-weight:500}}.cl small{{color:var(--muted)}}
.bd{{display:inline-block;margin:4px 4px 0 0;font-size:11px;color:var(--amber);border:1px solid var(--amber);border-radius:4px;padding:0 4px}}
.cl.hit{{outline:2px solid var(--amber)}}
.cl{{position:relative}}.cl.ts{{border:3px solid var(--amber)}}.cl.ts::before{{content:"釣れ筋";position:absolute;top:6px;left:6px;z-index:1;background:var(--amber);color:#1a1200;font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px}}
.tsure-box{{border:2px solid var(--amber)}}.tsure-box .tcat-tsl a{{min-height:34px;padding:4px 10px;font-size:13px}}.tcat-tsc b{{font-size:15px}}.tcat-tsc small{{color:var(--muted)}}
[data-tcat-rank] li a{{color:var(--ink)}}.tsure-box h2{{color:var(--amber)}}
.ts-card{{display:grid;grid-template-columns:120px 1fr;gap:12px;align-items:start;padding:10px 0;border-top:1px solid var(--line)}}.ts-card:first-of-type{{border-top:0}}
.ts-card img{{width:120px;height:90px;object-fit:contain;background:#fff;border-radius:8px;border:2px solid var(--amber)}}
.ts-card b{{display:block;font-size:15px;line-height:1.4}}.ts-card small{{color:var(--muted)}}.ts-card .links{{margin:8px 0 0}}.ts-card .links a{{min-height:34px;padding:4px 10px;font-size:13px}}
.app-box{{display:grid;gap:12px}}.app-head{{display:flex;gap:12px;align-items:center}}.app-head img{{width:64px;height:64px;border-radius:14px}}.app-head b{{font-size:18px;display:block}}.app-head small{{color:var(--muted)}}
.app-banner img{{display:block;width:100%;height:auto;border-radius:12px}}.app-box ul{{margin:0;padding-left:1.2em}}.app-box li{{margin:2px 0}}.app-btns{{display:flex;flex-wrap:wrap;gap:8px}}.app-btns a.sub{{background:transparent;color:var(--teal);border:1px solid var(--teal)}}
.hide{{display:none!important}}
.app-box p{{margin:0 0 10px}}.app-box a.btn{{display:inline-block;background:var(--teal);color:#03161c;font-weight:700;text-decoration:none;border-radius:10px;padding:10px 16px}}
footer{{color:var(--muted);font-size:13px;border-top:1px solid var(--line);margin-top:28px;padding-top:14px}}
</style>
</head>
<body>
<div class="wrap">
<header class="top"><a href="https://cutlassfish.tokyo/">東京湾の魚・釣り</a><a class="app" href="/">ドラゴンカウンター</a></header>
<p class="eyebrow">TENYA CATALOG</p>
<h1>船タチウオテンヤ カタログ</h1>
<p class="lead">{lead}</p>
<p class="note"><b style="color:var(--ink)">号数は {zlist}</b>のテンヤを載せています。色の名前・号数はメーカーの表記です。{upd} 時点。最新の情報はメーカーのページで確かめてください。</p>
<span class="pr">PR：このページはアフィリエイト広告（Amazon・楽天・Yahoo!ショッピング）を利用しています</span>

<div data-tcat="1">
<section class="box tsure-box" data-tcat-ts="1" style="display:none">
 <h2>釣れ筋テンヤ</h2>
 <div data-tcat-ts-list="1"></div>
</section>

<section class="box" data-tcat-rank="1" style="display:none">
 <h2>ドラゴンカウンターのランキング</h2>
 <p class="note" style="margin:-4px 0 10px">釣果記録アプリ「ドラゴンカウンター」に匿名で集まった記録から。号数はまとめています。</p>
 <div class="rk-cols"><div data-tcat-rank-catch="1" style="display:none"><h3>よく釣れているテンヤ</h3><ol></ol></div><div data-tcat-rank-use="1" style="display:none"><h3>よく使われているテンヤ</h3><ol></ol></div></div>
</section>

<div data-tcat-bar="1"></div>

{cards}
</div>

<section class="box app-box">
 <div class="app-head"><img src="/icon-192.png" alt="" width="64" height="64"><div><b>ドラゴンカウンター</b><small>タチウオの釣果記録アプリ（無料・登録なし）</small></div></div>
 <a class="app-banner" href="/"><img src="/og.png" alt="ドラゴンカウンター：タチウオの釣果を時間の経過と共に、テンヤ・潮・船の向きと一緒に記録" width="1200" height="630" loading="lazy"></a>
 <p>ドラゴンカウンターは釣果を数えるアプリですが、<b>持っているテンヤの管理</b>もできます。このページと同じテンヤのリストを持っているので、持っているテンヤを選んで個数まで一覧にしておけます。その中から選んでおけば、釣れたときにボタンを押すだけで「どのテンヤで、何時に釣れたか」が残ります。</p>
 <ul><li>このページと同じリストから、持っているテンヤを登録・個数を管理</li><li>釣り場を選ぶと、潮回りと満潮・干潮が自動で入る</li><li>アタリ・バラシ・釣れた時刻を、ボタン1つで記録</li><li>ドラゴン（120cm以上）や大漁も記録できる</li><li>記録はスマホの中に保存。アプリとしてホーム画面にも置ける</li></ul>
 <div class="app-btns"><a class="btn" href="/">ドラゴンカウンターを開く</a><a class="btn sub" href="https://cutlassfish.tokyo/article/dragon-counter/">使い方の記事を読む</a></div>
</section>

<footer>
 <p>写真はメーカーの製品写真を切り抜いたものです。写真のない色もあります。</p>
 <p>Amazonのアソシエイトとして、このサイトは適格販売により収入を得ています。</p>
 <p><a href="https://cutlassfish.tokyo/">東京湾の魚・釣り（cutlassfish.tokyo）</a></p>
</footer>
</div>
<script src="/tenya-catalog/catalog.js?v={js}" defer></script>
</body>
</html>
'''


def main():
    allc, plist, rmap, pv = build()
    os.makedirs(OUT, exist_ok=True)
    s = page(allc, plist, pv)
    open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(s)
    json.dump(rmap, open(os.path.join(OUT, 'rank-map.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(len(plist), 'products,', sum(len(r['cols']) for r in plist), 'colours,', len(rmap), 'items,',
          sum(1 for r in plist for c in r['cols'].values() if c['img']), 'with photo,', len(s) // 1024, 'KB')
    sys.path.insert(0, HERE); import tenya_article; tenya_article.build_article()   # the same catalog as a cutlassfish.tokyo article


if __name__ == '__main__':
    main()
