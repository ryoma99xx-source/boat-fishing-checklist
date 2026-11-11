"""Merges the per-maker research files into tools/tairaba/catalog.json (text only: maker, product, weights, colours, URL).

    python3 tools/tairaba_catalog.py <folder with <maker>.json files> [--date 2026-11-12]

Each input file: {"maker","heads":[{series,url,material,type,weights,colors,note}],"ties":[{series,url,shape,colors,note}],"skirts":[{series,url,colors}]}
Products marked discontinued (廃番/生産終了/discontinued in note) and products with no colours are left out."""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tairaba', 'catalog.json')
ORDER = ['ダイワ', 'シマノ', 'ジャッカル', 'ハヤブサ', 'メジャークラフト']
GONE = re.compile(r'廃番|生産終了|販売終了|discontinued', re.I)


def clean(xs):
    out = []
    for x in xs or []:
        x = re.sub(r'\s+', ' ', str(x)).strip()
        if x and x not in out:
            out.append(x)
    return out


def main():
    src = sys.argv[1]
    date = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else ''
    cat = {'v': date, 'heads': [], 'ties': [], 'skirts': []}
    for f in sorted(glob.glob(os.path.join(src, '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        m = d.get('maker', '').strip()
        for h in d.get('heads', []):
            if GONE.search(h.get('note', '') or ''): continue
            c = clean(h.get('colors'))
            w = sorted({int(round(float(x))) for x in (h.get('weights') or []) if str(x).replace('.', '', 1).isdigit()})
            if not c: continue
            cat['heads'].append({'m': m, 's': h['series'].strip(), 'mat': 'TG' if re.search(r'TG|タングステン', (h.get('material') or '') + h['series']) else '鉛',
                                 'type': (h.get('type') or '').strip(), 'w': w, 'c': c, 'u': h.get('url', ''), 'note': (h.get('note') or '').strip()[:80]})
        for t in d.get('ties', []):
            if GONE.search(t.get('note', '') or ''): continue
            c = clean(t.get('colors'))
            if not c: continue
            cat['ties'].append({'m': m, 's': t['series'].strip(), 'sh': (t.get('shape') or '').strip(), 'c': c, 'u': t.get('url', ''), 'note': (t.get('note') or '').strip()[:80]})
        for k in d.get('skirts', []):
            c = clean(k.get('colors'))
            if not c: continue
            cat['skirts'].append({'m': m, 's': k['series'].strip(), 'c': c, 'u': k.get('url', ''), 'w': []})
    rank = lambda r: (ORDER.index(r['m']) if r['m'] in ORDER else 99, r['m'])
    for k in ('heads', 'ties', 'skirts'):
        cat[k].sort(key=rank)
    json.dump(cat, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print({k: len(cat[k]) for k in ('heads', 'ties', 'skirts')}, 'makers', sorted({r['m'] for k in ('heads', 'ties') for r in cat[k]}))


if __name__ == '__main__':
    main()
