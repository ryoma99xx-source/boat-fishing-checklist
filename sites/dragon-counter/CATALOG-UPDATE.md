# ドラゴンカウンター：テンヤカタログの月1回更新（Claude が行う）

毎月1日、定期タスク「テンヤカタログの月次更新」が新しい Claude Code セッションでこの手順を回す。ChatGPT は使わない。

## 守ること（個人のデータを消さないため）

- カタログは**足すだけ**。すでにあるテンヤの メーカー・製品名・号数・カラー の表記は**絶対に変えない・消さない**
  （アプリは所有テンヤをこの4つから作った ID で覚えている。表記を変えると所有テンヤから見えなくなる。念のためアプリ側に名前の控えもあるが、頼らない）
- 発売された・生産終了になった などの「状態」だけは、表記を変えずに `status` で更新できる
- カタログの編集は `tools/catalog_add.py` だけで行う。`public/index.html` の `TENYA_CAT` は触らない
- 個人の所有テンヤ・個数・当日のリスト・自分で追加したテンヤ・釣行の記録は各スマホの中にあり、カタログ更新では変わらない

## 手順

1. `git fetch origin claude/relaxed-mayer-1u2nhq && git checkout claude/relaxed-mayer-1u2nhq`、`pip install scipy`（写真の切り出しが速くなる。無くても動く）
2. `python3 sites/dragon-counter/tools/catalog_add.py --export` で `public/catalog-all.txt` を最新にし、今のカタログ全件を読む。`発売予定` のもの（例：DAIWA 船タチウオテンヤ Rhythm 替えヘッド＝2025年12月に発売延期）は毎回、公式で発売されたか確かめる
3. 調査（WebSearch / WebFetch）。対象は船のタチウオ用テンヤ。メーカー表記は次のどれか：
   DAIWA / SHIMANO / JACKALL / HAYABUSA / OWNER / Major Craft / PRO MARINE / START / YAMASHITA / DUO / がまかつ / マルシン漁具
   - 各メーカーの公式サイト（製品ページ・新製品ニュース）を見る。釣具店やまとめサイトの情報だけでは入れない。推測で埋めない（シマノ公式はこの環境から 403 で見られない。シマノだけは大手釣具店の商品ページで製品名・色名・JAN を確かめてよい）
   - 新しい製品、既存製品の新しい号数・新しいカラーで、カタログに無いもの → `new`
   - カタログにあるものの状態が変わった（発売予定 → 発売、生産終了 など）→ `status`
   - 既にあるテンヤは `catalog-all.txt` の表記と1文字も変えずに書く。新しいテンヤの製品名は、同じ製品があればその表記に合わせ、無ければ公式の製品名どおり。カラーは公式のカラー名どおり。号数ごとに1行
   - `s` は `""` / `発売予定` / `限定色` / `生産終了・在庫のみ` / `売り切れあり` のどれか。替えヘッドは `h: true`。`u` は公式の製品ページ（分かる範囲で）
4. 結果を `/tmp/catalog.json` に書く：
   `{"checked":"YYYY-MM-DD","new":[{"m":"DAIWA","p":"製品名","u":"https://…","h":false,"z":40,"c":"カラー名","s":""}],"status":[{"m":"DAIWA","p":"製品名","z":40,"c":"カラー名","s":""}]}`
5. `python3 sites/dragon-counter/tools/catalog_add.py /tmp/catalog.json` で確認。エラーが出たら、表記を公式で確かめて直す。確かめられなければその行を外す
6. 足すもの・状態が変わるものがあれば `--write` を付けて実行（catalog-extra.json・catalog-all.json・DEPLOY が更新される）
7. **写真**（新しく足したテンヤ・写真が無かったテンヤの分。下の「テンヤの頭の写真」も読む）
   - 公式に色別写真があるメーカーは取得コマンド：`tools/tenya_images.py daiwa|jackall|start|duo|hayabusa`（既にある id は飛ばす）。それ以外は公式製品ページの色別画像を `work/src/<id>.jpg` に置く（id は `python3 -c "import sys;sys.path.insert(0,'sites/dragon-counter/tools');import catalog_add as ca;print(ca.key('DAIWA','製品名',40,'カラー名'))"`）
   - 公式に無ければ釣具店の色別商品写真（店の写真は `work/retail.json` に `{id:{url,page,src,name}}` を足す＝店写真モードで切り出される）。Amazon・シマノ公式は使えない。bot 対策の回避はしない
   - `python3 sites/dragon-counter/tools/tenya_images.py cut <id…>` で切り出し、**必ず確認シートを作って目で見る**（頭だけか・縁が白く荒くないか・色の取り違えが無いか）。欠ける／枠や文字が混ざるときは元画像を頭だけに手で切り抜いて `retail.json` に `plain: true`
   - 写真が見つからない id は、最後の報告に「写真なし：…」と書く（カタログには足したままでよい）
