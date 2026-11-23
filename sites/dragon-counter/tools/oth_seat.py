"""ほかの席の人の釣果（座席ごと）。オーナー指示 2026-11-23：「場所と時間と魚種とメモだけで良い」。

記録画面の「👥ほかの席」から、船の座席図で席を選び、魚種・メモを入れて記録する。時刻は押した時刻（直せる）、
場所はそのときのスマホの位置（📍と同じく自動。取れなければ無し）。自分の枚数には入らない。
保存先は釣行の tr.oth = [{id, side, seat, t, sp, memo, lat, lon, acc}]。履歴の釣行カードに席ごとの数を出す。

    apply(s, lay_default='both')
3つのカウンター共通（2026-11-23）：ドラゴンカウンターの public/index.html に一度だけ当てて保存済み（lay_default='both'）。
タイラバ・ティップランはそこから作る（ティップランは tipran_build.py で OTH_LAY を 'one' に）。ビルドでは呼ばない。
"""


def apply(s, lay_default='both'):
    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('oth_seat: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    js = r"""/* oth-seat v1：ほかの席の釣果 */
let othF=null;const OTH_LAY='""" + lay_default + r"""';
const othOf=tr=>(tr&&tr.oth)||[];
const othSeatTxt=(tr,o)=>seatShort({side:o.side,seat:o.seat,seats:tr.seats,lay:tr.lay||OTH_LAY});
function othSum(tr){const L=othOf(tr);if(!L.length)return '';const m={};L.forEach(o=>{const k=othSeatTxt(tr,o);m[k]=(m[k]||0)+1});
  return `<div class="oth-sum">👥 ほかの席 ${L.length}件：${Object.entries(m).map(([k,n])=>`${esc(k)} ${n}`).join('・')}</div>`}
function othSheet(){const f=othF,tr=f&&S.trips[f.tid];if(!tr)return;const lay=tr.lay||OTH_LAY,L=othOf(tr);
  const cnt={};L.forEach(o=>{const k=o.side+o.seat;cnt[k]=(cnt[k]||0)+1});
  const pf={seats:tr.seats||8,lay,side:lay==='one'?(tr.side||'R'):(f.side||tr.side||'R'),seat:f.seat||0};
  let svg=seatPickerSVG(pf).replace(/data-act="pickSeat"/g,'data-act="othSeat"');
  const n=pf.seats,x0=290,x1=46,xs=i=>n<2?x0:x0-(i-1)*(x0-x1)/(n-1);let tx='';
  for(const side of (lay==='one'?[pf.side]:['L','R']))for(let i=1;i<=n;i++){const c=cnt[side+i];if(c)tx+=`<text x="${r1(xs(i))}" y="${side==='L'?56:82}" text-anchor="middle" font-size="13" font-weight="800" style="fill:var(--catch,#e47b25)">${c}</text>`}
  if(tr.seat){const y=(tr.side||'R')==='L'?34:96;if(lay!=='one'||(tr.side||'R')===pf.side)tx+=`<text x="${r1(xs(tr.seat))}" y="${y+4}" text-anchor="middle" font-size="9" font-weight="800" style="fill:var(--teal)" pointer-events="none">自</text>`}
  svg=svg.replace('</svg>',tx+'</svg>');
  const sps=[spOf((tr.cur&&tr.cur.sp)||SOLO).name,...gedoNames().filter(x=>x!==spOf((tr.cur&&tr.cur.sp)||SOLO).name)];if(!f.sp)f.sp=sps[0];
  openSheet(`<div class="sheet-h"><h2>👥 ほかの席の釣果</h2><button class="btn sm ghost" data-act="closeSheet">閉じる</button></div>
   <p class="muted">ほかの人が釣ったら、その席を押して記録します（自分の枚数には入りません）。時刻と場所（スマホの位置）は自動で入ります。</p>
   <div class="field"><span>席${f.seat?`：<b>${esc(seatLabel({side:pf.side,seat:f.seat,seats:n,lay}))}</b>`:'（押して選ぶ）'}</span><div class="seatwrap oth-seat">${svg}</div></div>
   <div class="field"><span>魚種</span><div class="chips wrap">${sps.map(x=>`<button class="chip ${f.sp===x?'on':''}" data-act="othSp" data-d="${esc(x)}">${esc(x)}</button>`).join('')}</div></div>
   <div class="oth-g2"><label class="field"><span>時刻</span><input type="time" id="othT" value="${esc(f.t||'')}" placeholder="今"></label>
   <label class="field"><span>メモ（任意）</span><input type="text" id="othMemo" value="${esc(f.memo||'')}" placeholder="例：60cm・底から5m"></label></div>
   <button class="btn primary big" data-act="othAdd" ${f.seat?'':'disabled'}>${f.seat?'この席に1件記録':'席を選んでください'}</button>
   ${L.length?`<h3 class="oth-h">この日のほかの席（${L.length}件）</h3><div class="oth-list">${L.slice().sort((a,b)=>b.t-a.t).map(o=>`<div class="oth-r"><b>${hm(o.t)}</b><span>${esc(othSeatTxt(tr,o))}・${esc(o.sp)}${o.memo?`・${esc(o.memo)}`:''}${isFinite(o.lat)?' 📍':''}</span><button class="btn sm ghost" data-act="othDel" data-id="${o.id}">${f.armed===o.id?'本当に消す':'消す'}</button></div>`).join('')}</div>`:''}`,{kind:'oth'})}
function othKeep(){const m=$('#othMemo'),t=$('#othT');if(othF){if(m)othF.memo=m.value;if(t)othF.t=t.value}}
"""
    R("function photoIds(tr){", js + "function photoIds(tr){")
    R('aria-label="この釣行の写真">📷写真${photoIds(tr).length?`<small>${photoIds(tr).length}</small>`:\'\'}</button>',
      'aria-label="この釣行の写真">📷写真${photoIds(tr).length?`<small>${photoIds(tr).length}</small>`:\'\'}</button><button class="pill sm rm-loc" data-act="othOpen" data-id="${tr.id}" aria-label="ほかの席の釣果">👥ほかの席${othOf(tr).length?`<small>${othOf(tr).length}</small>`:\'\'}</button>')
    R("  pickSeat:b=>{",
      "  othOpen:b=>{othF={tid:b.dataset.id||(active()&&active().id),side:'',seat:0,sp:'',memo:'',t:''};othSheet()},\n"
      "  othSeat:b=>{othKeep();othF.side=b.dataset.side;othF.seat=+b.dataset.i;othSheet()},\n"
      "  othSp:b=>{othKeep();othF.sp=b.dataset.d;othSheet()},\n"
      "  othAdd:()=>{othKeep();const f=othF,tr=f&&S.trips[f.tid];if(!tr||!f.seat)return;let t=Date.now();if(f.t){const [h,m]=f.t.split(':').map(Number),d=new Date(tr.date+'T00:00:00');d.setHours(h,m,0,0);t=d.getTime()}\n"
      "    const lay=tr.lay||OTH_LAY,o={id:uid(),side:lay==='one'?(tr.side||'R'):f.side,seat:f.seat,t,sp:f.sp,memo:(f.memo||'').trim()};(tr.oth=tr.oth||[]).push(o);touch(tr);buzz();\n"
      "    if(navigator.geolocation&&S.prefs.catchLoc!==false&&!f.t)navigator.geolocation.getCurrentPosition(pos=>{o.lat=+pos.coords.latitude.toFixed(6);o.lon=+pos.coords.longitude.toFixed(6);o.acc=Math.round(pos.coords.accuracy||0);touch(tr)},()=>{},{enableHighAccuracy:true,timeout:15000,maximumAge:5000});\n"
      "    toast(`${hm(t)} ${othSeatTxt(tr,o)}の${o.sp}を記録しました`);f.memo='';f.t='';f.armed=null;othSheet();render()},\n"
      "  othDel:b=>{othKeep();const f=othF,tr=f&&S.trips[f.tid];if(!tr)return;if(f.armed!==b.dataset.id){f.armed=b.dataset.id;return othSheet()}tr.oth=othOf(tr).filter(o=>o.id!==b.dataset.id);f.armed=null;touch(tr);othSheet();render()},\n"
      "  pickSeat:b=>{")
    # 履歴の釣行カード
    R("const memoHTML=t=>(t.memo||'').trim()?`<div class=\"memo-box\">📝 ${esc(t.memo.trim()).replace(/\\n/g,'<br>')}</div>`:'';",
      "const memoHTML=t=>othSum(t)+((t.memo||'').trim()?`<div class=\"memo-box\">📝 ${esc(t.memo.trim()).replace(/\\n/g,'<br>')}</div>`:'');")
    R("</style>", ".oth-seat svg{width:100%;height:auto}.oth-h{font-size:16px;margin:18px 0 6px}.oth-list{display:flex;flex-direction:column;gap:6px}"
      ".oth-r{display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--line);border-radius:10px}.oth-r span{flex:1;min-width:0;font-size:14px}"
      ".oth-sum{font-size:13px;color:var(--muted);margin:4px 0}.oth-g2{display:grid;grid-template-columns:1fr 1.6fr;gap:10px}</style>")
    return s
