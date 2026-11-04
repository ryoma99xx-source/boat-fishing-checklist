# ドラゴンカウンター：テンヤカタログの月1回更新（Claude が行う）

毎月1日、定期タスク「テンヤカタログの月次更新」が新しい Claude Code セッションでこの手順を回す。ChatGPT は使わない。

## 守ること（個人のデータを消さないため）

- カタログは**足すだけ**。すでにあるテンヤの メーカー・製品名・号数・カラー の表記は**絶対に変えない・消さない**
  （アプリは所有テンヤをこの4つから作った ID で覚えている。表記を変えると所有テンヤから見えなくなる。念のためアプリ側に名前の控えもあるが、頼らない）
- 発売された・生産終了になった などの「状態」だけは、表記を変えずに `status` で更新できる
- カタログの編集は `tools/catalog_add.py` だけで行う。`public/index.html` の `TENYA_CAT` は触らない
- 個人の所有テンヤ・個数・当日のリスト・自分で追加したテンヤ・釣行の記録は各スマホの中にあり、カタログ更新では変わらない

## 手順

1. `git fetch origin claude/relaxed-mayer-1u2nhq && git checkout claude/relaxed-mayer-1u2nhq`
2. `python3 sites/dragon-counter/tools/catalog_add.py --export` で `public/catalog-all.txt` を最新にし、今のカタログ全件を読む
3. 調査（WebSearch / WebFetch）。対象は船のタチウオ用テンヤ。メーカー表記は次のどれか：
   DAIWA / SHIMANO / JACKALL / HAYABUSA / OWNER / Major Craft / PRO MARINE / START / YAMASHITA / DUO / がまかつ / マルシン漁具
   - 各メーカーの公式サイト（製品ページ・新製品ニュース）を見る。釣具店やまとめサイトの情報だけでは入れない。推測で埋めない
   - 新しい製品、既存製品の新しい号数・新しいカラーで、カタログに無いもの → `new`
   - カタログにあるものの状態が変わった（発売予定 → 発売、生産終了 など）→ `status`
   - 既にあるテンヤは `catalog-all.txt` の表記と1文字も変えずに書く。新しいテンヤの製品名は、同じ製品があればその表記に合わせ、無ければ公式の製品名どおり。カラーは公式のカラー名どおり。号数ごとに1行
   - `s` は `""` / `発売予定` / `限定色` / `生産終了・在庫のみ` / `売り切れあり` のどれか。替えヘッドは `h: true`。`u` は公式の製品ページ（分かる範囲で）
4. 結果を `/tmp/catalog.json` に書く：
   `{"checked":"YYYY-MM-DD","new":[{"m":"DAIWA","p":"製品名","u":"https://…","h":false,"z":40,"c":"カラー名","s":""}],"status":[{"m":"DAIWA","p":"製品名","z":40,"c":"カラー名","s":""}]}`
5. `python3 sites/dragon-counter/tools/catalog_add.py /tmp/catalog.json` で確認。エラーが出たら、表記を公式で確かめて直す。確かめられなければその行を外す
6. 足すものがあれば `--write` を付けて実行 → `git add sites/dragon-counter` → commit → push（push で公開される）。数分後に https://dragon-counter.cutlassfish.tokyo/catalog-all.json の `updated` と `count` が変わったことを確認
7. 台帳に記録：ToolSearch で `select:ArtifactData` を読み込み、https://claude.ai/artifact/T4YTywvucGbbGSaWmu3VFQ の `features/f-dragon-catalog` を `get` → `if_version` 付きで `update`：`logs` に `{at, by:'Claude', text:'月次更新：追加 n 件・状態 n 件（調べたメーカー…）。追加したもの：…'}` を足し、`status:'公開済み'`、`next:'次回は <翌月1日>'`、`updatedAt`。`meta/heartbeat` も `{at, note:'カタログ更新'}` で更新
8. 最後に、調べたメーカー、追加したテンヤ、状態を変えたテンヤ、確かめられず外したものを日本語で5行以内にまとめる。足すものが無ければ「追加なし」と一言

## 手で全件リストをもらったとき（例：ChatGPT が出した一覧）

その一覧を上の JSON の形に直して `catalog_add.py` に通す。表記はカタログ側を正とし、一覧側の表記揺れ（全角半角・中黒・スペース）は合わせる。既にあるものは自動で飛ぶので、一覧の全件を `new` に入れてよい。