8. `git add sites/dragon-counter` → commit → push（DEPLOY が変わったコミットの push で公開される。写真だけ足したときは `sites/dragon-counter/DEPLOY` の日時行を書き換えてから commit）。数分後に https://dragon-counter.cutlassfish.tokyo/catalog-all.json の `updated`/`count` と https://dragon-counter.cutlassfish.tokyo/tenya/index.json の `ids` の数が変わったことを確認
9. 台帳に記録：ToolSearch で `select:ArtifactData` を読み込み、https://claude.ai/artifact/T4YTywvucGbbGSaWmu3VFQ の `features/f-dragon-catalog` を `get` → `if_version` 付きで `update`：`logs` に `{at, by:'Claude', text:'月次更新：追加 n 件・状態 n 件・写真 n 件（調べたメーカー…）。追加したもの：…。写真なし：…'}` を足し、`status:'公開済み'`、`next:'次回は <翌月1日>'`、`updatedAt`。`meta/heartbeat` も `{at, note:'カタログ更新'}` で更新
10. 最後に、調べたメーカー、追加したテンヤ、状態を変えたテンヤ、足した写真、確かめられず外したもの・写真が無いものを日本語で5行以内にまとめる。足すものが無ければ「追加なし」と一言

## 手で全件リストをもらったとき（例：ChatGPT が出した一覧）

その一覧を上の JSON の形に直して `catalog_add.py` に通す。表記はカタログ側を正とし、一覧側の表記揺れ（全角半角・中黒・スペース）は合わせる。既にあるものは自動で飛ぶので、一覧の全件を `new` に入れてよい。

## テンヤの頭の写真（色見本）

**写真の鉄則（オーナー指示 2026-11-05）：写真は「切り抜くだけ」。元の写真の画素は一切変えない。**
- やってよいのは、背景を透明にする・頭だけに切る・縮小する、だけ。色補正・塗り直し・描き足し・鮮鋭化・形の変更はしない
- 生成 AI（OpenAI の画像生成／編集、ChatGPT の画像機能など）に写真を作らせたり「きれいに」させたりしない。生成 AI の出力は切り抜きではなく描き直しで、目や模様が本物と変わる（試して確認済み）。使うなら元写真の画素をそのまま使う自前の切り抜きだけ
- 縁のにじみ（白背景との混ざり）は、縁の帯で透明度を調整して白を差し引く処理（`defringe`）までは可。帯の内側の画素は触らない
- 頭の形を忠実に：鼻先・ラインアイ・フックアイを欠けさせない。欠けるなら枠や処理を変えるのではなく元写真を手で頭だけに切り抜いて `plain: true`
- 確認は必ず目で（確認シート）。「頭だけか」「縁が白く荒くないか」「色・目・模様が元写真どおりか」「色の取り違えが無いか」

`public/tenya/<id>.webp` に、各テンヤの頭だけを切り出した写真を置いている（`public/tenya/index.json` が一覧。2026-11-05 時点で 646 件すべて。HAYABUSA ベーシックシングル 夜光（SW405）はオーナー提供の写真）。アプリはこの一覧にある id だけ写真を出す。

- 元画像は `work/src/<id>.jpg|png`（git には入れない。2026-11-06 時点の `work/`（元画像 650 件と `retail.json`）は、オーナー専用の非公開 Artifact「テンヤ写真の元データ」 https://claude.ai/artifact/PZEZuQ33VQCs5PVA1qTcZ8 のアセット置き場に退避済み。元画像 650 件・`retail.json`・`vault-index.json`（ファイル名 → sha256）。戻すときは Artifact の `list`（scope assets）で各アセットの sha256 を得て、`vault-index.json` と突き合わせて `read`（path にアセット id）で取り出し、`work/src/<名前>` に置く）。出どころは `work/retail.json`（id → url / page / src / name。手で切り抜いたものは `cropped`、頭だけに切り抜き済みで通常処理にするものは `plain: true`）
- メーカー公式の色別写真：DAIWA（現行品）・JACKALL・START・DUO・HAYABUSA（`tools/tenya_images.py daiwa|jackall|start|duo|hayabusa` で取得）、Major Craft・YAMASHITA・マルシン・HAYABUSA SW409 は公式ページから手動取得
- SHIMANO サーベルマスター 船テンヤ（10 色）・ゲキハヤ（6 色）・β ゲキハヤ（5 色）はオーナー提供の公式カラーチャートから色ごとに切り出し（`work/retail.json` に出どころ）
- 公式に無いもの（SHIMANO のそれ以外・DAIWA 旧型・OWNER・がまかつ・PRO MARINE など）は釣具店の色別商品写真（相模屋・マルニシ・ポイント・ポイント東日本・フィッシングマックス・キャスティング・釣人館 などの Yahoo!店）。店の写真は `retail.json` に載せると「店写真モード」で切り出す（枠線・GLOW バッジ・夜光写真・スナップ・リーダー・フックホルダーを除き、目の位置から頭を探す。同じ店×製品で構図が固定のものは `FIXED` の固定枠）。写真の加工・掲載はオーナーの判断（2026-11-04）
- シマノ公式サイトと Amazon はこの環境から取得できない（403 / 確認ページ）。回避はしない
- 新しい色を足したら：公式があれば上の取得コマンド、無ければ販売店の写真を `tools/tenya_images.py add <id> <file>` で足す（店の写真なら `work/retail.json` にも id と出どころを書く）。全件書き出しは `tools/tenya_images.py cut`（`cut <id…>` / `cut <メーカー>` で一部だけ）。`pip install scipy` があると速い（無くても動く）
- 切り出し結果は必ず目で確認する（確認シートを作って見る）。頭の一部が欠ける・枠や文字が混ざる場合は、元画像を頭だけに手で切り抜いて `plain: true` にするのが早い
