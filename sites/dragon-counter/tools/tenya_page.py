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
import html, json, os, re, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
PUB = os.path.join(SITE, 'public')
OUT = os.path.join(PUB, 'tenya-catalog')
URL = 'https://dragon-counter.cutlassfish.tokyo/tenya-catalog/'
AMAZON_TAG = '3pdpenguinfis-22'
RAKUTEN_ID = '596849ef.4c28cf8e.596849f0.7ddddc88'
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


def rakuten(kw):
    u = 'https://search.rakuten.co.jp/search/mall/%s/' % urllib.parse.quote(kw)
    q = urllib.parse.quote(u, safe='')
    return 'https://hb.afl.rakuten.co.jp/hgc/%s/?pc=%s&m=%s' % (RAKUTEN_ID, q, q)


def load():
    s = open(os.path.join(PUB, 'index.html'), encoding='utf-8').read()
    cat = json.loads(re.search(r'const TENYA_CAT=(\{.*?\});\n', s, re.S).group(1))
    info = {(m, p): {'u': u, 'h': bool(h)} for m, p, u, h in cat['products']}
    ex = json.load(open(os.path.join(PUB, 'catalog-extra.json'), encoding='utf-8'))
    for x in ex['items']:
        info.setdefault((x['m'], x['p']), {'u': x.get('u', ''), 'h': bool(x.get('h'))})
    allc = json.load(open(os.path.join(PUB, 'catalog-all.json'), encoding='utf-8'))
    ti = json.load(open(os.path.join(PUB, 'tenya', 'index.json'), encoding='utf-8'))
    return allc, info, set(ti['ids']), ti.get('v', '')


