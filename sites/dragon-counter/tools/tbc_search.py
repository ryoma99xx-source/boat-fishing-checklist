"""タイラバのカタログ登録（ヘッド・ネクタイ・スカート）を検索できるようにする。オーナー指示 2026-11-22。

カタログの画面の上に検索欄を出す。メーカー・製品名・形・色で探せる（ひらがな／カタカナ、全角／半角、大文字／小文字はどれでも同じ）。
空白で区切ると全部を含むものに絞る。結果を押すと、そのメーカーと製品を選んだ状態になり、検索した言葉に合う色には印が付く。
打っている間は結果の欄だけを書き直す（入力欄から指が外れないように）。

    apply(s)
"""


def apply(s):
    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('tbc_search: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    js = r"""/* tbc-search v1：カタログを検索して登録 */
const tbcTok=q=>normQ(q).split(/[\s　]+/).filter(Boolean).map(t=>tbcWt(t));
function tbcHay(r){return normQ([r.m,r.s,r.mat||'',r.sh||'',r.type||''].join(' '))+(r.w&&r.w.length?' '+r.w.map(g=>`<${g}g>`).join(' '):'')}
const tbcWt=t=>/^\d+g?$/.test(t)?`<${parseInt(t)}g>`:t;
function tbcFindRows(q){const tk=tbcTok(q);if(!tk.length)return [];const out=[];
  tbcRows().forEach((r,i)=>{const h=tbcHay(r),cs=r.c.map(normQ);
    if(!tk.every(t=>h.includes(t)||cs.some(c=>c.includes(t))))return;
    const rest=tk.filter(t=>!h.includes(t)),hit=rest.length?r.c.filter((c,j)=>rest.every(t=>cs[j].includes(t))):[];
    if(rest.length&&!hit.length)return;out.push([r,i,hit])});return out}
function tbcResHTML(){const q=(tbc&&tbc.q)||'';if(!tbcTok(q).length)return '';const L=tbcFindRows(q),N=40;
  if(!L.length)return `<p class="muted tbq-none">「${esc(q)}」に合う製品はありません。メーカーを選んで探してください。</p>`;
  return `<p class="muted tbq-n">${L.length}件${L.length>N?`（上から${N}件）`:''}</p><div class="tbq-list">${L.slice(0,N).map(([r,i,hit])=>`<button class="tbq-r ${i===tbc.i?'on':''}" data-act="tbcHit" data-i="${i}"><small>${esc(r.m)}</small><b>${esc(r.s)}${r.mat==='TG'?'<small>（TG）</small>':''}</b>${hit.length?`<span>${hit.slice(0,4).map(esc).join('・')}${hit.length>4?` ほか${hit.length-4}色`:''}</span>`:`<span>${r.c.length}色${tbc.kind==='rigs'&&r.w.length?`・${r.w.length}種の重さ`:''}</span>`}</button>`).join('')}</div>`}
function tbcQ(v){tbc.q=v;const el=$('#tbcRes');if(el)el.innerHTML=tbcResHTML()}
const tbcCHit=c=>{const tk=tbcTok((tbc&&tbc.q)||''),r=tbc&&tbc.i>=0?tbcRows()[tbc.i]:null;if(!tk.length||!r)return false;const h=tbcHay(r),rest=tk.filter(t=>!h.includes(t));return rest.length>0&&rest.every(t=>normQ(c).includes(t))};
"""
    R("function tbcSheet(){", js + "function tbcSheet(){")
    R("""<div class="field"><span>メーカー</span><div class="chips wrap">${makers.map(m=>`<button class="chip ${m===tbc.m?'on':''}" data-act="tbcMaker\"""",
      """<div class="field tbq"><span>検索（メーカー・製品名・色）</span><input type="search" id="tbcQInp" placeholder="例：紅牙 ネクタイ、ゼブラ、TG 100" value="${esc(tbc.q||'')}" oninput="tbcQ(this.value)" autocomplete="off" enterkeyhint="search"><div id="tbcRes">${tbcResHTML()}</div></div>
   <div class="field"><span>メーカーから選ぶ</span><div class="chips wrap">${makers.map(m=>`<button class="chip ${m===tbc.m?'on':''}" data-act="tbcMaker\"""")
    # 色のチップ：検索した言葉に合う色に印
    R("""<button class="chip ${im?'cimg':''} ${tbc.c.has(c)?'on':''}" data-act="tbcC\"""",
      """<button class="chip ${im?'cimg':''} ${tbc.c.has(c)?'on':''} ${tbcCHit(c)?'qhit':''}" data-act="tbcC\"""")
    R("tbcOpen:b=>{tbc={kind:b.dataset.kind,m:'',i:-1,w:new Set(),c:new Set()};tbcSheet()},",
      "tbcOpen:b=>{tbc={kind:b.dataset.kind,m:'',i:-1,w:new Set(),c:new Set(),q:''};tbcSheet();setTimeout(()=>{const x=$('#tbcQInp');if(x&&matchMedia('(hover:hover)').matches)x.focus()},60)},\n"
      "  tbcHit:b=>{const r=tbcRows()[+b.dataset.i];if(!r)return;tbc.m=r.m;tbc.i=+b.dataset.i;tbc.w=new Set();tbc.c=new Set();if(r.w&&r.w.length===1)tbc.w.add(r.w[0]);"
      "const g=tbcTok(tbc.q).map(t=>/^<\\d+g>$/.test(t)?parseInt(t.slice(1)):0).filter(n=>n&&r.w&&r.w.includes(n));g.forEach(n=>tbc.w.add(n));tbcSheet();"
      "setTimeout(()=>{const x=$('#sheet .chip.qhit')||$('#sheet [data-act=\"tbcW\"]')||$('#sheet [data-act=\"tbcC\"]');if(x)x.scrollIntoView({block:'center',behavior:'smooth'})},60)},")
    css = (".tbq input{width:100%;font-size:17px;padding:11px 12px;border:2px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink);box-sizing:border-box}"
           ".tbq-n,.tbq-none{margin:6px 0 4px;font-size:13px}.tbq-list{display:flex;flex-direction:column;gap:6px;max-height:46vh;overflow:auto}"
           ".tbq-r{display:flex;flex-direction:column;align-items:flex-start;text-align:left;gap:1px;padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink);font:inherit}"
           ".tbq-r small{font-size:12px;opacity:.75}.tbq-r b{font-size:16px}.tbq-r span{font-size:13px;opacity:.85}.tbq-r.on{border-color:var(--acc);border-width:2px}"
           ".chip.qhit{outline:3px solid #f59f00;outline-offset:1px}")
    R("</style>", css + "</style>")
    return s
