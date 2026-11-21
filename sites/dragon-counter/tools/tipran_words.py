"""ティップランカウンターに残っていたタチウオの言葉を直す（オーナー指示 2026-11-21「ほかにおかしなところない？」）。

  - 履歴のカレンダー：「この月：釣行 n回・タチウオ n本」、日ごとの「n本」→ アオリイカ・杯
  - ダッシュボード・期間・データの書き出し・キロアップの数の「本」→「杯」
  - 地図の「・前から約…km」→「・一つ前の記録から約…km」（ドラゴンカウンターと同じ言い方）

tipran_build.py の最後に apply() を通す。単体でも、いまの public/tipran/index.html に当てられる:
    python3 tools/tipran_words.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TIPRAN = os.path.join(os.path.dirname(HERE), 'public', 'tipran', 'index.html')
MARK = '/* tipran-words v1 */'

FIX = [
    ("この月：釣行 ${mTrips.length}回・タチウオ ${mTot}本", "この月：釣行 ${mTrips.length}回・アオリイカ ${mTot}杯"),
    ('<span class="cd-d">${d}</span><b>${n}<small>本</small></b>', '<span class="cd-d">${d}</span><b>${n}<small>杯</small></b>'),
    ('<p class="tv-n">この期間に<b>${n}本</b></p>', '<p class="tv-n">この期間に<b>${n}杯</b></p>'),
    ('（釣果 ${catches}本）', '（釣果 ${catches}杯）'),
    ('キロアップ ${nDragon(tr,SOLO)}本</span>', 'キロアップ ${nDragon(tr,SOLO)}杯</span>'),
    ('${r1(v.s/v.n)}本<small>／${v.n}回</small>', '${r1(v.s/v.n)}杯<small>／${v.n}回</small>'),
    ('<span>${SA_JP[k]}</span><b>${m[k].catch}本<small>', '<span>${SA_JP[k]}</span><b>${m[k].catch}杯<small>'),
    ('<span>${KA_JP[k]}</span><b>${m[k].catch}本<small>', '<span>${KA_JP[k]}</span><b>${m[k].catch}杯<small>'),
]


def apply(s):
    if MARK in s:
        return s
    for old, new in FIX:
        n = s.count(old)
        if n < 1:
            raise SystemExit('tipran_words: not found: ' + old[:80])
        s = s.replace(old, new)
    s = s.replace('・前から約${kmTxt', '・一つ前の記録から約${kmTxt')
    s = s.replace('<script>', '<script>' + MARK, 1)
    return s


if __name__ == '__main__':
    s = open(TIPRAN, encoding='utf-8').read()
    s2 = apply(s)
    if s2 == s:
        print('already applied')
    else:
        open(TIPRAN, 'w', encoding='utf-8').write(s2)
        print('ok', len(s2))
