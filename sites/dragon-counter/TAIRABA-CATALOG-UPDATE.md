# タイラバカウンター：ヘッド・ネクタイ・スカートのカタログの月1回更新（Claude が行う）

毎月、定期タスク「タイラバのカタログの月次更新」が新しい Claude Code セッションでこの手順を回す（オーナー指示 2026-11-26）。
対象は3つ：アプリ（タイラバカウンター `/tairaba/` のカタログ）、カタログのページ（`/tairaba-catalog/`＝ヘッド・スカート、`/tairaba-catalog/ties/`＝ネクタイ）、同じ中身の記事2本。

## 守ること（個人のデータを消さないため）

- カタログは**足すだけ**。すでにあるヘッド・ネクタイ・スカートの メーカー・製品名・色・重さ の表記は**絶対に変えない・消さない**
  （アプリは持っているものを「メーカー|製品|色」で覚えている。表記が変わると、持っている人の登録が見えなくなる）
- 生産終了になったものも消さない。調査ファイルに `discontinued: true` を**付けない**（付けるとカタログから消える）。そのまま残す
- 毎回 `tools/tairaba_check_addonly.py` で「足すだけ」になっているかを確かめる。消えた・名前が変わったものが出たら、直すまで公開しない
- `tools/tairaba/research/flea.json`（フリマアプリ系）はさわらない（オーナーが写真を選んだもの）
- ドラゴンカウンター（`public/index.html`）とティップランカウンター（`public/tipran/`）は変えない
- 個人の登録・釣行の記録は各スマホの中にあり、カタログ更新では変わらない

## 手順

1. `git fetch origin claude/relaxed-mayer-1u2nhq && git checkout claude/relaxed-mayer-1u2nhq`、`cd sites/dragon-counter`、`export PYTHONDONTWRITEBYTECODE=1`
2. 今のカタログを控える：`cp tools/tairaba/catalog.json /tmp/tb-catalog-before.json`
3. 調査（WebSearch / WebFetch）。対象はタイラバ（鯛ラバ）のヘッド、ネクタイ（ワームのネクタイ・ネクタイと針の替えユニットも含む）、スカート。
   メーカーは `tools/tairaba/research/` にあるメーカー（表記は各ファイルの `maker` どおり。製品ごとの `url` が前に確かめたページ）
   - 各メーカーの公式サイト・公式ショップ（製品ページ・新製品ニュース）を見る。まとめサイトの情報だけでは入れない。推測で埋めない
     - シマノ公式と Amazon はこの環境から見られない。シマノだけは大手釣具店の商品ページで製品名・色名を確かめてよい
     - 公式サイトが無いメーカー（ソルトウォーターボーイズなど）は、調査ファイルの `note` にある販売店のページで確かめる
   - 新しい製品、既存製品の新しい色・重さで、カタログに無いもの → 調査ファイルに**足す**
     - ヘッド：`heads` に `{"series","url","material","type","weights":[…],"colors":[…],"note"}`、または既存の製品の `weights` / `colors` の**後ろに**足す
     - ネクタイ：`ties` に `{"series","url","shape","colors":[…],"note"}`、または既存の `colors` の後ろに足す
     - スカート：`skirts` に `{"series","url","colors":[…]}`、または既存の `colors` の後ろに足す
     - 製品名・色名は公式どおり。既にある製品は、その表記に1文字も変えずに合わせる
     - UROKODO は、ショップの商品を型（AT・ATW・ST・WT・RW・WW・FAT-W・CORE-W・AT＋）ごとの製品にまとめてある。新しい商品は、その型の製品の `colors` に「色の名前 品番（柄）」の形で足す
   - 新しいメーカーを足すときは、`research/<名前>.json` を作り、`tools/tairaba_catalog.py` の `ORDER` に名前を足す（足す前にオーナーに聞かなくてよいのは、すでにカタログにあるメーカーの新製品だけ。新しいメーカーは報告に「候補」として書くだけにする）
4. `python3 tools/tairaba_catalog.py tools/tairaba/research --date YYYY-MM-DD`（今日の日付）でカタログを作り直す
5. `python3 tools/tairaba_check_addonly.py /tmp/tb-catalog-before.json` で確認。「消えた・名前が変わった」が出たら、調査ファイルを直して 4 からやり直す。
   足すものが無ければ（追加 0 件）、`git checkout tools/tairaba/catalog.json` で日付を戻し、何も公開せずに 11 の報告へ
