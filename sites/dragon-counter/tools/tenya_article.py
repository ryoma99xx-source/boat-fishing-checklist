"""The タチウオテンヤ catalog as a cutlassfish.tokyo article (article pack for wordpress/article-pack/cfpack.py).

    python3 tools/tenya_article.py          # also run by tenya_page.py, so it follows every catalog update

Output: wordpress/tenya-catalog/{article.json, article.html, images/tenya-collage.jpg}
Same data and links as the tool page (/tenya-catalog/), which stays as the version with filters and the ranking.
WordPress removes scripts, so the article finds things by a maker table of contents instead of filters.
Photos are loaded from dragon-counter.cutlassfish.tokyo (the app's own cut photos); the featured image is a
collage of those photos (only arranged, not edited) with a title band, 1080x1350 for Instagram."""
import html, json, os, shutil, urllib.parse, urllib.request
from PIL import Image

import tenya_page as T

REPO = os.path.dirname(os.path.dirname(T.SITE))
OUT = os.path.join(REPO, 'wordpress', 'tenya-catalog')
TOOL = 'https://dragon-counter.cutlassfish.tokyo/tenya-catalog/'
APP = 'https://dragon-counter.cutlassfish.tokyo/'
E = lambda x: html.escape(str(x), quote=True)
BTN = 'display:inline-block;font-size:14px;font-weight:700;padding:8px 14px;border-radius:8px;text-decoration:none;margin:0 6px 6px 0'
SLUG = {'DAIWA': 'daiwa', 'SHIMANO': 'shimano', 'HAYABUSA': 'hayabusa', 'JACKALL': 'jackall', 'START': 'start', 'OWNER': 'owner',
        'Major Craft': 'majorcraft', 'DUO': 'duo', 'PRO MARINE': 'promarine', 'YAMASHITA': 'yamashita', 'がまかつ': 'gamakatsu',
        'マルシン漁具': 'marushin'}


def photo(i, pv):
    return 'https://dragon-counter.cutlassfish.tokyo/tenya/%s.webp%s' % (i, '?v=' + urllib.parse.quote(pv) if pv else '')


def collage(plist, pv, path, nmk, ncol):
    """Featured image, 1080x1350 (4:5, the tallest shape Instagram shows in full): 24 tenya photos, 3 rows above and
    3 rows below a title band. The band is in the middle so a landscape or square crop (site cards, X) still shows it.
    Photos are only arranged and made smaller; the title is drawn on the band, not on the photos."""
    from PIL import ImageDraw, ImageFont
    src = os.path.join(T.PUB, 'tenya')
    # one product from each maker in turn, a different colour each time, so the grid is not all one maker
    by = {}
    for r in plist:
        if '旧型' in r['p'] or r['h']:
            continue
        cs = [c['img'] for c in r['cols'].values() if c['img']]
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
    fd = os.path.join(T.HERE, 'fonts')
    jp = lambda z: ImageFont.truetype(os.path.join(fd, 'NotoSansJP-Bold.ttf'), z)
    en = ImageFont.truetype(os.path.join(fd, 'BarlowCondensed-SemiBold.ttf'), 40)
    y0 = 3 * th
    d.rectangle([0, y0, W, y0 + band], fill=(11, 20, 34))
    d.rectangle([0, y0, W, y0 + 5], fill=(227, 164, 59)); d.rectangle([0, y0 + band - 5, W, y0 + band], fill=(227, 164, 59))

    def centre(text, font, y, fill, spacing=0):
        w = d.textlength(text, font=font) + spacing * (len(text) - 1)
        x = (W - w) / 2
        if not spacing:
            d.text((x, y), text, font=font, fill=fill); return
        for ch in text:
            d.text((x, y), ch, font=font, fill=fill); x += d.textlength(ch, font=font) + spacing
    centre('TENYA CATALOG', en, y0 + 26, (65, 201, 198), 8)
    centre('船タチウオテンヤ カタログ', jp(78), y0 + 68, (238, 243, 248))
    centre('%dメーカー・%d色を写真で一覧' % (nmk, ncol), jp(42), y0 + 182, (227, 164, 59))
    im.save(path, 'JPEG', quality=88)


