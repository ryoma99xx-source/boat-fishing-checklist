"""Builds the tackle catalog (TCAT) in public/index.html from researched JSON lists.

  python3 tackle_cat.py tackle/rods.json tackle/reels.json [--write]   (lists kept in tools/tackle/)

rods.json:  {"items":[{maker,series,model,length_m,tier,price_jpy,url,status}]}
reels.json: {"items":[{maker,series,model,kind,gear,price_jpy,url,status}]}
Ids are a hash of maker|series|model, so an item keeps its id (and stays owned) across updates.
Add only; to drop an item, keep it out of the JSON — owned ids that disappear still show by name
because trips keep a snapshot of the names.
"""
import hashlib, json, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, '..', 'public', 'index.html')


def hid(prefix, *parts):
    return prefix + hashlib.sha1('|'.join(parts).encode()).hexdigest()[:8]


def main():
    rods = json.load(open(sys.argv[1], encoding='utf-8'))['items']
    reels = json.load(open(sys.argv[2], encoding='utf-8'))['items']
    out_r, out_q, seen = [], [], set()
    for x in rods:
        i = hid('rd', x['maker'], x['series'], x['model'])
        if i in seen:
            continue
        seen.add(i)
        out_r.append([i, x['maker'], x['series'].strip(), x['model'].strip(), x.get('length_m') or '', x.get('tier') or '', x.get('status') or ''])
    for x in reels:
        i = hid('rl', x['maker'], x['series'], x['model'])
        if i in seen:
            continue
        seen.add(i)
        out_q.append([i, x['maker'], x['series'].strip(), x['model'].strip(), x.get('kind') or 'bait', x.get('status') or ''])
    order = {'DAIWA': 0, 'SHIMANO': 1, 'がまかつ': 2, 'Abu Garcia': 3, 'Tailwalk': 4}
    key = lambda a: (order.get(a[1], 9), a[2], a[3])
    out_r.sort(key=key)
    out_q.sort(key=lambda a: (a[4] != 'electric', order.get(a[1], 9), a[2], a[3]))
    cat = {'v': datetime.date.today().strftime('%Y年%-m月'), 'rods': out_r, 'reels': out_q}
    src = open(INDEX, encoding='utf-8').read()
    new = re.sub(r'const TCAT=\{.*?\}; //', 'const TCAT=' + json.dumps(cat, ensure_ascii=False, separators=(',', ':')) + '; //', src, count=1, flags=re.S)
    assert new != src or 'const TCAT=' in src
    print(f'rods {len(out_r)}  reels {len(out_q)}  ({len(json.dumps(cat, ensure_ascii=False))} bytes)')
    if '--write' in sys.argv:
        open(INDEX, 'w', encoding='utf-8').write(new)
        print('written')


if __name__ == '__main__':
    main()
