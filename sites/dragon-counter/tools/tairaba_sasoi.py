"""タイラバカウンターの「詳細モード」：アタリの出方・巻きの速さ・アタリの位置・合わせ。オーナー指示 2026-11-22。

  出方　　：巻き／フォール                                   （e.sa = 'maki' | 'fall'）
  巻きの速さ：スロー（0.5m/秒以下）／中速（1m/秒前後）／高速（1.5m/秒以上）
            使っているリールが電動なら 1〜16 の目盛りだけ（オーナー指示 2026-11-23）          （e.spd = 'slow'|'mid'|'fast'|'1'..'16'）
  アタリの位置：巻き始め（底から3mまで）／3〜7m／7mより上　※巻きのときだけ（e.tn = 'lo'|'mid'|'hi'）
  合わせ　：あり／なし                                       （e.ka = 'awase' | 'none'）
釣れた・アタリ・バラシのどれも同じ。どれも選ばずに記録することもできる。
ドラゴンカウンター・ティップランカウンターは変えない（tairaba_build.py が、ティップランの元になる版を書いたあとで当てる）。
"""
import re

MARK = '/* tairaba-sasoi v1 */'
SPD3 = [('slow', 'スロー', '0.5m/秒以下', 'ス'), ('mid', '中速', '1m/秒前後', '中'), ('fast', '高速', '1.5m/秒以上', '高')]
TN = [('lo', '巻き始め', '底から3mまで', '下'), ('mid', '3〜7m', '底から', '中'), ('hi', '7mより上', '底から', '上')]


