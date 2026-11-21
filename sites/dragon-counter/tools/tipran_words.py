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


# ドラゴンカウンターから入ってくる新しい機能（インスタ用の画像）をティップラン用に
FIX_NEW = [
    ("'いちばん釣れたテンヤ'", "'いちばん釣れたエギ'"),
    ("'いちばん釣れたタイラバ'", "'いちばん釣れたエギ'"),
    ("o.push(T(32,y+14,'DRAGON COUNTER',", "o.push(T(32,y+14,'TIPRUN COUNTER',"),
    ("o.push(T(W/2,bot,'dragon-counter.cutlassfish.tokyo',", "o.push(T(W/2,bot,'dragon-counter.cutlassfish.tokyo/tipran',"),
    # いちばん釣れたエギの写真は、ティップランのエギの写真（/tipran/egi/）から
    ("if((t&&TIMG.has(id))||GPH[id]){try{const im=new Image();await new Promise((ok,ng)=>{im.onload=ok;im.onerror=ng;im.src=TIMG.has(id)?`/tenya/${id}.webp${TV?'?v='+encodeURIComponent(TV):''}`:GPH[id]});",
     "const ei=rigIm(sp,id);if(ei||GPH[id]){try{const im=new Image();await new Promise((ok,ng)=>{im.onload=ok;im.onerror=ng;im.src=ei?`/tipran/egi/${ei}.webp`:GPH[id]});"),
]


def apply(s):
    if MARK in s:
        return s
    for old, new in FIX:   # タイラバ側で魚の名前・単位を spOf(SOLO) から出すようにしたので、無ければそのままでよい
        s = s.replace(old, new)
    if 'タチウオ ${mTot}本' in s or '<small>本</small>' in s:
        raise SystemExit('tipran_words: タチウオ・本 left over')
    s = s.replace('・前から約${kmTxt', '・一つ前の記録から約${kmTxt')
    for old, new in FIX_NEW:   # 入っていれば直す
        s = s.replace(old, new)
    s = s.replace('/* いちばん釣れたテンヤ（', '/* いちばん釣れたエギ（')
    if "'いちばん釣れたテンヤ'" in s or "'いちばん釣れたタイラバ'" in s or "T(32,y+14,'DRAGON COUNTER'" in s or "im.src=TIMG.has(id)?`/tenya/" in s:
        raise SystemExit('tipran_words: insta left over')
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
