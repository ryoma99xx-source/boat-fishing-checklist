"""座席の「片舷／両舷」（trip.lay = 'one' | 'both'）。ティップランカウンター（基本は片舷流し）とタイラバカウンター（選べる）で使う。

    apply(s, default='one', one_label=('片舷流し', '（基本）'), both_label=('両舷', '（バーティカル）'))
default は、選んでいない釣行・前の記録の扱い。ティップランは 'one'、タイラバは 'both'（ドラゴンカウンターと同じ両舷）。
"""


def apply(s, default='one', one_label=('片舷流し', '（基本）'), both_label=('両舷', '（バーティカル）')):
    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('seat_lay: %d (want %d): %s' % (c, n, old[:90]))
        if default != 'one':
            new = new.replace("||'one'", "||'%s'" % default)
        new = new.replace('片舷流し<small>（基本）</small>', '%s<small>%s</small>' % one_label).replace('両舷<small>（バーティカル）</small>', '%s<small>%s</small>' % both_label)
        s = s.replace(old, new)

    # ───────── 座席：基本は片舷流し（全員が片側に並ぶ）。両舷・バーティカルも選べる。trip.lay = 'one' | 'both'
    R("function fixPeople(f){f.people=clampP(f.people);f.seats=perSide(f.people);",
      "function fixPeople(f){f.people=clampP(f.people);f.lay=f.lay||'one';f.seats=f.lay==='one'?f.people:perSide(f.people);if(f.side!=='L')f.side='R';")
    R("end:(b&&b.end)||'13:30',memo:''}}", "end:(b&&b.end)||'13:30',memo:'',lay:S.prefs.lay||'one'}}")
    R("function formFromTrip(tr){return {mode:'edit',id:tr.id,date:tr.date,boat:tr.boat,people:tr.people||tr.seats*2,seats:tr.seats,side:tr.side,seat:tr.seat,",
      "function formFromTrip(tr){return {mode:'edit',id:tr.id,date:tr.date,boat:tr.boat,lay:tr.lay||'one',people:tr.people||(tr.lay==='both'?tr.seats*2:tr.seats),seats:tr.seats,side:tr.side,seat:tr.seat,")
    R("people:f.people,seats:f.seats,side:f.side,seat:f.seat,station:f.station,", "people:f.people,seats:f.seats,side:f.side,seat:f.seat,lay:f.lay||'one',station:f.station,")
    R("Object.assign(tr,{date:f.date,boat:f.boat.trim(),people:f.people,seats:f.seats,side:f.side,seat:f.seat,memo:f.memo});",
      "Object.assign(tr,{date:f.date,boat:f.boat.trim(),people:f.people,seats:f.seats,side:f.side,seat:f.seat,lay:f.lay||'one',memo:f.memo});")
    R("Object.assign(S.prefs,{boat:tr.boat,seats:tr.seats,side:tr.side,seat:tr.seat,", "Object.assign(S.prefs,{boat:tr.boat,seats:tr.seats,side:tr.side,seat:tr.seat,lay:tr.lay,")
    R("<b>${esc(seatLabel({side:f.side,seat:f.seat,seats:f.seats}))}</b><span class=\"muted\">${f.side==='L'?'左':'右'}舷・前から${f.seat}番目／${f.people}人（片舷${f.seats}席）</span>",
      "<b>${esc(seatLabel({side:f.side,seat:f.seat,seats:f.seats,lay:f.lay}))}</b><span class=\"muted\">${f.lay==='one'?`片舷流し（${f.side==='L'?'左':'右'}舷）・前から${f.seat}番目／${f.people}人`:`${f.side==='L'?'左':'右'}舷・前から${f.seat}番目／${f.people}人（片舷${f.seats}席）`}</span>")
    R("for(const side of ['L','R'])for(let i=1;i<=sideSeats(f,side);i++){const y=side==='L'?34:96,", "for(const side of (f.lay==='one'?[f.side||'R']:['L','R']))for(let i=1;i<=sideSeats(f,side);i++){const y=side==='L'?34:96,")
    R("for(const side of ['L','R'])for(let i=1;i<=sN(side);i++){const x=side==='L'?xl:xr,", "for(const side of (tr.lay==='one'?[tr.side||'R']:['L','R']))for(let i=1;i<=sN(side);i++){const x=side==='L'?xl:xr,")
    R('<text x="180" y="20" text-anchor="middle" font-size="12" style="fill:var(--muted)">左舷</text><text x="180" y="124" text-anchor="middle" font-size="12" style="fill:var(--muted)">右舷</text>',
      '${f.lay===\'one\'?`<text x="180" y="${f.side===\'L\'?20:124}" text-anchor="middle" font-size="12" style="fill:var(--muted)">${f.side===\'L\'?\'左\':\'右\'}舷（片舷流し）</text>`:\'<text x="180" y="20" text-anchor="middle" font-size="12" style="fill:var(--muted)">左舷</text><text x="180" y="124" text-anchor="middle" font-size="12" style="fill:var(--muted)">右舷</text>\'}')
    R('   <div class="seatwrap"><div id="seatPick">${seatPickerSVG(f)}</div>',
      '   ${layHTML(f)}<div class="seatwrap"><div id="seatPick">${seatPickerSVG(f)}</div>')
    R("function seatPickerSVG(f){", "function layHTML(f){const l=f.lay||'one';return `<div class=\"seg\" id=\"laySeg\" style=\"margin:4px 0 8px\"><button class=\"${l==='one'?'on':''}\" data-act=\"pickLay\" data-d=\"one\">片舷流し<small>（基本）</small></button><button class=\"${l==='both'?'on':''}\" data-act=\"pickLay\" data-d=\"both\">両舷<small>（バーティカル）</small></button></div>${l==='one'?`<div class=\"chips\" id=\"sideSeg\" style=\"margin:0 0 8px\"><span class=\"muted\" style=\"align-self:center\">釣り座の舷</span>${[['R','右舷'],['L','左舷']].map(([k,t])=>`<button class=\"chip ${(f.side||'R')===k?'on':''}\" data-act=\"pickSide\" data-d=\"${k}\" aria-pressed=\"${(f.side||'R')===k}\">${t}</button>`).join('')}</div>`:''}`}\nfunction seatPickerSVG(f){")
    R("  pickSeat:b=>{", "  pickLay:b=>{const f=curForm;if(!f)return;f.lay=b.dataset.d;f.seat=null;fixPeople(f);refreshSeat();const g=$('#laySeg'),h=$('#sideSeg');if(h)h.remove();if(g)g.outerHTML=layHTML(f)},\n  pickSide:b=>{const f=curForm;if(!f)return;f.side=b.dataset.d;f.seat=null;refreshSeat();const g=$('#laySeg'),h=$('#sideSeg');if(h)h.remove();if(g)g.outerHTML=layHTML(f)},\n  pickSeat:b=>{")
    R("const z={};real.forEach(t=>{const k=t.side+seatZone(t);", "const z={};real.forEach(t=>{const k=(t.lay==='one'?'O':t.side)+seatZone(t);")
    R("const nm=(side==='L'?'左':'右')+zone;", "const nm=(side==='L'?'左':side==='O'?'':'右')+zone;")
    R("return chips+`<div class=\"zones\">${['ミヨシ寄り','胴の間','トモ寄り'].map(zn=>cell('L',zn)+cell('R',zn)).join('')}</div><div class=\"zones-foot\">トモ</div>`}",
      "const one=Object.keys(z).some(k=>k[0]==='O'),both=Object.keys(z).some(k=>k[0]!=='O');return chips+(one?`<p class=\"muted\" style=\"margin:6px 0 4px\">片舷流し</p><div class=\"zones\" style=\"grid-template-columns:1fr\">${['ミヨシ寄り','胴の間','トモ寄り'].map(zn=>cell('O',zn)).join('')}</div>`:'')+(both?`${one?'<p class=\"muted\" style=\"margin:10px 0 4px\">両舷・バーティカル</p>':''}<div class=\"zones\">${['ミヨシ寄り','胴の間','トモ寄り'].map(zn=>cell('L',zn)+cell('R',zn)).join('')}</div><div class=\"zones-foot\">トモ</div>`:'')}")

    R("o.push(TX(xl-40,240,'左舷',{size:14,fill:P.muted,anchor:'middle'}));o.push(TX(xr+40,240,'右舷',{size:14,fill:P.muted,anchor:'middle'}));",
      "if(tr.lay!=='one'){o.push(TX(xl-40,240,'左舷',{size:14,fill:P.muted,anchor:'middle'}));o.push(TX(xr+40,240,'右舷',{size:14,fill:P.muted,anchor:'middle'}))}else o.push(TX(tr.side==='L'?xl-40:xr+40,240,tr.side==='L'?'左舷':'右舷',{size:14,fill:P.muted,anchor:'middle'}));")
    # ───────── 片舷流しの人数は、はじめ8人（両舷は16人）。前に選んだ人数があればそれを使う
    R("people:b?(b.people||b.seats*2):(p.people||(p.seats||8)*2)", "people:b?(b.people||b.seats*2):(p.people||((p.lay||'one')==='one'?8:16))")
    return s
