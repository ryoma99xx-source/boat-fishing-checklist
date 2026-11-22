"""タイラバカウンターのカタログの数（説明用）。カタログを足したら、これを動かして数を出し直す。

    python3 tools/tairaba_stats.py        → tools/tairaba/STATS.md を書き、画面にも出す

数え方
  ネクタイ：製品の数、色の数（製品×色）
  ヘッド：製品の数、重さの数（製品×重さ）、色の数（製品×色）、選べる形（製品×重さ×色）、ちがう重さの種類
  組み合わせ：ヘッド（製品×重さ×色）× ネクタイ（製品×色）。スカート・針は数えない（任意のため）
  写真：tools/tairaba/images.json にある色（アプリに出している分）
"""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
cat = json.load(open(os.path.join(HERE, 'tairaba', 'catalog.json'), encoding='utf-8'))
img = json.load(open(os.path.join(HERE, 'tairaba', 'images.json'), encoding='utf-8')) if os.path.exists(os.path.join(HERE, 'tairaba', 'images.json')) else {}
hold = set()
hp = os.path.join(HERE, 'tairaba', 'images-hold.json')
if os.path.exists(hp):
    hold = set(json.load(open(hp, encoding='utf-8'))['keys'])
has = lambda k, r, c: ('%s|%s|%s|%s' % (k, r['m'], r['s'], c)) in img and ('%s|%s|%s|%s' % (k, r['m'], r['s'], c)) not in hold

H, T, K = cat['heads'], cat['ties'], cat['skirts']
h_prod = len(H)
h_w = sum(max(1, len(r['w'])) for r in H)
h_c = sum(len(r['c']) for r in H)
h_all = sum(max(1, len(r['w'])) * len(r['c']) for r in H)
h_wkinds = sorted({w for r in H for w in r['w']})
t_prod, t_c = len(T), sum(len(r['c']) for r in T)
k_prod, k_c = len(K), sum(len(r['c']) for r in K)
h_img = sum(1 for r in H for c in r['c'] if has('heads', r, c))
t_img = sum(1 for r in T for c in r['c'] if has('ties', r, c))
makers = sorted({r['m'] for r in H + T + K})

by = collections.OrderedDict()
for r in H:
    x = by.setdefault(r['m'], {'hp': 0, 'hw': 0, 'hc': 0, 'ha': 0, 'tp': 0, 'tc': 0})
    x['hp'] += 1; x['hw'] += max(1, len(r['w'])); x['hc'] += len(r['c']); x['ha'] += max(1, len(r['w'])) * len(r['c'])
for r in T:
    x = by.setdefault(r['m'], {'hp': 0, 'hw': 0, 'hc': 0, 'ha': 0, 'tp': 0, 'tc': 0})
    x['tp'] += 1; x['tc'] += len(r['c'])

n = lambda v: '{:,}'.format(v)
out = ['# タイラバカウンターのカタログの数（%s時点）' % (cat.get('v') or ''), '',
       '## まとめ', '',
       '| | 数 |', '|---|---|',
       '| メーカー | %d社 |' % len(makers),
       '| ヘッド | %s製品・重さ違い %s種・色違い %s種 → **選べるヘッド %s通り**（製品×重さ×色） |' % (n(h_prod), n(h_w), n(h_c), n(h_all)),
       '| ヘッドの重さ | %s〜%sg の %d段階 |' % (h_wkinds[0], h_wkinds[-1], len(h_wkinds)),
       '| ネクタイ | %s製品・**%s色** |' % (n(t_prod), n(t_c)),
       '| スカート | %s製品・%s色 |' % (n(k_prod), n(k_c)),
       '| **ヘッド×ネクタイの組み合わせ** | **%s通り**（%s × %s） |' % (n(h_all * t_c), n(h_all), n(t_c)),
       '| 写真がある色 | ヘッド %s/%s色・ネクタイ %s/%s色 |' % (n(h_img), n(h_c), n(t_img), n(t_c)), '',
       '言い方の例：「ヘッドは%s製品・重さと色の違いで%s通り、ネクタイは%s製品・%s色。組み合わせると約%s億通り」' % (n(h_prod), n(h_all), n(t_prod), n(t_c), round(h_all * t_c / 1e8, 1)) if h_all * t_c >= 1e8 else
       '言い方の例：「ヘッドは%s製品・重さと色の違いで%s通り、ネクタイは%s製品・%s色。組み合わせると約%s万通り」' % (n(h_prod), n(h_all), n(t_prod), n(t_c), n(round(h_all * t_c / 1e4))),
       '', '## メーカーごと', '',
       '| メーカー | ヘッド製品 | 重さ違い | 色違い | 選べるヘッド | ネクタイ製品 | ネクタイ色 |', '|---|---|---|---|---|---|---|']
for m, x in by.items():
    out.append('| %s | %d | %s | %s | %s | %d | %s |' % (m, x['hp'], n(x['hw']), n(x['hc']), n(x['ha']), x['tp'], n(x['tc'])))
out += ['', '数え方：重さ違い＝製品ごとの重さの数の合計、色違い＝製品ごとの色の数の合計、選べるヘッド＝製品ごとに（重さの数×色の数）の合計。'
        '組み合わせにスカート・針は入れていない（任意のため）。カタログにない自作・自分で登録した分は入らない。']
open(os.path.join(HERE, 'tairaba', 'STATS.md'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('\n'.join(out))
