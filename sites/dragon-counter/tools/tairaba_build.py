"""Builds タイラバカウンター (public/tairaba/index.html) from ドラゴンカウンター (public/index.html).

ドラゴンカウンター is the one source of code. This script copies it and changes only what differs:
name and addresses, the fish (マダイ), the tairaba parts (ヘッド・ネクタイ・針), nationwide spots and map,
Open-Meteo currents everywhere, and its own storage key, service worker and data folder.
Every replacement must match exactly the expected number of times, so a change in ドラゴンカウンター
that breaks a patch stops the build instead of producing a half-converted page.

    python3 tools/tairaba_build.py      (run from sites/dragon-counter)
"""
import base64
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(HERE, '..', 'public')
OUT = os.path.join(PUB, 'tairaba')
URL = 'https://dragon-counter.cutlassfish.tokyo/tairaba/'

s = open(os.path.join(PUB, 'index.html'), encoding='utf-8').read()
coast_jp = open(os.path.join(HERE, 'tairaba', 'coast-japan.txt')).read().strip()
assert re.fullmatch(r'[-0-9,;]+', coast_jp)


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


# ───────── name, addresses, icons
R('<title>ドラゴンカウンター｜TOKYO BAY FISHING</title>', '<title>タイラバカウンター｜TOKYO BAY FISHING</title>')
RX(r'<meta name="description" content="[^"]*">',
   '<meta name="description" content="マダイの釣果を時間の経過と共に、タイラバ（ヘッド・ネクタイ・針）・潮・流れと一緒に記録する無料ツール。全国どこの釣り場でも、潮回りと満潮・干潮、流れの向きと速さが自動で入ります。記録は端末に保存され、釣果データは匿名で集計に使います。">')
R('<link rel="canonical" href="https://dragon-counter.cutlassfish.tokyo/">', f'<link rel="canonical" href="{URL}">')
R('<meta property="og:title" content="ドラゴンカウンター"><meta property="og:url" content="https://dragon-counter.cutlassfish.tokyo/"><meta property="og:image" content="https://dragon-counter.cutlassfish.tokyo/og.png">',
  f'<meta property="og:title" content="タイラバカウンター"><meta property="og:url" content="{URL}"><meta property="og:image" content="{URL}icon-512.png">')
