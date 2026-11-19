# ティップランカウンター：エギ・シンカーカタログの月1回更新（Claude が行う）

毎月、定期タスク「ティップランのエギ・シンカーカタログの月次更新」が新しい Claude Code セッションでこの手順を回す。
対象は2つ：アプリ（ティップランカウンター `/tipran/` のエギ・シンカーのカタログ）と、カタログのページ（`/egi-catalog/`）・同じ中身の記事。

## 守ること（個人のデータを消さないため）

- カタログは**足すだけ**。すでにあるエギ・シンカーの メーカー・製品名・色・号数・重さ の表記は**絶対に変えない・消さない**
  （アプリは持っているエギを「メーカー|製品|色」、シンカーを「メーカー|製品|重さ|色」で覚えている。表記が変わると、持っている人の登録が見えなくなる）
- 生産終了になったものも消さない。エギは調査ファイルの `legacy: true`（画面では「旧モデル（生産終了）」）で残す
- 毎回 `tools/tipran_check_addonly.py` で「足すだけ」になっているかを確かめる。消えた・名前が変わったものが出たら、直すまで公開しない
- 個人の登録・釣行の記録は各スマホの中にあり、カタログ更新では変わらない

## 手順

1. `git fetch origin claude/relaxed-mayer-1u2nhq && git checkout claude/relaxed-mayer-1u2nhq`、`cd sites/dragon-counter`、`export PYTHONDONTWRITEBYTECODE=1`
2. 今のカタログを控える：`cp tools/tipran/catalog.json /tmp/catalog-before.json`
3. 調査（WebSearch / WebFetch）。対象はボート・ティップラン用のエギ（2.5号以上）と、エギに足すシンカー（増し錘）。メーカーは `tools/tipran/research/` と `tools/tipran/research-sinkers/` にあるメーカー（表記はそのファイルどおり）
   - 各メーカーの公式サイト（製品ページ・新製品ニュース）を見る。釣具店やまとめサイトの情報だけでは入れない。推測で埋めない（シマノ公式と Amazon はこの環境から見られない。シマノだけは大手釣具店の商品ページで製品名・色名・JAN を確かめてよい）
   - 新しい製品、既存製品の新しい号数・重さ・色で、カタログに無いもの → 調査ファイルに**足す**
     - エギ：`tools/tipran/research/<maker>.json` の `egis` に製品を足す、または既存の製品の `colors` / `sizes` の**後ろに**足す（`{"series","url","sizes":[{"size":"3.5","weights":[30]}],"colors":[…]}`）
     - シンカー：`tools/tipran/research-sinkers/<maker>.json` の `sinkers` に足す、または既存の `weights` / `colors` に足す（重さで色が違うときは `colorsByWeight`）
     - 製品名・色名は公式どおり。既にある製品は、その表記に1文字も変えずに合わせる
   - 生産終了になったエギは `legacy: true` を付けるだけ（`discontinued` だけにすると消えてしまうので注意）
4. `python3 tools/tipran_catalog.py tools/tipran/research --date YYYY-MM-DD`（今日の日付）でカタログを作り直す
5. `python3 tools/tipran_check_addonly.py /tmp/catalog-before.json` で確認。「消えた・名前が変わった」が出たら、調査ファイルを直して 4 からやり直す。足すものが無ければ（追加 0 件）9 へ
6. **写真**（新しく足した色の分。写真は「切り抜くだけ」。下の鉄則を必ず守る）
   - エギ：公式の色別写真（無ければ釣具店の色別商品写真）を `work/egi/raw/` に置き、`work/egi/manifest-<メーカー>.json` = `[{"series","color","image_url","file":"raw/…","source"}]` を書いて `python3 tools/tipran_images.py work/egi`（既にある写真は残る。足した分だけ `public/tipran/egi/` と `tools/tipran/egi-images.json` に入る）
   - シンカー：`work/sinker/raw/` に置き、`work/sinker/manifest.json` = `[{"m","s","color","image_url","file":"raw/…","source"}]`（color "" は製品全体の写真）を書いて `python3 tools/sinker_images.py work/sinker`（`public/tipran/sinker/` と `tools/tipran/sinker-images.json`。シンカーの写真はカタログのページと記事だけに出す。アプリには出さない）
   - **必ず確認シートを作って目で見る**（そのエギ・シンカーだけが写っているか・色の取り違えが無いか・文字や別の写真が混ざっていないか）。写真が見つからない色は報告に「写真なし：…」と書く（カタログには足したままでよい）
   - `work/` は git に入れない
7. アプリを作り直す（順番が大事）：`python3 tools/tairaba_build.py` → `python3 tools/tipran_build.py` → `git checkout public/tairaba/index.html`（タイラバは変えない）
8. カタログのページと記事の元を作り直す：`python3 tools/egi_page.py`
9. `DEPLOY` の日時行を書き換えて、`git add sites/dragon-counter wordpress/egi-catalog` → commit → push（DEPLOY が変わったコミットの push で公開される）。数分後に https://dragon-counter.cutlassfish.tokyo/egi-catalog/ の製品数・色数が変わったことを確かめる
10. **記事も更新する**：`python3 tools/egi_page.py --push`。エギ・シンカーカタログの記事（https://cutlassfish.tokyo/article/tipran-egi-catalog/ 、記事ID 1420）の本文とアイキャッチが、いまのカタログで差し替わる（オーナーの指示で、この記事はカタログに合わせて毎月更新する）
    - 環境変数 `WP_USER` / `WP_APP_PASSWORD` が要る（値は表示しない）。無いとき・失敗したときは、そのまま報告に書く（ページは更新済みなので、作業は止めない）
    - 終わったら `git add wordpress/egi-catalog` → commit → push（アイキャッチが変わったときは `featured.json` が書き換わる）
11. 最後に、調べたメーカー、追加したエギ・シンカー（製品・色・号数・重さ）、旧モデルにしたもの、足した写真、確かめられず外したもの・写真が無いもの、記事を更新できたかを日本語で5行以内にまとめる。足すものが無ければ「追加なし」と一言

## 写真の鉄則（オーナー指示）

- 写真は「切り抜くだけ」。元の写真の画素は一切変えない。色補正・塗り直し・描き足し・鮮鋭化・形の変更をしない
- 生成 AI（画像の生成・編集）で写真を作ったり加工したりしない
- やってよいのは、そのエギ・シンカーの周りで切る・縮小する、だけ（`tipran_images.py` / `sinker_images.py` がやる）
- bot 対策や確認ページの回避はしない
