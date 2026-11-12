"""Builds ティップランカウンター (public/tipran/index.html) from タイラバカウンター (public/tairaba/index.html).

タイラバカウンター is itself built from ドラゴンカウンター (tools/tairaba_build.py), so the chain is
    public/index.html  →  tairaba_build.py  →  public/tairaba/index.html  →  tipran_build.py  →  public/tipran/index.html
Run tairaba_build.py first. What changes here: name and addresses, the target (アオリイカ, 杯, size in g),
the parts (エギ and an optional 増し錘 instead of ヘッド・ネクタイ・針・スカート), and the キロアップ mark
(ドラゴンカウンターの「ドラゴン」の仕組みを、1kg以上の印として使う).

    python3 tools/tipran_build.py      (run from sites/dragon-counter)
"""
import base64
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(HERE, '..', 'public')
OUT = os.path.join(PUB, 'tipran')
URL = 'https://dragon-counter.cutlassfish.tokyo/tipran/'

s = open(os.path.join(PUB, 'tairaba', 'index.html'), encoding='utf-8').read()


def R(old, new, n=1):
    global s
    c = s.count(old)
    if c != n:
        sys.exit(f'patch failed ({c} matches, expected {n}): {old[:90]!r}')
    s = s.replace(old, new)


def RX(pat, new, n=1, flags=0):
    global s
    s2, c = re.subn(pat, new, s, flags=flags)
    if c != n:
        sys.exit(f'regex patch failed ({c} matches, expected {n}): {pat[:90]!r}')
    s = s2


def ALL(old, new):
    """Replace every occurrence (at least one)."""
    global s
    if old not in s:
        sys.exit(f'global replace found nothing: {old!r}')
    s = s.replace(old, new)


# ───────── parts: エギ (rigs) and 増し錘 (skirts slot, optional). ネクタイ・針 are not used.
RX(r"\{id:'madai',name:'マダイ',unit:'枚',sizeUnit:'cm',rigLabel:'ヘッド',baitLabel:'ネクタイ',hookLabel:'針',skirtLabel:'スカート',tairaba:true,variants:\[\{id:'madai',name:'マダイ'\}\],rigs:\[\],baits:\[\],hooks:\[\],skirts:\[\]\}",
   "{id:'tiprun',name:'アオリイカ',unit:'杯',sizeUnit:'g',rigLabel:'エギ',baitLabel:'',skirtLabel:'増し錘',tairaba:true,variants:[{id:'tiprun',name:'アオリイカ'}],rigs:[],baits:[],hooks:[],skirts:[]}")
R("const SOLO='madai';", "const SOLO='tiprun';")
R("sp:'madai',g:{}", "sp:'tiprun',g:{}")
R("const GEDO_DEF=['ホウボウ','カサゴ','イトヨリ','アマダイ','ハマチ','ワラサ','サバ','アジ'];", "const GEDO_DEF=['コウイカ','ヤリイカ','スルメイカ','マダコ','カサゴ','エソ','フグ'];")
RX(r"const TB_DL=\{.*?\};",
   "const TB_DL={mk:['ダイワ','ヤマシタ','ヤマリア','シマノ','デュエル','ハリミツ','林釣漁具','自作'],sz:['3.0','3.5','4.0'],hc:['赤テープ','金テープ','マーブル','ケイムラ','夜光','虹テープ','紫','オレンジ','ピンク','ブラウン'],tc:[],hs:[],ts:[],ks:[]};", flags=re.S)
RX(r"function tbName\(k,x\)\{.*?\n  return x\.type==='diy'[^\n]*\n",
   "function tbName(k,x){if(k==='skirts')return x.g?x.g+'g':'';return [x.maker,x.shape?x.shape+'号':'',x.g?x.g+'g':'',x.color].filter(Boolean).join(' ')}\n", flags=re.S)