RX(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="マダイの釣果を、タイラバ・潮・流れと一緒に時系列で記録する無料ツール">')
R('<meta name="twitter:card" content="summary_large_image">', '<meta name="twitter:card" content="summary">')
R('<link rel="manifest" href="/manifest.webmanifest">', '<link rel="manifest" href="/tairaba/manifest.webmanifest">')
R('<link rel="apple-touch-icon" href="/icon-180.png">', '<link rel="apple-touch-icon" href="/tairaba/icon-180.png">')
R('<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">', '<link rel="icon" type="image/png" sizes="192x192" href="/tairaba/icon-192.png">')
R('<meta name="apple-mobile-web-app-title" content="ドラゴンカウンター">', '<meta name="apple-mobile-web-app-title" content="タイラバカウンター">')
R('<script>window.TBTCNT={"sw": "/sw.js", "scope": "/", "catalogExtraUrl": "/catalog-extra.json", "home": "https://cutlassfish.tokyo/"};</script>',
  '<script>window.TBTCNT={"sw": "/tairaba/sw.js", "scope": "/tairaba/", "catalogExtraUrl": "/catalog-extra.json", "home": "https://cutlassfish.tokyo/"};</script>')
icon = base64.b64encode(open(os.path.join(OUT, 'icon-192.png'), 'rb').read()).decode()
RX(r'(<a class="brand" href="https://cutlassfish.tokyo/"><img class="b-ic" src=")data:image/webp;base64,[A-Za-z0-9+/=]+(")', r'\g<1>data:image/png;base64,' + icon + r'\g<2>')
R('<b>DRAGON COUNTER</b>', '<b>TAIRABA COUNTER</b>')

# ───────── storage, data collection, backups, shared images
R("const LS='tachiuo-log.v1';", "const LS='tairaba-log.v1';")
R("const SHARE_URL='/collect.php'", "const SHARE_URL='/tairaba/collect.php'")
R("app:'dragon-counter'", "app:'tairaba-counter'", 2)
R('dragon-counter-backup-', 'tairaba-counter-backup-')
R('dragon-${tr.date}', 'tairaba-${tr.date}', 2)
R('font-weight="700" fill="#ffffff" letter-spacing="${z(1.5)}">DRAGON COUNTER</text>', 'font-weight="700" fill="#ffffff" letter-spacing="${z(1.5)}">TAIRABA COUNTER</text>')
R('text-anchor="end">dragon-counter.cutlassfish.tokyo</text>', 'text-anchor="end">dragon-counter.cutlassfish.tokyo/tairaba</text>')

# ───────── the fish: マダイ only, no 大物 mark, no 大漁 mark, no sample trip, no preset boats or spots
R("function defaultSpecies(){return [\n",
  "function defaultSpecies(){return [\n  {id:'madai',name:'マダイ',unit:'枚',sizeUnit:'cm',rigLabel:'ヘッド',baitLabel:'ネクタイ',hookLabel:'針',skirtLabel:'スカート',tairaba:true,variants:[{id:'madai',name:'マダイ'}],rigs:[],baits:[],hooks:[],skirts:[]},\n")
R("const SOLO='tachiuo';", "const SOLO='madai';")
R("const GEDO_DEF=['トラフグ','サバフグ','サワラ','アジ'];", "const GEDO_DEF=['ホウボウ','カサゴ','イトヨリ','アマダイ','ハマチ','ワラサ','サバ','アジ'];")
R("const isTairyo=date=>dayCatch(date)>=TAIRYO;", "const isTairyo=date=>false;")
R("if(!s.samplesV2){delete s.trips.sample;const a=makeSampleTachi();s.trips[a.id]=a;if(!SOLO){const b=makeSampleFugu();s.trips[b.id]=b}s.samplesV2=true;if(!s.ui.figTrip||!s.trips[s.ui.figTrip])s.ui.figTrip=a.id}",
  "if(!s.samplesV2){delete s.trips.sample;s.samplesV2=true}")
R("if(!M.boats1){c.boats=c.boats||[];for(const name of ['教至丸','こうゆう丸','長谷川丸','一ノ瀬丸'])", "if(!M.boats1){c.boats=c.boats||[];for(const name of [])")
RX(r"const DEFAULT_SPOTS=\[[^\]]*\];", "const DEFAULT_SPOTS=[];")

# 大物の印（ドラゴン）は使わない：タチウオ専用の表示はすべて sp==='tachiuo' で出ているので、魚種がマダイなら出ない

# ───────── recording: simple only (誘い・掛け方はテンヤ用なので出さない)
R("const modeOf=tr=>tr&&tr.mode==='detail'?'detail':'simple';", "const modeOf=tr=>'simple';")
R('<span class="mseg" role="group" aria-label="記録のしかた"><button class="${modeOf(tr)===\'simple\'?\'on\':\'\'}" data-act="recMode" data-d="simple">シンプル</button><button class="${modeOf(tr)===\'detail\'?\'on\':\'\'}" data-act="recMode" data-d="detail">詳細</button></span>', '')
R("function fModeHTML(f){const m=f.rmode||'';", "function fModeHTML(f){f.rmode='simple';return '';const m=f.rmode||'';")
R("${f.kind!=='gedo'?`<div class=\"field\"><span>誘い</span>", "${false?`<div class=\"field\"><span>誘い</span>")

# ───────── tairaba parts: ヘッド (rigs) ・ ネクタイ (baits) ・ 針 (hooks)
R("const label=k==='rigs'?s.rigLabel:s.baitLabel;", "const label=k==='rigs'?s.rigLabel:k==='hooks'?s.hookLabel:s.baitLabel;")
R(":{rig:pf.rig||firstVis(sp,'rigs'),bait:pf.bait||firstVis(sp,'baits')}}", ":{rig:pf.rig||firstVis(sp,'rigs'),bait:pf.bait||firstVis(sp,'baits'),hook:pf.hook||firstVis(sp,'hooks'),skirt:pf.skirt||''}}")
R("else if(!g.rig)g.rig=firstVis(sp,'rigs');if(!g.bait)", "else if(!g.rig)g.rig=firstVis(sp,'rigs');if(!g.hook)g.hook=firstVis(sp,'hooks');if(!g.bait)")
R("chipsHTML(sp,'rigs',g.rig,'fRig'))", "chipsHTML(sp,'rigs',g.rig,'fRig')+chipsHTML(sp,'hooks',g.hook,'fHook')+skirtChips(g.skirt,'fSkirt'))")
R("  fRig:b=>{fGear(startDraft,startDraft.sp).rig=b.dataset.id;$('#fGear').innerHTML=fGearHTML(startDraft)},",
  "  fRig:b=>{fGear(startDraft,startDraft.sp).rig=b.dataset.id;$('#fGear').innerHTML=fGearHTML(startDraft)},\n  fHook:b=>{fGear(startDraft,startDraft.sp).hook=b.dataset.id;$('#fGear').innerHTML=fGearHTML(startDraft)},\n  fSkirt:b=>{fGear(startDraft,startDraft.sp).skirt=b.dataset.id;$('#fGear').innerHTML=fGearHTML(startDraft)},")
R("bait:needBait(tsp,g)?g.bait:'',size:''", "bait:needBait(tsp,g)?g.bait:'',hook:g.hook||'',skirt:g.skirt||'',size:''")
R("const rec={t:now,sp:tr.cur.sp,rig:g.rig,bait:needBait(tr.cur.sp,g)?g.bait:''};", "const rec={t:now,sp:tr.cur.sp,rig:g.rig,bait:needBait(tr.cur.sp,g)?g.bait:'',hook:g.hook||'',skirt:g.skirt||''};")
R("gearLog:[{t:start,sp:f.sp,rig:cg.rig,bait:needBait(f.sp,cg)?cg.bait:''}]", "gearLog:[{t:start,sp:f.sp,rig:cg.rig,bait:needBait(f.sp,cg)?cg.bait:'',hook:cg.hook||'',skirt:cg.skirt||''}]")
R("function evGearText(e){const gs=e.gsp||e.sp,s=spOf(gs);return [listName(gs,'rigs',e.rig),s.baitLabel?listName(gs,'baits',e.bait):'',",
  "function evGearText(e){const gs=e.gsp||e.sp,s=spOf(gs);return [listName(gs,'rigs',e.rig),s.baitLabel?listName(gs,'baits',e.bait):'',e.hook?listName(gs,'hooks',e.hook):'',e.skirt?'スカート '+listName(gs,'skirts',e.skirt):'',")
R("function curRigLabel(tr){const sp=tr.cur.sp,g=curGear(tr);if(isTenya(sp,g))return g.rig&&tenyaOf(g.rig)?tenyaLabel(g.rig):'未選択';return listName(sp,'rigs',g.rig)}",
  "function curRigLabel(tr){const sp=tr.cur.sp,g=curGear(tr);if(isTenya(sp,g))return g.rig&&tenyaOf(g.rig)?tenyaLabel(g.rig):'未選択';return [listName(sp,'rigs',g.rig),listName(sp,'baits',g.bait),g.skirt?'スカート '+listName(sp,'skirts',g.skirt):''].filter(Boolean).join('／')||'未登録'}")
R("<span>${ten?'使用テンヤ':'仕掛け'}</span>", "<span>${ten?'使用テンヤ':'タイラバ'}</span>")
R("`<button class=\"tb-btn\" data-act=\"rigPick\"><span>仕掛け</span><b>${esc(METHOD_JP[methodOf(sp,g)]||'仕掛け')}</b></button>`",
  "`<button class=\"tb-btn\" data-act=\"rigPick\"><span>針</span><b>${esc(listName(sp,'hooks',g.hook)||'未登録')}</b></button>`")
R("${needBait(sp,g)?`<button class=\"tb-btn\" data-act=\"baitPick\">", "${needBait(sp,g)&&!s.tairaba?`<button class=\"tb-btn\" data-act=\"baitPick\">")
R("  rigPick:()=>{const tr=active();if(!tr)return;const sp=tr.cur.sp,g=curGear(tr);openSheet(`<div class=\"sheet-h\"><h2>仕掛け</h2><button class=\"btn sm ghost\" data-act=\"closeSheet\">閉じる</button></div>${spOf(sp).catalog?'':chipsHTML(sp,'rigs',g.rig,'setRigS')}",
  "  rigPick:()=>{const tr=active();if(!tr)return;const sp=tr.cur.sp,g=curGear(tr);openSheet(`<div class=\"sheet-h\"><h2>タイラバを替える</h2><button class=\"btn sm ghost\" data-act=\"closeSheet\">閉じる</button></div><p class=\"muted\" style=\"margin:0\">替えた部品だけ押してください。押した時刻から記録に反映されます。</p>${spOf(sp).catalog?'':chipsHTML(sp,'rigs',g.rig,'setRigK')+chipsHTML(sp,'baits',g.bait,'setBaitK')+chipsHTML(sp,'hooks',g.hook,'setHookK')+skirtChips(g.skirt,'setSkirtK')}")
R("  setRigS:b=>{", "  setRigK:b=>{const tr=active();curGear(tr).rig=b.dataset.id;logGear(tr);touch(tr);acts.rigPick()},\n  setBaitK:b=>{const tr=active();curGear(tr).bait=b.dataset.id;logGear(tr);touch(tr);acts.rigPick()},\n  setHookK:b=>{const tr=active();curGear(tr).hook=b.dataset.id;S.prefs.g[tr.cur.sp]={...(S.prefs.g[tr.cur.sp]||{}),hook:b.dataset.id};logGear(tr);touch(tr);acts.rigPick()},\n  setSkirtK:b=>{const tr=active();curGear(tr).skirt=b.dataset.id;S.prefs.g[tr.cur.sp]={...(S.prefs.g[tr.cur.sp]||{}),skirt:b.dataset.id};logGear(tr);touch(tr);acts.rigPick()},\n  setRigS:b=>{")
R(":g.rig,bait:g.bait}:{rig:g.rig,bait:g.bait};", ":g.rig,bait:g.bait}:{rig:g.rig,bait:g.bait,hook:g.hook||'',skirt:g.skirt||''};")
# edit one record: 針 too
R("rig:e.rig,bait:e.bait,size:e.size===undefined", "rig:e.rig,bait:e.bait,hook:e.hook||'',skirt:e.skirt||'',size:e.size===undefined")
R("g.id===f[k==='rigs'?'rig':'bait']?'selected':''", "g.id===f[k==='rigs'?'rig':k==='hooks'?'hook':k==='skirts'?'skirt':'bait']?'selected':''")
R("<select id=\"evBait\" data-ef=\"bait\">${sel('baits')}</select></label>`:''}</div>",
  "<select id=\"evBait\" data-ef=\"bait\">${sel('baits')}</select></label>`:''}${gs.hookLabel?`<label class=\"field\"><span>${esc(gs.hookLabel)}</span><select id=\"evHook\" data-ef=\"hook\"><option value=\"\" ${!f.hook?'selected':''}>未選択</option>${sel('hooks')}</select></label>`:''}${gs.skirtLabel?`<label class=\"field\"><span>${esc(gs.skirtLabel)}</span><select id=\"evSkirt\" data-ef=\"skirt\"><option value=\"\" ${!f.skirt?'selected':''}>なし</option>${sel('skirts')}</select></label>`:''}</div>")
R("rig:f.rig,bait:f.bait,size:f.kind==='catch'?f.size:''", "rig:f.rig,bait:f.bait,hook:f.hook||'',skirt:f.skirt||'',size:f.kind==='catch'?f.size:''")
# dashboard: by 針 too
R("return [(multi?spOf(g).name+'：':'')+listName(g,k==='rig'?'rigs':'baits',id),v]", "return [(multi?spOf(g).name+'：':'')+((k==='skirt'&&!id?'なし':listName(g,k==='rig'?'rigs':k==='hook'?'hooks':k==='skirt'?'skirts':'baits',id))||'未選択'),v]")
R("if(gs.baitLabel||multi)bars(multi?'餌など別':`${gs.baitLabel}別`,grp('bait'));", "if(gs.baitLabel||multi)bars(multi?'餌など別':`${gs.baitLabel}別`,grp('bait'));if(gs.hookLabel)bars(`${gs.hookLabel}別`,grp('hook'));if(gs.skirtLabel&&c.some(e=>e.skirt))bars(`${gs.skirtLabel}別`,grp('skirt'));")
# anonymous data: the parts' names too
R("bait:e.bait||'',baitName:nm(g,'baits',e.bait),", "bait:e.bait||'',baitName:nm(g,'baits',e.bait),hook:e.hook||'',hookName:nm(g,'hooks',e.hook),skirt:e.skirt||'',skirtName:nm(g,'skirts',e.skirt),")

# ───────── registration tab: タイラバの部品 in place of テンヤ
R('<h2 class="sec-h" id="tenyaSec0">テンヤ</h2>\n  ${tenyaSectionHTML()}', '<h2 class="sec-h" id="tenyaSec0">タイラバ</h2>\n  ${tbPartsHTML()}')
TB = r'''
/* ---------- タイラバの部品（ヘッド・ネクタイ・針・スカート）：項目を分けて登録し、名前はそこから作る ---------- */
const TB_DL={hs:['丸型','ドロップ型','扁平型','スリム型'],hc:['オレンジ','赤','金','緑','ピンク','黒','グロー','チャート'],mk:['ダイワ','シマノ','ジャッカル','ハヤブサ','メジャークラフト','自作'],ts:['カーリー','ストレート','極細ストレート','ダブルカーリー','ワイド'],ks:['ラバー','シリコン','ティンセル入り'],tc:['オレンジ','赤','金','緑','ピンク','黒','グロー','チャート','オレンジ×金']};
let tbHookType='pkg';
/* スカートは付けない人も多いので「なし」を選べる。初期値は「なし」 */
function skirtChips(sel,act){const s=spOf(SOLO),l=(s.skirts||[]).filter(g=>!g.hidden);
  return `<div class="gearpick"><div class="gp-lbl">スカート<small class="muted">（任意）</small></div><div class="chips wrap"><button class="chip ${!sel?'on':''}" data-act="${act}" data-id="" aria-pressed="${!sel}">なし</button>${l.map(g=>`<button class="chip ${g.id===sel?'on':''}" data-act="${act}" data-id="${g.id}" aria-pressed="${g.id===sel}">${esc(g.name)}</button>`).join('')}<button class="chip add" data-act="goGear" aria-label="スカートを登録">＋</button></div></div>`}
const tbVal=id=>{const el=$('#'+id);return el?el.value.trim():''};
const tbDl=(id,k)=>`<datalist id="${id}">${TB_DL[k].map(x=>`<option value="${esc(x)}">`).join('')}</datalist>`;
function tbName(k,x){if(k==='rigs')return [x.g?x.g+'g':'',x.shape,x.color].filter(Boolean).join(' ')+(x.maker?`（${x.maker}）`:'');
  if(k==='baits'||k==='skirts')return [x.shape,x.color].filter(Boolean).join(' ');
  return x.type==='diy'?['自作',x.n?x.n+'本針':'',x.size?'針'+x.size:'',x.line?'糸'+x.line:''].filter(Boolean).join(' '):'市販 '+(x.pkg||'')}
function tbList(k){const s=spOf(SOLO),l=s[k]||[];return l.length?l.map(g=>`<div class="grow ${g.hidden?'hid':''}"><span class="tb-nm">${esc(g.name)}</span><button class="btn sm" data-act="itemHide" data-sp="${SOLO}" data-kind="${k}" data-id="${g.id}">${g.hidden?'表示する':'隠す'}</button><button class="btn sm" data-act="tbDel" data-kind="${k}" data-id="${g.id}">消す</button></div>`).join(''):'<p class="muted">まだありません。</p>'}
function tbPartsHTML(){const H=tbHookType;
  return `<div class="card" id="tbHeads"><h2>ヘッド</h2><p class="muted">重さ・形・色・メーカーを入れて登録します。記録では「80g 丸型 オレンジ（ダイワ）」のように出ます。</p>${tbList('rigs')}
   <div class="tb-form"><label class="field"><span>重さ（g）</span><input type="number" id="tbHg" inputmode="numeric" min="1" max="500" placeholder="例：80"></label>
    <label class="field"><span>形</span><input type="text" id="tbHs" list="tbHsL" placeholder="例：丸型">${tbDl('tbHsL','hs')}</label>
    <label class="field"><span>色</span><input type="text" id="tbHc" list="tbHcL" placeholder="例：オレンジ">${tbDl('tbHcL','hc')}</label>
    <label class="field"><span>メーカー</span><input type="text" id="tbHm" list="tbHmL" placeholder="例：ダイワ">${tbDl('tbHmL','mk')}</label></div>
   <button class="btn sm primary" data-act="tbAdd" data-kind="rigs">ヘッドを登録</button></div>
  <div class="card" id="tbTies"><h2>ネクタイ</h2><p class="muted">形と色を入れて登録します。</p>${tbList('baits')}
   <div class="tb-form"><label class="field"><span>形</span><input type="text" id="tbTs" list="tbTsL" placeholder="例：カーリー">${tbDl('tbTsL','ts')}</label>
    <label class="field"><span>色</span><input type="text" id="tbTc" list="tbTcL" placeholder="例：赤">${tbDl('tbTcL','tc')}</label></div>
   <button class="btn sm primary" data-act="tbAdd" data-kind="baits">ネクタイを登録</button></div>
  <div class="card" id="tbHooks"><h2>針</h2><p class="muted">市販の針（パッケージもの）は商品名を、自作の針は何本針か・針の号数・糸の号数を入れます。</p>${tbList('hooks')}
   <div class="seg" style="margin:8px 0"><button class="${H==='pkg'?'on':''}" data-act="tbHookType" data-d="pkg">市販品</button><button class="${H==='diy'?'on':''}" data-act="tbHookType" data-d="diy">自作</button></div>
   ${H==='pkg'?`<label class="field"><span>商品名</span><input type="text" id="tbPk" placeholder="例：紅牙 フックユニット 早掛けSS M"></label>`
    :`<div class="tb-form"><label class="field"><span>何本針</span><select id="tbN">${[1,2,3,4].map(n=>`<option value="${n}" ${n===2?'selected':''}>${n}本針</option>`).join('')}</select></label>
    <label class="field"><span>針の号数</span><input type="text" id="tbSz" placeholder="例：10号 / M"></label>
    <label class="field"><span>糸の号数</span><input type="text" id="tbLn" placeholder="例：5号"></label></div>`}
   <button class="btn sm primary" data-act="tbAdd" data-kind="hooks">針を登録</button></div>
  <div class="card" id="tbSkirts"><h2>スカート<small class="muted">（任意）</small></h2><p class="muted">使う人だけ登録してください。記録では「なし」も選べます。</p>${tbList('skirts')}
   <div class="tb-form"><label class="field"><span>素材・形</span><input type="text" id="tbKs" list="tbKsL" placeholder="例：ラバー">${tbDl('tbKsL','ks')}</label>
    <label class="field"><span>色</span><input type="text" id="tbKc" list="tbKcL" placeholder="例：オレンジ">${tbDl('tbKcL','tc')}</label></div>
   <button class="btn sm primary" data-act="tbAdd" data-kind="skirts">スカートを登録</button></div>`}
'''
TB_ACTS = r'''
Object.assign(acts,{
  tbHookType:b=>{tbHookType=b.dataset.d;render();setTimeout(()=>{const el=$('#tbHooks');if(el)el.scrollIntoView({block:'start'})},40)},
  tbAdd:b=>{const k=b.dataset.kind;let x;
    if(k==='rigs'){x={g:tbVal('tbHg'),shape:tbVal('tbHs'),color:tbVal('tbHc'),maker:tbVal('tbHm')};if(!x.g&&!x.color)return toast('重さか色を入れてください')}
    else if(k==='baits'){x={shape:tbVal('tbTs'),color:tbVal('tbTc')};if(!x.shape&&!x.color)return toast('形か色を入れてください')}
    else if(k==='skirts'){x={shape:tbVal('tbKs'),color:tbVal('tbKc')};if(!x.shape&&!x.color)return toast('素材か色を入れてください')}
    else if(tbHookType==='diy'){x={type:'diy',n:tbVal('tbN'),size:tbVal('tbSz'),line:tbVal('tbLn')};if(!x.size&&!x.line)return toast('針か糸の号数を入れてください')}
    else{x={type:'pkg',pkg:tbVal('tbPk')};if(!x.pkg)return toast('商品名を入れてください')}
    x.name=tbName(k,x);x.id=uid();const s=spOf(SOLO);s[k]=s[k]||[];if(s[k].some(g=>g.name===x.name&&!g.hidden))return toast(`「${x.name}」はもう登録されています`);
    s[k].push(x);cfgTouch();const sec={rigs:'tbHeads',baits:'tbTies',hooks:'tbHooks',skirts:'tbSkirts'}[k];render();setTimeout(()=>{const el=$('#'+sec);if(el)el.scrollIntoView({block:'start'})},40);toast(`「${x.name}」を登録しました`)},
  tbDel:b=>{if(b.dataset.armed!=='1'){b.dataset.armed='1';b.textContent='本当に？';return}const s=spOf(SOLO),k=b.dataset.kind;s[k]=(s[k]||[]).filter(g=>g.id!==b.dataset.id);cfgTouch();render()}});
'''
R("/* ---------- species & gear settings ---------- */", TB + "/* ---------- species & gear settings ---------- */")
R("/* ---------- boot ---------- */", TB_ACTS + "/* ---------- boot ---------- */")
R('.mapreg button{min-height:38px;font-size:14px}', '.mapreg button{min-height:38px;font-size:14px}.tb-form{display:grid;grid-template-columns:1fr 1fr;gap:8px 10px;margin:8px 0}.tb-nm{flex:1;min-width:0;font-weight:700}')

# ───────── nationwide spots, map and currents
R("const inArea=(x,a)=>{const k=spotArea(x);return !k||k===a};", "const inArea=(x,a)=>true;")
R("const seg=`<div class=\"seg areaseg\">", "const seg=AREAS.length<2?'':`<div class=\"seg areaseg\">")
R("const AREAS=[['tokyo','東京湾'],['osaka','大阪湾']];", "const AREAS=[];")
R("${(S.cfg.mig||{}).osaka1?'':`<button class=\"btn sm\" data-act=\"addOsaka\"", "${true?'':`<button class=\"btn sm\" data-act=\"addOsaka\"")
RX(r"function stOptions\(sel\)\{const G=\[.*?\];",
   "function stOptions(sel){const G=[['全国（北から）',Object.keys(ST_LL).filter(c=>TIDE.st[c]).sort((a,b)=>ST_LL[b][0]-ST_LL[a][0])]];", flags=re.S)
R("function inTokyoBay(lat,lon){return lat>35.12&&lat<35.72&&lon>139.6&&lon<140.15}", "function inTokyoBay(lat,lon){return false} // 全国：流れはどこでも Open-Meteo の海流")
R("wave:bay?r1n(avg(pick(m,'wave_height'))):null,noWave:!bay,", "wave:r1n(avg(pick(m,'wave_height'))),noWave:false,")
R("'※東京湾の外では、潮の向きと速さを Open-Meteo の海流データ（約8km四方の推算値）から出しています。'", "'※潮の向きと速さは、Open-Meteo の海流データ（約8km四方の推算値）から出しています。'")
R("const COAST_W='", "/* 全国（関東・大阪湾の範囲を除く。国土数値情報（行政区域）を加工、0.01度単位） */\nconst COAST_JP='" + coast_jp + "';\nconst COAST_W='")
R("for(const poly of (COAST+';'+COAST_W).split(';')){if(!poly)continue;const v=poly.split(',').map(Number);let x=0,y=0;const pts=[];\n    for(let i=0;i<v.length;i+=2){x+=v[i];y+=v[i+1];const [px,py]=toXY(x/1000,y/1000);",
  "for(const [src,div] of [[COAST,1000],[COAST_W,1000],[COAST_JP,100]])for(const poly of src.split(';')){if(!poly)continue;const v=poly.split(',').map(Number);let x=0,y=0;const pts=[];\n    for(let i=0;i<v.length;i+=2){x+=v[i];y+=v[i+1];const [px,py]=toXY(x/div,y/div);")
R("MAP_REG={bay:[139.8,35.42,62],sagami:[139.42,35.15,72],boso:[140.25,35.3,110],all:[139.9,35.55,160],osaka:[135.05,34.45,78]};",
  "MAP_REG={hokkaido:[142.8,43.4,620],tohoku:[140.6,39.3,560],kanto:[139.8,35.3,230],chubu:[137.4,35.6,420],kansai:[135.2,34.4,300],chushikoku:[133.0,34.0,480],kyushu:[130.6,32.4,520],okinawa:[127.4,26.3,520],all:[134.6,34.9,2000],bay:[139.8,35.42,62]};")
R("[['bay','東京湾'],['sagami','相模湾'],['boso','外房'],['all','関東'],['osaka','大阪湾']]",
  "[['all','全国'],['hokkaido','北海道'],['tohoku','東北'],['kanto','関東'],['chubu','中部'],['kansai','関西'],['chushikoku','中国・四国'],['kyushu','九州'],['okinawa','沖縄']]")
R('.mapreg button{min-height:38px;font-size:14px}', '.mapreg{display:flex;flex-wrap:wrap;gap:4px}.mapreg button{min-height:38px;font-size:14px;flex:1 0 22%}')
R("v.w=Math.min(190,Math.max(6,v.w))", "v.w=Math.min(2200,Math.max(6,v.w))")
R("const w=Math.min(190,Math.max(6,v.w*k))", "const w=Math.min(2200,Math.max(6,v.w*k))")
R("const w=Math.min(190,Math.max(6,pinch.v.w*pinch.d/d))", "const w=Math.min(2200,Math.max(6,pinch.v.w*pinch.d/d))")
R("<text x=\"${(x+u*1.6).toFixed(2)}\" y=\"${(y+u*1.1).toFixed(2)}\" font-size=\"${(u*2.6).toFixed(2)}\" class=\"m-stt\">${esc(TIDE.st[c].n)}</text>",
  "${v.w>400?'':`<text x=\"${(x+u*1.6).toFixed(2)}\" y=\"${(y+u*1.1).toFixed(2)}\" font-size=\"${(u*2.6).toFixed(2)}\" class=\"m-stt\">${esc(TIDE.st[c].n)}</text>`}")
R("else{const [lon,lat,w]=MAP_REG[ar==='osaka'?'osaka':'bay'];setViewLL(lon,lat,w)}", "else{const [lon,lat,w]=MAP_REG.all;setViewLL(lon,lat,w)}")
R("const pts=ed?[ed]:S.cfg.spots.filter(x=>spotArea(x)===ar).concat(base&&spotArea(base)===ar?[base]:[]);", "const pts=ed?[ed]:S.cfg.spots.concat(base?[base]:[]);")
R("const w=Math.max(34,(x1-x0)*1.5+12,((y1-y0)*1.4+14)/MAP_AR);", "const w=Math.min(1900,Math.max(34,(x1-x0)*1.5+12,((y1-y0)*1.4+14)/MAP_AR));")

# ───────── counts and dashboard: マダイ（枚）
RX(r"(catchesOf|nKind)\((t|tr),'tachiuo'", r"\1(\2,SOLO", 8)
R("x!=='tachiuo'", "x!==SOLO")
R("e.sp!=='tachiuo'", "e.sp!==SOLO", 2)
R("return best||'tachiuo'}", "return best||SOLO}")
R("sp:'tachiuo',g:{}", "sp:'madai',g:{}")
R("kpi(tot,'本','タチウオ合計')", "kpi(tot,'枚','マダイ合計')")
R("kpi(r1(tot/L.length),'本','1回あたり')", "kpi(r1(tot/L.length),'枚','1回あたり')")
R("kpi(hrs?r1(tot/hrs):0,'本','1時間あたり')", "kpi(hrs?r1(tot/hrs):0,'枚','1時間あたり')")
R("${kpi(N(best),'本','最高'", "${kpi(N(best),'枚','最高'")
R("${kpi(drag,'本','ドラゴン',tot?`全体の${Math.round(drag/tot*100)}%`:'')}${kpi(tai,'日','大漁（20本以上）',`${days.length}日中`)}", "")
R("<b>${v}本</b>", "<b>${v}枚</b>", 2)
R("length}本</b></button>", "length}枚</b></button>")
R("${rank('よく釣れたテンヤ',(t,e)=>e.rig&&tenyaOf(e.rig)?e.rig:'',k=>tenyaLabel(k),3,'tenView')}",
  "${rank('よく釣れたヘッド',(t,e)=>e.rig||'',k=>listName(SOLO,'rigs',k)||'（消した部品）')}${rank('よく釣れたネクタイ',(t,e)=>e.bait||'',k=>listName(SOLO,'baits',k)||'（消した部品）')}${rank('よく釣れた針',(t,e)=>e.hook||'',k=>listName(SOLO,'hooks',k)||'（消した部品）')}${rank('よく釣れたスカート',(t,e)=>e.skirt||'',k=>listName(SOLO,'skirts',k)||'（消した部品）')}")
R("よく釣れたテンヤ・釣り場・潮回りなどが出ます", "よく釣れたタイラバ・釣り場・潮回りなどが出ます")
R('<p class="eyebrow">TOOL 05 / DRAGON COUNTER</p><div class="hero-h"><h1>ドラゴンカウンター</h1>', '<p class="eyebrow">TOOL / TAIRABA COUNTER</p><div class="hero-h"><h1>タイラバカウンター</h1>')
R('タチウオの釣果を時間の経過と共に、テンヤ・潮・船の向きと一緒に記録する。', 'マダイの釣果を時間の経過と共に、タイラバ・潮・流れと一緒に記録する。')
RX(r'  <h2 class="sec-h">仕掛けと餌</h2>\n  <div class="card"><h2>仕掛け</h2>.*?\n  \$\{listCard\(sp,\'baits\',\'その他の餌（テンヤのとき）\'[^\n]*\n', '', flags=re.S)

R("tx(242,62,'本'", "tx(242,62,'枚'")
R("tx(268,84,'うちドラゴン 3'", "tx(268,84,'アタリ 5'")
R("tx(168,42,'使用テンヤ'", "tx(168,42,'タイラバ'")
R("tx(168,64,'SS AH ケイムラ'", "tx(168,64,'80g オレンジ'")
R("tx(196,116,'ドラゴン'", "tx(196,116,'針'")
R("tx(196,132,'120cm以上'", "tx(196,132,'自作 2本針'")
R('釣り場、船と自分の席、今日のテンヤのリストを選んで出船します。', '釣り場、船と自分の席、タイラバを選んで出船します。')
R('所有テンヤ・リスト', 'タイラバの部品')
R('時刻ごとの釣果・テンヤと餌・誘いと掛け方・潮・船の向き・記録した場所', '時刻ごとの釣果・タイラバ（ヘッド・ネクタイ・針）・潮・流れ・船の向き・記録した場所')
R('釣れる時間や潮・テンヤの傾向', '釣れる時間や潮・タイラバの傾向')

R('r="${(u*.9).toFixed(2)}" class="m-st"', 'r="${(u*(v.w>400?.3:.9)).toFixed(2)}" class="m-st"')
R('<rect x="-500" y="-500" width="2000" height="2000" class="m-sea"/>', '<rect x="-2500" y="-2000" width="5000" height="5000" class="m-sea"/>')
R("${rig?'・'+(tenyaLabel(rig)||''):''}）", "${rig?'・'+(tenyaLabel(rig)||listName(SOLO,'rigs',rig)||''):''}）", 2)

R('※本数は自分の席で釣れた分だけです', '※枚数は自分の席で釣れた分だけです', 2)

# ───────── words on screen
R("  {k:'ようこそ',t:'釣果を時間の経過と共に記録',d:'ドラゴンカウンターは、タチウオの釣果を時間の経過と共に、使ったテンヤ・潮・船の向きと一緒に記録するアプリです。釣果データは匿名で集めて傾向の分析に使います。使うことでこれに同意したものとします。'},",
  "  {k:'ようこそ',t:'釣果を時間の経過と共に記録',d:'タイラバカウンターは、マダイの釣果を時間の経過と共に、使ったタイラバ（ヘッド・ネクタイ・針）・潮・流れと一緒に記録するアプリです。全国どこの釣り場でも使えます。釣果データは匿名で集めて傾向の分析に使います。使うことでこれに同意したものとします。'},")
RX(r"  \{k:'準備',t:'所有テンヤを登録',d:'[^']*'\},",
   "  {k:'準備',t:'タイラバの部品を登録',d:'画面下の右端にある「登録」タブで、持っているヘッド（重さ・形・色・メーカー）、ネクタイ（形・色）、針（市販品は商品名、自作は何本針・針と糸の号数）を登録します。スカートは使う人だけ登録できます。竿・リール・糸も登録できます。'},")
RX(r"  \{k:'出船',t:'釣り場と席を選ぶ',d:'[^']*'\},",
   "  {k:'出船',t:'釣り場と席を選ぶ',d:'釣り場を選ぶだけで、潮回りと満潮・干潮、流れの向きと速さが自動で入ります。釣り場は全国の地図か現在地から登録できます。船と自分の席もタップで選びます。'},")
RX(r"  \{k:'釣れたら',t:'「釣れた」を1タップ',d:'[^']*'\},",
   "  {k:'釣れたら',t:'「釣れた」を1タップ',d:'「釣れた＋1」で、今使っているタイラバ（ヘッド・ネクタイ・針）と一緒に1枚記録します。部品を替えたら「タイラバ」のボタンから、替えた部品だけ選び直します（押しても記録はされません）。アタリ・バラシも同じように記録されます。押し間違えたら下の「直前の釣果を取り消し」。マダイ以外が掛かったら小さな「外道」ボタンから（枚数には入りません）。'},")

open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(s)
print('ok', len(s))
