"""タイラバカウンターの竿とリールのカタログ（tools/tairaba/tackle.json）。オーナー指示 2026-11-22。

    python3 tools/tairaba_tackle.py [--date 2026-11-22]     カタログを作り直す
    （アプリへは tairaba_build.py が apply() で入れる）

もと（リポジトリに置く）:
  竿　　　　 tools/tairaba/research-rods/<maker>.json   {"maker","rods":[{series,model,type:"bait|spinning",length_m,lure_g,status,…}]}
  電動リール tools/tairaba/research-reels/electric-*.json {"maker","reels":[{series,model,kind:"electric",counter,…}]}
  ベイト・スピニングのリールは、ティップランの調査（tools/tipran/research-reels/）をそのまま使う（小型両軸100〜300番・スピニング2500〜3000番）
行の形:
  rods  [id, メーカー, シリーズ, 品番, 長さm, 'bait'|'spinning', ルアー重さ, 状態]
  reels [id, メーカー, シリーズ, 品番, 'bait'|'electric'|'spinning', カウンター0|1, 状態]
id はメーカー|シリーズ|品番のハッシュ（ティップランと同じ作り方。同じリールは同じ id）。
竿は「ベイト」と「キャスラバ（スピニング）」、リールは「ベイト」「電動」「スピニング」で分けて選ぶ。
電動のリールを使っているときは、詳細モードの巻きの速さが 1〜20 になる（tairaba_sasoi.py）。
"""
import glob, hashlib, json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'tairaba')
TP = os.path.join(HERE, 'tipran')
OUT = os.path.join(D, 'tackle.json')
MAKER = {'DAIWA': 'ダイワ', 'SHIMANO': 'シマノ', 'Abu Garcia': 'アブガルシア', 'tailwalk': 'テイルウォーク', 'Tailwalk': 'テイルウォーク', '宇崎日新': '宇崎日新'}
ORDER = ['ダイワ', 'シマノ', 'ジャッカル', 'メジャークラフト', 'がまかつ', 'アブガルシア', 'テイルウォーク', '天龍', 'オリムピック', 'エバーグリーン', 'ヤマガブランクス',
         '宇崎日新', 'クレイジーオーシャン']


def nk(x):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(x or ''))).strip()


def maker(x):
    m = re.sub(r'\(.*?\)$', '', nk(x)).strip()
    return MAKER.get(m, m)


def hid(prefix, *parts):
    return prefix + hashlib.sha1('|'.join(parts).encode()).hexdigest()[:8]


def order(m):
    return (ORDER.index(m) if m in ORDER else 99, m)


def st(x):
    s = nk(x.get('status'))
    return '旧モデル' if s.startswith('旧モデル') else '限定モデル' if '限定' in s else ''