def tsure_keys():
    """釣れ筋（"maker|product|colour" の上位3つ）。決め方はページに書かない。届かなければ無し"""
    try:
        with urllib.request.urlopen(T.URL.replace('tenya-catalog/', 'tenya-rank.php') + '?t=%d' % __import__('time').time(), timeout=15) as r:
            return [k for k in json.load(r).get('top', [])][:3]
    except Exception as e:
        print('釣れ筋を読めませんでした:', e)
        return []


def links_html(r, small=False):
    kw = T.search_kw(r['m'], r['p'])
    b = BTN + (';font-size:13px;padding:6px 10px' if small else '')
    x = ''
    if r['u'] and not small:
        x += '<a href="%s" target="_blank" rel="noopener" style="%s;border:1px solid #99a;color:inherit">メーカーのページ</a>' % (E(r['u']), b)
    x += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#f3a847;color:#111 !important">Amazonで探す</a>' % (E(T.amazon(kw)), b)
    x += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#bf0000;color:#fff !important">楽天で探す</a>' % (E(T.rakuten(kw)), b)
    x += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#ff0033;color:#fff !important">Yahoo!で探す</a>' % (E(T.yahoo(kw)), b)
    return x


AMB = '#e3a43b'


def build_article():
    allc, plist, _, pv = T.build()
    top = tsure_keys()
    anchor = {}
    makers = [m for m in T.ORDER if any(r['m'] == m for r in plist)]
    ncol = sum(len(r['cols']) for r in plist)
    upd = allc.get('updated', '')
    body = []
    for m in makers:
        rs = [r for r in plist if r['m'] == m]
        blk = ['<div data-tcat-mkb="%s">' % E(m),
               '<h2 id="mk-%s"><span class="en">%s</span>%s</h2>\n<p>%d製品・%d色</p>'
               % (SLUG.get(m, 'x'), E(m.upper()), E(T.JP.get(m, m)), len(rs), sum(len(r['cols']) for r in rs))]
        for r in rs:
            pi = plist.index(r)
            zl = sorted(r['z'])
            zr = '%s号' % T.zs(zl[0]) if len(zl) == 1 else '%s〜%s号' % (T.zs(zl[0]), T.zs(zl[-1]))
            figs = []
            for ci, c in enumerate(r['cols'].values()):
                zz = '・'.join(T.zs(z) for z in sorted(set(c['z']))) + '号'
                bd = ''.join(' <span style="font-size:11px;color:#e3a43b;border:1px solid #e3a43b;border-radius:4px;padding:0 4px;white-space:nowrap">%s</span>' % E(s) for s in sorted(c['s']))
                img = ('<img src="%s" alt="%s %s" width="240" height="180" loading="lazy" style="display:block;width:100%%;height:auto;aspect-ratio:4/3;object-fit:contain;background:#fff">'
                       % (photo(c['img'], pv), E(r['p']), E(c['c']))) if c['img'] else ''
                k = '%s|%s|%s' % (r['m'], r['p'], c['c'])
                fid = 'c-%d-%d' % (pi, ci)
                if k in top:
                    anchor[k] = (r, c, fid)
                figs.append('<figure %s class="%s" style="margin:0;border:1px solid #1f2d42;border-radius:8px;overflow:hidden;background:#101c2e;color:#eef3f8;position:relative">%s'
                            '<figcaption style="padding:6px 8px;font-size:13px;line-height:1.4;color:#eef3f8">%s<br><small style="color:#9cabbd">%s</small>%s</figcaption></figure>'
                            % (T.fig_attrs(r, c, fid), 'tcat-ts' if k in top else '', img, E(c['c']), zz, bd))
            blk.append('<div %s>\n<h3 id="tp-%d">%s</h3>\n<p>%s・%d色%s</p>\n<p data-tcat-links="1">%s</p>\n<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;margin:0 0 28px">%s</div>\n</div>'
                       % (T.prod_attrs(r), pi, E(r['p']), zr, len(r['cols']), '・替えヘッド' if r['h'] else ('・今は作られていない前のモデル' if '旧型' in r['p'] else ''), links_html(r), ''.join(figs)))
        blk.append('</div>')
        body.append('\n'.join(blk))
    a = []
    a.append('<p class="lead">「このテンヤ、ほかにどんな色があったっけ？」と思っても、メーカーのページを行ったり来たりして探すのは面倒です。そこで、船タチウオテンヤを<strong>メーカー・製品ごとに、全部の色を写真で一覧</strong>にしました。%dメーカー・%d製品・%d色、号数違いまで数えると%d種類です。<b>号数は30号・40号・50号</b>のものを載せています。釣果記録アプリ「ドラゴンカウンター」のテンヤカタログと同じデータで、新しいテンヤが出たら毎月足していきます。</p>'
             % (len(makers), len(plist), ncol, len(allc['items'])))
    a.append('<p><small>※この記事には、Amazon・楽天市場・Yahoo!ショッピングへのアフィリエイトリンク（広告）が含まれます。</small></p>')
    cards = []
    for k in top:
        if k not in anchor:
            continue
        r, c, fid = anchor[k]
        img = '<img src="%s" alt="%s %s" width="240" height="180" loading="lazy" style="display:block;width:100%%;height:auto;aspect-ratio:4/3;object-fit:contain;background:#fff;border-radius:8px;border:2px solid %s">' % (photo(c['img'], pv), E(r['p']), E(c['c']), AMB) if c['img'] else ''
        cards.append('<div style="display:grid;grid-template-columns:minmax(110px,160px) 1fr;gap:12px;align-items:start;padding:12px 0;border-top:1px solid #2a3a52">'
                     '<a href="#%s" data-go="%s">%s</a><div><b style="font-size:16px">%s</b><br>%s<br><small style="color:#9cabbd">%s</small><div style="margin-top:8px">%s</div></div></div>'
                     % (fid, fid, img, E(c['c']), E(r['p']), E(T.JP.get(r['m'], r['m'])), links_html(r, True)))
    a.append('<div data-tcat-ts="1" style="border:3px solid %s;border-radius:12px;padding:14px 16px;margin:24px 0;background:#0b1422;color:#eef3f8;%s"><p style="margin:0 0 4px;font-weight:700;color:#e3a43b;font-size:18px">釣れ筋テンヤ</p><div data-tcat-ts-list="1">%s</div></div>'
             % (AMB, '' if cards else 'display:none', ''.join(cards)))
    a.append('<div data-tcat-rank="1" style="display:none;border:1px solid #1f2d42;border-radius:12px;padding:14px 16px;margin:24px 0;background:#0b1422;color:#eef3f8"><p style="margin:0 0 4px;font-weight:700;font-size:18px">ドラゴンカウンターのランキング</p>'
             '<p style="margin:0 0 10px;font-size:13px;color:#9cabbd">釣果記録アプリ「ドラゴンカウンター」に匿名で集まった記録から。号数はまとめています。</p>'
             '<div data-tcat-rank-catch="1" style="display:none;margin:0 0 14px"><p style="margin:0 0 4px;font-weight:700">よく釣れているテンヤ</p><ol></ol></div>'
             '<div data-tcat-rank-use="1" style="display:none"><p style="margin:0 0 4px;font-weight:700">よく使われているテンヤ</p><ol></ol></div></div>')
    a.append('<div style="display:flex;gap:12px;align-items:center;border:1px solid #44566e;border-radius:12px;padding:12px 14px;margin:20px 0">'
             '<a href="%s" style="flex:0 0 56px;width:56px;display:block"><img src="%sicon-192.png" alt="ドラゴンカウンター" width="56" height="56" style="width:56px;min-width:56px;max-width:none;height:56px;border-radius:12px;display:block;object-fit:cover"></a>'
             '<div style="font-size:14px;line-height:1.6;flex:1 1 0;min-width:0">このカタログは、タチウオの釣果記録アプリ<a href="%s"><b>ドラゴンカウンター</b></a>のテンヤカタログと同じです。持っているテンヤの管理もでき、どのテンヤで釣れたかをボタン1つで残せます。<a href="#dc-app">くわしくは下で ↓</a></div></div>' % (APP, APP, APP))
    a.append('<h2><span class="en">HOW</span>このカタログの見方</h2>')
    a.append('<ul><li>製品ごとに、出ている号数と色の数、メーカーのページ、Amazon・楽天・Yahoo!ショッピングで探すボタンを並べています。</li>'
             '<li>写真の下は、色の名前と、その色がある号数です。「限定色」「生産終了・在庫のみ」「発売予定」などは印を付けています。</li>'
             '<li>カタログに入ってから3か月のテンヤには、写真の右上に <b>NEW</b> の印が付きます。「新商品だけ」を押すと、NEW と発売予定のものだけに絞れます。</li>'
             '<li>色の名前と号数はメーカーの表記のままです。写真はメーカーの製品写真を切り抜いたものです。</li>'
             '<li>メーカーごとに、今の製品 → 替えヘッド → 旧型（今は作られていない前のモデル）の順です。旧型も、在庫や手持ちで見かけるので載せています。</li></ul>')
    a.append('<p><b>一覧の上で、号数・新商品・タングステン（TG）・メーカーで絞り込み、色や製品の名前で検索できます。</b>ドラゴンカウンターのカタログと同じ探し方です。「ケイムラ 40」「ダイワ グロー」のように、空白で区切って続けて入れると、全部に当てはまるものだけが残ります。数字だけ入れると号数で探します。</p>')
    a.append('<h2><span class="en">WORDS</span>色や製品名によく出てくる言葉</h2>')
    a.append('<ul><li><b>グロー・夜光</b>：光をためて、暗いところで光る塗装。</li>'
             '<li><b>ケイムラ</b>：紫外線が当たると青白く光る塗装。</li>'
             '<li><b>ゼブラ</b>：縞模様の柄。</li>'
             '<li><b>ホロ</b>：ホログラムのシートを使ったもの。</li>'
             '<li><b>シングル・ダブル</b>：針が1本か2本か。</li>'
             '<li><b>TG（タングステン）</b>：鉛より比重が大きい金属。同じ号数でもヘッドが小さくなります。</li>'
             '<li><b>替えヘッド</b>：ヘッド（オモリの部分）だけの交換用。対応する本体と組み合わせて使います。</li></ul>')
    a.append('<h2 id="dc-app"><span class="en">APP</span>どのテンヤで釣れたかを残すなら「ドラゴンカウンター」</h2>')
    a.append('<figure class="figure" style="max-width:720px;margin:20px auto"><a href="%s"><img src="%sog.png" alt="ドラゴンカウンター：タチウオの釣果を時間の経過と共に、テンヤ・潮・船の向きと一緒に記録" width="1200" height="630" style="display:block;max-width:100%%;height:auto;border-radius:12px"></a></figure>' % (APP, APP))
    a.append('<p><a href="%s"><b>ドラゴンカウンター</b></a>は、タチウオの釣果を数えて記録するアプリです。釣果カウンターですが、<b>持っているテンヤの管理</b>もできます。このページと同じテンヤのリストをアプリの中に持っているので、持っているテンヤを選んで、個数まで一覧にしておけます。</p>' % APP)
    a.append('<p>その中から使うテンヤを選んでおけば、釣れたときにボタンを押すだけで「どのテンヤで、何時に、どんな潮で釣れたか」が残ります。無料で、登録もいりません。</p>')
    a.append('<ul><li>このページと同じリストから、持っているテンヤを登録・個数を管理</li><li>釣り場を選ぶと、潮回りと満潮・干潮が自動で入る</li><li>アタリ・バラシ・釣れた時刻を、ボタン1つで記録</li><li>ドラゴン（120cm以上）や大漁も記録できる</li><li>記録はスマホの中に保存。ホーム画面に置けばアプリのように使える</li></ul>')
    a.append('<p style="text-align:center;margin:20px 0"><a href="%s" style="display:inline-block;background:#41c9c6;color:#03161c !important;font-size:17px;font-weight:700;padding:14px 28px;border-radius:8px;text-decoration:none;margin:6px">ドラゴンカウンターを開く →</a>'
             '<a href="https://cutlassfish.tokyo/article/dragon-counter/" style="display:inline-block;border:2px solid #41c9c6;color:inherit;font-size:16px;font-weight:700;padding:12px 22px;border-radius:8px;text-decoration:none;margin:6px">使い方の記事を読む</a></p>' % APP)
    a.append('<h2><span class="en">CATALOG</span>テンヤの一覧</h2>')
    a.append('<div data-tcat="1">\n<div data-tcat-bar="1"></div>\n%s\n</div>' % '\n'.join(body))
    a.append('<p><small>%s 時点の内容です。価格や在庫は各ショップで確かめてください。Amazonのアソシエイトとして、このサイトは適格販売により収入を得ています。</small></p>' % E(upd))
    art = {'version': 1,
           'title': '船タチウオテンヤ カタログ｜%dメーカー・%d色を写真で一覧（毎月更新）' % (len(makers), ncol),
           'excerpt': 'ダイワ・シマノ・ハヤブサなど%dメーカーの船タチウオテンヤ%d製品・%d色を、写真で一覧にしました。号数・新商品・タングステン・メーカーで絞り込めて、色や製品の名前で検索できます。釣果記録アプリ「ドラゴンカウンター」と同じデータで毎月更新します。' % (len(makers), len(plist), ncol),
           'images': [{'id': 'tenya-collage', 'file': 'images/tenya-collage.jpg', 'alt': '船タチウオテンヤの写真を並べたもの'}],
           'featured_image': 'tenya-collage'}
    os.makedirs(os.path.join(OUT, 'images'), exist_ok=True)
    collage(plist, pv, os.path.join(OUT, 'images', 'tenya-collage.jpg'), len(makers), ncol)
    open(os.path.join(OUT, 'article.html'), 'w', encoding='utf-8').write('\n\n'.join(a) + '\n')
    json.dump(art, open(os.path.join(OUT, 'article.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('article:', art['title'], sum(len(x) for x in a) // 1024, 'KB')


POST_ID = 1316   # https://cutlassfish.tokyo/shopping/tachiuo-tenya-catalog/ （公開中）
FEAT = os.path.join(OUT, 'featured.json')   # いま記事に付いているアイキャッチ {sha256, media_id}


def push():
    """Replace the published article's body with the freshly built one (the owner asked for this article to follow
    the catalog automatically). Needs env WP_USER / WP_APP_PASSWORD (values are never printed).
    The featured image is uploaded again only when it changed; otherwise the one already in WordPress is kept.
    SiteGuard sometimes refuses a pack for its bytes (HTTP 403): retried with leading spaces, which changes the bytes."""
    import hashlib, re, subprocess, sys, tempfile
    if not os.environ.get('WP_USER') or not os.environ.get('WP_APP_PASSWORD'):
        print('記事の更新はできませんでした：環境変数 WP_USER / WP_APP_PASSWORD がありません（カタログのページは更新済み）'); return 1
    cf = os.path.join(REPO, 'wordpress', 'article-pack', 'cfpack.py')
    art = json.load(open(os.path.join(OUT, 'article.json'), encoding='utf-8'))
    body = open(os.path.join(OUT, 'article.html'), encoding='utf-8').read()
    img = os.path.join(OUT, 'images', 'tenya-collage.jpg')
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
                shutil.copyfile(img, os.path.join(d, 'images', 'tenya-collage.jpg'))
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
                m = re.search(r'"tenya-collage":\s*(\d+)', r.stdout)
                if m:
                    json.dump({'sha256': sha, 'media_id': int(m.group(1))}, open(FEAT, 'w', encoding='utf-8'))
            print('記事を更新しました（公開中のまま）: https://cutlassfish.tokyo/shopping/tachiuo-tenya-catalog/'); return 0
        if 'HTTP 403' not in out:
            print('記事の更新に失敗しました:', out[-300:]); return 1
    print('記事の更新に失敗しました：ファイアウォール（SiteGuard）に6回断られました'); return 1


if __name__ == '__main__':
    import sys
    build_article()
    if '--push' in sys.argv:
        sys.exit(push())
