"""Builds ティップランカウンター (public/tipran/index.html) from タイラバカウンター (public/tairaba/index.html).

タイラバカウンター is itself built from ドラゴンカウンター (tools/tairaba_build.py), so the chain is
    public/index.html  →  tairaba_build.py  →  public/tairaba/index.html  →  tipran_build.py  →  public/tipran/index.html
Run tairaba_build.py first. What changes here: name and addresses, the target (アオリイカ, 杯, size in g),
the parts (エギ and an optional シンカー instead of ヘッド・ネクタイ・針・スカート), and the キロアップ mark
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


# ───────── parts: エギ (rigs) and シンカー (skirts slot, optional). ネクタイ・針 are not used.
RX(r"\{id:'madai',name:'マダイ',unit:'枚',sizeUnit:'cm',rigLabel:'ヘッド',baitLabel:'ネクタイ',hookLabel:'針',skirtLabel:'スカート',tairaba:true,variants:\[\{id:'madai',name:'マダイ'\}\],rigs:\[\],baits:\[\],hooks:\[\],skirts:\[\]\}",
   "{id:'tiprun',name:'アオリイカ',unit:'杯',sizeUnit:'g',rigLabel:'エギ',baitLabel:'',skirtLabel:'シンカー',tairaba:true,variants:[{id:'tiprun',name:'アオリイカ'}],rigs:[],baits:[],hooks:[],skirts:[]}")
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
  <div class="card" id="tbSkirts"><h2>シンカー（増し錘）<small class="muted">（任意）</small></h2><p class="muted">使う重さを登録しておくと、記録のときに選べます。付けないときは「なし」。</p>${tbList('skirts')}
   <div class="tb-form"><label class="field"><span>重さ（g）</span><input type="number" id="tbKg" inputmode="numeric" min="1" max="300" placeholder="例：10"></label></div>
   <button class="btn sm primary" data-act="tbAdd" data-kind="skirts">シンカーを登録</button></div>`}
""", flags=re.S)
R("    if(k==='rigs'){x={g:tbVal('tbHg'),shape:tbVal('tbHs'),color:tbVal('tbHc'),maker:tbVal('tbHm')};if(!x.g&&!x.color)return toast('重さか色を入れてください')}",
  "    if(k==='rigs'){x={g:tbVal('tbHg'),shape:tbVal('tbHs').replace(/号$/,''),color:tbVal('tbHc'),maker:tbVal('tbHm')};if(!x.shape&&!x.color)return toast('号数か色を入れてください')}")
R("    else if(k==='skirts'){x={shape:tbVal('tbKs'),color:tbVal('tbKc')};if(!x.shape&&!x.color)return toast('素材か色を入れてください')}",
  "    else if(k==='skirts'){x={g:tbVal('tbKg')};if(!x.g)return toast('重さを入れてください')}")
R("`<button class=\"tb-btn\" data-act=\"rigPick\"><span>針</span><b>${esc(listName(sp,'hooks',g.hook)||'未登録')}</b></button>`",
  "`<button class=\"tb-btn\" data-act=\"rigPick\"><span>シンカー</span><b>${esc(g.skirt?listName(sp,'skirts',g.skirt):'なし')}</b></button>`")
R("<h2>タイラバを替える</h2>", "<h2>エギ・シンカーを替える</h2>")
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
   '<meta name="description" content="ティップランのアオリイカの釣果を時間の経過と共に、エギ・シンカー・潮・流れと一緒に記録する無料ツール。全国どこの釣り場でも、潮回りと満潮・干潮、流れの向きと速さが自動で入ります。キロアップ（1kg以上）も記録できます。記録は端末に保存され、釣果データは匿名で集計に使います。">')
