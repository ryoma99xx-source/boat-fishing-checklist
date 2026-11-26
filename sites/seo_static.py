"""小さなツール3つ（リール糸管理・持ち物チェック・テンヤシミュレーター）を AI・検索に読まれやすくする付け足し。
オーナー指示 2026-11-26（「公開時のまま」のサイトだが、ファイルを足すことと <head> の印だけ OK）。

    python3 sites/seo_static.py        何度回しても同じ結果になる

やること（アプリの動きは変えない）
- robots.txt（全部どうぞ＋サイトマップの場所）・sitemap.xml・llms.txt（AI 向けの案内）を置く。
- リール糸管理・持ち物チェック：<head> の <!--seo--> 〜 <!--/seo--> に、足りない説明文（meta description）・正式なURLの印（canonical）・
  構造化データ（JSON-LD）を入れる。すでにある説明文・canonical には重ねない。
- テンヤシミュレーター：HTML はさわらない（React が描き直すページなので）。正式なURLの印は .htaccess の Link ヘッダーで、
  古い版のページ（/versions/）は versions/.htaccess で検索に出さない（X-Robots-Tag: noindex）。
- .htaccess：.txt と .xml を UTF-8 で返す。
- mirror-manifest.json：変えたファイル・足したファイルのハッシュを合わせる（sites/test/apache_check.py が照合に使う）。
"""
import hashlib, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ORG = {'@type': 'Organization', 'name': '3rd-Penguin Fishing Lab.', 'url': 'https://cutlassfish.tokyo/'}
SITE = {'@type': 'WebSite', 'name': '東京湾の魚・釣り（3rd-Penguin Fishing Lab.）', 'url': 'https://cutlassfish.tokyo/'}
NOTE = 'AI・検索向けの印を追加（説明文・canonical・構造化データ、2026-11-26）'

SITES = {
    'reel-line-manager': {
        'name': 'リール糸管理ツール', 'alt': 'REEL LINE MANAGER',
        'desc': 'リールの糸を、もう迷わない。リールごとの糸の種類・号数・長さ・巻き替え日・使用回数をまとめて記録できる、釣り人のための無料ツール。替えスプールやラインの在庫、買い物メモも管理できます。登録なしで使え、データは端末の中に保存されます。',
        'image': '/icons/icon-512.png', 'article': 'https://cutlassfish.tokyo/article/reel-line-manager/',
        'pages': [('/', 'index.html', None),
                  ('/help.html', 'help.html', 'リール糸管理ツールの使い方。スマホのホーム画面に追加する方法、リール・替えスプール・ラインの在庫の登録、バックアップと復元、データ保存の仕組み、よくある質問。')],
    },
    'dont-forget-anything': {
        'name': '釣り持ち物チェックツール', 'alt': "Don't forget anything",
        'desc': '釣り方ごとの持ち物リストをチェックボックスで管理する無料ツール。釣行前の準備の抜け漏れをなくします。テンヤタチウオ用・泳がせ用・遠征用のリストが最初から入っていて、自分の釣り方に合わせて編集・共有できます。登録なしで使え、データは端末の中に保存されます。',
        'image': '/icons/icon-512.png', 'article': 'https://cutlassfish.tokyo/article/dont-forget-anything/',
        'pages': [('/', 'index.html', None),
                  ('/help.html', 'help.html', '釣り持ち物チェックツール（Don\'t forget anything）の使い方。スマホのホーム画面に追加する方法、リストの編集とカスタマイズ、リストの共有、バックアップと復元、データ保存の仕組み、よくある質問。')],
    },
    'tenya-simulator': {
        'name': 'テンヤシミュレーター', 'alt': 'テンヤ海中挙動シミュレーター',
        'desc': 'タチウオのテンヤが海中でどう動くかを見る無料の理論シミュレーター。ダイワタイプとシマノ平型タイプのテンヤをA/B比較でき、叩きの幅・回数・保持角度・潮流を変えて、ヘッドの上下動とひねりを見比べられます。',
        'image': '/icons/tenya-app-v2-512.png', 'article': 'https://cutlassfish.tokyo/article/tenya-simulator/',
        'pages': [('/', 'index.html', None)], 'no_html': True,
    },
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def write(fp, text):
    b = text.encode('utf-8')
    if os.path.exists(fp) and open(fp, 'rb').read() == b:
        return False
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, 'wb').write(b)
    return True