def apply(s):
    if MARK in s:
        return s

    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('tairaba_sasoi: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    def RX(pat, new, flags=0):
        nonlocal s
        s2, c = re.subn(pat, new, s, flags=flags)
        if c != 1:
            raise SystemExit('tairaba_sasoi: regex %d: %s' % (c, pat[:90]))
        s = s2

    spd = '{' + ','.join("'%s':'%s'" % (k, j) for k, j, _, _ in SPD3) + "," + ','.join("'%d':'電動 %d'" % (i, i) for i in range(1, 17)) + '}'
    spdn = '{' + ','.join("'%s':'%s'" % (k, n) for k, _, n, _ in SPD3) + '}'
    spda = '{' + ','.join("'%s':'%s'" % (k, a) for k, _, _, a in SPD3) + '}'
    tn = '{' + ','.join("'%s':'%s'" % (k, j) for k, j, _, _ in TN) + '}'
    tnn = '{' + ','.join("'%s':'%s'" % (k, n) for k, _, n, _ in TN) + '}'

    # 詳細モードを使えるように（タイラバ版で止めたところを戻す）
    R("const modeOf=tr=>'simple';", "const modeOf=tr=>tr&&tr.mode==='detail'?'detail':'simple';")
    R('<div class="td-top"><span class="td-h">${isTairyo',
      '<div class="td-top"><span class="td-h"><span class="mseg" role="group" aria-label="記録のしかた"><button class="${modeOf(tr)===\'simple\'?\'on\':\'\'}" data-act="recMode" data-d="simple">シンプル</button><button class="${modeOf(tr)===\'detail\'?\'on\':\'\'}" data-act="recMode" data-d="detail">詳細</button></span>${isTairyo')
    R("function fModeHTML(f){f.rmode='simple';return '';const m=f.rmode||'';", "function fModeHTML(f){const m=f.rmode||'';")

    # 項目
    RX(r"/\* 誘い：[^*]*\*/\nconst SA_JP=\{[^}]*\};",
       MARK + "\n/* 出方（e.sa）・巻きの速さ（e.spd）・アタリの位置（e.tn）・合わせ（e.ka）。釣れた・アタリ・バラシに付ける */\n"
       "const SA_JP={maki:'巻き',fall:'フォール'};const SPD_JP=" + spd + ",SPD_N=" + spdn + ",SPD_A=" + spda + ";const TN_JP=" + tn + ",TN_N=" + tnn + ";\n"
       "const SPD_KEYS=Object.keys(SPD_JP).sort((a,b)=>(isNaN(a)?0:1)-(isNaN(b)?0:1)||(+a)-(+b)),TN_KEYS=Object.keys(TN_JP);let nextX=null;")
    RX(r"/\* 掛け方：[^*]*\*/\nconst KA_JP=\{[^}]*\}", "const KA_JP={awase:'合わせあり',none:'合わせなし'}")
    R("const detailTxt=e=>[e.sa?SA_JP[e.sa]:'',e.ka?KA_JP[e.ka]:''].filter(Boolean).join('・');",
      "const detailTxt=e=>[e.sa?SA_JP[e.sa]+(e.sa==='maki'&&e.spd?' '+SPD_JP[e.spd]:''):'',e.sa==='maki'&&e.tn?'位置 '+TN_JP[e.tn]:'',e.ka?KA_JP[e.ka]:''].filter(Boolean).join('・');")
    R("if(nextKa){e.ka=nextKa;nextKa=null}", "if(nextKa){e.ka=nextKa;nextKa=null}if(nextX){Object.assign(e,nextX);nextX=null}")

    # 記録の流れ：出方 → （巻きなら）速さ → 位置 → 合わせ。1枚ずつ押して進む
    RX(r"function openKake\(kind,sa\)\{.*?\nfunction openSasoi\(kind\)\{.*?\{kind:'sasoi'\}\)\}\n",
       lambda m: r"""function tkElec(id){const st=id?setOf(id):null,q=st?tkItem(st.reel):null;return !!(q&&q.kind==='electric')}
function trElec(){const tr=active();return tkElec(tr&&tr.tk&&tr.tk.cur)}
function evElec(f){const tr=S.trips[f.tid],e=tr&&tr.events.find(x=>x.id===f.id);return tkElec(e&&e.tk)}
let trD=null;
function openSasoi(kind){const tr=active();if(!tr)return;trD={kind,elec:trElec()};trStep()}
function trStep(){const d=trD,k=d.kind,L=S.ui.lastTr||{},n=d.sa==='maki'?4:d.sa?2:0;
  const head=(no,ttl)=>`<div class="sheet-h"><h2>${KIND_JP[k]}：${ttl}</h2><button class="btn sm ghost" data-act="closeSheet">閉じる</button></div><p class="muted">${n?no+'/'+n+'　':''}${[d.sa?SA_JP[d.sa]:'',d.sa==='maki'&&d.spd?SPD_JP[d.spd]:'',d.tn?TN_JP[d.tn]:''].filter(Boolean).join(' → ')}</p>`;
  const b=(f,v,lbl,sub)=>`<button class="sa-b ${L[f]===v?'on':''}" data-act="trPick" data-f="${f}" data-v="${v}">${lbl}${sub?`<small>${sub}</small>`:''}</button>`;
  const skip=(f,t)=>`<button class="btn" data-act="trPick" data-f="${f}" data-v="">${t}</button>`;
  const back=d.sa!==undefined?`<button class="btn sm ghost" data-act="trBack">← ひとつ戻る</button>`:'';
  let h;
  if(d.sa===undefined)h=head(1,'アタリの出方')+`<div class="sa-grid tr-sa">${b('sa','maki','巻き')}${b('sa','fall','フォール')}</div>`+`<button class="btn" data-act="trDone">選ばずに記録</button>`;
  else if(d.sa==='maki'&&d.spd===undefined)h=head(2,'巻きの速さ')+(d.elec
     ?`<div class="sa-grid tr-el">${SPD_KEYS.filter(x=>!isNaN(x)).map(x=>b('spd',x,x)).join('')}</div><p class="muted">電動リールの速さの目盛り（使っているリールが電動のため、数字で選びます）</p>`
     :`<div class="sa-grid tr-sa tr-3">${SPD_KEYS.filter(x=>isNaN(x)).map(x=>b('spd',x,SPD_JP[x],SPD_N[x])).join('')}</div><button class="btn sm ghost" data-act="trElec">電動リールの目盛り（1〜16）で選ぶ</button>`)+skip('spd','速さは選ばない（次へ）')+back;
  else if(d.sa==='maki'&&d.tn===undefined)h=head(3,'アタリの位置')+`<div class="sa-grid tr-sa tr-3">${TN_KEYS.map(x=>b('tn',x,TN_JP[x],TN_N[x])).join('')}</div>`+skip('tn','位置は選ばない（次へ）')+back;
  else h=head(n,'合わせ')+`<div class="sa-grid tr-sa">${KA_KEYS.map(x=>b('ka',x,KA_JP[x])).join('')}</div>`+skip('ka','合わせは選ばずに記録')+back;
  openSheet(h,{kind:'sasoi'})}
function trRec(){const d=trD;if(!d)return;$('#sheet').hidden=true;sheetCtx=null;nextSa=d.sa||null;nextKa=d.ka||null;
  const x={};if(d.sa==='maki'){if(d.spd)x.spd=d.spd;if(d.tn)x.tn=d.tn}nextX=Object.keys(x).length?x:null;
  S.ui.lastTr={sa:d.sa||'',spd:d.spd||'',tn:d.tn||'',ka:d.ka||''};lastTap=0;bypassDetail=true;trD=null;try{recKind(d.kind)}finally{bypassDetail=false;nextSa=null;nextKa=null;nextX=null}}
""", flags=re.S)
    RX(r"  saRec:b=>\{.*?\n  saBack:b=>openSasoi\(b\.dataset\.k\),\n  kaRec:b=>\{.*?\n    try\{recKind\(k\)\}finally\{bypassDetail=false;nextSa=null;nextKa=null\}\},\n",
       lambda m: "  trPick:b=>{const d=trD;if(!d)return;const f=b.dataset.f,v=b.dataset.v;d[f]=v;if(f==='sa'&&v!=='maki'){d.spd='';d.tn=''}if(f==='ka')return trRec();trStep()},\n"
                 "  trBack:()=>{const d=trD;if(!d)return;if(d.sa!=='maki'){delete d.sa;delete d.spd;delete d.tn}else for(const f of ['tn','spd','sa'])if(d[f]!==undefined){delete d[f];break}trStep()},\n"
                 "  trElec:()=>{if(!trD)return;trD.elec=!trD.elec;trStep()},\n"
                 "  trDone:()=>{if(!trD)return;trD.sa='';trD.ka='';trRec()},\n",
       flags=re.S)
    R("toast(b.dataset.d==='detail'?'詳細モード：釣れた・アタリ・バラシを押すと、誘いと掛け方を選んで記録します'",
      "toast(b.dataset.d==='detail'?'詳細モード：釣れた・アタリ・バラシを押すと、出方・速さ・位置・合わせを選んで記録します'")
    R(".sa-grid .sa-fall{grid-column:1/-1;min-height:52px}",
      ".sa-grid .sa-fall{grid-column:1/-1;min-height:52px}.sa-grid.tr-sa{grid-template-columns:1fr 1fr}.sa-grid.tr-sa.tr-3{grid-template-columns:1fr 1fr 1fr}"
      ".sa-grid.tr-sa .sa-b{min-height:72px;font-size:18px}.sa-grid.tr-sa .sa-b small{display:block;font-size:11px;font-weight:400;opacity:.8;margin-top:2px}"
      ".sa-grid.tr-el{grid-template-columns:repeat(4,1fr)}.sa-grid.tr-el .sa-b{min-height:56px;font-size:20px}")

    # 記録を直す画面
    RX(r"\$\{false\?`<div class=\"field\"><span>誘い</span>.*?`:''\}`:''\}\n",
       lambda m: "${f.kind!=='gedo'?`<div class=\"field\"><span>アタリの出方</span><div class=\"chips wrap\">${['',...Object.keys(SA_JP)].map(k=>`<button class=\"chip ${f.sa===k?'on':''}\" data-act=\"evSa\" data-d=\"${k}\">${k?SA_JP[k]:'なし'}</button>`).join('')}</div></div>"
                 "${f.sa==='maki'?`<div class=\"field\"><span>巻きの速さ</span><div class=\"chips wrap\">${['',...SPD_KEYS.filter(k=>!evElec(f)||!isNaN(k)||(f.spd||'')===k)].map(k=>`<button class=\"chip ${(f.spd||'')===k?'on':''}\" data-act=\"evX\" data-f=\"spd\" data-d=\"${k}\">${k?(isNaN(k)?SPD_JP[k]:k):'なし'}</button>`).join('')}</div><small class=\"muted\">${evElec(f)?'電動リールの目盛りで選びます':'数字は電動リールの目盛り'}</small></div>"
                 "<div class=\"field\"><span>アタリの位置（底から）</span><div class=\"chips wrap\">${['',...TN_KEYS].map(k=>`<button class=\"chip ${(f.tn||'')===k?'on':''}\" data-act=\"evX\" data-f=\"tn\" data-d=\"${k}\">${k?TN_JP[k]:'なし'}</button>`).join('')}</div></div>`:''}"
                 "<div class=\"field\"><span>合わせ</span><div class=\"chips wrap\">${['',...KA_KEYS].map(k=>`<button class=\"chip ${f.ka===k?'on':''}\" data-act=\"evKa\" data-d=\"${k}\">${k?KA_JP[k]:'なし'}</button>`).join('')}</div></div>`:''}\n",
       flags=re.S)
    R("evF={tid:tr.id,back:back||null,id,sa:e.sa||'',ka:e.ka||'',", "evF={tid:tr.id,back:back||null,id,sa:e.sa||'',ka:e.ka||'',spd:e.spd||'',tn:e.tn||'',")
    R("  evSa:b=>{", "  evX:b=>{const tm=$('#evTime');if(tm)evF.t=tm.value;const m=$('#evMemo');if(m)evF.memo=m.value;evF[b.dataset.f]=b.dataset.d;renderEvSheet()},\n  evSa:b=>{")
    R("if(f.sa&&f.kind!=='gedo')e.sa=f.sa;else delete e.sa;if(f.ka&&f.kind!=='gedo'&&f.kind!=='bite')e.ka=f.ka;else delete e.ka;",
      "if(f.sa&&f.kind!=='gedo')e.sa=f.sa;else delete e.sa;if(f.ka&&f.kind!=='gedo')e.ka=f.ka;else delete e.ka;"
      "if(e.sa==='maki'&&f.spd)e.spd=f.spd;else delete e.spd;if(e.sa==='maki'&&f.tn)e.tn=f.tn;else delete e.tn;")

    # 書き出し
    R("sa:e.sa||'',ka:e.ka||'',fish:", "sa:e.sa||'',spd:e.spd||'',tn:e.tn||'',ka:e.ka||'',fish:")

    # 振り返りの図：札（上＝速さ・フ、下＝合／無。塗り＝巻き、白抜き＝フォール）
    R("mv=e.sa&&e.sa.endsWith('move'),st=e.sa&&e.sa.endsWith('stay')", "mv=e.sa==='maki',st=e.sa==='fall'")
    R("e.sa.startsWith('maki')?'巻':e.sa==='fall'?'フ':e.sa==='oki'?'置':'叩'", "e.sa==='fall'?'フ':e.spd?(SPD_A[e.spd]||e.spd):'巻'")
    R("e.ka==='soku'?'即':'深'", "e.ka==='awase'?'合':'無'")
    R("label(top,'誘い・掛け方','詳細モードの記録')", "label(top,'出方・合わせ','詳細モードの記録')")
    R("rows=SA_KEYS.map(k=>[SA_JP[k],e=>e.sa===k]).concat(KA_KEYS.map(k=>[KA_JP[k],e=>e.ka===k])).filter(([,f])=>dv.some(f));",
      "rows=SA_KEYS.map(k=>[SA_JP[k],e=>e.sa===k]).concat(SPD_KEYS.map(k=>['　'+(isNaN(k)?SPD_JP[k]:'電動 '+k),e=>e.sa==='maki'&&e.spd===k]),TN_KEYS.map(k=>['　位置 '+TN_JP[k],e=>e.sa==='maki'&&e.tn===k]),KA_KEYS.map(k=>[KA_JP[k],e=>e.ka===k])).filter(([,f])=>dv.some(f));")
    R("'誘い・掛け方ごとの数'", "'出方・速さ・位置・合わせごとの数'")
    leg = ("if(dv.length){y+=22;o.push(`<rect x=\"24\" y=\"${y-12}\" width=\"16\" height=\"16\" rx=\"3\" fill=\"${P.catch}\"/>`+TX(32,y+1,'中',{size:10,bold:1,fill:'#fff',anchor:'middle'})+TX(46,y,'巻き（塗り）',{size:12,fill:P.muted})"
           "+`<rect x=\"150\" y=\"${y-12}\" width=\"16\" height=\"16\" rx=\"3\" fill=\"#fff\" stroke=\"${P.catch}\" stroke-width=\"1.6\"/>`+TX(158,y+1,'フ',{size:10,bold:1,fill:P.catch,anchor:'middle'})+TX(172,y,'フォール（白抜き）　枠の色＝釣れた／アタリ／バラシ',{size:12,fill:P.muted}));"
           "y+=20;o.push(TX(24,y,'上：ス＝スロー　中＝中速　高＝高速　数字＝電動の目盛り　下：合＝合わせあり　無＝なし',{size:12,fill:P.muted}))}")
    RX(r"if\(dv\.length\)\{y\+=22;o\.push\(`<rect x=\"24\" y=\"\$\{y-12\}\" width=\"16\" height=\"16\" rx=\"3\" fill=\"\$\{P\.catch\}\"/>`\+TX\(32,y\+1,'巻'.*?枠の色＝釣れた／アタリ／バラシ',\{size:12,fill:P\.muted\}\)\)\}",
       lambda m: leg)

    # 分析：出方・速さ・位置・合わせごと
    RX(r"<h3>誘いごと（詳細モードで記録した分）</h3>", "<h3>アタリの出方ごと（詳細モードで記録した分）</h3>")
    R("<h3>掛け方ごと</h3>", "<h3>合わせごと</h3>")
    i = s.find("<h3>合わせごと</h3>")
    j = s.find("</div>`})()}", i) + len("</div>`})()}")
    extra = ("\n   ${(()=>{const row=(ttl,keys,lab,get)=>{const m={};L.forEach(t=>t.events.forEach(e=>{const k=get(e);if(!k||!['catch','bite','lost'].includes(e.kind))return;if(e.kind==='catch'&&e.sp!==SOLO)return;m[k]=m[k]||{catch:0,bite:0,lost:0};m[k][e.kind]++}));const it=keys.filter(k=>m[k]);if(!it.length)return '';"
             "return `<div class=\"rank\"><h3>${ttl}</h3>${it.map(k=>`<div class=\"rk sa-rk\"><span>${lab(k)}</span><b>${m[k].catch}${esc(spOf(SOLO).unit)}<small>・アタリ${m[k].bite}・バラシ${m[k].lost}</small></b></div>`).join('')}</div>`};"
             "return row('巻きの速さごと',SPD_KEYS,k=>isNaN(k)?SPD_JP[k]+'（'+SPD_N[k]+'）':'電動 '+k,e=>e.sa==='maki'&&e.spd)+row('アタリの位置ごと（巻き）',TN_KEYS,k=>TN_JP[k],e=>e.sa==='maki'&&e.tn)})()}")
    s = s[:j] + extra + s[j:]

    # 説明の文
    R("誘い（巻き／叩き × 誘い中／ステイ中）と掛け方（即掛け／深追い）を選んで記録します。",
      "アタリの出方（巻き／フォール）、巻きの速さ、アタリの位置、合わせ（あり／なし）を選んで記録します。")
    RX(r"<b>誘い</b>（[^）]*）と、<b>掛け方</b>（即掛け／深追い）を選んで記録します。[^<]*",
       "<b>アタリの出方</b>（巻き／フォール）→ 巻きなら<b>速さ</b>（スロー0.5m/秒以下・中速1m/秒前後・高速1.5m/秒以上。電動リールは目盛り1〜16）と<b>アタリの位置</b>（巻き始め＝底から3mまで・3〜7m・7mより上）→ <b>合わせ</b>（あり／なし）の順に押して記録します。釣れた・アタリ・バラシとも同じです。")
    s = s.replace('各記録の時刻に小さな札（上＝巻／叩、塗り＝誘い中・白抜き＝ステイ中、下＝即／深）', '各記録の時刻に小さな札（上＝速さ／フ、塗り＝巻き・白抜き＝フォール、下＝合わせ）')
    s = s.replace('誘い・掛け方', '出方・合わせ').replace('誘いと掛け方', '出方と合わせ').replace('誘いや掛け方', '出方や合わせ')
    left = [m.group(0) for m in re.finditer(r'.{0,30}(掛け方|叩き|即掛け|深追い|ステイ中).{0,30}', s)]
    left = [x for x in left if 'HAYABUSA' not in x and '誘い速掛' not in x]
    if left:
        raise SystemExit('tairaba_sasoi: left over: ' + ' / '.join(left[:8]))
    return s
