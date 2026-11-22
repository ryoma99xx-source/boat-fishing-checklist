"""タイラバカウンター：座席の片舷／両舷を選べる（seat_lay.py。選んでいなければ両舷）と、初期登録の船。オーナー指示 2026-11-22。

  初期登録の船（同じ名前がすでにあれば足さない。一度だけ）
    長谷川丸　　　：両舷・10人
    のんちゃん丸　：片舷（右舷）・8人
    なぶらフィッシング・村本海事・野毛屋：名前だけ（人数・片舷／両舷は決めない）
  船には片舷／両舷と舷も覚えさせ、船を選ぶとそれが入る。
"""
import seat_lay

MARK = '/* tairaba-seats v1 */'
BOATS = [('長谷川丸', {'people': 10, 'lay': 'both'}), ('のんちゃん丸', {'people': 8, 'lay': 'one', 'side': 'R'}),
         ('なぶらフィッシング', {}), ('村本海事', {}), ('野毛屋', {})]


def apply(s):
    if MARK in s:
        return s
    s = seat_lay.apply(s, 'both', one_label=('片舷', '（片側だけ）'), both_label=('両舷', '（両側）'))

    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('tairaba_seats: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    import json
    js = json.dumps([dict(name=n, **v) for n, v in BOATS], ensure_ascii=False, separators=(',', ':'))
    # 初期登録の船（一度だけ。すでに同じ名前があれば足さない）
    R("M.boats1=1}", "M.boats1=1}\n  " + MARK + "\n  if(!M.tbBoats1){c.boats=c.boats||[];for(const d of " + js + "){if(!c.boats.some(b=>b.name===d.name))c.boats.push({id:uid(),spots:[],...d})}M.tbBoats1=1}")
    # 船に片舷／両舷と舷を覚えさせる・船を選ぶと入る
    R("function registerBoat(tr){const b=S.cfg.boats.find(x=>x.name===tr.boat);const v={people:tr.people||tr.seats*2,seats:tr.seats,side:tr.side,seat:tr.seat};",
      "function registerBoat(tr){const b=S.cfg.boats.find(x=>x.name===tr.boat);const v={people:tr.people||tr.seats*2,seats:tr.seats,side:tr.side,seat:tr.seat,lay:tr.lay||'both'};")
    R("Object.assign(f,{boat:bt.name,people:bt.people||(bt.seats?bt.seats*2:f.people)});",
      "Object.assign(f,{boat:bt.name,people:bt.people||(bt.seats?bt.seats*2:f.people)});if(bt.lay){f.lay=bt.lay;f.seat=null}if(bt.side)f.side=bt.side;")
    # 船を選んだら、片舷／両舷の切り替えも描き直す
    R("if(sheetCtx&&sheetCtx.kind==='trip')openTripSheet(sheetCtx.id,f);else render()},\n  fRig:",
      "if(sheetCtx&&sheetCtx.kind==='trip')openTripSheet(sheetCtx.id,f);else render()},\n  fRig:")
    s = s.replace('片舷流し', '片舷')   # タイラバは「片舷」と呼ぶ（流し方の名前ではない）
    return s
