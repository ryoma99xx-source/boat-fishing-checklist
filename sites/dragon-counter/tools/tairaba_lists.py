"""タイラバカウンター：針は任意（「なし」を選べる）、ヘッドとネクタイの「リスト」（一軍リストなど）。オーナー指示 2026-11-22。

  - 針：出船の準備・タイラバを替える画面で「なし」を選べる。最初から針を選んだ状態にはしない。
  - リスト：登録タブのヘッド・ネクタイの欄で、名前付きのリストをいくつでも作れる（S.cfg.tbl = {rigs:[{id,name,items}], baits:[…]}）。
    出船の準備でヘッドとネクタイのリストをそれぞれ選ぶと（f.lst → tr.lst）、その日の選択肢はリストのものが先に並び、
    リストにないものは「ほかの…」を開くと選べる。記録の中身は変わらない。
tairaba_build.py が、ティップランの元になる版を書いたあとで当てる。
"""
import re

MARK = '/* tairaba-lists v1 */'


def apply(s):
    if MARK in s:
        return s

    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('tairaba_lists: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    # ── 針は任意
    R("hook:pf.hook||firstVis(sp,'hooks')", "hook:pf.hook||''")
    R("if(!g.hook)g.hook=firstVis(sp,'hooks');", "")
    R("chipsHTML(sp,'rigs',g.rig,'fRig')+chipsHTML(sp,'hooks',g.hook,'fHook')",
      "lstPick(f,'rigs')+chipsL(sp,'rigs',g.rig,'fRig',(f.lst||{}).rigs)+optChips('hooks',g.hook,'fHook')")
    R("chipsHTML(sp,'baits',g.bait,'fBait')", "lstPick(f,'baits')+chipsL(sp,'baits',g.bait,'fBait',(f.lst||{}).baits)")
    R("chipsHTML(sp,'rigs',g.rig,'setRigK')+chipsHTML(sp,'baits',g.bait,'setBaitK')+chipsHTML(sp,'hooks',g.hook,'setHookK')",
      "chipsL(sp,'rigs',g.rig,'setRigK',(tr.lst||{}).rigs)+chipsL(sp,'baits',g.bait,'setBaitK',(tr.lst||{}).baits)+optChips('hooks',g.hook,'setHookK')")
    R("<span>針</span><b>${esc(listName(sp,'hooks',g.hook)||'未登録')}</b>", "<span>針</span><b>${esc(listName(sp,'hooks',g.hook)||'なし')}</b>")
    R('<div class="card" id="tbHooks"><h2>針</h2>', '<div class="card" id="tbHooks"><h2>針<small class="muted">（任意）</small></h2>')

    # ── リスト：登録タブ
    R('data-kind="rigs">ヘッドを登録</button></div>', 'data-kind="rigs">ヘッドを登録</button>${tblHTML(\'rigs\')}</div>')
    R('data-kind="baits">ネクタイを登録</button></div>', 'data-kind="baits">ネクタイを登録</button>${tblHTML(\'baits\')}</div>')
    # 出船：選んだリストを釣行に残す
    R("cur:{sp:f.sp,g:{[f.sp]:cg}},memo:", "cur:{sp:f.sp,g:{[f.sp]:cg}},...(f.lst?{lst:{...f.lst}}:{}),memo:")
    R("  fRig:b=>{fGear(startDraft,startDraft.sp).rig=b.dataset.id;$('#fGear').innerHTML=fGearHTML(startDraft)},",
      "  fRig:b=>{fGear(startDraft,startDraft.sp).rig=b.dataset.id;$('#fGear').innerHTML=fGearHTML(startDraft)},\n"
      "  fLst:b=>{const f=startDraft,k=b.dataset.k,id=b.dataset.id;f.lst={...(f.lst||{}),[k]:id};S.prefs.lst={...(S.prefs.lst||{}),[k]:id};"
      "const L=TBL()[k].find(x=>x.id===id),g=fGear(f,f.sp),key=k==='rigs'?'rig':'bait';if(L){const ok=L.items.filter(i=>(spOf(SOLO)[k]||[]).some(x=>x.id===i&&!x.hidden));if(ok.length&&!ok.includes(g[key]))g[key]=ok[0]}"
      "$('#fGear').innerHTML=fGearHTML(f)},\n"
      "  tblAdd:b=>{const k=b.dataset.k,L=TBL()[k];L.push({id:'tl'+uid(),name:k==='rigs'?(L.length?'ヘッドのリスト'+(L.length+1):'一軍'):(L.length?'ネクタイのリスト'+(L.length+1):'一軍'),items:[]});cfgTouch();render()},\n"
      "  tblDel:b=>{const k=b.dataset.k;if(!b.classList.contains('armed')){b.classList.add('armed');b.textContent='もう一度押すと消します';setTimeout(()=>{b.classList.remove('armed');b.textContent='リストを消す'},3000);return}"
      "TBL()[k]=TBL()[k].filter(x=>x.id!==b.dataset.l);cfgTouch();render()},\n"
      "  tblTog:b=>{const L=TBL()[b.dataset.k].find(x=>x.id===b.dataset.l);if(!L)return;const id=b.dataset.id,i=L.items.indexOf(id);if(i>=0)L.items.splice(i,1);else L.items.push(id);cfgTouch();"
      "b.classList.toggle('on',i<0);b.setAttribute('aria-pressed',String(i<0));const n=b.closest('.tbl-card');if(n){const c=n.querySelector('.tbl-n');if(c)c.textContent=L.items.length+'件'}},")

    js = MARK + r"""
/* ヘッド・ネクタイのリスト（一軍リストなど）。S.cfg.tbl = {rigs:[{id,name,items:[]}], baits:[…]} */
function TBL(){const c=S.cfg;c.tbl=c.tbl||{};c.tbl.rigs=c.tbl.rigs||[];c.tbl.baits=c.tbl.baits||[];return c.tbl}
const tblLabel=k=>k==='rigs'?'ヘッド':'ネクタイ';
function tblHTML(k){const s=spOf(SOLO),own=(s[k]||[]).filter(g=>!g.hidden),L=TBL()[k],W=tblLabel(k);
  return `<div class="tbl" id="tbl-${k}"><h3 class="tk-g">${W}のリスト<small class="muted">（任意）</small></h3><p class="muted">「一軍」「深場用」のように${W}の組み合わせを作っておくと、出船のときにリストを選んで、その${W}だけを並べられます。リストにない${W}も「ほかの${W}」から選べます。</p>
   ${L.map(l=>`<div class="tbl-card"><div class="grow"><input type="text" data-tbl="${k}" data-l="${l.id}" value="${esc(l.name)}" aria-label="リストの名前"><span class="tbl-n muted">${l.items.length}件</span><button class="btn sm danger" data-act="tblDel" data-k="${k}" data-l="${l.id}">リストを消す</button></div>
     <div class="chips wrap tbl-items">${own.map(g=>{const on=l.items.includes(g.id);return `<button class="chip ${on?'on':''}" data-act="tblTog" data-k="${k}" data-l="${l.id}" data-id="${g.id}" aria-pressed="${on}">${gph(g.id,'ch')}${esc(g.name)}</button>`}).join('')||`<span class="muted">先に${W}を登録してください</span>`}</div></div>`).join('')}
   <button class="btn sm" data-act="tblAdd" data-k="${k}">＋ ${W}のリストを作る</button></div>`}
/* 出船の準備：リストを選ぶ */
function lstPick(f,k){const L=TBL()[k].filter(l=>l.items.length);if(!L.length)return `<div class="gearpick lstpick"><button class="golink" data-act="goSec" data-sec="tbl-${k}">${tblLabel(k)}の一軍リストを作る →</button></div>`;const cur=(f.lst||{})[k]||'';
  return `<div class="gearpick lstpick"><div class="gp-lbl">${tblLabel(k)}のリスト</div><div class="chips wrap"><button class="chip ${!cur?'on':''}" data-act="fLst" data-k="${k}" data-id="">すべて</button>${L.map(l=>`<button class="chip ${cur===l.id?'on':''}" data-act="fLst" data-k="${k}" data-id="${l.id}">${esc(l.name)}</button>`).join('')}</div></div>`}
/* リストのものを先に、ほかは「ほかの…」の中に */
function chipsL(sp,k,sel,act,lid){const s=spOf(sp),label=k==='rigs'?s.rigLabel:s.baitLabel;if(!label)return '';
  const all=(s[k]||[]).filter(g=>!g.hidden),L=lid?TBL()[k].find(l=>l.id===lid):null;
  const main=L&&L.items.length?L.items.map(id=>all.find(g=>g.id===id)).filter(Boolean):all,rest=L&&L.items.length?all.filter(g=>!L.items.includes(g.id)):[];
  const chip=g=>`<button class="chip ${g.id===sel?'on':''}" data-act="${act}" data-id="${g.id}" aria-pressed="${g.id===sel}">${gph(g.id,'ch')}${esc(g.name)}</button>`;
  return `<div class="gearpick"><div class="gp-lbl">${esc(label)}${L?`<small class="muted">（${esc(L.name)}）</small>`:''}</div><div class="chips wrap">${main.map(chip).join('')}<button class="chip add" data-act="goGear" aria-label="${esc(label)}を登録">＋</button></div>`
   +(rest.length?`<details class="tbl-more"${rest.some(g=>g.id===sel)?' open':''}><summary>ほかの${esc(label)}（${rest.length}）</summary><div class="chips wrap">${rest.map(chip).join('')}</div></details>`:'')+`</div>`}
/* 針など、任意のもの：「なし」を選べる */
function optChips(k,sel,act){const s=spOf(SOLO),label=k==='hooks'?s.hookLabel:k,l=(s[k]||[]).filter(g=>!g.hidden);
  return `<div class="gearpick"><div class="gp-lbl">${esc(label)}<small class="muted">（任意）</small></div><div class="chips wrap"><button class="chip ${!sel?'on':''}" data-act="${act}" data-id="" aria-pressed="${!sel}">なし</button>${l.map(g=>`<button class="chip ${g.id===sel?'on':''}" data-act="${act}" data-id="${g.id}" aria-pressed="${g.id===sel}">${gph(g.id,'ch')}${esc(g.name)}</button>`).join('')}<button class="chip add" data-act="goGear" aria-label="${esc(label)}を登録">＋</button></div></div>`}
document.addEventListener('change',e=>{const t=e.target;if(!t||!t.dataset||!t.dataset.tbl)return;const L=TBL()[t.dataset.tbl].find(x=>x.id===t.dataset.l);if(!L)return;L.name=t.value.trim()||L.name;cfgTouch()});
"""
    R("function skirtChips(sel,act){", js + "function skirtChips(sel,act){")
    # 前回選んだリストを、次の出船の準備でも選んだ状態に
    R("function newForm(){return fixPeople(newForm0())}",
      "function newForm(){const f=fixPeople(newForm0());const p=S.prefs.lst||{},ok={};for(const k of ['rigs','baits'])if(p[k]&&TBL()[k].some(l=>l.id===p[k]&&l.items.length))ok[k]=p[k];if(Object.keys(ok).length)f.lst=ok;return f}")
    R(".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}",
      ".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}\n"
      ".tbl{margin-top:14px;border-top:1px solid var(--line);padding-top:10px;scroll-margin-top:96px}.tbl-card{border:1px solid var(--line);border-radius:12px;padding:10px;margin:8px 0}.tbl-card .grow{display:flex;gap:8px;align-items:center}.tbl-card .grow input{flex:1;min-width:0}.tbl-n{flex:none;font-size:13px}"
      ".tbl-items .chip{max-width:100%;white-space:normal;text-align:left;line-height:1.35;display:inline-flex;align-items:center;overflow-wrap:anywhere}"
      ".tbl-more{margin-top:6px}.tbl-more summary{cursor:pointer;color:var(--muted);font-size:14px;padding:6px 0}")
    # チュートリアル
    R("、針（市販品は商品名、自作は何本針・針と糸の号数）を登録します。スカートは使う人だけ登録できます。竿・リール・糸も登録できます。'}",
      "を登録します。針とスカートは任意です（記録では「なし」も選べます）。よく使うヘッドとネクタイは、それぞれ「一軍」などのリストにまとめておくと、出船のときにリストを選んで、その日の分だけ並べられます。竿・リール・糸も登録できます。'}")
    R("船と自分の席もタップで選びます。'},", "船を選ぶと、その船の片舷／両舷と人数が入ります（当日に合わせて変えられます）。自分の席もタップで選びます。その日に使うヘッド・ネクタイのリストもここで選びます。'},")
    # 一軍リストを作る画面（出船の準備のリンクから開く）。tools/tbl_focus.py
    import tbl_focus
    s = tbl_focus.apply(s, ['rigs', 'baits'], 'ヘッド・ネクタイ')
    return s
