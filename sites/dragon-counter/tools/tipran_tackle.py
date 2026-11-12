"""Builds the rod and reel catalog of ティップランカウンター (tools/tipran/tackle.json) from the research files.

    python3 tools/tipran_tackle.py [--date 2026-11-12]

Input (kept in the repo):
  tools/tipran/research-rods/<maker>.json   {"maker","rods":[{series,model,type:"spinning|bait",length_m,egi_g,status,…}]}
  tools/tipran/research-reels/<maker>.json  {"maker","reels":[{series,model,kind:"spinning|bait",counter,status,…}]}
Scope (decided after the bait tip-run survey, see research notes):
  rods  = rods sold for tip-run / boat eging, spinning and bait; discontinued bait models are kept as 旧モデル
  reels = spinning 2500–3000 class (eging series in full) + small boat 両軸 100–300 class, with or without counter
Output rows (tipran_build.py puts them into the app's TCAT):
  rods  [id, maker, series, model, length_m, type('spinning'|'bait'), egi_g, status]
  reels [id, maker, series, model, kind('spinning'|'bait'), counter(0|1), status]
Ids are a hash of maker|series|model, so an item keeps its id (and stays owned) across updates."""
import glob, hashlib, json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'tipran')
MAKER = {'CRONO': 'クロノ', 'アルファタックル': 'アルファタックル', 'プロマリン': 'プロマリン', 'タカミヤ': 'タカミヤ', '宇崎日新': '宇崎日新',
         'DAIWA': 'ダイワ', 'SHIMANO': 'シマノ', 'Abu Garcia': 'アブガルシア', 'tailwalk': 'テイルウォーク', 'Tailwalk': 'テイルウォーク'}
ORDER = ['ダイワ', 'シマノ', 'がまかつ', 'メジャークラフト', 'アブガルシア', 'オリムピック', 'テイルウォーク', 'バレーヒル', 'ジャッカル', 'クレイジーオーシャン', 'エバーグリーン',
         'ヤマガブランクス', '天龍']
NOTE = {('エバーグリーン', 'NIMC-70MST ディープエモーション70'): 'ディープエギング用'}   # ティップラン専用ではないが、沖のベイトの釣りで使う竿


def nk(x):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(x or ''))).strip()


def maker(x):
    m = re.sub(r'\(.*?\)$', '', nk(x)).strip()
    return MAKER.get(m, m)


def hid(prefix, *parts):
    return prefix + hashlib.sha1('|'.join(parts).encode()).hexdigest()[:8]


def order(m):
    return (ORDER.index(m) if m in ORDER else 99, m)


def main():
    date = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else ''
    rods, reels, seen = [], [], set()
    for f in sorted(glob.glob(os.path.join(D, 'research-rods', '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        m = maker(d.get('maker'))
        for x in d.get('rods') or []:
            s, model = nk(x.get('series')), nk(x.get('model'))
            if not model:
                continue
            i = hid('rd', m, s, model)
            if i in seen:
                continue
            seen.add(i)
            st = NOTE.get((m, model)) or nk(x.get('status'))
            t = 'bait' if x.get('type') == 'bait' else 'spinning'
            ln = x.get('length_m')
            rods.append([i, m, s, model, ln if isinstance(ln, (int, float)) else '', t, nk(x.get('egi_g')), st])
    for f in sorted(glob.glob(os.path.join(D, 'research-reels', '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        m = maker(d.get('maker'))
        for x in d.get('reels') or []:
            s, model = nk(x.get('series')), nk(x.get('model'))
            if not model:
                continue
            i = hid('rl', m, s, model)
            if i in seen:
                continue
            seen.add(i)
            k = 'bait' if x.get('kind') == 'bait' else 'spinning'
            st = nk(x.get('status'))
            reels.append([i, m, s, model, k, 1 if x.get('counter') else 0, st if len(st) <= 12 else ''])
    rods.sort(key=lambda a: (order(a[1]), a[7] == '旧モデル', a[2], a[5] == 'bait', a[3]))
    reels.sort(key=lambda a: (a[4] == 'bait', order(a[1]), a[2], a[3]))
    out = {'v': date, 'rods': rods, 'reels': reels}
    json.dump(out, open(os.path.join(D, 'tackle.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    cnt = lambda L, i, v: sum(1 for a in L if a[i] == v)
    print('rods %d (spinning %d, bait %d, makers %d)' % (len(rods), cnt(rods, 5, 'spinning'), cnt(rods, 5, 'bait'), len({a[1] for a in rods})))
    print('reels %d (spinning %d, bait %d, counter %d, makers %d)' % (len(reels), cnt(reels, 4, 'spinning'), cnt(reels, 4, 'bait'), cnt(reels, 5, 1), len({a[1] for a in reels})))
    print('%d bytes' % os.path.getsize(os.path.join(D, 'tackle.json')))


if __name__ == '__main__':
    main()