6. **色ごとの写真**（新しく足した色の分。下の鉄則を必ず守る）
   - 公式の色別写真（無ければ大手釣具店の色別商品写真）を `work/tairaba-img/<メーカー>/raw/` に置き、
     `work/tairaba-img/<メーカー>/manifest-<メーカー>.json` = `[{"kind":"heads|ties|skirts","series","color","image_url","file":"raw/…","source":"official|<店の名前>","note":"","crop":[x0,y0,x1,y1]（要るときだけ）,"asis":true（白地に白い製品のときだけ）}]` を書く。
     `series`・`color` は、作り直したあとの `tools/tairaba/catalog.json` の `s`・`c` と1文字も違わないこと
   - `python3 tools/tairaba_images.py work/tairaba-img`（前からある写真は残る。足した分だけ `public/tairaba/img/` と `tools/tairaba/images.json` に入る。「not matched」が 0 であること）
   - **必ず確認シートを作って目で見る**（その製品のその色だけが写っているか・色の取り違えが無いか）。1枚に何色も写った写真は使わない。迷ったら写真なしにする。写真が見つからない色は報告に「写真なし：…」と書く（カタログには足したままでよい）
7. **形の写真**（新しく足したネクタイ・スカートの製品で、色ごとの写真が色見本・アップだけ、または写真が1枚も無いとき）
   - その製品の全体の形がわかる公式の写真を1枚、`work/tairaba-shape/<メーカー>/raw/` に置き、
     `work/tairaba-shape/<メーカー>/shapes-<メーカー>.json` = `[{"series","ok":false,"why":"","image_url","file":"raw/…","source","crop"（要るときだけ）}]` を書く（スカートは `work/tairaba-shape/skirts/shapes-skirts.json` で、各行に `"maker"` も書く）
   - `python3 tools/tairaba_shapes.py work/tairaba-shape`（前からある形の写真は残る。`tools/tairaba/shapes.json`）
   - 形の写真は、同じ製品だけが写っていれば何色か並んだ写真でもよい。別の製品の写真は使わない
8. アプリとページを作り直す（順番が大事）：
   `python3 tools/tairaba_build.py` → `python3 tools/tipran_build.py` → `git checkout public/tipran/index.html`（ティップランは変えない。差が出ていなければ何も起きない）
   → `python3 tools/tairaba_stats.py`（数の表）→ `python3 tools/tairaba_page.py`（カタログのページ2つと記事の元）
   - サイトマップ・AI向けの案内・構造化データは、これらのスクリプトが自動で作り直す（`tools/seo_extras.py`）
   - ネクタイに製品・メーカーを足したときは、`tools/tairaba_page.py` の `TIE_UPDATES` のいちばん上に1行足してから `tairaba_page.py` を回す
     （例：`('2026/12/03', 'ダイワ・ジャッカルの新製品を追加しました。いまは<b>%(nm)dメーカー・%(np)d製品・%(nc)d色</b>です。')`。文の中に % をそのまま書くときは %% にする。記事には新しい3つまで出る）
9. `DEPLOY` の2行目を書き換えて、`git add sites/dragon-counter wordpress/tairaba-head-catalog wordpress/tairaba-tie-catalog` → commit → push（DEPLOY が変わったコミットの push で公開される。`work/` は git に入らない）。
   数分後に https://dragon-counter.cutlassfish.tokyo/tairaba-catalog/ と https://dragon-counter.cutlassfish.tokyo/tairaba-catalog/ties/ の製品数・色数が変わったことを確かめる
10. **記事も更新する**：`python3 tools/tairaba_page.py --push`。ヘッドの記事（記事ID 1569）とネクタイの記事（記事ID 1571）の本文とアイキャッチが、いまのカタログで差し替わる
    - 環境変数 `WP_USER` / `WP_APP_PASSWORD` が要る（値は表示しない）。無いとき・失敗したときは、そのまま報告に書く（ページは更新済みなので、作業は止めない）
    - ネクタイの記事は WordPress の取り込みの上限（本文 1MB）に近い。「大きすぎます」と出たら、記事は更新せずに報告に書く（直し方はオーナーと相談）
    - 終わったら `git add wordpress/tairaba-catalog-posts.json wordpress/tairaba-head-catalog wordpress/tairaba-tie-catalog` → commit → push
11. 最後に、調べたメーカー、追加したもの（製品・色・重さ）、足した写真、確かめられず外したもの・写真が無いもの、新しいメーカーの候補、記事を更新できたかを日本語で5行以内にまとめる。足すものが無ければ「追加なし」と一言

## 写真の鉄則（オーナー指示）

- 写真は「切り抜く」と「縮める」だけ。元の写真の画素は一切変えない。色補正・塗り直し・描き足し・鮮鋭化・形の変更をしない
- 生成 AI（画像の生成・編集）で写真を作ったり加工したりしない
- 写真は公式のもの。公式に無い色だけ、大手釣具店の色別の商品写真（店の名前を `source` に書く）。ある色の写真を別の色に使い回さない
- bot 対策や確認ページの回避はしない
