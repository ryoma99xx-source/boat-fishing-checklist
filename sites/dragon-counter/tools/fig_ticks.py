"""振り返りの図（時系列）：横軸の時刻を、釣りをした時間の長さに合わせた間隔で入れる。オーナー指示 2026-11-23。

これまでは1時間ごとの点線が帯の下に隠れ、時刻は図のいちばん下にしか出ていなかった。
  間隔：2時間半まで＝15分、8時間半まで＝30分、14時間まで＝1時間、それより長い＝2時間
  時刻は図の上（帯の上の行）と下の両方に出し、縦の点線は帯の上に薄く重ねる（ちょうどの時刻は少し濃く）。

    apply(s)
3つのカウンター共通（2026-11-23）：ドラゴンカウンターの public/index.html に一度だけ当てて保存済み。
タイラバ・ティップランはそこから作るので、ビルドでは呼ばない（もう一度当てると数が合わず止まる）。
"""


def apply(s):
    def R(old, new, n=1):
        nonlocal s
        c = s.count(old)
        if c != n:
            raise SystemExit('fig_ticks: %d (want %d): %s' % (c, n, old[:90]))
        s = s.replace(old, new)

    R("if(b)o.push(TX(26,top+46,b,{size:11,fill:P.muted}))};const gridTop=y;",
      "if(b)o.push(TX(26,top+46,b,{size:11,fill:P.muted}))};y+=24;const gridTop=y;")
    R("const H1=3600e3;for(let h=Math.ceil(t0/H1)*H1;h<=t1;h+=H1){const x=X(h);under.push(`<line x1=\"${r1(x)}\" y1=\"${gridTop}\" x2=\"${r1(x)}\" y2=\"${y}\" stroke=\"${P.grid}\" stroke-dasharray=\"3 4\"/>`);o.push(TX(x,y+20,hm(h),{size:12,fill:P.muted,anchor:'middle'}))}",
      "{const H1=3600e3,DU=t1-t0,ST=DU<=2.5*H1?H1/4:DU<=8.5*H1?H1/2:DU<=14*H1?H1:2*H1;"
      "for(let h=Math.ceil(t0/ST)*ST;h<=t1;h+=ST){const x=X(h),mj=h%H1===0;"
      "o.push(`<line x1=\"${r1(x)}\" y1=\"${gridTop}\" x2=\"${r1(x)}\" y2=\"${y}\" stroke=\"#7f93a6\" stroke-width=\"${mj?1.2:0.8}\" stroke-dasharray=\"${mj?'4 4':'2 5'}\" opacity=\"${mj?0.6:0.4}\" pointer-events=\"none\"/>`);"
      "o.push(TX(x,gridTop-8,hm(h),{size:mj?13:11,bold:mj?1:0,fill:mj?P.ink:P.muted,anchor:'middle'}));"
      "o.push(TX(x,y+20,hm(h),{size:mj?13:11,bold:mj?1:0,fill:mj?P.ink:P.muted,anchor:'middle'}))}}")
    return s
