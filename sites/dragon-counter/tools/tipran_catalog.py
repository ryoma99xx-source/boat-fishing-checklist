"""Merges the per-maker tip-run egi research files into tools/tipran/catalog.json (text only).

    python3 tools/tipran_catalog.py <folder with <maker>.json> [--date 2026-11-12]

Input: {"maker","egis":[{series,url,sizes:[{size,weights}],colors,note,discontinued}]}
Only sizes 2.5号 and up. Items with "discontinued": true or with no colours are left out.
Colour names: NFKC (half-width kana → full width), leading part numbers (e.g. "A01 ") removed for display."""
import glob, json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tipran', 'catalog.json')
# 表示名の統一（フィッシュリーグはマルキユーのブランド、ケストレルはカンジインターナショナルのクロノ）
MAKER = {'フィッシュリーグ': 'マルキユー', 'カンジインターナショナル': 'クロノ'}
ORDER = ['ダイワ', 'シマノ', 'ヤマシタ', 'デュエル', 'バレーヒル', 'クレイジーオーシャン', 'マルキユー', 'ジャッカル', 'メジャークラフト', 'エバーグリーン', 'ジークラック', 'キーストン', 'マルシン漁具', 'ハリミツ', 'スクイッドマニア', 'クロノ', 'XOOX']


def norm(x):
    x = unicodedata.normalize('NFKC', str(x))
    x = re.sub(r'\s+', ' ', x).strip()
    # 品番を外す：「001 金アジ」「01.BLBP ブルー夜光…」「B1 レッド」「#12 …」
    return re.sub(r'^(?:\d{1,3}\.[A-Z]{1,6}|[A-Z]{0,3}-?\d{2,5}|[A-Z]{1,3}\d{1,2}|#[A-Z]{0,4}\d{1,4})\s+', '', x)


def size(z):
    z = unicodedata.normalize('NFKC', str(z)).replace('号', '').strip()
    try:
        v = float(z)
    except ValueError:
        return None
    t = '%g' % v  # 2.75号・3.25号もそのまま（3 → 3.0）
    return v, (t if '.' in t else t + '.0')


# ───────── シンカー（増し錘）：tools/tipran/research-sinkers/<maker>.json
# 入力 {"maker","sinkers":[{series,url,weights:[g],colors,colorsByWeight?,discontinued?,…}]}
# 出力の行 {m, s, w:[g…], c:[色…], cw?:{g:[色の番号…]}（重さで色が違うとき）, u, note}
SINKER_NAME = {'スクイッドジャンキー ピッタリシンカー 1個入': 'スクイッドジャンキー ピッタリシンカー', 'Egibow MASK DU SINKER(マスクドシンカー)': 'Egibow マスクドシンカー',
               'エギスタTR シンカーQC(クイックチェンジ)': 'エギスタTR シンカーQC', 'クイック®TRシンカー': 'クイックTRシンカー'}
SINKER_NOTE = {'アゴリグシンカー3': 'スナップに掛ける小さいオモリ（ティップラン専用ではありません）', 'ヘッドシンカー': 'スナップに掛ける小さいオモリ（ティップラン専用ではありません）',
               'カチッとシンカー': 'ローハイド紫煙の中のオモリを入れ替える専用品', 'シンカー仮面TR': '生産終了（店頭在庫のみ）'}
SINKER_ORDER = ORDER + ['ハヤブサ', '釣研', 'キザクラ', 'ナカジマ', 'ウロコ', '第一精工']


def sinkers(src):
    rows = []
    for f in sorted(glob.glob(os.path.join(src, '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        m = re.sub(r'\(.*?\)$', '', norm(d.get('maker', ''))).strip()
        m = MAKER.get(m, m)
        col = lambda x: re.sub(r'^(?:\d{1,3}\.\s*)?[A-Z]{1,3}\s+(?=[^\x00-\x7f])', '', norm(x))   # 「O オレンジ」「PU パープル」の記号を外す
        for e in d.get('sinkers', []):
            s = norm(e['series']); s = SINKER_NAME.get(s, s)
            w = sorted({float(x) for x in e.get('weights') or []})
            w = [int(x) if x == int(x) else x for x in w]
            c = []
            for x in e.get('colors') or []:
                x = col(x)
                if x and x not in c:
                    c.append(x)
            if not w:
                continue
            r = {'m': m, 's': s, 'w': w, 'c': c, 'u': e.get('url') or '', 'note': SINKER_NOTE.get(s, '')}
            cw = e.get('colorsByWeight')
            if cw and c:
                mp = {}
                for g in w:
                    have = cw.get(str(g)) or cw.get('%g' % g) or []
                    mp['%g' % g] = [c.index(col(x)) for x in have if col(x) in c]
                if any(len(v) != len(c) for v in mp.values()):
                    r['cw'] = mp
            rows.append(r)
    rows.sort(key=lambda r: (SINKER_ORDER.index(r['m']) if r['m'] in SINKER_ORDER else 99, r['m']))
    return rows


def main():
    src = sys.argv[1]
    date = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else ''
    rows = []
    for f in sorted(glob.glob(os.path.join(src, '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        m = re.sub(r'\(.*?\)$', '', norm(d.get('maker', ''))).strip()  # 「キーストン(Keystone)」→「キーストン」
        m = MAKER.get(m, m)
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
            rows.append({'m': m, 's': norm(e['series']), 'o': o, 'w': list(range(len(o))), 'c': c, 'u': e.get('url', ''), 'note': ''})  # 調査メモ（英語まじり）は画面に出さない。research/*.json に残る
    rows.sort(key=lambda r: (ORDER.index(r['m']) if r['m'] in ORDER else 99, r['m']))
    sk = sinkers(os.path.join(HERE, 'tipran', 'research-sinkers'))
    json.dump({'v': date, 'heads': rows, 'ties': [], 'skirts': sk}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(rows), 'products', sorted({r['m'] for r in rows}))
    print(len(sk), 'sinkers', [r['m'] + ' ' + r['s'] for r in sk])


if __name__ == '__main__':
    main()