def build():
    allc, info, photos, pv = load()
    prods, rmap = {}, {}
    for it in allc['items']:
        m, p, z, c, st = it['m'], it['p'], it['z'], it['c'], it.get('s', '')
        i = fnv('%s|%s|%s|%s' % (m, p, zs(z), c))
        pr = prods.setdefault((m, p), {'m': m, 'p': p, 'cols': {}, 'z': set(), **info.get((m, p), {'u': '', 'h': False})})
        col = pr['cols'].setdefault(c, {'c': c, 'z': [], 'img': '', 's': set()})
        col['z'].append(float(z)); pr['z'].add(float(z))
        if st:
            col['s'].add(st)
        if not col['img'] and i in photos:
            col['img'] = i
        rmap[i] = '%s|%s|%s' % (m, p, c)
    plist = sorted(prods.values(), key=lambda r: (ORDER.index(r['m']) if r['m'] in ORDER else 99, '旧型' in r['p'], r['h'], r['p']))  # 今の製品 → 替えヘッド → 旧型
    return allc, plist, rmap, pv


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
            cols.append('<figure class="cl" id="c-%d-%d" data-c="%s" data-z="%s">%s<figcaption><b>%s</b><small>%s</small>%s</figcaption></figure>'
                        % (pi, ci, E(c['c']), ' '.join(zs(z) for z in sorted(set(c['z']))), img, E(c['c']), zz, badge))
        cards.append('''<section class="pd" id="p-%d" data-m="%s" data-z="%s" data-h="%d">
 <h2><small>%s</small>%s</h2>
 <p class="meta">%s・%d色%s</p>
 <p class="links">%s<a class="buy az" href="%s" target="_blank" rel="nofollow sponsored noopener">Amazonで探す</a><a class="buy rk" href="%s" target="_blank" rel="nofollow sponsored noopener">楽天で探す</a></p>
 <div class="grid">%s</div>
</section>''' % (pi, E(r['m']), ' '.join(zs(z) for z in zl), 1 if r['h'] else 0, E(JP.get(r['m'], r['m'])), E(r['p']), zr, len(r['cols']),
                 '・替えヘッド' if r['h'] else '',
                 '<a class="off" href="%s" target="_blank" rel="noopener">メーカーのページ ↗</a>' % E(r['u']) if r['u'] else '',
                 E(amazon(kw)), E(rakuten(kw)), ''.join(cols)))
    idx = {('%s|%s|%s' % (r['m'], r['p'], c['c'])): {'a': 'c-%d-%d' % (pi, ci), 'n': '%s %s' % (r['p'], c['c']), 'mk': JP.get(r['m'], r['m']),
                                                    'img': c['img']} for pi, r in enumerate(plist) for ci, c in enumerate(r['cols'].values())}
    upd = allc.get('updated', '')
    desc = '船タチウオテンヤの全カラーを写真で一覧。ダイワ・シマノ・ハヤブサなど%dメーカー%d製品・%d色を、号数・色で絞り込めます。釣果記録アプリ「ドラゴンカウンター」のテンヤカタログと同じデータで毎月更新。' % (len(makers), len(plist), ncol)
    return TPL.format(
        title='船タチウオテンヤ カタログ｜%dメーカー・%d色を写真で比較' % (len(makers), ncol), desc=E(desc), url=URL,
        lead='主要%dメーカーの船タチウオテンヤ %d製品・%d色を写真で一覧にしました。メーカー・号数・色の名前で絞り込めます。' % (len(makers), len(plist), ncol),
        upd=E(upd), makers=''.join('<button class="chip" data-mk="%s">%s</button>' % (E(m), E(JP.get(m, m))) for m in makers),
        sizes=''.join('<option value="%s">%s号</option>' % (zs(z), zs(z)) for z in sizes),
        cards='\n'.join(cards), idx=json.dumps(idx, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'),
        pv=json.dumps(pv))


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
:root{{--bg:#060a11;--surface:#0b1422;--surface2:#101c2e;--line:#1f2d42;--ink:#eef3f8;--muted:#9cabbd;--teal:#41c9c6;--amber:#e3a43b;--pink:#e5577f;--r:14px;
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
.rk-cols ol{{list-style:none;margin:0;padding:0;counter-reset:r}}
.rk-cols li{{counter-increment:r;display:grid;grid-template-columns:28px 64px 1fr;gap:8px;align-items:center;padding:6px 0;border-top:1px solid var(--line)}}
.rk-cols li::before{{content:counter(r);font-family:var(--f-num);font-size:22px;color:var(--amber);text-align:center}}
.rk-cols li img,.rk-cols li .noimg{{width:64px;height:48px;object-fit:contain;background:#fff;border-radius:6px}}
.rk-cols li a{{color:var(--ink);text-decoration:none;font-size:14px;line-height:1.35}}.rk-cols li small{{display:block;color:var(--muted);font-size:12px}}
.filters{{position:sticky;top:0;z-index:5;background:rgba(6,10,17,.94);backdrop-filter:blur(6px);padding:10px 0;border-bottom:1px solid var(--line)}}
.chips{{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}}.chips::-webkit-scrollbar{{display:none}}
.chip{{flex:none;min-height:38px;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);font:inherit;font-size:14px}}
.chip.on{{background:var(--teal);border-color:var(--teal);color:#03161c;font-weight:700}}
.frow{{display:flex;gap:8px;margin-top:8px}}
.frow select,.frow input{{min-height:40px;border-radius:10px;border:1px solid var(--line);background:var(--surface2);color:var(--ink);font:inherit;font-size:16px;padding:6px 10px}}
.frow select{{flex:0 0 108px}}.frow input{{flex:1;min-width:0}}
.count{{color:var(--muted);font-size:13px;margin:8px 0 0}}
.pd{{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:14px;margin:14px 0;scroll-margin-top:130px}}
.pd h2{{font-size:18px;line-height:1.4;margin:0}}.pd h2 small{{display:block;font-size:13px;color:var(--teal);font-weight:500}}
.meta{{color:var(--muted);font-size:14px;margin:2px 0 8px}}
.links{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}}
.links a{{display:inline-flex;align-items:center;min-height:38px;padding:6px 14px;border-radius:10px;font-size:14px;font-weight:700;text-decoration:none}}
.off{{border:1px solid var(--line);color:var(--ink)!important;font-weight:500!important}}
.buy.az{{background:#f3a847;color:#111}}.buy.rk{{background:#bf0000;color:#fff}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}@media(min-width:600px){{.grid{{grid-template-columns:repeat(4,minmax(0,1fr))}}}}
.cl{{margin:0;background:var(--surface2);border:1px solid var(--line);border-radius:10px;overflow:hidden;scroll-margin-top:140px}}
.cl img,.cl .noimg{{display:block;width:100%;height:auto;aspect-ratio:4/3;object-fit:contain;background:#fff}}
.noimg{{display:flex!important;align-items:center;justify-content:center;color:#889;font-size:12px}}
.cl figcaption{{padding:6px 8px 8px;font-size:13px;line-height:1.35}}.cl b{{display:block;font-weight:500}}.cl small{{color:var(--muted)}}
.bd{{display:inline-block;margin:4px 4px 0 0;font-size:11px;color:var(--amber);border:1px solid var(--amber);border-radius:4px;padding:0 4px}}
.cl.hit{{outline:2px solid var(--amber)}}
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
<p class="note">色の名前・号数はメーカーの表記です。{upd} 時点。最新の情報はメーカーのページで確かめてください。</p>
<span class="pr">PR：このページはアフィリエイト広告（Amazon・楽天）を利用しています</span>

<section class="box" id="rank" hidden>
 <h2>ドラゴンカウンターのランキング</h2>
 <p class="note" style="margin:-4px 0 10px">釣果記録アプリ「ドラゴンカウンター」に匿名で集まった記録から。号数はまとめています。</p>
 <div class="rk-cols"><div id="rkCatch"><h3>よく釣れているテンヤ</h3><ol></ol></div><div id="rkUse"><h3>よく使われているテンヤ</h3><ol></ol></div></div>
</section>

<div class="filters">
 <div class="chips" id="mk"><button class="chip on" data-mk="">すべて</button>{makers}</div>
 <div class="frow"><select id="sz" aria-label="号数"><option value="">号数</option>{sizes}</select><input id="q" type="search" placeholder="色・製品名で探す（例：グロー、ゼブラ）" aria-label="色・製品名で探す"></div>
 <p class="count" id="cnt"></p>
</div>

{cards}

<section class="box app-box">
 <h2>釣れたテンヤを記録するなら</h2>
 <p>ドラゴンカウンターは、タチウオの釣果を時間・テンヤ・潮と一緒に記録する無料のアプリです。このカタログのテンヤから「持っているテンヤ」を選んでおけば、釣れたときにボタンを押すだけで記録できます。</p>
 <a class="btn" href="/">ドラゴンカウンターを開く</a>
</section>

<footer>
 <p>写真はメーカーの製品写真を切り抜いたものです。写真のない色もあります。</p>
 <p>Amazonのアソシエイトとして、このサイトは適格販売により収入を得ています。</p>
 <p><a href="https://cutlassfish.tokyo/">東京湾の魚・釣り（cutlassfish.tokyo）</a></p>
</footer>
</div>
<script>
(()=>{{
const IDX={idx},PV={pv};
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
let mk='';
function apply(){{const z=$('#sz').value,q=$('#q').value.trim().toLowerCase();let np=0,nc=0;
 $$('.pd').forEach(p=>{{let show=(!mk||p.dataset.m===mk)&&(!z||p.dataset.z.split(' ').includes(z));
  const pn=p.querySelector('h2').textContent.toLowerCase();let k=0;
  p.querySelectorAll('.cl').forEach(c=>{{const ok=show&&(!z||c.dataset.z.split(' ').includes(z))&&(!q||pn.includes(q)||c.dataset.c.toLowerCase().includes(q));c.classList.toggle('hide',!ok);if(ok)k++}});
  p.classList.toggle('hide',!k);if(k){{np++;nc+=k}}}});
 $('#cnt').textContent=`${{np}}製品・${{nc}}色`}}
$('#mk').addEventListener('click',e=>{{const b=e.target.closest('[data-mk]');if(!b)return;mk=b.dataset.mk;$$('#mk .chip').forEach(x=>x.classList.toggle('on',x===b));apply()}});
$('#sz').addEventListener('change',apply);$('#q').addEventListener('input',apply);apply();
const esc=s=>String(s).replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
const li=k=>{{const x=IDX[k];if(!x)return '';const im=x.img?`<img src="/tenya/${{x.img}}.webp${{PV?'?v='+encodeURIComponent(PV):''}}" alt="" loading="lazy">`:'<span class="noimg"></span>';
 return `<li>${{im}}<a href="#${{x.a}}" data-go="${{x.a}}">${{esc(x.n)}}<small>${{esc(x.mk)}}</small></a></li>`}};
fetch('/tenya-rank.php',{{cache:'no-cache'}}).then(r=>r.ok?r.json():null).then(d=>{{if(!d)return;let any=false;
 for(const [k,id] of [['catch','rkCatch'],['use','rkUse']]){{const l=(d[k]||[]).filter(x=>IDX[x]);const el=$('#'+id);if(l.length>=10){{el.querySelector('ol').innerHTML=l.slice(0,10).map(li).join('');any=true}}else el.remove()}}
 if(any)$('#rank').hidden=false}}).catch(()=>{{}});
document.addEventListener('click',e=>{{const a=e.target.closest('[data-go]');if(!a)return;mk='';$$('#mk .chip').forEach((x,i)=>x.classList.toggle('on',i===0));$('#sz').value='';$('#q').value='';apply();
 $$('.cl.hit').forEach(x=>x.classList.remove('hit'));const t=document.getElementById(a.dataset.go);if(t)t.classList.add('hit')}});
}})();
</script>
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


if __name__ == '__main__':
    main()