def build(date=''):
    rods, reels, seen = [], [], set()
    for f in sorted(glob.glob(os.path.join(D, 'research-rods', '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        m = maker(d.get('maker'))
        for x in d.get('rods') or []:
            s, model = nk(x.get('series')), nk(x.get('model'))
            if not model or x.get('discontinued'):
                continue
            i = hid('rd', m, s, model)
            if i in seen:
                continue
            seen.add(i)
            ln = x.get('length_m')
            rods.append([i, m, s, model, round(ln, 2) if isinstance(ln, (int, float)) else '', 'spinning' if x.get('type') == 'spinning' else 'bait', nk(x.get('lure_g')), st(x)])
    src = [(f, 'electric') for f in sorted(glob.glob(os.path.join(D, 'research-reels', 'electric-*.json')))]
    src += [(f, 'bait') for f in sorted(glob.glob(os.path.join(D, 'research-reels', 'bait-*.json')))]   # タイラバだけに足すベイトリール（例：ソルティガ BJ）
    src += [(f, None) for f in sorted(glob.glob(os.path.join(TP, 'research-reels', '*.json')))]
    for f, kind in src:
        d = json.load(open(f, encoding='utf-8'))
        m = maker(d.get('maker'))
        for x in d.get('reels') or []:
            s, model = nk(x.get('series')), nk(x.get('model'))
            if not model or x.get('discontinued'):
                continue
            i = hid('rl', m, s, model)
            if i in seen:
                continue
            seen.add(i)
            k = kind or ('bait' if x.get('kind') == 'bait' else 'spinning')
            reels.append([i, m, s, model, k, 1 if x.get('counter') else 0, ''])
    rods.sort(key=lambda a: (order(a[1]), a[7] == '旧モデル', a[2], a[5] == 'spinning', a[3]))
    kr = {'bait': 0, 'electric': 1, 'spinning': 2}
    reels.sort(key=lambda a: (kr[a[4]], order(a[1]), a[2], a[3]))
    out = {'v': date, 'rods': rods, 'reels': reels}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    cnt = lambda L, i, v: sum(1 for a in L if a[i] == v)
    print('rods %d (bait %d, spinning %d, makers %d)' % (len(rods), cnt(rods, 5, 'bait'), cnt(rods, 5, 'spinning'), len({a[1] for a in rods})))
    print('reels %d (bait %d, electric %d, spinning %d)' % (len(reels), cnt(reels, 4, 'bait'), cnt(reels, 4, 'electric'), cnt(reels, 4, 'spinning')))


def apply(s):
    if not os.path.exists(OUT):
        return s

    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('tairaba_tackle: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    def RX(pat, new, flags=0):
        nonlocal s
        s2, c = re.subn(pat, new, s, flags=flags)
        if c != 1:
            raise SystemExit('tairaba_tackle: regex %d: %s' % (c, pat[:90]))
        s = s2

    TK = json.load(open(OUT, encoding='utf-8'))
    mk = lambda L: list(dict.fromkeys(a[1] for a in L))
    dj = lambda x: json.dumps(x, ensure_ascii=False, separators=(',', ':'))
    v = TK.get('v') or ''
    vj = (v[:4] + '年' + str(int(v[5:7])) + '月') if re.match(r'\d{4}-\d\d', v) else v
    RX(r"const TCAT=\{.*?\}; //", lambda m: 'const TCAT=' + dj({'v': vj, 'rods': TK['rods'], 'reels': TK['reels']}) + '; //', flags=re.S)
    RX(r"const TK_MK=\{[^}]*\};\nconst TK_MAKERS=\{[^}]*\};", lambda m: 'const TK_MK={};\nconst TK_MAKERS=' + dj({'rod': mk(TK['rods']), 'reel': mk(TK['reels'])}) + ';')
    R("(TCAT.rods||[]).forEach(a=>tcBy[a[0]]={id:a[0],k:'rod',m:a[1],s:a[2],model:a[3],len:a[4],tier:a[5],st:a[6]||''});(TCAT.reels||[]).forEach(a=>tcBy[a[0]]={id:a[0],k:'reel',m:a[1],s:a[2],model:a[3],kind:a[4],st:a[5]||''});",
      "(TCAT.rods||[]).forEach(a=>tcBy[a[0]]={id:a[0],k:'rod',m:a[1],s:a[2],model:a[3],len:a[4],kind:a[5],lure:a[6]||'',st:a[7]||''});(TCAT.reels||[]).forEach(a=>tcBy[a[0]]={id:a[0],k:'reel',m:a[1],s:a[2],model:a[3],kind:a[4],counter:!!a[5],st:a[6]||''});")
    # 種類の名前：竿はベイト／キャスラバ、リールはベイト／電動／スピニング
    R("const tkKind=it=>it&&it.kind==='electric'?'電動':'';",
      "const tkKind=it=>!it?'':it.kind==='electric'?'電動':it.kind==='spinning'?(it.k==='rod'||String(it.id).startsWith('ur-')?'キャスラバ':'スピニング'):it.kind==='bait'?'ベイト':'';")
    R("(!tkQ.kind||(tkQ.kind==='electric')===(x.kind==='electric'))", "(!tkQ.kind||x.kind===tkQ.kind)")
    R("${k==='reel'?`<div class=\"seg tk-kind\">${[['','すべて'],['bait','ベイト'],['electric','電動']].map(",
      "${1?`<div class=\"seg tk-kind\">${(k==='rod'?[['','すべて'],['bait','ベイト'],['spinning','キャスラバ']]:[['','すべて'],['bait','ベイト'],['electric','電動'],['spinning','スピニング']]).map(")
    R("${x.len?`<small>${x.len}m</small>`:''}${x.kind==='electric'?'<small>電動</small>':''}",
      "${x.len?`<small>${x.len}m</small>`:''}<small>${tkKind(x)}</small>${x.lure?`<small>${esc(x.lure)}${/g/.test(x.lure)?'':'g'}</small>`:''}")
    R("placeholder=\"${k==='rod'?'例：極鋭、サーベルマスター、175':'例：ソルティガ、フォースマスター、200'}\"", "placeholder=\"${k==='rod'?'例：紅牙、炎月、69':'例：シーボーグ、フォースマスター、200'}\"")
    R("placeholder=\"${k==='rod'?'例：極鋭タチウオテンヤSP EX MH-175':'例：ソルティガ BJ 100SH'}\"", "placeholder=\"${k==='rod'?'例：紅牙 X 69MHB':'例：シーボーグ 200J'}\"")
    # 自分で登録：種類を選ぶ（電動にすると、巻きの速さが 1〜20 になる）
    R('<label class="field"><span>製品名・型番</span><input type="text" id="tkcN"',
      '<label class="field"><span>種類</span><select id="tkcK">${(k===\'rod\'?[[\'bait\',\'ベイト\'],[\'spinning\',\'キャスラバ（スピニング）\']]:[[\'bait\',\'ベイト\'],[\'electric\',\'電動\'],[\'spinning\',\'スピニング\']]).map(([v,l])=>`<option value="${v}">${l}</option>`).join(\'\')}</select></label>\n'
      '   <label class="field"><span>製品名・型番</span><input type="text" id="tkcN"')
    R("...(k==='reel'?{kind:'bait'}:{})", "kind:($('#tkcK')||{}).value||'bait'")
    # タイラバの標準の糸：PE0.8号・200m（タチウオ用は1.5号）
    c = s.count("pe:'1.5'")
    if c < 1:
        raise SystemExit("tairaba_tackle: pe:'1.5' not found")
    s = s.replace("pe:'1.5'", "pe:'0.8'")
    # メーカーの並びは1行で横に送る。カタログの下に「保存して戻る」
    R(".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}",
      ".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}\n"
      ".gearpick .chips.wrap .chip{max-width:100%;white-space:normal;text-align:left;line-height:1.35;display:inline-flex;align-items:center;overflow-wrap:anywhere}.gearpick .chips.wrap .chip .eimg{flex:none}\n"   # 長い部品名を折り返す（はみ出さない）
      ".chips.wrap.tk-mk{flex-wrap:nowrap;overflow-x:auto;padding-bottom:6px}.seg.tk-kind button{font-size:14px;padding-left:4px;padding-right:4px;white-space:nowrap}")
    R("押すと所有に追加／もう一度押すと外れます。${TCAT.v?`カタログ：${esc(TCAT.v)}時点。`:''}</p>`,{kind:'tkcat'})}",
      "押すと所有に追加／もう一度押すと外れます。${TCAT.v?`カタログ：${esc(TCAT.v)}時点。`:''}</p>\n   <div class=\"tb-foot\"><button class=\"btn primary\" data-act=\"tkCatDone\">所有タックルを保存して戻る</button></div>`,{kind:'tkcat'})}")
    R("  closeSheet:()=>closeSheet(),", "  closeSheet:()=>closeSheet(),\n  tkCatDone:()=>{const t=TK();closeSheet();cfgTouch();render();toast(`保存しました（ロッド${t.rods.mine.length}・リール${t.reels.mine.length}）`)},")
    return s


if __name__ == '__main__':
    build(sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '')
