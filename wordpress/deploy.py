#!/usr/bin/env python3
"""自作プラグインを cutlassfish.tokyo に入れる（cutlassfish-deploy プラグインの受け口を使う）。

  python3 wordpress/deploy.py list                  入っている自作プラグインと版
  python3 wordpress/deploy.py <folder> [<folder>…]  wordpress/<folder> を zip にして「置き換え」で入れる
                                                     （前から有効なら有効のまま。新規は --activate で有効化）

認証は記事の cfpack.py と同じ環境変数 WP_USER・WP_APP_PASSWORD（値は表示しない・保存しない）。
"""
import base64, io, json, os, sys, urllib.error, urllib.parse, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get('WP_URL', 'https://cutlassfish.tokyo').rstrip('/') + '/wp-json/cfdeploy/v1'


def call(path, data=None):
    u, p = os.environ.get('WP_USER'), os.environ.get('WP_APP_PASSWORD')
    if not u or not p:
        sys.exit('環境変数 WP_USER と WP_APP_PASSWORD が未設定です')
    r = urllib.request.Request(URL + path, data=data, method='POST' if data is not None else 'GET')
    r.add_header('Authorization', 'Basic ' + base64.b64encode(f'{u}:{p}'.encode()).decode())
    r.add_header('User-Agent', 'cfdeploy/1.0')
    r.add_header('Accept', 'application/json')
    if data is not None:
        r.add_header('Content-Type', 'application/zip')
    try:
        with urllib.request.urlopen(r, timeout=300) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        b = e.read().decode('utf-8', 'replace')
        try:
            b = json.loads(b).get('message', b)
        except Exception:
            pass
        return {'error': f'HTTP {e.code}: {b[:300]}'}


def pack(folder):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(os.path.join(HERE, folder)):
            for f in sorted(files):
                if f.startswith('.') or f.endswith('.pyc'):
                    continue
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, HERE))
    return buf.getvalue()


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if not a or a == ['list']:
        print(json.dumps(call('/plugins'), ensure_ascii=False, indent=1))
        return
    q = '&activate=1' if '--activate' in sys.argv else ''
    bad = 0
    for f in a:
        f = f.strip('/')
        if not os.path.isdir(os.path.join(HERE, f)):
            print(f, 'NG: フォルダがありません'); bad = 1; continue
        r = call('/install?slug=' + urllib.parse.quote(f) + q, pack(f))
        if r.get('error'):
            print(f, 'NG', r['error']); bad = 1
        else:
            print(f, 'OK', r.get('from'), '→', r.get('to'), '有効' if r.get('active') else '無効')
    sys.exit(bad)


if __name__ == '__main__':
    main()
