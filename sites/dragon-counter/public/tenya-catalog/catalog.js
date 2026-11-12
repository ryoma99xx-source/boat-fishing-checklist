/* テンヤカタログの絞り込み・検索・釣れ筋・ランキング。
   ツール版のページ（/tenya-catalog/）と cutlassfish.tokyo の記事（プラグイン cutlassfish-tenya-catalog が読み込む）で同じものを使う。
   絞り込みと検索は、ドラゴンカウンターのカタログと同じ決まり：
   - 号数（全号数・30・40・50号）、すべて／新商品だけ（発売予定と、2か月以内にカタログに入ったもの）、メーカー
   - 素材：すべて／タングステン（TG）だけ（製品の data-tg）
   - 検索は空白で区切った語をすべて含むもの。数字だけ（「40」「40号」）は号数。ひらがなはカタカナと同じに扱う
   ページ側の印：[data-tcat] の中に [data-tcat-bar]（ここに操作部品を作る）・[data-tcat-cnt]、製品 [data-tcat-p]、色 [data-tcat-c]、
   メーカーのまとまり [data-tcat-mkb]、釣れ筋 [data-tcat-ts]、ランキング [data-tcat-rank]。 */
(()=>{
const root=document.querySelector('[data-tcat]');if(!root)return;
const RANK=/(^|\.)cutlassfish\.tokyo$/.test(location.hostname)&&location.hostname!=='dragon-counter.cutlassfish.tokyo'?'https://dragon-counter.cutlassfish.tokyo/tenya-rank.php':'/tenya-rank.php';   // 記事（cutlassfish.tokyo）からはアプリのサーバーへ
const $$=(s,el)=>[...(el||document).querySelectorAll(s)];
const normQ=x=>String(x||'').normalize('NFKC').toLowerCase().replace(/[ぁ-ゖ]/g,c=>String.fromCharCode(c.charCodeAt(0)+0x60));
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const NEW_MS=60*864e5;
const isNew=f=>(f.dataset.st||'').includes('発売予定')||(f.dataset.a&&Date.now()-new Date(f.dataset.a).getTime()<NEW_MS);
const st={z:'',only:'',tg:'',m:'',q:''};
const show=(el,on)=>{el.hidden=!on;el.style.display=on?'':'none'};

/* 色：置かれたページの地の色が暗ければ暗い配色、明るければ明るい配色（ページが --tcat-* を決めていればそれを使う） */
const isDark=(()=>{for(let el=root;el;el=el.parentElement){const m=getComputedStyle(el).backgroundColor.match(/[\d.]+/g);if(!m||(m.length>3&&+m[3]<.5))continue;
    return (.299*m[0]+.587*m[1]+.114*m[2])<128}return false})();
const C=isDark?{bg:'rgba(6,10,17,.96)',line:'#1f2d42',chip:'#0b1422',field:'#101c2e',ink:'#eef3f8',muted:'#9cabbd'}
             :{bg:'rgba(255,255,255,.97)',line:'#c9d1db',chip:'#fff',field:'#fff',ink:'#222',muted:'#667'};
const css=document.createElement('style');css.textContent=`
.tcat-bar{position:sticky;top:0;z-index:20;background:var(--tcat-bg,${C.bg});border-bottom:1px solid var(--tcat-line,${C.line});padding:10px 0;margin:0 0 10px}
.tcat-seg{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 8px}
.tcat-seg button{min-height:38px;padding:4px 14px;border-radius:999px;border:1px solid var(--tcat-line,${C.line});background:var(--tcat-chip,${C.chip});color:var(--tcat-ink,${C.ink});font:inherit;font-size:14px;cursor:pointer}
.tcat-seg button.on{background:var(--tcat-on,#41c9c6);border-color:var(--tcat-on,#41c9c6);color:var(--tcat-on-ink,#03161c);font-weight:700}
.tcat-row{display:flex;gap:8px;flex-wrap:wrap}
.tcat-row select,.tcat-q input{min-height:42px;border-radius:10px;border:1px solid var(--tcat-line,${C.line});background:var(--tcat-field,${C.field});color:var(--tcat-ink,${C.ink});font:inherit;font-size:16px;padding:6px 10px}
.tcat-row select{flex:1 1 160px;min-width:0}
.tcat-q{position:relative;flex:2 1 220px;min-width:0}.tcat-q input{width:100%;box-sizing:border-box;padding-right:40px}
.tcat-q button{position:absolute;right:4px;top:50%;transform:translateY(-50%);width:34px;height:34px;border:0;background:none;color:var(--tcat-muted,${C.muted});font-size:20px;cursor:pointer}
.tcat-cnt{font-size:13px;color:var(--tcat-muted,${C.muted});margin:6px 0 0}.tcat-help{font-size:13px;color:var(--tcat-muted,${C.muted});margin:4px 0 0}
.tcat-none{padding:16px;text-align:center;color:var(--tcat-muted,${C.muted})}
[data-tcat-c].tcat-ts{border:3px solid #e3a43b!important;position:relative}
[data-tcat-c].tcat-ts::before{content:"釣れ筋";position:absolute;top:6px;left:6px;z-index:1;background:#e3a43b;color:#1a1200;font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px}
[data-tcat-c].tcat-hit{outline:3px solid #e3a43b;outline-offset:2px}
.tcat-tsc{display:grid;grid-template-columns:minmax(100px,140px) 1fr;gap:12px;align-items:start;padding:10px 0;border-top:1px solid var(--tcat-ts-line,${C.line})}.tcat-tsc:first-child{border-top:0}
.tcat-tsc img{display:block;width:100%;height:auto;aspect-ratio:4/3;object-fit:contain;background:#fff;border-radius:8px;border:2px solid #e3a43b}
.tcat-tsl{margin-top:8px;display:flex;flex-wrap:wrap;gap:6px}.tcat-tsc small{color:var(--tcat-muted,${C.muted})}
[data-tcat-rank] ol{list-style:none;margin:0;padding:0;counter-reset:r}[data-tcat-rank] li{counter-increment:r;margin:0}
[data-tcat-rank] li a{display:grid;grid-template-columns:28px 64px 1fr;gap:8px;align-items:center;text-decoration:none;color:inherit;padding:6px 0;border-top:1px solid var(--tcat-line,${C.line});font-size:14px;line-height:1.35}
[data-tcat-rank] li a::before{content:counter(r);font-size:22px;font-weight:700;color:#e3a43b;text-align:center}
[data-tcat-rank] li img{width:64px;height:48px;object-fit:contain;background:#fff;border-radius:6px}[data-tcat-rank] li small{display:block;color:var(--tcat-muted,${C.muted});font-size:12px}
.tcat-hide{display:none!important}`;
document.head.appendChild(css);

/* 操作部品 */
const figs=$$('[data-tcat-c]',root),prods=$$('[data-tcat-p]',root);
const sizes=[...new Set(figs.flatMap(f=>(f.dataset.z||'').split(' ').filter(Boolean)))].sort((a,b)=>a-b);
const makers=[];prods.forEach(p=>{if(!makers.some(x=>x[0]===p.dataset.m))makers.push([p.dataset.m,p.dataset.mj||p.dataset.m])});
const bar=root.querySelector('[data-tcat-bar]');
if(bar){bar.className='tcat-bar';bar.innerHTML=`
 <div class="tcat-seg" data-k="z">${[['','全号数'],...sizes.map(z=>[z,z+'号'])].map(([v,l])=>`<button type="button" data-v="${v}" class="${v===''?'on':''}">${l}</button>`).join('')}</div>
 <div class="tcat-seg" data-k="only"><button type="button" data-v="" class="on">すべて</button><button type="button" data-v="new">新商品だけ</button></div>
 ${prods.some(p=>p.dataset.tg)?`<div class="tcat-seg" data-k="tg"><button type="button" data-v="" class="on">すべての素材</button><button type="button" data-v="1">タングステン（TG）だけ</button></div>`:''}
 <div class="tcat-row"><select aria-label="メーカー"><option value="">すべてのメーカー</option>${makers.map(([m,j])=>`<option value="${esc(m)}">${esc(j===m?m:m+'（'+j+'）')}</option>`).join('')}</select>
 <div class="tcat-q"><input type="search" placeholder="検索（例：ケイムラ 40、ダイワ グロー）" autocomplete="off" enterkeyhint="search" aria-label="テンヤを検索"><button type="button" aria-label="検索を消す" hidden>×</button></div></div>
 <p class="tcat-help" hidden>「新商品だけ」：発売予定のものと、ここ2か月以内にカタログへ追加されたテンヤです。</p>
 <p class="tcat-cnt"></p>`;
 bar.addEventListener('click',e=>{const b=e.target.closest('.tcat-seg button');if(b){const k=b.parentNode.dataset.k;st[k]=b.dataset.v;$$('button',b.parentNode).forEach(x=>x.classList.toggle('on',x===b));apply();return}
   if(e.target.closest('.tcat-q button')){st.q='';bar.querySelector('.tcat-q input').value='';apply()}});
 bar.querySelector('select').addEventListener('change',e=>{st.m=e.target.value;apply()});
 bar.querySelector('.tcat-q input').addEventListener('input',e=>{st.q=e.target.value;apply()})}
const none=document.createElement('p');none.className='tcat-none tcat-hide';none.textContent='当てはまるテンヤがありません。';
if(bar)bar.after(none);

function apply(){const terms=normQ(st.q).split(/\s+/).filter(Boolean);let np=0,nc=0;
  prods.forEach(p=>{let k=0;const okP=(!st.m||p.dataset.m===st.m)&&(!st.tg||p.dataset.tg==='1');
    $$('[data-tcat-c]',p).forEach(f=>{const zs=(f.dataset.z||'').split(' ');let ok=okP&&(!st.z||zs.includes(st.z))&&(st.only!=='new'||isNew(f));
      if(ok&&terms.length){const h=f.dataset.q||'',h2=h.replace(/[\s・･\-]/g,'');
        ok=terms.every(q=>{const n=q.replace(/号$/,'');if(/^\d+$/.test(n))return zs.includes(n);return h.includes(q)||h2.includes(q.replace(/[・･\-]/g,''))})}
      f.classList.toggle('tcat-hide',!ok);if(ok)k++});
    p.classList.toggle('tcat-hide',!k);if(k){np++;nc+=k}});
  $$('[data-tcat-mkb]',root).forEach(b=>b.classList.toggle('tcat-hide',!b.querySelector('[data-tcat-p]:not(.tcat-hide)')));
  $$('[data-tcat-static]',root).forEach(b=>b.classList.toggle('tcat-hide',!!(st.z||st.only||st.tg||st.m||terms.length)));
  if(bar){bar.querySelector('.tcat-cnt').textContent=`${np}製品・${nc}色`;bar.querySelector('.tcat-help').hidden=st.only!=='new';bar.querySelector('.tcat-q button').hidden=!st.q}
  none.classList.toggle('tcat-hide',np>0)}
apply();

/* 一覧の中のその色へ飛ぶ（絞り込みを外してから） */
document.addEventListener('click',e=>{const a=e.target.closest('[data-go]');if(!a)return;const t=document.getElementById(a.dataset.go);if(!t)return;e.preventDefault();
  Object.assign(st,{z:'',only:'',tg:'',m:'',q:''});if(bar){$$('.tcat-seg',bar).forEach(s=>$$('button',s).forEach((x,i)=>x.classList.toggle('on',i===0)));bar.querySelector('select').value='';bar.querySelector('.tcat-q input').value=''}
  apply();$$('.tcat-hit').forEach(x=>x.classList.remove('tcat-hit'));t.classList.add('tcat-hit');t.scrollIntoView({behavior:'smooth',block:'center'})});

/* 釣れ筋とランキング（ドラゴンカウンターの集計。回数は出さない） */
const byKey={};figs.forEach(f=>{byKey[f.dataset.k]=f});
const card=(k,small)=>{const f=byKey[k];if(!f)return '';const p=f.closest('[data-tcat-p]'),img=f.querySelector('img');
  const ln=p?$$('[data-tcat-links] a[rel~="sponsored"]',p).map(a=>{const c=a.cloneNode(true);c.textContent=c.textContent.replace('で探す','');return c.outerHTML}).join(' '):'';
  return small?`<li><a href="#${f.id}" data-go="${f.id}">${img?`<img src="${esc(img.currentSrc||img.src)}" alt="" loading="lazy">`:''}<span>${esc(p?p.dataset.name:'')} ${esc(f.dataset.cn||'')}<small>${esc(p?p.dataset.mj:'')}</small></span></a></li>`
   :`<div class="tcat-tsc"><a href="#${f.id}" data-go="${f.id}">${img?`<img src="${esc(img.currentSrc||img.src)}" alt="" loading="lazy">`:''}</a><div><b>${esc(f.dataset.cn||'')}</b><br>${esc(p?p.dataset.name:'')}<br><small>${esc(p?p.dataset.mj:'')}</small><div class="tcat-tsl">${ln}</div></div></div>`};
fetch(RANK+'?h='+Math.floor(Date.now()/36e5),{cache:'no-cache'}).then(r=>r.ok?r.json():null).then(d=>{if(!d)return;
  const top=(d.top||[]).filter(k=>byKey[k]).slice(0,3);
  if(top.length){$$('.tcat-ts').forEach(x=>x.classList.remove('tcat-ts'));top.forEach(k=>byKey[k].classList.add('tcat-ts'));
    $$('[data-tcat-ts]').forEach(box=>{const l=box.querySelector('[data-tcat-ts-list]');if(l)l.innerHTML=top.map(k=>card(k)).join('');show(box,true)})}
  let any=false;
  $$('[data-tcat-rank]').forEach(box=>{for(const k of ['catch','use']){const el=box.querySelector(`[data-tcat-rank-${k}]`);if(!el)continue;const l=(d[k]||[]).filter(x=>byKey[x]);
      if(l.length>=10){el.querySelector('ol').innerHTML=l.slice(0,10).map(x=>card(x,true)).join('');show(el,true);any=true}else show(el,false)}
    show(box,any)})}).catch(()=>{});
})();
