"""ティップランカウンター：エギのリスト（一軍リストなど）。オーナー指示 2026-11-22。タイラバカウンター（tairaba_lists.py）と同じ考え方。

  登録タブのエギの欄で、名前付きのリストをいくつでも作れる（S.cfg.tbl.rigs = [{id,name,items}]）。
  出船の準備でエギのリストを選ぶと（f.lst → tr.lst）、その日はリストのエギが先に並び、リストにないエギは「ほかのエギ」から選べる。
  号数の絞り込みは、リストと一緒に使える。シンカーはリストなし。
tipran_build.py の最後に apply() を通す。
"""

MARK = '/* tipran-lists v1 */'


def apply(s):
    if MARK in s:
        return s

    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('tipran_lists: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    # 選ぶところ：リストのエギを先に、ほかは「ほかのエギ」に（号数の絞り込みはそのまま効く）
    R("""function chipsHTML(sp,k,sel,act){const s=spOf(sp);const label=k==='rigs'?s.rigLabel:k==='hooks'?s.hookLabel:s.baitLabel;if(!label)return '';
  return `<div class="gearpick"><div class="gp-lbl">${esc(label)}</div>${k==='rigs'?rigZRow(s[k]):''}<div class="chips wrap">${(s[k]||[]).filter(g=>!g.hidden).map(g=>
  `<button class="chip ${g.id===sel?'on':''}" data-act="${act}" data-id="${g.id}"${k==='rigs'?` data-z="${esc(g.shape||'')}"`:''} aria-pressed="${g.id===sel}">${k==='rigs'?eimg(egiIm(g),'ch'):''}${gph(g.id,'ch')}${esc(g.name)}</button>`).join('')}<button class="chip add" data-act="goGear" aria-label="${esc(label)}を登録">＋</button></div></div>`}""",
      """function chipsHTML(sp,k,sel,act,lid){const s=spOf(sp);const label=k==='rigs'?s.rigLabel:k==='hooks'?s.hookLabel:s.baitLabel;if(!label)return '';
  const all=(s[k]||[]).filter(g=>!g.hidden),L=k==='rigs'&&lid?TBL().rigs.find(l=>l.id===lid):null,on=L&&L.items.length;
  const main=on?L.items.map(id=>all.find(g=>g.id===id)).filter(Boolean):all,rest=on?all.filter(g=>!L.items.includes(g.id)):[];
  const chip=g=>`<button class="chip ${g.id===sel?'on':''}" data-act="${act}" data-id="${g.id}"${k==='rigs'?` data-z="${esc(g.shape||'')}"`:''} aria-pressed="${g.id===sel}">${k==='rigs'?eimg(egiIm(g),'ch'):''}${gph(g.id,'ch')}${esc(g.name)}</button>`;
  return `<div class="gearpick"><div class="gp-lbl">${esc(label)}${on?`<small class="muted">（${esc(L.name)}）</small>`:''}</div>${k==='rigs'?rigZRow(all):''}<div class="chips wrap">${main.map(chip).join('')}<button class="chip add" data-act="goGear" aria-label="${esc(label)}を登録">＋</button></div>`
   +(rest.length?`<details class="tbl-more"${rest.some(g=>g.id===sel)?' open':''}><summary>ほかの${esc(label)}（${rest.length}）</summary><div class="chips wrap">${rest.map(chip).join('')}</div></details>`:'')+`</div>`}""")
    R("chipsHTML(sp,'rigs',g.rig,'fRig')", "lstPick(f,'rigs')+chipsHTML(sp,'rigs',g.rig,'fRig',(f.lst||{}).rigs)")
    R("chipsHTML(sp,'rigs',g.rig,'setRigK')", "chipsHTML(sp,'rigs',g.rig,'setRigK',(tr.lst||{}).rigs)")
    # 登録タブ・出船・前回のリスト
    R('data-kind="rigs">エギを登録</button></div>', 'data-kind="rigs">エギを登録</button>${tblHTML(\'rigs\')}</div>')
    R("cur:{sp:f.sp,g:{[f.sp]:cg}},memo:", "cur:{sp:f.sp,g:{[f.sp]:cg}},...(f.lst?{lst:{...f.lst}}:{}),memo:")
    R("function newForm(){return fixPeople(newForm0())}",
      "function newForm(){const f=fixPeople(newForm0());const p=(S.prefs.lst||{}).rigs;if(p&&TBL().rigs.some(l=>l.id===p&&l.items.length))f.lst={rigs:p};return f}")
    R("  fRig:b=>{fGear(startDraft,startDraft.sp).rig=b.dataset.id;$('#fGear').innerHTML=fGearHTML(startDraft)},",
      "  fRig:b=>{fGear(startDraft,startDraft.sp).rig=b.dataset.id;$('#fGear').innerHTML=fGearHTML(startDraft)},\n"
      "  fLst:b=>{const f=startDraft,k=b.dataset.k,id=b.dataset.id;f.lst={...(f.lst||{}),[k]:id};S.prefs.lst={...(S.prefs.lst||{}),[k]:id};"
      "const L=TBL()[k].find(x=>x.id===id),g=fGear(f,f.sp);if(L){const ok=L.items.filter(i=>(spOf(SOLO)[k]||[]).some(x=>x.id===i&&!x.hidden));if(ok.length&&!ok.includes(g.rig))g.rig=ok[0]}"
      "$('#fGear').innerHTML=fGearHTML(f)},\n"
      "  tblAdd:b=>{const k=b.dataset.k,L=TBL()[k];L.push({id:'tl'+uid(),name:L.length?'エギのリスト'+(L.length+1):'一軍',items:[]});cfgTouch();render()},\n"
      "  tblDel:b=>{const k=b.dataset.k;if(!b.classList.contains('armed')){b.classList.add('armed');b.textContent='もう一度押すと消します';setTimeout(()=>{b.classList.remove('armed');b.textContent='リストを消す'},3000);return}"
      "TBL()[k]=TBL()[k].filter(x=>x.id!==b.dataset.l);cfgTouch();render()},\n"
      "  tblTog:b=>{const L=TBL()[b.dataset.k].find(x=>x.id===b.dataset.l);if(!L)return;const id=b.dataset.id,i=L.items.indexOf(id);if(i>=0)L.items.splice(i,1);else L.items.push(id);cfgTouch();"
      "b.classList.toggle('on',i<0);b.setAttribute('aria-pressed',String(i<0));const n=b.closest('.tbl-card');if(n){const c=n.querySelector('.tbl-n');if(c)c.textContent=L.items.length+'件'}},")
    js = MARK + r"""
/* エギのリスト（一軍リストなど）。S.cfg.tbl.rigs = [{id,name,items:[]}] */
function TBL(){const c=S.cfg;c.tbl=c.tbl||{};c.tbl.rigs=c.tbl.rigs||[];return c.tbl}
function tblHTML(k){const s=spOf(SOLO),own=(s[k]||[]).filter(g=>!g.hidden),L=TBL()[k],W='エギ';
  return `<div class="tbl" id="tbl-${k}"><h3 class="tk-g">${W}のリスト<small class="muted">（任意）</small></h3><p class="muted">「一軍」「濁り用」のようにエギの組み合わせを作っておくと、出船のときにリストを選んで、そのエギだけを並べられます。リストにないエギも「ほかのエギ」から選べます。</p>
   ${L.map(l=>`<div class="tbl-card"><div class="grow"><input type="text" data-tbl="${k}" data-l="${l.id}" value="${esc(l.name)}" aria-label="リストの名前"><span class="tbl-n muted">${l.items.length}件</span><button class="btn sm danger" data-act="tblDel" data-k="${k}" data-l="${l.id}">リストを消す</button></div>
     <div class="chips wrap tbl-items">${own.map(g=>{const on=l.items.includes(g.id);return `<button class="chip ${on?'on':''}" data-act="tblTog" data-k="${k}" data-l="${l.id}" data-id="${g.id}" aria-pressed="${on}">${eimg(egiIm(g),'ch')}${gph(g.id,'ch')}${esc(g.name)}</button>`}).join('')||`<span class="muted">先にエギを登録してください</span>`}</div></div>`).join('')}
   <button class="btn sm" data-act="tblAdd" data-k="${k}">＋ エギのリストを作る</button></div>`}
/* 出船の準備：リストを選ぶ（まだ無ければ、作る場所へのリンク） */
function lstPick(f,k){const L=TBL()[k].filter(l=>l.items.length);if(!L.length)return `<div class="gearpick lstpick"><button class="golink" data-act="goSec" data-sec="tbl-${k}">エギの一軍リストを作る →</button></div>`;const cur=(f.lst||{})[k]||'';
  return `<div class="gearpick lstpick"><div class="gp-lbl">エギのリスト</div><div class="chips wrap"><button class="chip ${!cur?'on':''}" data-act="fLst" data-k="${k}" data-id="">すべて</button>${L.map(l=>`<button class="chip ${cur===l.id?'on':''}" data-act="fLst" data-k="${k}" data-id="${l.id}">${esc(l.name)}</button>`).join('')}</div></div>`}
document.addEventListener('change',e=>{const t=e.target;if(!t||!t.dataset||!t.dataset.tbl)return;const L=TBL()[t.dataset.tbl].find(x=>x.id===t.dataset.l);if(!L)return;L.name=t.value.trim()||L.name;cfgTouch()});
"""
    R("function rigZRow(l){", js + "function rigZRow(l){")
    R(".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}",
      ".timg.cur{grid-column:1;grid-row:1;width:34px;height:26px}\n"
      ".tbl{margin-top:14px;border-top:1px solid var(--line);padding-top:10px;scroll-margin-top:96px}.tbl-card{border:1px solid var(--line);border-radius:12px;padding:10px;margin:8px 0}.tbl-card .grow{display:flex;gap:8px;align-items:center}.tbl-card .grow input{flex:1;min-width:0}.tbl-n{flex:none;font-size:13px}"
      ".tbl-items .chip{max-width:100%;white-space:normal;text-align:left;line-height:1.35;display:inline-flex;align-items:center;overflow-wrap:anywhere}"
      ".tbl-more{margin-top:6px}.tbl-more summary{cursor:pointer;color:var(--muted);font-size:14px;padding:6px 0}")
    R("gp.querySelectorAll('.chips [data-z]').forEach(c=>c.hidden=!!z&&c.dataset.z!==z)}",
      "gp.querySelectorAll('.chips [data-z]').forEach(c=>c.hidden=!!z&&c.dataset.z!==z);const d=gp.querySelector('details.tbl-more');if(d&&z&&d.querySelector('[data-z=\"'+z+'\"]'))d.open=true}")
    # チュートリアル
    R("持っているエギ（メーカー・号数・重さ・色）と、使うシンカーの重さを登録します。竿・リール・糸も登録できます。'}",
      "持っているエギ（メーカー・号数・重さ・色）と、使うシンカーの重さを登録します。よく使うエギは「一軍」などのリストにまとめておくと、出船のときにリストを選んで、その日の分だけ並べられます。竿・リール・糸も登録できます。'}")
    R("船と自分の席もタップで選びます。'},", "船と自分の席もタップで選びます。その日に使うエギのリストもここで選びます。'},")
    return s
