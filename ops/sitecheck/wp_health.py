#!/usr/bin/env python3
"""WordPress（cutlassfish.tokyo）の点検結果を読む。プラグイン cutlassfish-health の /wp-json/cfhealth/v1/status。
読むだけで、何も変更しない。認証は cfpack.py・deploy.py と同じ環境変数 WP_USER・WP_APP_PASSWORD（値は表示しない）。
このリポジトリは公開なので、結果をファイルやコミットに残さない（画面に出すだけ）。

    python3 ops/sitecheck/wp_health.py          要点（問題があれば「要確認」）
    python3 ops/sitecheck/wp_health.py --json   全部
"""
import base64, json, os, sys, urllib.error, urllib.request

URL = os.environ.get('WP_URL', 'https://cutlassfish.tokyo').rstrip('/') + '/wp-json/cfhealth/v1/status'
KNOWN_ADMINS_ENV = 'CF_KNOWN_ADMINS'   # 任意：知っている管理者のログイン名（カンマ区切り）。設定が無ければ一覧を出すだけ


def get():
    u, p = os.environ.get('WP_USER'), os.environ.get('WP_APP_PASSWORD')
    if not u or not p:
        sys.exit('環境変数 WP_USER と WP_APP_PASSWORD が未設定です')
    r = urllib.request.Request(URL)
    r.add_header('Authorization', 'Basic ' + base64.b64encode(f'{u}:{p}'.encode()).decode())
    r.add_header('User-Agent', 'cfhealth/1.0')
    r.add_header('Accept', 'application/json')
    try:
        with urllib.request.urlopen(r, timeout=120) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        sys.exit(f'読めませんでした: HTTP {e.code}')


def main():
    d = get()
    if '--json' in sys.argv:
        print(json.dumps(d, ensure_ascii=False, indent=1)); return
    warn = []
    print(f"WordPress {d['wp']}（PHP {d['php']}）")
    if d['core_updates']:
        warn.append('本体の更新あり: ' + ', '.join(d['core_updates']))
    pu = [f"{p['name']} {p['version']}→{p['update']}" for p in d['plugins'] if p.get('update')]
    tu = [f"{t['name']} {t['version']}→{t['update']}" for t in d['themes'] if t.get('update')]
    if pu: warn.append('プラグインの更新: ' + ' / '.join(pu))
    if tu: warn.append('テーマの更新: ' + ' / '.join(tu))
    cf = d['core_files']
    print(f"本体ファイル：{cf['checked']}個を照合")
    if cf['changed'] or cf['missing']:
        warn.append(f"本体ファイルが公式と違う：変更 {cf['changed'][:10]}・無い {cf['missing'][:10]}")
    if d['root_extra_php']:
        warn.append('サイトのいちばん上に、見覚えのない PHP: ' + ', '.join(d['root_extra_php']))
    if d['uploads_php']:
        warn.append('アップロード置き場に PHP（ふつうは無い）: ' + ', '.join(d['uploads_php'][:10]))
    rec = [f for f, _ in d['recent_files']]
    print(f"ここ7日で書き換わったプラグイン・テーマのファイル：{len(rec)}個")
    # 自作プラグインと、ふだん自分で書き換えるファイル（Independent Analytics の設定）は除く
    odd = [f for f in rec if not f.startswith(('/plugins/cutlassfish', '/plugins/dragon-counter', '/plugins/cf-gear-deals', '/plugins/egi-catalog', '/plugins/independent-analytics/iawp-click-config.php'))]
    if odd:
        print('  （自作以外）' + ', '.join(odd[:20]) + (' …' if len(odd) > 20 else ''))
    known = {x.strip() for x in os.environ.get(KNOWN_ADMINS_ENV, '').split(',') if x.strip()}
    admins = d['admins']
    print(f"管理者：{len(admins)}人")
    if known:
        new = [a['login'] for a in admins if a['login'] not in known]
        if new: warn.append('知らない管理者: ' + ', '.join(new))
    if not d.get('auto_update_core_minor'):
        warn.append('本体の小さな更新（セキュリティ修正）の自動更新が切れています')
    print('要確認：' if warn else '問題なし')
    for w in warn:
        print(' - ' + w)
    sys.exit(1 if any(not w.startswith(('プラグインの更新', 'テーマの更新', '本体の更新')) for w in warn) else 0)


if __name__ == '__main__':
    main()