RX(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="ティップランのアオリイカの釣果を、エギ・シンカー・潮・流れと一緒に時系列で記録する無料ツール">')
ALL('タイラバカウンター', 'ティップランカウンター')
ALL('TAIRABA COUNTER', 'TIPRUN COUNTER')
ALL('dragon-counter.cutlassfish.tokyo/tairaba', 'dragon-counter.cutlassfish.tokyo/tipran')
ALL('/tairaba/', '/tipran/')
R("const LS='tairaba-log.v1';", "const LS='tipran-log.v1';")
ALL('tairaba-counter', 'tipran-counter')
ALL('tairaba-${tr.date}', 'tipran-${tr.date}')
ALL('スカート', 'シンカー')
ALL('よく釣れたヘッド', 'よく釣れたエギ')
ALL('タイラバ', 'エギ')
ALL('マダイ', 'アオリイカ')
ALL("'枚'", "'杯'")
ALL('枚</b>', '杯</b>')
ALL('枚数', '杯数')
ALL('ドラゴン', 'キロアップ')
ALL('エギ（ヘッド・ネクタイ・針）', 'エギとシンカー・キロアップ')
ALL('120cm以上', '1kg以上')
ALL('サイズ（全長・任意）', 'サイズ（重さ・任意）')
RX(r"  \{k:'ようこそ',t:'釣果を時間の経過と共に記録',d:'[^']*'\},",
   "  {k:'ようこそ',t:'釣果を時間の経過と共に記録',d:'ティップランカウンターは、ティップランのアオリイカの釣果を時間の経過と共に、使ったエギ・シンカー・潮・流れと一緒に記録するアプリです。全国どこの釣り場でも使えます。釣果データは匿名で集めて傾向の分析に使います。使うことでこれに同意したものとします。'},")
RX(r"  \{k:'準備',t:'[^']*',d:'[^']*'\},",
   "  {k:'準備',t:'エギとシンカー（増し錘）を登録',d:'画面下の右端にある「登録」タブで、持っているエギ（メーカー・号数・重さ・色）と、使うシンカーの重さを登録します。竿・リール・糸も登録できます。'},")
RX(r"  \{k:'釣れたら',t:'「釣れた」を1タップ',d:'[^']*'\},",
   "  {k:'釣れたら',t:'「釣れた」を1タップ',d:'「釣れた＋1」で、今使っているエギとシンカーと一緒に1杯記録します。1kg以上なら先に「キロアップ」にチェック。エギやシンカーを替えたら「エギ」のボタンから選び直します（押しても記録はされません）。アタリ・バラシも同じように記録されます。押し間違えたら下の「直前の釣果を取り消し」。アオリイカ以外が掛かったら小さな「外道」ボタンから（杯数には入りません）。サイズ（g）はあとから記録の一覧で入れられます。'},")
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

# ───────── エギの写真（tipran_images.py が切り抜いて縮めたもの）：カタログの色ごと。行の i は c と同じ並びの写真番号
_ip = os.path.join(HERE, 'tipran', 'egi-images.json')
IMG = json.load(open(_ip, encoding='utf-8')) if os.path.exists(_ip) else {}
for r in EGI['heads']:
    ii = [(IMG.get('%s|%s|%s' % (r['m'], r['s'], c)) or {}).get('id', '') for c in r['c']]
    ii = [i if i and os.path.exists(os.path.join(OUT, 'egi', i + '.webp')) else '' for i in ii]
    if any(ii):
        r['i'] = ii
RX(r"const TB_CAT=\{.*?\};\n", lambda m: 'const TB_CAT=' + json.dumps(EGI, ensure_ascii=False, separators=(',', ':')) + ';\n', flags=re.S)
R("function tbName(k,x){",
  """/* 写真：登録したエギのメーカー・製品・色でカタログを引く（前に登録したものにも出る） */
const eimg=(id,cls)=>id?`<img class="eimg ${cls||''}" src="/tipran/egi/${id}.webp" alt="" loading="lazy" decoding="async" onerror="this.remove()">`:'';
function egiIm(x){if(!x||!x.series)return '';const r=TB_CAT.heads.find(r=>r.m===x.maker&&r.s===x.series);if(!r||!r.i)return '';return r.i[r.c.indexOf(x.color)]||''}
const rigIm=(sp,id)=>egiIm((spOf(sp).rigs||[]).find(x=>x.id===id));
function tbName(k,x){""")
R("""${cur.c.map(c=>`<button class="chip ${tbc.c.has(c)?'on':''}" data-act="tbcC" data-d="${esc(c)}">${esc(c)}</button>`).join('')}""",
  """${cur.c.map((c,j)=>{const im=cur.i&&cur.i[j];return `<button class="chip ${im?'cimg':''} ${tbc.c.has(c)?'on':''}" data-act="tbcC" data-d="${esc(c)}">${eimg(im,'cc')}<span>${esc(c)}</span></button>`}).join('')}""")
R("""l.map(g=>`<div class="grow ${g.hidden?'hid':''}"><span class="tb-nm">${esc(g.name)}</span>""",
  """l.map(g=>`<div class="grow ${g.hidden?'hid':''}">${k==='rigs'?eimg(egiIm(g),'row'):''}<span class="tb-nm">${esc(g.name)}</span>""")
R("""`<button class="chip ${g.id===sel?'on':''}" data-act="${act}" data-id="${g.id}" aria-pressed="${g.id===sel}">${esc(g.name)}</button>`).join('')}<button class="chip add" data-act="goGear" aria-label="${esc(label)}を登録">""",
  """`<button class="chip ${g.id===sel?'on':''}" data-act="${act}" data-id="${g.id}" aria-pressed="${g.id===sel}">${k==='rigs'?eimg(egiIm(g),'ch'):''}${esc(g.name)}</button>`).join('')}<button class="chip add" data-act="goGear" aria-label="${esc(label)}を登録">""")
R("""<button class="td-tenya ${ten&&curGear(tr).rig&&TIMG.has(curGear(tr).rig)?'has-img':''}" data-act="${ten?'curTenya':'rigPick'}">${ten?timg(curGear(tr).rig,'cur'):''}""",
  """<button class="td-tenya ${(ten?curGear(tr).rig&&TIMG.has(curGear(tr).rig):rigIm(sp,curGear(tr).rig))?'has-img':''}" data-act="${ten?'curTenya':'rigPick'}">${ten?timg(curGear(tr).rig,'cur'):eimg(rigIm(sp,curGear(tr).rig),'cur')}""")
R(".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}",
  ".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}\n"
  ".eimg{flex:none;object-fit:contain;background:#fff;border-radius:6px}\n"
  ".eimg.cur{grid-column:1;grid-row:1;width:64px;height:28px}\n"
  ".eimg.row{width:76px;height:34px}\n"
  ".eimg.ch{width:56px;height:26px;vertical-align:middle;margin:-4px 8px -4px -6px}\n"
  ".chips.wrap .chip.cimg{box-sizing:border-box;display:inline-flex;flex-direction:column;align-items:stretch;gap:4px;flex:0 0 calc(50% - 4px);width:calc(50% - 4px);max-width:calc(50% - 4px);min-width:0;border-radius:12px;padding:6px;white-space:normal;text-align:center;font-size:14px;line-height:1.3}\n"
  ".eimg.cc{width:100%;height:60px;border-radius:8px}\n"
  ".chip.cimg.on .eimg{outline:3px solid var(--chipon);outline-offset:-3px}\n"
  "[data-act=tbcSeries]{max-width:100%;white-space:normal;text-align:left;border-radius:14px}")

# ───────── カタログに自分の製品・号数・色を足す（メーカーごと）。足したものは spOf(SOLO).own に残り、次からカタログに一緒に出る
# own = {p:[{m,s}], o:{'m|s':[{z,g}]}, c:{'m|s':[色]}}。カタログの行に足した分は no/nc より後ろ（点線で出す）
RX(r"function tbcRows\(\)\{.*?,\{kind:'tbc'\}\)\}\n", lambda m: r"""function tbcOwn(){const s=spOf(SOLO);return s.own=s.own||{p:[],o:{},c:{}}}
function tbcRows(){const L=TB_CAT[TBC_KEY[tbc.kind]]||[];if(tbc.kind!=='rigs')return L;const ow=tbcOwn();
  return L.map(r=>{const k=r.m+'|'+r.s,xo=ow.o[k]||[],xc=ow.c[k]||[];if(!xo.length&&!xc.length)return r;const o=[...(r.o||[]),...xo];return {...r,o,w:o.map((_,i)=>i),c:[...r.c,...xc],no:(r.o||[]).length,nc:r.c.length}})
   .concat(ow.p.map(p=>{const k=p.m+'|'+p.s,o=ow.o[k]||[];return {m:p.m,s:p.s,o,w:o.map((_,i)=>i),c:ow.c[k]||[],mine:1,no:0,nc:0}}))}
const tbcMineO=(r,j)=>j>=(r.no??(r.o||[]).length),tbcMineC=(r,j)=>j>=(r.nc??r.c.length);
function tbcAddForm(t){if(tbc.add!==t)return '';const inp=(id,l,ph,x)=>`<label class="field"><span>${l}</span><input type="${x||'text'}" id="${id}" placeholder="${ph}"${x==='number'?' inputmode="numeric" min="1" max="300"':''}></label>`;
  return `<div class="tbc-add">${t==='m'?inp('tbcM','メーカー','例：〇〇釣具')+inp('tbcP','製品','例：〇〇TR'):t==='p'?inp('tbcP','製品',`例：${esc(tbc.m)}の製品名`):t==='o'?inp('tbcZ','号数','例：3.5')+inp('tbcG','重さ（g）','例：30','number'):inp('tbcCn','色','例：赤テープ')}
   <div class="tbc-add-b"><button class="btn sm primary" data-act="tbcAddOk">追加</button><button class="btn sm ghost" data-act="tbcAdd" data-d="">やめる</button></div></div>`}
function tbcSheet(){const rows=tbcRows(),makers=[...new Set(rows.map(r=>r.m))];if(!tbc.m)tbc.m=makers[0]||'';const rig=tbc.kind==='rigs',dl=tbc.del;
  const ser=rows.map((r,i)=>[r,i]).filter(([r])=>r.m===tbc.m),cur=tbc.i>=0?rows[tbc.i]:null;
  const sk=tbc.kind==='skirts';
  /* シンカー：重さで色が違う製品（cw）は、選んだ重さにある色だけ出す。色は選ばなくてもよい */
  const cols=cur&&sk&&cur.cw&&tbc.w.size?cur.c.filter((c,j)=>[...tbc.w].some(g=>(cur.cw[g]||[]).includes(j))):cur?cur.c:[];
  const n=cur?(sk?tbc.w.size*Math.max(1,cols.filter(c=>tbc.c.has(c)).length):(rig&&cur.w.length?tbc.w.size:1)*tbc.c.size):0;
  const plus=(t,l)=>rig&&!dl?`<button class="chip add ${tbc.add===t?'on':''}" data-act="tbcAdd" data-d="${t}">＋ ${l}</button>`:'';
  const anyMine=rig&&(rows.some(r=>r.mine||r.no!=null));
  openSheet(`<div class="sheet-h stick"><h2>カタログ（${TBC_JP[tbc.kind]}）</h2><button class="btn sm ghost" data-act="tbcClose">閉じる</button></div>
   ${rig?`<p class="muted" style="margin:0">カタログにない製品・号数・色は「＋」で足せます。足したものは点線で、次からも出ます。</p>`:''}
   <div class="field"><span>メーカー</span><div class="chips wrap">${makers.map(m=>`<button class="chip ${m===tbc.m?'on':''}" data-act="tbcMaker" data-d="${esc(m)}">${esc(m)}</button>`).join('')}${plus('m','メーカー')}</div>${tbcAddForm('m')}</div>
   <div class="field"><span>製品</span><div class="chips wrap">${ser.map(([r,i])=>`<button class="chip ${r.mine?'mine':''} ${dl&&r.mine?'del':''} ${i===tbc.i?'on':''}" data-act="${dl&&r.mine?'tbcDelP':'tbcSeries'}" data-i="${i}">${dl&&r.mine?'✕ ':''}${esc(r.s)}${r.mat==='TG'?'<small>（TG）</small>':''}</button>`).join('')}${plus('p','製品')}</div>${tbcAddForm('p')}</div>
   ${cur?`${cur.note?`<p class="muted" style="margin:0">${esc(cur.note)}</p>`:''}
    ${sk?`<div class="field"><span>重さ（持っているものを全部）</span><div class="chips wrap">${cur.w.map(g=>`<button class="chip ${tbc.w.has(g)?'on':''}" data-act="tbcW" data-d="${g}">${g}g</button>`).join('')}</div></div>`:''}
    ${rig?`<div class="field"><span>号数・重さ（持っているものを全部）</span><div class="chips wrap">${cur.w.map(g=>{const o=cur.o[g]||{},mi=tbcMineO(cur,g);return `<button class="chip ${mi?'mine':''} ${dl&&mi?'del':''} ${tbc.w.has(g)?'on':''}" data-act="${dl&&mi?'tbcDelW':'tbcW'}" data-d="${g}">${dl&&mi?'✕ ':''}${o.z?esc(o.z)+'号':''}${o.g?' '+o.g+'g':''}</button>`}).join('')}${plus('o','号数・重さ')}</div>${tbcAddForm('o')}</div>`:''}
    <div class="field" ${sk&&!cur.c.length?'hidden':''}><span>${sk?'色（選ばなくてもよい）':'色（持っているものを全部）'}</span><div class="chips wrap">${cur.c.map((c,j)=>{if(sk&&!cols.includes(c))return '';const im=cur.i&&cur.i[j],mi=rig&&tbcMineC(cur,j);return `<button class="chip ${im?'cimg':''} ${mi?'mine':''} ${dl&&mi?'del':''} ${tbc.c.has(c)?'on':''}" data-act="${dl&&mi?'tbcDelC':'tbcC'}" data-d="${esc(c)}">${eimg(im,'cc')}<span>${dl&&mi?'✕ ':''}${esc(c)}</span></button>`}).join('')}${plus('c','色')}</div>${tbcAddForm('c')}</div>
    ${cur.u?`<a class="golink" href="${esc(cur.u)}" target="_blank" rel="noopener">メーカーのページで見る ↗</a>`:''}`:'<p class="muted">製品を選んでください。</p>'}
   ${anyMine?`<button class="btn sm ghost" data-act="tbcDelMode" style="align-self:flex-start">${dl?'整理を終わる':'自分で足したものを整理（消す）'}</button>`:''}
   <div class="tb-foot"><button class="btn primary" data-act="tbcSave" ${n&&!dl?'':'disabled'}>${dl?'整理中（✕を押すと消えます）':n?`${n}件を登録`:!cur?'製品を選んでください':sk?'重さを選んでください':rig&&cur.w.length&&!tbc.w.size?'号数・重さを選んでください':'色を選んでください'}</button></div>`,{kind:'tbc'});
  if(tbc.add){const el=$('#'+({m:'tbcM',p:'tbcP',o:'tbcZ',c:'tbcCn'}[tbc.add]));if(el)setTimeout(()=>el.focus(),30)}}
""", flags=re.S)
RX(r"  tbcMaker:b=>\{tbc\.m=b\.dataset\.d;", "  tbcMaker:b=>{tbc.add='';tbc.m=b.dataset.d;")
RX(r"  tbcSeries:b=>\{tbc\.i=\+b\.dataset\.i;", "  tbcSeries:b=>{tbc.add='';tbc.i=+b.dataset.i;")
R("  tbcSave:()=>{const r=tbcRows()[tbc.i];if(!r)return;",
  """  tbcAdd:b=>{tbc.add=tbc.add===b.dataset.d?'':b.dataset.d;tbcSheet()},
  tbcDelMode:()=>{tbc.del=!tbc.del;tbc.add='';tbcSheet()},
  tbcAddOk:()=>{const t=tbc.add,ow=tbcOwn(),rows=tbcRows(),r=rows[tbc.i];
    if(t==='m'||t==='p'){const m=t==='m'?tbVal('tbcM'):tbc.m,p=tbVal('tbcP');if(!m||!p)return toast(t==='m'?'メーカーと製品を入れてください':'製品名を入れてください');
      if(!rows.some(x=>x.m===m&&x.s===p))ow.p.push({m,s:p});tbc.m=m;tbc.i=tbcRows().findIndex(x=>x.m===m&&x.s===p);tbc.w=new Set();tbc.c=new Set()}
    else if(t==='o'){if(!r)return;const z=tbVal('tbcZ').replace(/号$/,''),g=Math.round(+tbVal('tbcG')||0);if(!z&&!g)return toast('号数か重さを入れてください');const k=r.m+'|'+r.s;
      let j=r.o.findIndex(o=>String(o.z||'')===z&&(+o.g||0)===g);if(j<0){(ow.o[k]=ow.o[k]||[]).push({z,g});j=r.o.length}tbc.w.add(j)}
    else if(t==='c'){if(!r)return;const c=tbVal('tbcCn');if(!c)return toast('色を入れてください');const k=r.m+'|'+r.s;if(!r.c.includes(c))(ow.c[k]=ow.c[k]||[]).push(c);tbc.c.add(c)}
    tbc.add='';cfgTouch();tbcSheet()},
  tbcDelP:b=>{const r=tbcRows()[+b.dataset.i];if(!r||!r.mine)return;const ow=tbcOwn(),k=r.m+'|'+r.s;ow.p=ow.p.filter(p=>!(p.m===r.m&&p.s===r.s));delete ow.o[k];delete ow.c[k];
    tbc.i=-1;tbc.w=new Set();tbc.c=new Set();if(!tbcRows().some(x=>x.m===tbc.m))tbc.m='';cfgTouch();tbcSheet()},
  tbcDelW:b=>{const r=tbcRows()[tbc.i];if(!r)return;const ow=tbcOwn(),k=r.m+'|'+r.s,j=+b.dataset.d-(r.no||0);(ow.o[k]||[]).splice(j,1);tbc.w=new Set();cfgTouch();tbcSheet()},
  tbcDelC:b=>{const r=tbcRows()[tbc.i];if(!r)return;const ow=tbcOwn(),k=r.m+'|'+r.s,c=b.dataset.d;ow.c[k]=(ow.c[k]||[]).filter(x=>x!==c);tbc.c.delete(c);cfgTouch();tbcSheet()},
  tbcSave:()=>{const r=tbcRows()[tbc.i];if(!r||tbc.del)return;""")
R("const ws=k==='rigs'&&r.w.length?[...tbc.w].sort((a,b)=>a-b):[''];", "const ws=k==='rigs'&&r.w.length?[...tbc.w].sort((a,b)=>a-b):[-1];")
R("color:c,shape:o.z||'',cat:true,id:uid()};", "color:c,shape:o.z||'',cat:!r.mine,id:uid()};")
R(".tb-form{display:grid;grid-template-columns:1fr 1fr;gap:8px 10px;margin:8px 0}",
  ".tb-form{display:grid;grid-template-columns:1fr 1fr;gap:8px 10px;margin:8px 0}"
  ".chip.mine{border-style:dashed}.chip.del{border-color:var(--pink);color:var(--pink)}"
  ".tbc-add{display:grid;grid-template-columns:1fr 1fr;gap:8px 10px;margin-top:10px;padding:10px;border:1px dashed var(--line);border-radius:12px}"
  ".tbc-add .field:only-of-type{grid-column:1/-1}.tbc-add-b{grid-column:1/-1;display:flex;gap:8px}")

# ───────── シンカー（増し錘）のカタログ：製品＋重さで登録、色は任意。記録には「エギ王TRシンカー 20g オレンジ」のように出る
R("if(!r||tbc.del)return;const s=spOf(SOLO),k=tbc.kind;s[k]=s[k]||[];let n=0;",
  "if(!r||tbc.del)return;const s=spOf(SOLO),k=tbc.kind;s[k]=s[k]||[];let n=0;\n"
  "    if(k==='skirts'){for(const g of [...tbc.w].sort((a,b)=>a-b)){const cs=r.c.filter((c,j)=>tbc.c.has(c)&&(!r.cw||(r.cw[g]||[]).includes(j)));\n"
  "        for(const c of (cs.length?cs:[''])){const x={maker:r.m,series:r.s,g:String(g),color:c,cat:true,id:uid()};x.name=tbName(k,x);if(s[k].some(y=>y.name===x.name&&!y.hidden))continue;s[k].push(x);n++}}\n"
  "      cfgTouch();toast(n?`${n}件を登録しました`:'もう登録されています');return acts.tbcClose()}")
R("if(k==='skirts')return x.g?x.g+'g':'';", "if(k==='skirts')return [x.series,x.g?x.g+'g':'',x.color].filter(Boolean).join(' ');")
R("${tbList('skirts')}",
  "${tbList('skirts')}${TB_CAT.skirts.length?`<button class=\"btn sm\" data-act=\"tbcOpen\" data-kind=\"skirts\" style=\"margin:8px 0\">📖 カタログから選ぶ（${[...new Set(TB_CAT.skirts.map(r=>r.m))].length}社・${TB_CAT.skirts.length}製品）</button><p class=\"muted\" style=\"margin:0\">カタログにないものは、下に重さを入れて登録</p>`:''}")
R("使う重さを登録しておくと、記録のときに選べます。", "メーカーのカタログから選ぶか、使う重さを登録しておくと、記録のときに選べます。")

# ───────── 竿とリールのカタログ（tools/tipran/tackle.json、tipran_tackle.py が作る）
# タチウオ用のカタログをティップラン用に差し替える。スピニングとベイトを同じ一覧に入れ、絞り込みで分ける。
# rods [id,メーカー,シリーズ,品番,長さm,spinning|bait,エギの重さg,状態] / reels [id,メーカー,シリーズ,品番,spinning|bait,カウンター0|1,状態]
_tp = os.path.join(HERE, 'tipran', 'tackle.json')
if os.path.exists(_tp) and not os.environ.get('TIPRAN_HOLD_TACKLE'):   # TIPRAN_HOLD_TACKLE=1：竿・リールのカタログを入れずに作る（公開の指示を待つ間）
    TK = json.load(open(_tp, encoding='utf-8'))
    _mk = lambda L: list(dict.fromkeys(a[1] for a in L))
    _d = lambda x: json.dumps(x, ensure_ascii=False, separators=(',', ':'))
    RX(r"const TCAT=\{.*?\}; //", lambda m: 'const TCAT=' + _d({'v': '2026年11月', 'rods': TK['rods'], 'reels': TK['reels']}) + '; //', flags=re.S)
    RX(r"const TK_MK=\{[^}]*\};\nconst TK_MAKERS=\{[^}]*\};", lambda m: 'const TK_MK={};\nconst TK_MAKERS=' + _d({'rod': _mk(TK['rods']), 'reel': _mk(TK['reels'])}) + ';')
    R("(TCAT.rods||[]).forEach(a=>tcBy[a[0]]={id:a[0],k:'rod',m:a[1],s:a[2],model:a[3],len:a[4],tier:a[5],st:a[6]||''});(TCAT.reels||[]).forEach(a=>tcBy[a[0]]={id:a[0],k:'reel',m:a[1],s:a[2],model:a[3],kind:a[4],st:a[5]||''});",
      "(TCAT.rods||[]).forEach(a=>tcBy[a[0]]={id:a[0],k:'rod',m:a[1],s:a[2],model:a[3],len:a[4],kind:a[5],egi:a[6]||'',st:a[7]||''});(TCAT.reels||[]).forEach(a=>tcBy[a[0]]={id:a[0],k:'reel',m:a[1],s:a[2],model:a[3],kind:a[4],counter:!!a[5],st:a[6]||''});")
    R("const tkKind=it=>it&&it.kind==='electric'?'電動':'';", "const tkKind=it=>it&&it.kind==='bait'?'ベイト':'';")
    # 絞り込み：竿はスピニング／ベイト、リールはスピニング／ベイト／カウンター付き
    R("(!tkQ.kind||(tkQ.kind==='electric')===(x.kind==='electric'))", "(!tkQ.kind||(tkQ.kind==='counter'?x.counter:x.kind===tkQ.kind))")
    R("${k==='reel'?`<div class=\"seg tk-kind\">${[['','すべて'],['bait','ベイト'],['electric','電動']].map(",
      "${1?`<div class=\"seg tk-kind\">${(k==='rod'?[['','すべて'],['spinning','スピニング'],['bait','ベイト']]:[['','すべて'],['spinning','スピニング'],['bait','ベイト'],['counter','カウンター']]).map(")
    R("${x.len?`<small>${x.len}m</small>`:''}${x.kind==='electric'?'<small>電動</small>':''}",
      "${x.len?`<small>${x.len}m</small>`:''}${x.kind==='bait'?'<small>ベイト</small>':''}${x.egi?`<small>${esc(x.egi)}g</small>`:''}${x.counter?'<small>カウンター付き</small>':''}")
    R("placeholder=\"${k==='rod'?'例：極鋭、サーベルマスター、175':'例：ソルティガ、フォースマスター、200'}\"", "placeholder=\"${k==='rod'?'例：エメラルダス、セフィア、65':'例：セフィア、エメラルダス、C3000'}\"")
    R("placeholder=\"${k==='rod'?'例：極鋭タチウオテンヤSP EX MH-175':'例：ソルティガ BJ 100SH'}\"", "placeholder=\"${k==='rod'?'例：エメラルダス AIR BOAT 65MLS-S':'例：セフィア XR C3000SDH'}\"")
    # ティップランの標準の糸：PE0.6号・200m（タチウオ用は1.5号）
    ALL("pe:'1.5'", "pe:'0.6'")
    R("...(k==='reel'?{kind:'bait'}:{})", "...(k==='reel'?{kind:''}:{})")
    # メーカーが多いので、メーカーの並びは1行で横に送る。絞り込みの文字は折り返さない大きさに
    R(".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}", ".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}\n.chips.wrap.tk-mk{flex-wrap:nowrap;overflow-x:auto;padding-bottom:6px}.seg.tk-kind button{font-size:14px;padding-left:4px;padding-right:4px;white-space:nowrap}")

# ───────── 片舷流しの人数は、はじめ8人（両舷は16人）。前に選んだ人数があればそれを使う
R("people:b?(b.people||b.seats*2):(p.people||(p.seats||8)*2)", "people:b?(b.people||b.seats*2):(p.people||((p.lay||'one')==='one'?8:16))")
# ───────── 使い方（チュートリアル）の絵と、残っていたタチウオ・テンヤの言葉
R("return row(10,true,'40号 パープルグロー','ダイワ SS AH')+row(48,true,'40号 ケイムラ','シマノ サーベルマスター')+row(86,false,'50号 ゴールド','ハヤブサ')+",
  "return row(10,true,'エギ王 TR 3.5号 30g 金アジ','エギ・ヤマシタ')+row(48,true,'エメラルダス ボート 3.5号 赤テープ','エギ・ダイワ')+row(86,true,'エギ王TRシンカー 20g','シンカー（増し錘）')+")
R("'一軍リスト（2）'", "'カタログから選べます'")
R("タチウオ以外に釣れた魚を、今の時刻と使用テンヤで1匹記録します（タチウオの本数には入りません）。", "アオリイカ以外に釣れたものを、今の時刻と使っているエギで1匹記録します（杯数には入りません）。")
R("時刻・テンヤ・種類（釣れた／アタリ／バラシ）", "時刻・エギ・種類（釣れた／アタリ／バラシ）")
R("設定（釣り場・船・テンヤ）は、新しいほうを使います。", "設定（釣り場・船・エギ）は、新しいほうを使います。")
R("テンヤは、その時刻にアプリで選んでいたものになります。", "エギは、その時刻にアプリで選んでいたものになります。")

# ───────── 使い方の絵：「カタログから選べます」の枠を文字に合わせて広げる。沖上がりの座席の図は片舷（1列）
R('<rect x="88" y="136" width="124" height="28" rx="14" style="fill:rgba(227,164,59,.14);stroke:var(--amber)"/>',
  '<rect x="66" y="136" width="168" height="28" rx="14" style="fill:rgba(227,164,59,.14);stroke:var(--amber)"/>')
R("""${[0,1,2,3,4,5,6].map(j=>`<circle cx="${226-j*28}" cy="130" r="${j===2?7:4}" style="fill:${j===2?'var(--amber)':'var(--muted)'}"/><circle cx="${226-j*28}" cy="146" r="4" style="fill:var(--muted)"/>`).join('')}""",
  """${[0,1,2,3,4,5,6].map(j=>`<circle cx="${226-j*28}" cy="138" r="${j===2?7:4.5}" style="fill:${j===2?'var(--amber)':'var(--muted)'}"/>`).join('')}""")
# ───────── 登録タブのエギの欄の見出し
R('<div class="card" id="tbHeads"><h2>エギ</h2>', '<div class="card" id="tbHeads"><h2>所有エギを登録する</h2>')

# ───────── エギを号数で絞る：カタログ（号数を選ぶと、その号数がある製品・その号数の重さだけ出る）と、記録で使うエギを選ぶところ
R("function tbcSheet(){const rows=tbcRows(),makers=[...new Set(rows.map(r=>r.m))];if(!tbc.m)tbc.m=makers[0]||'';",
  "function tbcSheet(){const rows=tbcRows(),zOk=r=>!tbc.z||tbc.kind!=='rigs'||(r.o||[]).some(o=>String(o.z)===tbc.z)||(r.mine&&!(r.o||[]).length),"
  "zs=tbc.kind==='rigs'?[...new Set(rows.flatMap(r=>(r.o||[]).map(o=>String(o.z||''))))].filter(Boolean).sort((a,b)=>a-b):[],"
  "makers=[...new Set(rows.filter(zOk).map(r=>r.m))];if(!tbc.m||!makers.includes(tbc.m))tbc.m=makers[0]||'';")
R("const ser=rows.map((r,i)=>[r,i]).filter(([r])=>r.m===tbc.m),", "const ser=rows.map((r,i)=>[r,i]).filter(([r])=>r.m===tbc.m&&zOk(r)),")
R("${cur.w.map(g=>{const o=cur.o[g]||{},mi=tbcMineO(cur,g);return", "${cur.w.filter(g=>!tbc.z||String((cur.o[g]||{}).z)===tbc.z).map(g=>{const o=cur.o[g]||{},mi=tbcMineO(cur,g);return")
R('<div class="field"><span>メーカー</span><div class="chips wrap">${makers.map',
  '${zs.length>1?`<div class="field"><span>号数で絞る</span><div class="chips wrap">${[\'\',...zs].map(z=>`<button class="chip ${(tbc.z||\'\')===z?\'on\':\'\'}" data-act="tbcZ" data-d="${z}">${z?z+\'号\':\'すべて\'}</button>`).join(\'\')}</div></div>`:\'\'}\n'
  '   <div class="field"><span>メーカー</span><div class="chips wrap">${makers.map')
R("const r=tbcRows()[tbc.i];if(r&&r.w&&r.w.length===1)tbc.w.add(r.w[0]);tbcSheet()},",
  "const r=tbcRows()[tbc.i];if(r&&r.w&&r.w.length===1)tbc.w.add(r.w[0]);if(r&&tbc.z){const m=r.w.filter(g=>String((r.o[g]||{}).z)===tbc.z);if(m.length===1)tbc.w.add(m[0])}tbcSheet()},")
R("  tbcAdd:b=>{", "  tbcZ:b=>{tbc.z=b.dataset.d;tbcLastZ=tbc.z;tbc.i=-1;tbc.w=new Set();tbc.c=new Set();tbc.add='';tbcSheet()},\n"
  "  rigZ:b=>{const gp=b.closest('.gearpick');gp.querySelectorAll('[data-act=\"rigZ\"]').forEach(x=>x.classList.toggle('on',x===b));const z=b.dataset.d;gp.querySelectorAll('.chips [data-z]').forEach(c=>c.hidden=!!z&&c.dataset.z!==z)},\n"
  "  tbcAdd:b=>{")
R("let tbc=null;", "let tbc=null,tbcLastZ='';   // 号数の絞り込みは、次にカタログを開いたときも残す")
RX(r"tbcOpen:b=>\{tbc=\{kind:b\.dataset\.kind,", "tbcOpen:b=>{tbc={z:b.dataset.kind==='rigs'?tbcLastZ:'',kind:b.dataset.kind,")
# 記録で使うエギを選ぶところ：持っているエギの号数が2つ以上なら、号数のボタンで絞れる
R('<div class="gp-lbl">${esc(label)}</div><div class="chips wrap">${(s[k]||[]).filter(g=>!g.hidden).map(g=>',
  '<div class="gp-lbl">${esc(label)}</div>${k===\'rigs\'?rigZRow(s[k]):\'\'}<div class="chips wrap">${(s[k]||[]).filter(g=>!g.hidden).map(g=>')
R("data-act=\"${act}\" data-id=\"${g.id}\" aria-pressed=\"${g.id===sel}\">${k==='rigs'?eimg(egiIm(g),'ch'):''}",
  "data-act=\"${act}\" data-id=\"${g.id}\"${k==='rigs'?` data-z=\"${esc(g.shape||'')}\"`:''} aria-pressed=\"${g.id===sel}\">${k==='rigs'?eimg(egiIm(g),'ch'):''}")
R("function chipsHTML(sp,k,sel,act){",
  "function rigZRow(l){const zs=[...new Set((l||[]).filter(g=>!g.hidden&&g.shape).map(g=>String(g.shape)))].sort((a,b)=>a-b);if(zs.length<2)return '';\n"
  "  return `<div class=\"chips rigz\">${['',...zs].map(z=>`<button class=\"chip ${z?'':'on'}\" data-act=\"rigZ\" data-d=\"${esc(z)}\">${z?esc(z)+'号':'全号数'}</button>`).join('')}</div>`}\n"
  "function chipsHTML(sp,k,sel,act){")
R(".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}", ".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}\n.chips.rigz{margin:2px 0 6px}.chips.rigz .chip{min-height:34px;padding:4px 12px;font-size:14px}")

R("<div class=\"card\"><h2>仕掛けと餌</h2>", "<div class=\"card\"><h2>エギとシンカー</h2>")

icon = base64.b64encode(open(os.path.join(OUT, 'icon-192.png'), 'rb').read()).decode()
RX(r'(<a class="brand" href="https://cutlassfish.tokyo/"><img class="b-ic" src=")data:image/png;base64,[A-Za-z0-9+/=]+(")', r'\g<1>data:image/png;base64,' + icon + r'\g<2>')

if 'マダイ' in s:
    sys.exit('left over: マダイ')
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(s)
print('ok', len(s))
