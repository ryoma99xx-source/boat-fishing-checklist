"""ティップランカウンターの「誘い」と「アタリの出方」（詳細モード）。オーナー指示 2026-11-21。

タイラバ版で止めている詳細モードを、ティップランでは使えるようにして、項目をティップラン用にする。
  誘い　　　：シャクリ中／ステイ直後／ロングステイ／フォール中／巻き上げ中
  アタリの出方：穂先が入る／穂先が戻る／重みが乗る／手元に来る（ドラゴンカウンターの「掛け方」の代わり。アタリにも付ける）
ドラゴンカウンター・タイラバカウンターは変えない。

tipran_build.py の最後に apply() を通す。単体でも、いまの public/tipran/index.html に当てられる:
    python3 tools/tipran_sasoi.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TIPRAN = os.path.join(os.path.dirname(HERE), 'public', 'tipran', 'index.html')
MARK = '/* tipran-sasoi v1 */'

SA = [('shakuri', 'シャクリ中', 'シ'), ('stay-just', 'ステイ直後', '直'), ('stay-long', 'ロングステイ', '長'),
      ('fall', 'フォール中', 'フ'), ('maki', '巻き上げ中', '巻')]
KA = [('iru', '穂先が入る', '入'), ('modoru', '穂先が戻る', '戻'), ('omomi', '重みが乗る', '重'), ('te', '手元に来る', '手')]
SA_TXT = '・'.join(j for _, j, _ in SA)
KA_TXT = '・'.join(j for _, j, _ in KA)


def apply(s):
    if MARK in s:
        return s

    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('tipran_sasoi: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    def RX(pat, new, flags=0):
        nonlocal s
        s2, c = re.subn(pat, new, s, flags=flags)
        if c != 1:
            raise SystemExit('tipran_sasoi: regex %d: %s' % (c, pat[:90]))
        s = s2

    js = lambda d: '{' + ','.join("'%s':'%s'" % (k, v) for k, v, _ in d) + '}'
    ab = lambda d: '({' + ','.join("'%s':'%s'" % (k, a) for k, _, a in d) + '})'

    # 詳細モードを使えるように（タイラバ版で止めたところを戻す）
    R("const modeOf=tr=>'simple';", "const modeOf=tr=>tr&&tr.mode==='detail'?'detail':'simple';")
    R('<div class="td-top"><span class="td-h">${isTairyo',
      '<div class="td-top"><span class="td-h"><span class="mseg" role="group" aria-label="記録のしかた"><button class="${modeOf(tr)===\'simple\'?\'on\':\'\'}" data-act="recMode" data-d="simple">シンプル</button><button class="${modeOf(tr)===\'detail\'?\'on\':\'\'}" data-act="recMode" data-d="detail">詳細</button></span>${isTairyo')
    R("function fModeHTML(f){f.rmode='simple';return '';const m=f.rmode||'';", "function fModeHTML(f){const m=f.rmode||'';")
    R('${false?`<div class="field"><span>誘い</span>', '${f.kind!==\'gedo\'?`<div class="field"><span>誘い</span>')
    R('${f.kind!==\'bite\'?`<div class="field"><span>掛け方</span>', '${true?`<div class="field"><span>アタリの出方</span>')

    # 項目
    RX(r"/\* 誘い：[^*]*\*/\nconst SA_JP=\{[^}]*\};",
       MARK + "\n/* 誘い：ティップラン用。釣れた・アタリ・バラシに付ける */\nconst SA_JP=" + js(SA) + ";")
    RX(r"/\* 掛け方：[^*]*\*/\nconst KA_JP=\{[^}]*\}",
       "/* アタリの出方（e.ka に入れる）。アタリにも付ける */\nconst KA_JP=" + js(KA))

    # 誘いを選ぶ画面（5つを並べる）→ 次にアタリの出方（アタリも、フォールも）
    RX(r'<div class="sa-grid"><span></span><b>誘い中</b><b>ステイ中</b>.*?</div>(\n   <button class="btn" data-act="saRec")',
       lambda m: '<div class="sa-grid tr-sa">${SA_KEYS.map(k=>`<button class="sa-b ${last===k?\'on\':\'\'}" data-act="saRec" data-k="${kind}" data-sa="${k}">${SA_JP[k]}</button>`).join(\'\')}</div>' + m.group(1),
       flags=re.S)
    R("${kind==='bite'?'そのとき、どう誘っていたかを押すと記録します。':'1/2　そのとき、どう誘っていたか。次に掛け方を選びます。'}",
      "1/2　そのとき、どうしていたか。次にアタリの出方を選びます。")
    R("${kind==='bite'?'誘いなしで記録':'誘いは選ばない（次へ）'}", "誘いは選ばない（次へ）")
    R("if(k!=='bite'&&sa==='fall')return acts.kaRec({dataset:{k,sa,ka:'soku'}});if(k!=='bite')return openKake(k,sa);", "return openKake(k,sa);")
    R("掛け方なしで記録", "出方は選ばずに記録")
    R(".sa-grid .sa-fall{grid-column:1/-1;min-height:52px}",
      ".sa-grid .sa-fall{grid-column:1/-1;min-height:52px}.sa-grid.tr-sa{grid-template-columns:1fr 1fr}.sa-grid.tr-sa .sa-b{min-height:64px;font-size:18px}.ka-grid .sa-b{min-height:64px;font-size:18px}")

    # 振り返りの図：札の文字と色（動かしている間＝塗り、止めている間＝白抜き）
    R("mv=e.sa&&e.sa.endsWith('move'),st=e.sa&&e.sa.endsWith('stay')", "mv=e.sa&&['shakuri','fall','maki'].includes(e.sa),st=e.sa&&e.sa.startsWith('stay')")
    R("e.sa.startsWith('maki')?'巻':e.sa==='fall'?'フ':'叩'", ab(SA) + "[e.sa]||''")
    R("e.ka==='soku'?'即':'深'", ab(KA) + "[e.ka]||''")
    R("label(top,'誘い・掛け方','詳細モードの記録')", "label(top,'誘い・アタリ','詳細モードの記録')")
    R("'誘い・掛け方ごとの数'", "'誘い・アタリの出方ごとの数'")
    leg = ('if(dv.length){y+=22;o.push(`<rect x="24" y="${y-12}" width="16" height="16" rx="3" fill="${P.catch}"/>`+TX(32,y+1,\'シ\',{size:10,bold:1,fill:\'#fff\',anchor:\'middle\'})+TX(46,y,\'動かしている間（塗り）\',{size:12,fill:P.muted})'
           '+`<rect x="196" y="${y-12}" width="16" height="16" rx="3" fill="#fff" stroke="${P.catch}" stroke-width="1.6"/>`+TX(204,y+1,\'直\',{size:10,bold:1,fill:P.catch,anchor:\'middle\'})+TX(218,y,\'止めている間（白抜き）　枠の色＝釣れた／アタリ／バラシ\',{size:12,fill:P.muted}));'
           'y+=20;o.push(TX(24,y,\'' + '　'.join('%s＝%s' % (a, j) for _, j, a in SA) + '\',{size:12,fill:P.muted}));'
           'y+=20;o.push(TX(24,y,\'' + '　'.join('%s＝%s' % (a, j) for _, j, a in KA) + '\',{size:12,fill:P.muted}))}')
    RX(r"if\(dv\.length\)\{y\+=22;o\.push\(`<rect x=\"24\" y=\"\$\{y-12\}\" width=\"16\" height=\"16\" rx=\"3\" fill=\"\$\{P\.catch\}\"/>`\+TX\(32,y\+1,'巻'.*?枠の色＝釣れた／アタリ／バラシ',\{size:12,fill:P\.muted\}\)\)\}",
       lambda m: leg)

    # 説明の文
    R("誘い（巻き／叩き × 誘い中／ステイ中）と掛け方（即掛け／深追い）を選んで記録します。",
      "誘い（" + SA_TXT + "）とアタリの出方（" + KA_TXT + "）を選んで記録します。")
    R("<b>誘い</b>（巻き／叩き × 誘い中／ステイ中、またはフォール中）と、<b>掛け方</b>（即掛け／深追い）を選んで記録します。アタリは誘いだけ、フォールの釣れた・バラシは即掛けとして記録します。",
      "<b>誘い</b>（" + SA_TXT + "）と、<b>アタリの出方</b>（" + KA_TXT + "）を選んで記録します。")
    R("<h3>掛け方ごと</h3>", "<h3>アタリの出方ごと</h3>")
    s = s.replace('誘い・掛け方', '誘い・アタリの出方').replace('誘いと掛け方', '誘いとアタリの出方').replace('誘いや掛け方', '誘いやアタリの出方')
    s = s.replace('：掛け方</h2>', '：アタリの出方</h2>').replace('}掛け方を押すと記録します', '}アタリの出方を押すと記録します')
    left = [m.group(0) for m in re.finditer(r'.{0,30}(掛け方|叩き|即掛け|深追い).{0,30}', s)]
    left = [x for x in left if 'HAYABUSA' not in x and '誘い速掛' not in x]
    if left:
        raise SystemExit('tipran_sasoi: left over: ' + ' / '.join(left[:6]))
    return s


if __name__ == '__main__':
    s = open(TIPRAN, encoding='utf-8').read()
    s2 = apply(s)
    if s2 == s:
        print('already applied')
    else:
        open(TIPRAN, 'w', encoding='utf-8').write(s2)
        print('ok', len(s2))
