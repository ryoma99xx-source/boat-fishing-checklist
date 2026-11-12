"""The タチウオテンヤ catalog as a cutlassfish.tokyo article (article pack for wordpress/article-pack/cfpack.py).

    python3 tools/tenya_article.py          # also run by tenya_page.py, so it follows every catalog update

Output: wordpress/tenya-catalog/{article.json, article.html, images/tenya-collage.jpg}
Same data and links as the tool page (/tenya-catalog/), which stays as the version with filters and the ranking.
WordPress removes scripts, so the article finds things by a maker table of contents instead of filters.
Photos are loaded from dragon-counter.cutlassfish.tokyo (the app's own cut photos); the featured image is a
collage of those photos (only arranged, not edited)."""
import html, json, os, urllib.parse
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


def collage(plist, pv, path):
    """1200x630: one photo from each product, in a grid on the site's dark colour."""
    src = os.path.join(T.PUB, 'tenya')
    pics = []
    for r in plist:
        for c in r['cols'].values():
            if c['img'] and '旧型' not in r['p'] and not r['h']:
                pics.append(c['img']); break
    W, H, cols, rows = 1200, 630, 6, 4
    cw, ch = W // cols, H // rows
    im = Image.new('RGB', (W, H), (6, 10, 17))
    for n, i in enumerate(pics[:cols * rows]):
        p = Image.open(os.path.join(src, i + '.webp')).convert('RGBA')
        p.thumbnail((cw - 12, ch - 12), Image.LANCZOS)
        tile = Image.new('RGBA', (cw - 8, ch - 8), (255, 255, 255, 255))
        tile.alpha_composite(p, ((tile.width - p.width) // 2, (tile.height - p.height) // 2))
        im.paste(tile.convert('RGB'), ((n % cols) * cw + 4, (n // cols) * ch + 4))
    im.save(path, 'JPEG', quality=85)


def build_article():
    allc, plist, _, pv = T.build()
    makers = [m for m in T.ORDER if any(r['m'] == m for r in plist)]
    ncol = sum(len(r['cols']) for r in plist)
    upd = allc.get('updated', '')
    toc = ''.join('<a href="#mk-%s" style="display:inline-block;border:1px solid #ccd;border-radius:999px;padding:4px 12px;margin:0 6px 8px 0;text-decoration:none">%s</a>'
                  % (SLUG.get(m, 'x'), E(T.JP.get(m, m))) for m in makers)
    body = []
    for m in makers:
        rs = [r for r in plist if r['m'] == m]
        body.append('<h2 id="mk-%s"><span class="en">%s</span>%s</h2>\n<p>%d製品・%d色</p>'
                    % (SLUG.get(m, 'x'), E(m.upper()), E(T.JP.get(m, m)), len(rs), sum(len(r['cols']) for r in rs)))
        for r in rs:
            zl = sorted(r['z'])
            zr = '%s号' % T.zs(zl[0]) if len(zl) == 1 else '%s〜%s号' % (T.zs(zl[0]), T.zs(zl[-1]))
            kw = T.search_kw(r['m'], r['p'])
            figs = []
            for c in r['cols'].values():
                zz = '・'.join(T.zs(z) for z in sorted(set(c['z']))) + '号'
                bd = ''.join(' <span style="font-size:11px;color:#b5710b;border:1px solid #b5710b;border-radius:4px;padding:0 4px;white-space:nowrap">%s</span>' % E(s) for s in sorted(c['s']))
                img = ('<img src="%s" alt="%s %s" width="240" height="180" loading="lazy" style="display:block;width:100%%;height:auto;aspect-ratio:4/3;object-fit:contain;background:#fff">'
                       % (photo(c['img'], pv), E(r['p']), E(c['c']))) if c['img'] else ''
                figs.append('<figure style="margin:0;border:1px solid #e3e6ea;border-radius:8px;overflow:hidden;background:#fff">%s'
                            '<figcaption style="padding:6px 8px;font-size:13px;line-height:1.4">%s<br><small style="color:#667">%s</small>%s</figcaption></figure>'
                            % (img, E(c['c']), zz, bd))
            links = ''
            if r['u']:
                links += '<a href="%s" target="_blank" rel="noopener" style="%s;border:1px solid #99a;color:inherit">メーカーのページ</a>' % (E(r['u']), BTN)
            links += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#f3a847;color:#111 !important">Amazonで探す</a>' % (E(T.amazon(kw)), BTN)
            links += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#bf0000;color:#fff !important">楽天で探す</a>' % (E(T.rakuten(kw)), BTN)
            links += '<a href="%s" target="_blank" rel="nofollow sponsored noopener" style="%s;background:#ff0033;color:#fff !important">Yahoo!で探す</a>' % (E(T.yahoo(kw)), BTN)
            body.append('<h3>%s</h3>\n<p>%s・%d色%s</p>\n<p>%s</p>\n<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;margin:0 0 28px">%s</div>'
                        % (E(r['p']), zr, len(r['cols']), '・替えヘッド' if r['h'] else ('・今は作られていない前のモデル' if '旧型' in r['p'] else ''), links, ''.join(figs)))
    a = []
    a.append('<p class="lead">「このテンヤ、ほかにどんな色があったっけ？」と思っても、メーカーのページを行ったり来たりして探すのは面倒です。そこで、船タチウオテンヤを<strong>メーカー・製品ごとに、全部の色を写真で一覧</strong>にしました。%dメーカー・%d製品・%d色。釣果記録アプリ「ドラゴンカウンター」のテンヤカタログと同じデータで、新しいテンヤが出たら毎月足していきます。</p>'
             % (len(makers), len(plist), ncol))
    a.append('<p><small>※この記事には、Amazon・楽天市場・Yahoo!ショッピングへのアフィリエイトリンク（広告）が含まれます。</small></p>')
    a.append('<h2><span class="en">HOW</span>このカタログの見方</h2>')
    a.append('<ul><li>製品ごとに、出ている号数と色の数、メーカーのページ、Amazon・楽天・Yahoo!ショッピングで探すボタンを並べています。</li>'
             '<li>写真の下は、色の名前と、その色がある号数です。「限定色」「生産終了・在庫のみ」「発売予定」などは印を付けています。</li>'
             '<li>色の名前と号数はメーカーの表記のままです。写真はメーカーの製品写真を切り抜いたものです。</li>'
             '<li>メーカーごとに、今の製品 → 替えヘッド → 旧型（今は作られていない前のモデル）の順です。旧型も、在庫や手持ちで見かけるので載せています。</li></ul>')
    a.append('<p><b>号数や色の名前で絞り込みたいとき</b>は、<a href="%s">ツール版のテンヤカタログ</a>が便利です。同じ内容を、メーカー・号数・色の名前（「グロー」「ゼブラ」など）で絞り込めます。ドラゴンカウンターに記録がたまったら、「よく釣れているテンヤ」「よく使われているテンヤ」のランキングもそちらに出ます。</p>' % TOOL)
    a.append('<h2><span class="en">WORDS</span>色や製品名によく出てくる言葉</h2>')
    a.append('<ul><li><b>グロー・夜光</b>：光をためて、暗いところで光る塗装。</li>'
             '<li><b>ケイムラ</b>：紫外線が当たると青白く光る塗装。</li>'
             '<li><b>ゼブラ</b>：縞模様の柄。</li>'
             '<li><b>ホロ</b>：ホログラムのシートを使ったもの。</li>'
             '<li><b>シングル・ダブル</b>：針が1本か2本か。</li>'
             '<li><b>TG（タングステン）</b>：鉛より比重が大きい金属。同じ号数でもヘッドが小さくなります。</li>'
             '<li><b>替えヘッド</b>：ヘッド（オモリの部分）だけの交換用。対応する本体と組み合わせて使います。</li></ul>')
    a.append('<h2><span class="en">APP</span>どのテンヤで釣れたかを残すなら</h2>')
    a.append('<p>このカタログは、タチウオの釣果記録アプリ<a href="%s">ドラゴンカウンター</a>のテンヤカタログと同じものです。持っているテンヤをこのカタログから選んでおけば、釣れたときにボタンを押すだけで「どのテンヤで、何時に、どんな潮で釣れたか」が残ります。無料で、登録もいりません。</p>' % APP)
    a.append('<h2><span class="en">CATALOG</span>メーカー別の一覧</h2>')
    a.append('<p>%s</p>' % toc)
    a.extend(body)
    a.append('<p><small>%s 時点の内容です。価格や在庫は各ショップで確かめてください。Amazonのアソシエイトとして、このサイトは適格販売により収入を得ています。</small></p>' % E(upd))
    art = {'version': 1,
           'title': '船タチウオテンヤ カタログ｜%dメーカー・%d色を写真で一覧（毎月更新）' % (len(makers), ncol),
           'excerpt': 'ダイワ・シマノ・ハヤブサなど%dメーカーの船タチウオテンヤ%d製品・%d色を、写真で一覧にしました。号数と色の名前の見方、メーカー別の目次付き。釣果記録アプリ「ドラゴンカウンター」と同じデータで毎月更新します。' % (len(makers), len(plist), ncol),
           'images': [{'id': 'tenya-collage', 'file': 'images/tenya-collage.jpg', 'alt': '船タチウオテンヤの写真を並べたもの'}],
           'featured_image': 'tenya-collage'}
    os.makedirs(os.path.join(OUT, 'images'), exist_ok=True)
    collage(plist, pv, os.path.join(OUT, 'images', 'tenya-collage.jpg'))
    open(os.path.join(OUT, 'article.html'), 'w', encoding='utf-8').write('\n\n'.join(a) + '\n')
    json.dump(art, open(os.path.join(OUT, 'article.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('article:', art['title'], sum(len(x) for x in a) // 1024, 'KB')


if __name__ == '__main__':
    build_article()