def head_block(s, host, path, cfg, desc):
    """<head> に入れる印。すでにあるものには重ねない"""
    outside = re.sub(r'<!--seo-->.*?<!--/seo-->', '', s, flags=re.S)
    parts = []
    if desc and '<meta name="description"' not in outside:
        parts.append('<meta name="description" content="%s">' % desc.replace('&', '&amp;').replace('"', '&quot;'))
    if 'rel="canonical"' not in outside:
        parts.append('<link rel="canonical" href="%s%s">' % (host, path))
    if path == '/':
        d = {'@context': 'https://schema.org', '@type': 'WebApplication', 'name': cfg['name'], 'alternateName': cfg['alt'], 'url': host + '/',
             'description': cfg['desc'], 'inLanguage': 'ja', 'image': host + cfg['image'], 'applicationCategory': 'SportsApplication', 'operatingSystem': 'Any',
             'browserRequirements': 'JavaScript が使えるブラウザ（スマートフォン・パソコン）', 'isAccessibleForFree': True,
             'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'JPY'}, 'publisher': ORG, 'isPartOf': SITE}
        parts.append('<script type="application/ld+json">%s</script>' % json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
    block = '<!--seo-->' + ''.join(parts) + '<!--/seo-->'
    if '<!--seo-->' in s:
        return re.sub(r'<!--seo-->.*?<!--/seo-->', lambda m: block, s, count=1, flags=re.S)
    assert s.count('</head>') == 1
    return s.replace('</head>', block + '</head>', 1)


def htaccess(s, sub, host):
    if 'AddType text/plain .txt' not in s:
        a = '  AddCharset utf-8 .html .js .mjs .css .json .webmanifest\n'
        assert s.count(a) == 1, sub
        s = s.replace(a, '  AddType text/plain .txt\n  AddType application/xml .xml\n  AddCharset utf-8 .html .js .mjs .css .json .webmanifest .txt .xml\n')
    if sub == 'tenya-simulator' and 'rel=\\"canonical\\"' not in s:
        s = s.rstrip('\n') + ('\n\n# 正式なURLの印（canonical）。HTML は React が描き直すので、ヘッダーで伝える（2026-11-26）\n'
                              '<IfModule mod_headers.c>\n  <Files "index.html">\n    Header set Link "<%s/>; rel=\\"canonical\\""\n  </Files>\n</IfModule>\n' % host)
    return s


def manifest(sub, changed, added):
    mp = os.path.join(HERE, sub, 'mirror-manifest.json')
    m = json.load(open(mp, encoding='utf-8'))
    recs = {r['file']: r for r in m['files']}
    pub = os.path.join(HERE, sub, 'public')
    for f in changed:
        b = open(os.path.join(pub, f), 'rb').read()
        r = recs[f]
        r['sha256'], r['bytes'] = sha(b), len(b)
        if NOTE not in r['modifications']:
            r['modifications'].append(NOTE)
    for f, ct in added:
        b = open(os.path.join(pub, f), 'rb').read()
        r = recs.get(f)
        if not r:
            r = {'path': '/' + f, 'file': f, 'content_type': ct, 'found_by': 'added 2026-11-26 (AI・検索向け)', 'modifications': []}
            m['files'].append(r)
        r['sha256'], r['bytes'] = sha(b), len(b)
    out = json.dumps(m, ensure_ascii=False, indent=1) + '\n'
    return write(mp, out)


def main():
    for sub, cfg in SITES.items():
        host = 'https://%s.cutlassfish.tokyo' % sub
        pub = os.path.join(HERE, sub, 'public')
        done, changed = [], []
        # 1) <head> の印
        if not cfg.get('no_html'):
            for path, f, desc in cfg['pages']:
                fp = os.path.join(pub, f)
                s = open(fp, encoding='utf-8').read()
                s2 = head_block(s, host, path, cfg, desc or cfg['desc'])
                if write(fp, s2):
                    done.append(f)
                changed.append(f)
        # 2) robots.txt・sitemap.xml・llms.txt
        files = {
            'robots.txt': 'User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % host,
            'sitemap.xml': '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                           + ''.join('<url><loc>%s%s</loc></url>\n' % (host, p) for p, f, d in cfg['pages']) + '</urlset>\n',
            'llms.txt': '# %s（%s）\n\n> %s\n\n' % (cfg['name'], cfg['alt'], cfg['desc'])
                        + ''.join('- [%s](%s%s)\n' % (cfg['name'] if p == '/' else cfg['name'] + 'の使い方', host, p) for p, f, d in cfg['pages'])
                        + '- [紹介記事](%s)\n- [運営サイト：東京湾の魚・釣り（3rd-Penguin Fishing Lab.）](https://cutlassfish.tokyo/)（案内：https://cutlassfish.tokyo/llms.txt）\n' % cfg['article'],
        }
        for f, text in files.items():
            if write(os.path.join(pub, f), text):
                done.append(f)
        # 3) .htaccess
        hp = os.path.join(pub, '.htaccess')
        if write(hp, htaccess(open(hp, encoding='utf-8').read(), sub, host)):
            done.append('.htaccess')
        if sub == 'tenya-simulator':
            if write(os.path.join(pub, 'versions', '.htaccess'),
                     '# 古い版のページは検索に出さない（いまの版は / ）。2026-11-26\n<IfModule mod_headers.c>\n  Header set X-Robots-Tag "noindex"\n</IfModule>\n'):
                done.append('versions/.htaccess')
        # 4) 照合用の一覧
        if manifest(sub, changed, [('robots.txt', 'text/plain; charset=utf-8'), ('sitemap.xml', 'application/xml; charset=utf-8'), ('llms.txt', 'text/plain; charset=utf-8')]):
            done.append('mirror-manifest.json')
        print(sub + ':', ', '.join(done) if done else '変更なし')


if __name__ == '__main__':
    main()
