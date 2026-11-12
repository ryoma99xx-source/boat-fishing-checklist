"""カタログにないテンヤの集計（ドラゴンカウンターに匿名で集まった釣行から）。毎月のテンヤ追加の候補探しに使う。

    python3 tools/tenya_report.py <trips folder> <out folder>     # 手元のコピーから
    python3 tools/tenya_report.py --ftp <out folder>               # サーバーの .data/trips を読む（GitHub の集計で使う）
        env: FTP_SERVER, FTP_USERNAME, FTP_PASSWORD（ドラゴンカウンターの FTP アカウント）

Only the tenya part of each trip is read; places, boats, times and everything else are not written anywhere.
Output: <out>/tenya-report.md and <out>/tenya-report.csv
  maker / product / colour / sizes / trips that used it / catches with it / last date
A tenya counts as "not in the catalog" when its id is not one of the catalog ids (tenya-catalog/rank-map.json).
Trips sent before 2026-11-12 carry only the short label (略称＋色); later ones carry maker, product, size and colour."""
import csv, io, json, os, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)


def trips_local(folder):
    for f in sorted(os.listdir(folder)):
        if f.endswith('.json'):
            try:
                yield json.load(open(os.path.join(folder, f), encoding='utf-8'))
            except Exception:
                pass


def trips_ftp():
    import ftplib, ssl
    ftp = ftplib.FTP_TLS(os.environ['FTP_SERVER'], context=ssl.create_default_context(), timeout=60)
    ftp.login(os.environ['FTP_USERNAME'], os.environ['FTP_PASSWORD'])
    ftp.prot_p()
    ftp.cwd('.data/trips')
    names = [n for n in ftp.nlst() if n.endswith('.json')]
    for n in names:
        b = io.BytesIO()
        ftp.retrbinary('RETR ' + n, b.write)
        try:
            yield json.loads(b.getvalue().decode('utf-8'))
        except Exception:
            pass
    ftp.quit()


def key(*a):
    return '|'.join(unicodedata.normalize('NFKC', str(x)).replace(' ', '').replace('　', '').lower() for x in a)


def main():
    if sys.argv[1] == '--ftp':
        src, out = trips_ftp(), sys.argv[2]
    else:
        src, out = trips_local(sys.argv[1]), sys.argv[2]
    known = set(json.load(open(os.path.join(SITE, 'public', 'tenya-catalog', 'rank-map.json'), encoding='utf-8')))
    rows, ntrips = {}, 0
    for d in src:
        if not isinstance(d, dict):
            continue
        ntrips += 1
        cu = {x.get('id'): x for x in (d.get('custom') or []) if isinstance(x, dict)}
        used, catches, label = set(), {}, {}
        for e in d.get('events') or []:
            if not isinstance(e, dict) or (e.get('gsp') or e.get('sp')) != 'tachiuo':
                continue
            r = e.get('rig') or ''
            if not r or r in known or not (r in cu or r.startswith('c')):
                continue
            used.add(r); label.setdefault(r, e.get('rigName') or '')
            if e.get('kind') == 'catch':
                catches[r] = catches.get(r, 0) + 1
        for g in d.get('gear') or []:
            r = isinstance(g, dict) and g.get('sp') == 'tachiuo' and g.get('rig') or ''
            if r and r not in known and (r in cu or r.startswith('c')):
                used.add(r); label.setdefault(r, g.get('rigName') or '')
        for r in used:
            x = cu.get(r)
            if x and (x.get('p') or x.get('c') or x.get('name')):
                k = key(x.get('m', ''), x.get('p', ''), x.get('c', ''), x.get('name', ''))
                show = {'m': x.get('m', ''), 'p': x.get('p', '') or x.get('name', ''), 'c': x.get('c', '')}
                z = str(x.get('z') or '')
            else:
                k, show, z = 'label|' + key(label.get(r, '')), {'m': '', 'p': '（名前だけ）' + label.get(r, ''), 'c': ''}, ''
            row = rows.setdefault(k, {**show, 'z': set(), 'trips': 0, 'catch': 0, 'last': ''})
            if z:
                row['z'].add(z)
            row['trips'] += 1
            row['catch'] += catches.get(r, 0)
            row['last'] = max(row['last'], str(d.get('date') or ''))
    lst = sorted(rows.values(), key=lambda r: (-r['trips'], -r['catch'], r['m'], r['p']))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'tenya-report.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['メーカー', '製品', '色', '号数', '使われた釣行', '釣れた数', '最後に使われた日'])
        for r in lst:
            w.writerow([r['m'], r['p'], r['c'], '・'.join(sorted(r['z'], key=lambda s: float(s) if s.replace('.', '', 1).isdigit() else 0)), r['trips'], r['catch'], r['last']])
    md = ['# カタログにないテンヤ（ドラゴンカウンターの釣行から）', '', f'読んだ釣行：{ntrips}件　カタログにないテンヤ：{len(lst)}種類', '',
          '| メーカー | 製品 | 色 | 号数 | 使われた釣行 | 釣れた数 | 最後 |', '|---|---|---|---|---|---|---|']
    for r in lst:
        md.append('| %s | %s | %s | %s | %d | %d | %s |' % (r['m'], r['p'], r['c'], '・'.join(sorted(r['z'])), r['trips'], r['catch'], r['last']))
    open(os.path.join(out, 'tenya-report.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    print(f'読んだ釣行 {ntrips} 件、カタログにないテンヤ {len(lst)} 種類')


if __name__ == '__main__':
    main()