RX(r"function tbPartsHTML\(\)\{.*?\n(?=/\* ---------- species & gear settings)",
   r"""function tbPartsHTML(){
  return `<div class="card" id="tbHeads"><h2>エギ</h2><p class="muted">メーカー・号数・重さ・色を入れて登録します。記録では「ダイワ 3.5号 40g 赤テープ」のように出ます。</p>${tbList('rigs')}
   <div class="tb-form"><label class="field"><span>メーカー</span><input type="text" id="tbHm" list="tbHmL" placeholder="例：ダイワ">${tbDl('tbHmL','mk')}</label>
    <label class="field"><span>号数</span><input type="text" id="tbHs" list="tbHsL" inputmode="decimal" placeholder="例：3.5">${tbDl('tbHsL','sz')}</label>
    <label class="field"><span>重さ（g）</span><input type="number" id="tbHg" inputmode="numeric" min="1" max="300" placeholder="例：40"></label>
    <label class="field"><span>色</span><input type="text" id="tbHc" list="tbHcL" placeholder="例：赤テープ">${tbDl('tbHcL','hc')}</label></div>
   <button class="btn sm primary" data-act="tbAdd" data-kind="rigs">エギを登録</button></div>
  <div class="card" id="tbSkirts"><h2>増し錘<small class="muted">（任意）</small></h2><p class="muted">使う重さを登録しておくと、記録のときに選べます。付けないときは「なし」。</p>${tbList('skirts')}
   <div class="tb-form"><label class="field"><span>重さ（g）</span><input type="number" id="tbKg" inputmode="numeric" min="1" max="300" placeholder="例：10"></label></div>
   <button class="btn sm primary" data-act="tbAdd" data-kind="skirts">増し錘を登録</button></div>`}
""", flags=re.S)
R("    if(k==='rigs'){x={g:tbVal('tbHg'),shape:tbVal('tbHs'),color:tbVal('tbHc'),maker:tbVal('tbHm')};if(!x.g&&!x.color)return toast('重さか色を入れてください')}",
  "    if(k==='rigs'){x={g:tbVal('tbHg'),shape:tbVal('tbHs').replace(/号$/,''),color:tbVal('tbHc'),maker:tbVal('tbHm')};if(!x.shape&&!x.color)return toast('号数か色を入れてください')}")
R("    else if(k==='skirts'){x={shape:tbVal('tbKs'),color:tbVal('tbKc')};if(!x.shape&&!x.color)return toast('素材か色を入れてください')}",
  "    else if(k==='skirts'){x={g:tbVal('tbKg')};if(!x.g)return toast('重さを入れてください')}")
R("`<button class=\"tb-btn\" data-act=\"rigPick\"><span>針</span><b>${esc(listName(sp,'hooks',g.hook)||'未登録')}</b></button>`",
  "`<button class=\"tb-btn\" data-act=\"rigPick\"><span>増し錘</span><b>${esc(g.skirt?listName(sp,'skirts',g.skirt):'なし')}</b></button>`")
R("<h2>タイラバを替える</h2>", "<h2>エギ・増し錘を替える</h2>")
R("替えた部品だけ押してください。押した時刻から記録に反映されます。", "替えたものだけ押してください。押した時刻から記録に反映されます。")

# ───────── キロアップ（1kg以上）：ドラゴンの仕組みを使う。タチウオ用の条件を、この釣り物に向ける
R("${sp==='tachiuo'?", "${sp===SOLO?", 2)
R("kind==='catch'&&sp==='tachiuo'&&dragonNext", "kind==='catch'&&sp===SOLO&&dragonNext")
R("f.sp==='tachiuo'", "f.sp===SOLO", 2)
RX(r"nDragon\((t|tr),'tachiuo'\)", r"nDragon(\1,SOLO)", 7)
R("${kpi(N(best),'枚','最高'", "${kpi(drag,'杯','キロアップ',tot?`全体の${Math.round(drag/tot*100)}%`:'')}${kpi(N(best),'杯','最高'")
R('.mapreg{display:flex;', '.ic-dragon{display:none!important}.mapreg{display:flex;')
R('min="0" max="200" step="0.5"', 'min="0" max="6000" step="10"')
R("placeholder=\"${s.sizeUnit==='cm'?'例：95':'未記入'}\"", "placeholder=\"${s.sizeUnit==='cm'?'例：95':'例：800'}\"")

