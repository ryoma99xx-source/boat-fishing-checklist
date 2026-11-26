"""AI・検索に読まれやすくするための付け足し（dragon-counter.cutlassfish.tokyo）。オーナー指示 2026-11-26。

    python3 tools/seo_extras.py        sitemap.xml・llms.txt・robots.txt を作り、各ページの構造化データ（JSON-LD）を入れ直す

- 構造化データ：<head> の <!--ld--> と <!--/ld--> の間を、ページの <title>・説明・正式なURL から作り直す（無ければ </head> の前に足す）。
  アプリ（カウンター3つ）は WebApplication、カタログは CollectionPage。見た目は変わらない。
- ページを作るスクリプト（tairaba_build・tipran_build・tenya_page・egi_page・tairaba_page）は書き出す前に ld() を通す。
- リンク集（/links/）は検索に出さない設定（noindex）なので、サイトマップに入れない。
"""
import html as H, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(os.path.dirname(HERE), 'public')
HOST = 'https://dragon-counter.cutlassfish.tokyo'
PAGES = [  # (公開の道, ファイル, 種類)
    ('/', 'index.html', 'app'),
    ('/tipran/', 'tipran/index.html', 'app'),
    ('/tairaba/', 'tairaba/index.html', 'app'),
    ('/tenya-catalog/', 'tenya-catalog/index.html', 'catalog'),
    ('/egi-catalog/', 'egi-catalog/index.html', 'catalog'),
    ('/tairaba-catalog/', 'tairaba-catalog/index.html', 'catalog'),
    ('/tairaba-catalog/ties/', 'tairaba-catalog/ties/index.html', 'catalog'),
]
KIND = {p: k for p, f, k in PAGES}
SITE = {'@type': 'WebSite', 'name': '東京湾の魚・釣り（3rd-Penguin Fishing Lab.）', 'url': 'https://cutlassfish.tokyo/'}


def _meta(s, name):
    m = re.search(r'<meta\s+(?:name|property)="%s"\s+content="([^"]*)"' % re.escape(name), s)
    return H.unescape(m.group(1)) if m else ''


def ld(s, path):
    """ページの html に構造化データを入れて返す。path は公開の道（例 '/tairaba/'）"""
    kind = KIND.get(path)
    if not kind:
        return s
    t = re.search(r'<title>(.*?)</title>', s, re.S)
    title = H.unescape(t.group(1).strip()) if t else ''
    desc = _meta(s, 'description')
    url = HOST + path
    if kind == 'app':
        d = {'@context': 'https://schema.org', '@type': 'WebApplication', 'name': title, 'url': url, 'description': desc,
             'applicationCategory': 'SportsApplication', 'operatingSystem': 'Web（ブラウザ）', 'inLanguage': 'ja',
             'isAccessibleForFree': True, 'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'JPY'},
             'publisher': {'@type': 'Organization', 'name': '3rd-Penguin Fishing Lab.', 'url': 'https://cutlassfish.tokyo/'}, 'isPartOf': SITE}
    else:
        d = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': title, 'url': url, 'description': desc,
             'inLanguage': 'ja', 'isPartOf': SITE, 'publisher': {'@type': 'Organization', 'name': '3rd-Penguin Fishing Lab.', 'url': 'https://cutlassfish.tokyo/'}}
    block = '<!--ld--><script type="application/ld+json">%s</script><!--/ld-->' % json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    if '<!--ld-->' in s:
        return re.sub(r'<!--ld-->.*?<!--/ld-->', lambda m: block, s, count=1, flags=re.S)
    return s.replace('</head>', block + '\n</head>', 1)


def lastmod(f):
    try:
        r = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', f], cwd=PUB, capture_output=True, text=True)
        return r.stdout.strip() or None
    except Exception:
        return None


def main():
    # 1) 各ページの構造化データを入れ直す
    for p, f, k in PAGES:
        fp = os.path.join(PUB, f)
        s = open(fp, encoding='utf-8').read()
        s2 = ld(s, p)
        if s2 != s:
            open(fp, 'w', encoding='utf-8').write(s2)
            print('ld:', f)
    # 2) サイトマップ
    xs = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p, f, k in PAGES:
        lm = lastmod(f)
        xs.append('<url><loc>%s%s</loc>%s</url>' % (HOST, p, '<lastmod>%s</lastmod>' % lm if lm else ''))
    xs.append('</urlset>')
    open(os.path.join(PUB, 'sitemap.xml'), 'w', encoding='utf-8').write('\n'.join(xs) + '\n')
    # 3) robots.txt（全部どうぞ＋サイトマップの場所）
    open(os.path.join(PUB, 'robots.txt'), 'w', encoding='utf-8').write('User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % HOST)
    # 4) llms.txt（AI 向けの案内）
    L = ['# 東京湾の釣りツール（3rd-Penguin Fishing Lab.）', '',
         '> 東京湾の船釣りのための無料ツール。登録なしでブラウザで使える釣果記録アプリ（タチウオ・アオリイカ・マダイ）と、テンヤ・エギ・タイラバの製品と色を写真で一覧にしたカタログ。記事は本サイト https://cutlassfish.tokyo/ にあります（https://cutlassfish.tokyo/llms.txt）。', '']
    for head, kind in (('## 釣果記録アプリ', 'app'), ('## カタログ', 'catalog')):
        L.append(head)
        for p, f, k in PAGES:
            if k != kind:
                continue
            s = open(os.path.join(PUB, f), encoding='utf-8').read()
            t = re.search(r'<title>(.*?)</title>', s, re.S)
            L.append('- [%s](%s%s): %s' % (H.unescape(t.group(1).strip()) if t else p, HOST, p, _meta(s, 'description')))
        L.append('')
    L += ['## そのほか', '- [東京湾の潮と流れ](https://tide-current-map.cutlassfish.tokyo/): 地図で東京湾の場所ごとの流れの向き・速さと潮位を見る無料ツール', '- [サイトマップ](%s/sitemap.xml)' % HOST]
    open(os.path.join(PUB, 'llms.txt'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('sitemap.xml, robots.txt, llms.txt')


if __name__ == '__main__':
    main()
