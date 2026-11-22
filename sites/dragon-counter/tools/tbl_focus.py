"""一軍リストを作る画面（タイラバ・ティップラン共通）。オーナー指示 2026-11-22。

出船の準備の「…の一軍リストを作る →」を押すと、登録タブを「一軍リストを作る」だけの形で開く。
ほかの登録（部品の登録・タックル・釣り場など）は「ほかの登録を開く」の中に折りたたむ。文字は大きめ。
登録タブを普通に開いたとき（下のタブから）は、これまでどおりの形。

    apply(s, kinds=['rigs','baits'], label='ヘッド・ネクタイ')
tairaba_lists.py / tipran_lists.py の最後で通す（tblHTML・lstPick があること）。
"""


def apply(s, kinds, label):
    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('tbl_focus: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    ks = '[' + ','.join("'%s'" % k for k in kinds) + ']'
    # 部品の欄の中のリストは、この画面のときは出さない（同じものが二つにならないように）
    for k in kinds:
        R("${tblHTML('%s')}</div>" % k, "${S.ui.tblFocus?'':tblHTML('%s')}</div>" % k)
    # 出船の準備のリンク → この画面
    R('data-act="goSec" data-sec="tbl-${k}"', 'data-act="goTbl" data-sec="tbl-${k}"')
    R("function render(){", "function render(){if(S.ui.tab!=='gear')S.ui.tblFocus=0;")
    R("function viewGear(){", """function viewGear(){if(!S.ui.tblFocus)return viewGear0();
  return `<h1>一軍リストを作る</h1><p class="tblf-lead">よく使う""" + label + """を、リストにまとめます。作ったら、下の「保存して記録に戻る」で出船の準備に戻り、リストを選んでください。</p>
  <div class="card tblfocus">${""" + ks + """.map(k=>tblHTML(k)).join('')}</div>
  <details class="tbl-others"><summary>ほかの登録を開く<small>（""" + label + """の登録・タックル・釣り場など）</small></summary>${viewGear0().replace('<h1>登録</h1>','')}</details>`}
function viewGear0(){""")
    R("  backRec:()=>{", "  goTbl:b=>{S.ui.tblFocus=1;S.ui.tab='gear';if(!$('#sheet').hidden){$('#sheet').hidden=true;sheetCtx=null}render();scrollTo(0,0)},\n  backRec:()=>{")
    R(".tbl{margin-top:14px;", ".tblf-lead{font-size:16px;line-height:1.7;color:var(--muted);margin:0 0 12px}"
      ".tblfocus .tbl{margin-top:4px;border-top:0;padding-top:4px}.tblfocus .tbl+.tbl{margin-top:22px;border-top:1px solid var(--line);padding-top:16px}"
      ".tblfocus .tbl h3{font-size:22px;margin:0 0 6px}.tblfocus .tbl>p{font-size:16px;line-height:1.7}"
      ".tblfocus .tbl-card .grow input{font-size:18px;min-height:48px}.tblfocus .tbl-items .chip{font-size:17px;min-height:50px;padding:10px 16px}"
      ".tblfocus .tbl>.btn{font-size:18px;min-height:54px;width:100%;margin-top:8px}"
      ".tbl-others{margin:18px 0}.tbl-others>summary{cursor:pointer;font-size:17px;font-weight:700;padding:14px 16px;border:1px solid var(--line);border-radius:12px;list-style:none}"
      ".tbl-others>summary small{display:block;font-weight:400;font-size:13px;color:var(--muted);margin-top:2px}.tbl-others[open]>summary{margin-bottom:12px}"
      ".tbl h3{font-size:19px}.tbl>p{font-size:15px;line-height:1.7}.tbl-items .chip{font-size:16px}"
      ".tbl{margin-top:14px;")
    return s
