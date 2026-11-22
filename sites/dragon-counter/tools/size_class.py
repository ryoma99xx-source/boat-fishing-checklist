"""釣れたもののサイズ区分（ティップラン：アオリイカ、タイラバ：マダイ）。オーナー指示 2026-11-22。

「釣れた」で記録したあと（シンプル・詳細のどちらでも）、サイズを選ぶ画面を出す。記録は押した時刻ですでに済んでいて、
選ばずに閉じてもよい。選んだ区分は e.szc に入れ、記録の一覧・記録を直す画面・書き出しに出す。
big に入れた区分を選んだら、大物の印（e.dragon。ティップランではキロアップ）も付ける。

    apply(s, [(key, 名前, 目安), …], big={key, …}, unit='杯')
"""
import json


def apply(s, classes, big=(), unit=''):
    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('size_class: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    cj = json.dumps([list(c) for c in classes], ensure_ascii=False)
    bj = json.dumps(sorted(big), ensure_ascii=False)
    js = r"""/* size-class v1：釣れたもののサイズ区分 */
const SZC=""" + cj + ",SZC_BIG=" + bj + r""";
const szLabel=k=>{const c=SZC.find(x=>x[0]===k);return c?c[1]:''};
function openSz(tid,eid){const tr=S.trips[tid];if(!tr)return;const e=tr.events.find(x=>x.id===eid);if(!e)return;if(!$('#sheet').hidden)return;
  openSheet(`<div class="sheet-h"><h2>サイズは？</h2><button class="btn sm ghost" data-act="closeSheet">閉じる</button></div><p class="muted">記録はもう済んでいます（${hm(e.t)}）。サイズを押すと、この記録に付きます。選ばなくてもかまいません。</p>
   <div class="sa-grid sz-grid">${SZC.map(([k,l,r])=>`<button class="sa-b ${e.szc===k?'on':''}" data-act="szPick" data-t="${tid}" data-e="${eid}" data-k="${k}">${esc(l)}<small>${esc(r)}</small></button>`).join('')}</div>
   <button class="btn" data-act="closeSheet">サイズは選ばない</button>`,{kind:'sz'})}
"""
    R("function recKind(kind){", js + "function recKind(kind){")
    R("tr.events.push(e);touch(tr);buzz();keepAwake();",
      "tr.events.push(e);touch(tr);buzz();keepAwake();if(kind==='catch'&&!osp&&e.sp===tr.cur.sp){const _t=tr.id,_e=e.id;setTimeout(()=>openSz(_t,_e),350)}")
    R("  evSa:b=>{",
      "  szPick:b=>{const tr=S.trips[b.dataset.t];if(!tr)return;const e=tr.events.find(x=>x.id===b.dataset.e);if(!e)return;e.szc=b.dataset.k;if(SZC_BIG.includes(e.szc))e.dragon=true;touch(tr);closeSheet();render();toast(`サイズ：${szLabel(e.szc)}`)},\n"
      "  evSz:b=>{const tm=$('#evTime');if(tm)evF.t=tm.value;const m=$('#evMemo');if(m)evF.memo=m.value;evF.szc=b.dataset.d;if(SZC_BIG.includes(evF.szc))evF.dragon=true;renderEvSheet()},\n  evSa:b=>{")
    # 記録を直す画面
    R("evF={tid:tr.id,back:back||null,id,", "evF={tid:tr.id,back:back||null,id,szc:e.szc||'',")
    R('<label class="field"><span>時刻</span><input type="time" id="evTime"',
      "${f.kind==='catch'?`<div class=\"field\"><span>サイズ区分</span><div class=\"chips wrap\">${[['','なし'],...SZC.map(x=>[x[0],x[1]])].map(([k,l])=>`<button class=\"chip ${(f.szc||'')===k?'on':''}\" data-act=\"evSz\" data-d=\"${k}\">${esc(l)}</button>`).join('')}</div></div>`:''}\n"
      '   <label class="field"><span>時刻</span><input type="time" id="evTime"')
    R("size:f.kind==='catch'?f.size:'',memo:f.memo.trim()", "size:f.kind==='catch'?f.size:'',szc:f.kind==='catch'?(f.szc||''):'',memo:f.memo.trim()")
    # 一覧の表示・書き出し
    R("e.size?sizeText(e.sp,e.size):'',", "e.szc?szLabel(e.szc):'',e.size?sizeText(e.sp,e.size):'',")
    R("size:e.size||'',dragon:!!e.dragon", "size:e.size||'',szc:e.szc||'',dragon:!!e.dragon")
    R(".sa-grid .sa-fall{grid-column:1/-1;min-height:52px}",
      ".sa-grid .sa-fall{grid-column:1/-1;min-height:52px}.sa-grid.sz-grid{grid-template-columns:1fr 1fr}.sa-grid.sz-grid .sa-b{min-height:66px;font-size:18px}.sa-grid.sz-grid .sa-b small{display:block;font-size:12px;font-weight:400;opacity:.8;margin-top:2px}")
    return s
