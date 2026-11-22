"""記録画面の下のドック（タイラバ・ティップラン共通）。オーナー指示 2026-11-22。

ドラゴンカウンターの「使用テンヤを変更」と同じように、画面の下に横スライドの列を出して、
押すと使っている部品をそれに替える（記録はしない）。
  タイラバ：ヘッドの列・ネクタイの列　／　ティップラン：エギの列
出船の準備で一軍リストを選んでいれば、そのリストのものを並べる（使っているものは必ず入れる）。
あわせて「出船条件を直す」を、船・席・釣り場の行の右上に置き、縦の場所を空ける。

    apply(s, rows=[('rigs','ヘッド','rig'),('baits','ネクタイ','bait')], img='gph', title='使用中のタイラバを変更')
img: 'gph'（自分で付けた写真）／'egi'（エギのカタログ写真＋自分の写真）
"""
import json


def apply(s, rows, img, title):
    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('gear_dock: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    im = "gph(g.id,'dkimg')" if img == 'gph' else "eimg(egiIm(g),'dkimg')+gph(g.id,'dkimg')"
    rj = json.dumps([list(r) for r in rows], ensure_ascii=False)
    js = r"""/* gear-dock v1：記録画面の下で、使う部品を横スライドで替える */
const GD_ROWS=""" + rj + r""";
function gearDock(tr){const sp=tr.cur.sp,s=spOf(sp),g=curGear(tr),c=catchesOf(tr,sp);
  return GD_ROWS.map(([k,lab,key])=>{const all=(s[k]||[]).filter(x=>!x.hidden);if(!all.length)return '';
    const L=(tr.lst||{})[k]&&typeof TBL==='function'?TBL()[k]&&TBL()[k].find(l=>l.id===tr.lst[k]):null;
    let items=L&&L.items.length?L.items.map(id=>all.find(x=>x.id===id)).filter(Boolean):all;if(g[key]&&!items.some(x=>x.id===g[key])){const cur=all.find(x=>x.id===g[key]);if(cur)items=[cur].concat(items)}
    return `<div class="dk-gr"><span class="dk-gl">${esc(lab)}${L?`<small>${esc(L.name)}</small>`:''}</span><div class="dk-row">${items.map(g2=>{const n=c.filter(e=>e[key]===g2.id).length;const g=g2;
      return `<button class="dk-t dk-g ${g.id===curGear(tr)[key]?'cur':''}" data-act="dockGear" data-k="${key}" data-id="${g.id}" aria-label="${esc(lab)}を${esc(g.name)}にする">${""" + im + r"""}<span class="dk-c">${esc(g.name)}</span><span class="dk-n">${n||''}</span></button>`}).join('')}</div></div>`}).join('')}
"""
    R("function dockHTML(tr){", js + "function dockHTML(tr){")
    R("if(SOLO&&!isTenya(sp,g))main='';", "if(SOLO&&!isTenya(sp,g))main=gearDock(tr);")
    R("`使用テンヤを変更<small>${fold?'閉じています・タップで開く':'切り替えのみ'}</small>`:'釣れた'}",
      "`使用テンヤを変更<small>${fold?'閉じています・タップで開く':'切り替えのみ'}</small>`:`" + title + "<small>${fold?'閉じています・タップで開く':'押すと替わります（記録はしません）'}</small>`}")
    R("${fold?'':`<div class=\"dk-row\">${main}</div>`}", "${fold?'':(main.startsWith('<div class=\"dk-gr')?main:`<div class=\"dk-row\">${main}</div>`)}")
    R("  backRec:()=>{", "  dockGear:b=>{const tr=active();if(!tr)return;const g=curGear(tr),key=b.dataset.k;if(g[key]===b.dataset.id)return;g[key]=b.dataset.id;logGear(tr);touch(tr);render();"
      "toast(`${key==='rig'?spOf(tr.cur.sp).rigLabel:spOf(tr.cur.sp).baitLabel}を「${listName(tr.cur.sp,key==='rig'?'rigs':'baits',b.dataset.id)}」に替えました`)},\n  backRec:()=>{")
    # 出船条件を直す：船・席・釣り場の行の右上へ
    R(".rm-edit{display:inline-flex;flex:none;margin:0;min-height:28px;padding:0 12px;align-items:center}",
      ".rm-edit{display:inline-flex;flex:none;margin:0;min-height:28px;padding:0 12px;align-items:center}\n"
      ".rmeta{position:relative}.rmeta .rm-txt{padding-right:118px}.rmeta .rm-edit{position:absolute;top:0;right:0;min-height:30px;padding:0 10px;font-size:12px}\n"
      ".dk-gr{display:flex;align-items:stretch;gap:6px;margin:0 0 6px}.dk-gr:last-child{margin-bottom:0}.dk-gl{flex:none;width:52px;display:flex;flex-direction:column;justify-content:center;font-size:12px;font-weight:700;color:var(--muted);line-height:1.2}.dk-gl small{font-weight:400;font-size:10px;color:var(--teal,#41c9c6)}"
      ".dk-gr .dk-row{flex:1;min-width:0;margin:0}.dk-t.dk-g{flex:0 0 136px;min-height:58px;padding:6px 10px;border-width:1.5px}.dk-t.dk-g.cur .dk-c{color:var(--catch-ink);font-weight:800}.dk-t.dk-g .dk-c{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:12px;line-height:1.3}")
    return s
