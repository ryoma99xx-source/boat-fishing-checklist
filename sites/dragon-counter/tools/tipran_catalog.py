"""Merges the per-maker tip-run egi research files into tools/tipran/catalog.json (text only).

    python3 tools/tipran_catalog.py <folder with <maker>.json> [--date 2026-11-12]

Input: {"maker","egis":[{series,url,sizes:[{size,weights}],colors,note,discontinued}]}
Only sizes 2.5号 and up. Items with "discontinued": true or with no colours are left out.
Colour names: NFKC (half-width kana → full width), leading part numbers (e.g. "A01 ") removed for display."""
import glob, json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tipran', 'catalog.json')
ORDER = ['ダイワ', 'シマノ', 'ヤマシタ', 'デュエル', 'バレーヒル', 'クレイジーオーシャン', 'フィッシュリーグ', 'ジャッカル', 'メジャークラフト', 'エバーグリーン', 'ジークラック', 'キーストン', 'マルシン漁具', 'ハリミツ']


def norm(x):
    x = unicodedata.normalize('NFKC', str(x))
    x = re.sub(r'\s+', ' ', x).strip()
    # 品番を外す：「001 金アジ」「01.BLBP ブルー夜光…」「B1 レッド」「#12 …」
    return re.sub(r'^(?:\d{1,3}\.[A-Z]{1,6}|[A-Z]{0,3}-?\d{2,5}|[A-Z]{1,3}\d{1,2}|#\d{1,4})\s+', '', x)


def size(z):
    z = unicodedata.normalize('NFKC', str(z)).replace('号', '').strip()
    try:
        v = float(z)
    except ValueError:
        return None
    t = '%g' % v  # 2.75号・3.25号もそのまま（3 → 3.0）
    return v, (t if '.' in t else t + '.0')


def main():
    src = sys.argv[1]
    date = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else ''
    rows = []
    for f in sorted(glob.glob(os.path.join(src, '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        m = re.sub(r'\(.*?\)$', '', norm(d.get('maker', ''))).strip()  # 「キーストン(Keystone)」→「キーストン」
        for e in d.get('egis', []):
            if e.get('discontinued') or e.get('exclude'):  # exclude: ティップラン用ではないと判断したもの
                continue
            c = []
            for x in e.get('colors') or []:
                x = norm(x)
                if x and x not in c:
                    c.append(x)
            o = []
            for sz in e.get('sizes') or []:
                zz = size(sz.get('size', ''))
                if not zz or zz[0] < 2.5:
                    continue
                ws = [w for w in (sz.get('weights') or []) if isinstance(w, (int, float)) or str(w).replace('.', '', 1).isdigit()]
                for w in (ws or [None]):
                    item = {'z': zz[1], 'g': (int(round(float(w))) if w is not None else 0)}
                    if item not in o:
                        o.append(item)
            if not c or not o:
                continue
            o.sort(key=lambda t: (float(t['z']), t['g']))
            rows.append({'m': m, 's': norm(e['series']), 'o': o, 'w': list(range(len(o))), 'c': c, 'u': e.get('url', ''), 'note': norm(e.get('note') or '')[:80]})
    rows.sort(key=lambda r: (ORDER.index(r['m']) if r['m'] in ORDER else 99, r['m']))
    json.dump({'v': date, 'heads': rows, 'ties': [], 'skirts': []}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(rows), 'products', sorted({r['m'] for r in rows}))


if __name__ == '__main__':
    main()