# ───────── words: name, addresses, keys, target
RX(r'<meta name="description" content="[^"]*">',
   '<meta name="description" content="ティップランのアオリイカの釣果を時間の経過と共に、エギ・増し錘・潮・流れと一緒に記録する無料ツール。全国どこの釣り場でも、潮回りと満潮・干潮、流れの向きと速さが自動で入ります。キロアップ（1kg以上）も記録できます。記録は端末に保存され、釣果データは匿名で集計に使います。">')
RX(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="ティップランのアオリイカの釣果を、エギ・増し錘・潮・流れと一緒に時系列で記録する無料ツール">')
ALL('タイラバカウンター', 'ティップランカウンター')
ALL('TAIRABA COUNTER', 'TIPRUN COUNTER')
ALL('dragon-counter.cutlassfish.tokyo/tairaba', 'dragon-counter.cutlassfish.tokyo/tipran')
ALL('/tairaba/', '/tipran/')
R("const LS='tairaba-log.v1';", "const LS='tipran-log.v1';")
ALL('tairaba-counter', 'tipran-counter')
ALL('tairaba-${tr.date}', 'tipran-${tr.date}')
ALL('スカート', '増し錘')
ALL('よく釣れたヘッド', 'よく釣れたエギ')
ALL('タイラバ', 'エギ')
ALL('マダイ', 'アオリイカ')
ALL("'枚'", "'杯'")
ALL('枚</b>', '杯</b>')
ALL('枚数', '杯数')
ALL('ドラゴン', 'キロアップ')
ALL('エギ（ヘッド・ネクタイ・針）', 'エギと増し錘・キロアップ')
ALL('120cm以上', '1kg以上')
ALL('サイズ（全長・任意）', 'サイズ（重さ・任意）')
RX(r"  \{k:'ようこそ',t:'釣果を時間の経過と共に記録',d:'[^']*'\},",
   "  {k:'ようこそ',t:'釣果を時間の経過と共に記録',d:'ティップランカウンターは、ティップランのアオリイカの釣果を時間の経過と共に、使ったエギ・増し錘・潮・流れと一緒に記録するアプリです。全国どこの釣り場でも使えます。釣果データは匿名で集めて傾向の分析に使います。使うことでこれに同意したものとします。'},")
RX(r"  \{k:'準備',t:'[^']*',d:'[^']*'\},",
   "  {k:'準備',t:'エギと増し錘を登録',d:'画面下の右端にある「登録」タブで、持っているエギ（メーカー・号数・重さ・色）と、使う増し錘の重さを登録します。竿・リール・糸も登録できます。'},")
RX(r"  \{k:'釣れたら',t:'「釣れた」を1タップ',d:'[^']*'\},",
   "  {k:'釣れたら',t:'「釣れた」を1タップ',d:'「釣れた＋1」で、今使っているエギと増し錘と一緒に1杯記録します。1kg以上なら先に「キロアップ」にチェック。エギや増し錘を替えたら「エギ」のボタンから選び直します（押しても記録はされません）。アタリ・バラシも同じように記録されます。押し間違えたら下の「直前の釣果を取り消し」。アオリイカ以外が掛かったら小さな「外道」ボタンから（杯数には入りません）。サイズ（g）はあとから記録の一覧で入れられます。'},")
R("tx(168,64,'80g オレンジ'", "tx(168,64,'3.5号 赤テープ'")
R("tx(196,116,'針'", "tx(196,116,'キロアップ'")
R("tx(196,132,'自作 2本針'", "tx(196,132,'1kg以上'")

# ───────── 座席：基本は片舷流し（全員が片側に並ぶ）。両舷・バーティカルも選べる。trip.lay = 'one' | 'both'
R("function fixPeople(f){f.people=clampP(f.people);f.seats=perSide(f.people);",
  "function fixPeople(f){f.people=clampP(f.people);f.lay=f.lay||'one';f.seats=f.lay==='one'?f.people:perSide(f.people);if(f.side!=='L')f.side='R';")
R("end:(b&&b.end)||'13:30',memo:''}}", "end:(b&&b.end)||'13:30',memo:'',lay:S.prefs.lay||'one'}}")
R("function formFromTrip(tr){return {mode:'edit',id:tr.id,date:tr.date,boat:tr.boat,people:tr.people||tr.seats*2,seats:tr.seats,side:tr.side,seat:tr.seat,",
  "function formFromTrip(tr){return {mode:'edit',id:tr.id,date:tr.date,boat:tr.boat,lay:tr.lay||'one',people:tr.people||(tr.lay==='both'?tr.seats*2:tr.seats),seats:tr.seats,side:tr.side,seat:tr.seat,")
R("people:f.people,seats:f.seats,side:f.side,seat:f.seat,station:f.station,", "people:f.people,seats:f.seats,side:f.side,seat:f.seat,lay:f.lay||'one',station:f.station,")
R("Object.assign(tr,{date:f.date,boat:f.boat.trim(),people:f.people,seats:f.seats,side:f.side,seat:f.seat,memo:f.memo});",
  "Object.assign(tr,{date:f.date,boat:f.boat.trim(),people:f.people,seats:f.seats,side:f.side,seat:f.seat,lay:f.lay||'one',memo:f.memo});")
R("Object.assign(S.prefs,{boat:tr.boat,seats:tr.seats,side:tr.side,seat:tr.seat,", "Object.assign(S.prefs,{boat:tr.boat,seats:tr.seats,side:tr.side,seat:tr.seat,lay:tr.lay,")
R("<b>${esc(seatLabel({side:f.side,seat:f.seat,seats:f.seats}))}</b><span class=\"muted\">${f.side==='L'?'左':'右'}舷・前から${f.seat}番目／${f.people}人（片舷${f.seats}席）</span>",
  "<b>${esc(seatLabel({side:f.side,seat:f.seat,seats:f.seats,lay:f.lay}))}</b><span class=\"muted\">${f.lay==='one'?`片舷流し（${f.side==='L'?'左':'右'}舷）・前から${f.seat}番目／${f.people}人`:`${f.side==='L'?'左':'右'}舷・前から${f.seat}番目／${f.people}人（片舷${f.seats}席）`}</span>")
R("for(const side of ['L','R'])for(let i=1;i<=n;i++){const y=side==='L'?34:96,", "for(const side of (f.lay==='one'?[f.side||'R']:['L','R']))for(let i=1;i<=n;i++){const y=side==='L'?34:96,")
R("for(const side of ['L','R'])for(let i=1;i<=n;i++){const x=side==='L'?xl:xr,", "for(const side of (tr.lay==='one'?[tr.side||'R']:['L','R']))for(let i=1;i<=n;i++){const x=side==='L'?xl:xr,")
R('<text x="180" y="20" text-anchor="middle" font-size="12" style="fill:var(--muted)">左舷</text><text x="180" y="124" text-anchor="middle" font-size="12" style="fill:var(--muted)">右舷</text>',
  '${f.lay===\'one\'?`<text x="180" y="${f.side===\'L\'?20:124}" text-anchor="middle" font-size="12" style="fill:var(--muted)">${f.side===\'L\'?\'左\':\'右\'}舷（片舷流し）</text>`:\'<text x="180" y="20" text-anchor="middle" font-size="12" style="fill:var(--muted)">左舷</text><text x="180" y="124" text-anchor="middle" font-size="12" style="fill:var(--muted)">右舷</text>\'}')
R('   <div class="seatwrap"><div id="seatPick">${seatPickerSVG(f)}</div>',
  '   ${layHTML(f)}<div class="seatwrap"><div id="seatPick">${seatPickerSVG(f)}</div>')
R("function seatPickerSVG(f){", "function layHTML(f){const l=f.lay||'one';return `<div class=\"seg\" id=\"laySeg\" style=\"margin:4px 0 8px\"><button class=\"${l==='one'?'on':''}\" data-act=\"pickLay\" data-d=\"one\">片舷流し<small>（基本）</small></button><button class=\"${l==='both'?'on':''}\" data-act=\"pickLay\" data-d=\"both\">両舷<small>（バーティカル）</small></button></div>${l==='one'?`<div class=\"chips\" id=\"sideSeg\" style=\"margin:0 0 8px\"><span class=\"muted\" style=\"align-self:center\">釣り座の舷</span>${[['R','右舷'],['L','左舷']].map(([k,t])=>`<button class=\"chip ${(f.side||'R')===k?'on':''}\" data-act=\"pickSide\" data-d=\"${k}\" aria-pressed=\"${(f.side||'R')===k}\">${t}</button>`).join('')}</div>`:''}`}\nfunction seatPickerSVG(f){")
R("  pickSeat:b=>{", "  pickLay:b=>{const f=curForm;if(!f)return;f.lay=b.dataset.d;f.seat=null;fixPeople(f);refreshSeat();const g=$('#laySeg'),h=$('#sideSeg');if(h)h.remove();if(g)g.outerHTML=layHTML(f)},\n  pickSide:b=>{const f=curForm;if(!f)return;f.side=b.dataset.d;f.seat=null;refreshSeat();const g=$('#laySeg'),h=$('#sideSeg');if(h)h.remove();if(g)g.outerHTML=layHTML(f)},\n  pickSeat:b=>{")
R("const z={};real.forEach(t=>{const k=t.side+seatZone(t);", "const z={};real.forEach(t=>{const k=(t.lay==='one'?'O':t.side)+seatZone(t);")
R("const nm=(side==='L'?'左':'右')+zone;", "const nm=(side==='L'?'左':side==='O'?'':'右')+zone;")
R("return chips+`<div class=\"zones\">${['ミヨシ寄り','胴の間','トモ寄り'].map(zn=>cell('L',zn)+cell('R',zn)).join('')}</div><div class=\"zones-foot\">トモ</div>`}",
  "const one=Object.keys(z).some(k=>k[0]==='O'),both=Object.keys(z).some(k=>k[0]!=='O');return chips+(one?`<p class=\"muted\" style=\"margin:6px 0 4px\">片舷流し</p><div class=\"zones\" style=\"grid-template-columns:1fr\">${['ミヨシ寄り','胴の間','トモ寄り'].map(zn=>cell('O',zn)).join('')}</div>`:'')+(both?`${one?'<p class=\"muted\" style=\"margin:10px 0 4px\">両舷・バーティカル</p>':''}<div class=\"zones\">${['ミヨシ寄り','胴の間','トモ寄り'].map(zn=>cell('L',zn)+cell('R',zn)).join('')}</div><div class=\"zones-foot\">トモ</div>`:'')}")

R("o.push(TX(xl-40,240,'左舷',{size:14,fill:P.muted,anchor:'middle'}));o.push(TX(xr+40,240,'右舷',{size:14,fill:P.muted,anchor:'middle'}));",
  "if(tr.lay!=='one'){o.push(TX(xl-40,240,'左舷',{size:14,fill:P.muted,anchor:'middle'}));o.push(TX(xr+40,240,'右舷',{size:14,fill:P.muted,anchor:'middle'}))}else o.push(TX(tr.side==='L'?xl-40:xr+40,240,tr.side==='L'?'左舷':'右舷',{size:14,fill:P.muted,anchor:'middle'}));")

# ───────── エギのカタログ（文字だけ）：tools/tipran/catalog.json（tipran_catalog.py が作る）
# 行の形 {m:メーカー, s:製品, o:[{z:'3.0',g:30},…], w:[0,1,…], c:[色…], u:URL, note}。w は o の番号（ヘッド用の重さ選びをそのまま使うため）
import json
_cp = os.path.join(HERE, 'tipran', 'catalog.json')
EGI = json.load(open(_cp, encoding='utf-8')) if os.path.exists(_cp) else {'v': '', 'heads': [], 'ties': [], 'skirts': []}
RX(r"const TB_CAT=\{.*?\};\n", lambda m: 'const TB_CAT=' + json.dumps(EGI, ensure_ascii=False, separators=(',', ':')) + ';\n', flags=re.S)
R("TBC_JP={rigs:'ヘッド',", "TBC_JP={rigs:'エギ',")
R("${tbc.kind==='rigs'&&cur.w.length?`<div class=\"field\"><span>重さ（持っているものを全部）</span><div class=\"chips wrap\">${cur.w.map(g=>`<button class=\"chip ${tbc.w.has(g)?'on':''}\" data-act=\"tbcW\" data-d=\"${g}\">${g}g</button>`).join('')}</div></div>`:''}",
  "${tbc.kind==='rigs'&&cur.w.length?`<div class=\"field\"><span>号数・重さ（持っているものを全部）</span><div class=\"chips wrap\">${cur.w.map(g=>{const o=cur.o[g]||{};return `<button class=\"chip ${tbc.w.has(g)?'on':''}\" data-act=\"tbcW\" data-d=\"${g}\">${esc(o.z)}号${o.g?' '+o.g+'g':''}</button>`}).join('')}</div></div>`:''}")
R("for(const g of ws)for(const c of r.c.filter(x=>tbc.c.has(x))){const x={maker:r.m,series:r.s,g:g?String(g):'',color:c,shape:r.sh||'',cat:true,id:uid()};",
  "for(const g of ws)for(const c of r.c.filter(x=>tbc.c.has(x))){const o=(r.o||[])[g]||{};const x={maker:r.m,series:r.s,g:o.g?String(o.g):'',color:c,shape:o.z||'',cat:true,id:uid()};")
R("function tbName(k,x){if(k==='skirts')return x.g?x.g+'g':'';return [x.maker,", "function tbName(k,x){if(k==='skirts')return x.g?x.g+'g':'';return [x.series||x.maker,")
R("<p class=\"muted\">メーカー・号数・重さ・色を入れて登録します。記録では「ダイワ 3.5号 40g 赤テープ」のように出ます。</p>${tbList('rigs')}",
  "<p class=\"muted\">メーカーのカタログから選ぶか、メーカー・号数・重さ・色を入れて登録します。</p>${tbList('rigs')}${TB_CAT.heads.length?`<button class=\"btn sm\" data-act=\"tbcOpen\" data-kind=\"rigs\" style=\"margin:8px 0\">📖 カタログから選ぶ（${[...new Set(TB_CAT.heads.map(r=>r.m))].length}社・${TB_CAT.heads.length}製品）</button><p class=\"muted\" style=\"margin:0\">カタログにないものは、下に入れて登録</p>`:''}")

icon = base64.b64encode(open(os.path.join(OUT, 'icon-192.png'), 'rb').read()).decode()
RX(r'(<a class="brand" href="https://cutlassfish.tokyo/"><img class="b-ic" src=")data:image/png;base64,[A-Za-z0-9+/=]+(")', r'\g<1>data:image/png;base64,' + icon + r'\g<2>')

if 'マダイ' in s:
    sys.exit('left over: マダイ')
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(s)
print('ok', len(s))
