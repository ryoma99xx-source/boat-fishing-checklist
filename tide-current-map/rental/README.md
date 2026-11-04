# 東京湾の潮と流れ — レンタルサーバー版

## これは何か

今 ChatGPT Sites で動いている「東京湾の潮と流れ」（https://tide-current-map.cutlassfish.tokyo/ ）を、
お名前.com レンタルサーバー（PHP＋ふつうのファイル）でも同じように動かすための仕組みです。

- 画面・データ・URL は今と同じです。アプリ本体は別ブランチ（`claude/funny-dijkstra-n8oyg0` の `tide-current-map/app/`）にあり、
  ここにはサーバー用に組み立てるスクリプトだけを置いています。
- 潮位（気象庁）・潮流推算（海上保安庁）を取りに行く部分は PHP（`/api/tide`・`/api/current`）、Google 地図キーを返す部分も PHP（`/api/map-config`）です。
- 今の ChatGPT Sites のサイトには何も変更を加えません。DNS を切り替えるまで、公開中のサイトはそのままです。

中身：

| ファイル | 役割 |
| --- | --- |
| `build-rental.mjs` | アプリからサーバーに置くファイル一式（HTML・JS・データ・PHP・.htaccess）を作る |
| `php/` | PHP と .htaccess のひな形 |
| `test/compare.mjs` | 今の版（Worker）と全URLの中身・ヘッダーを比べるテスト |
| `../../.github/workflows/deploy-tide-rental.yml` | GitHub からサーバーへ FTPS でアップロードする手順 |

## 1. GitHub に秘密情報を登録する（最初の1回だけ）

GitHub のこのリポジトリで **Settings → Secrets and variables → Actions → New repository secret** を開き、次を1つずつ追加します。

| 名前 | 入れる値 |
| --- | --- |
| `FTP_SERVER` | FTP サーバー名（サーバーパネルの「FTP情報」に書かれているもの） |
| `FTP_USERNAME` | FTP ユーザー名 |
| `FTP_PASSWORD` | FTP パスワード |
| `FTP_DIR_STAGING` | テスト用サブドメイン（tide-stg.cutlassfish.tokyo）の公開フォルダ。例：`/tide-stg.cutlassfish.tokyo/` |
| `FTP_DIR_PRODUCTION` | 本番用サブドメイン（tide-current-map.cutlassfish.tokyo）の公開フォルダ。例：`/tide-current-map.cutlassfish.tokyo/` |
| `GOOGLE_MAPS_BROWSER_KEY` | Google 地図のブラウザ用キー（今 ChatGPT Sites に入れているものと同じでよい） |
| `GOOGLE_MAPS_ENABLED` | Google 地図を使うなら `true`、使わないなら `false` |

- フォルダは、サーバーパネルでサブドメインを作ったときに表示される「公開フォルダ」をそのまま書きます。最後の `/` は無くても構いません。
- 2つのフォルダは必ず別にしてください（同じだとワークフローが止まります）。
- `GOOGLE_MAPS_ENABLED` は Secrets ではなく **Variables** タブに入れても構いません。
- Google Cloud 側で、キーの「ウェブサイトの制限」に `https://tide-stg.cutlassfish.tokyo/*` も追加しておくと、テスト用でも Google 地図が出ます。
- 秘密情報はログに表示されません。キーは `api/map-config/config.php` としてサーバーにだけ置かれ、GitHub には保存されません。

## 2. サーバー側の準備

サーバーパネルで次を行います。

1. サブドメイン `tide-stg.cutlassfish.tokyo`（テスト用）と `tide-current-map.cutlassfish.tokyo`（本番用）を追加する。
2. それぞれに無料SSLを設定する。
3. PHP のバージョンは 7.4 以上（8.x 推奨）にする。

本番用の `tide-current-map` は、DNS を切り替えるまでレンタルサーバーには届きません。
無料SSLが「DNS がこのサーバーを向いていないと発行できない」場合は、SSL の設定は手順5の切り替え直後に行ってください（そのあいだ数分〜数十分は https が使えません）。

## 3. アップロード（デプロイ）する

1. GitHub の **Actions** タブを開く。
2. 左の一覧から **Deploy tide map to rental server** を選ぶ。
3. 右の **Run workflow** を押す。
   - `app_ref`：そのまま（`claude/funny-dijkstra-n8oyg0`）。
   - `target`：**まず `staging`**。
4. 緑のチェックになれば完了です。赤なら、テストかアップロードで止まっています（サーバーには途中までしか上がらないことがあるので、直してもう一度実行してください）。

ワークフローは、アプリのテスト → サーバー用ファイルの作成 → 今の版との比較テスト → アップロード、の順に進みます。
サーバー上で消すのは「前回このワークフローが置いて、今回は無くなったファイル」だけです。指定したフォルダの外や、`cache/`・`.well-known/` には触れません。

## 4. テスト用（staging）を確認する

https://tide-stg.cutlassfish.tokyo/ を開いて、次を見ます。

- 地図が出て、流れの線が動く。
- 日付を変えると潮位のグラフが変わる（例：今日・明日・2027年の日付）。
- 「海上保安庁 潮流推算」に切り替えると推算図が重なる。
- Google 地図を有効にしている場合は Google 地図になる。
- https://tide-stg.cutlassfish.tokyo/api/tide?date=2026-11-03&station=TK で数字が並んだ JSON が出る。

問題なければ、もう一度 **Run workflow** を `target: production` で実行します。

## 5. DNS を切り替える（本番公開）

1. 本番用フォルダへのデプロイ（`production`）が終わっていることを確認する。
2. お名前.com の DNS 設定で、`tide-current-map` の CNAME を
   `custom-domains.chatgpt.site` から、サーバーパネルの案内にある値（レンタルサーバーのホスト名、または A レコードの IP アドレス）に変更する。
   - CNAME から A レコードに変える場合は、CNAME を消してから A レコードを追加します。
3. 反映には数分〜最大1日ほどかかります。反映後、無料SSL が有効なことを確認します。

## 6. 元に戻す（ロールバック）

DNS の `tide-current-map` を元の CNAME `custom-domains.chatgpt.site` に戻すだけです。
ChatGPT Sites のプロジェクト（`appgprj_6add2cbb45b481919ec5e41b49cb1067`）は消さずにそのまま残しておいてください。そちらは今回まったく変更していません。

## 検索（SEO）について

URL は同じ（`https://tide-current-map.cutlassfish.tokyo/`）で、ページのタイトル（`東京湾の潮と流れ | TIDE & CURRENT MAP`）と説明文（meta description）も今の版と1文字も変わりません（テストで確認しています）。
なお、今の版には canonical タグがもともと入っていないので、こちらも入っていません（同じ状態です）。

## 補足

- アプリを更新したら、同じワークフローをもう一度実行すれば反映されます（staging → production の順に）。
- `cache/` フォルダは PHP が自動で作る一時保存場所です（気象庁・海上保安庁から取ったデータを1時間だけ保存）。消しても問題ありません。
- 手元で試す場合：`node tide-current-map/rental/build-rental.mjs <アプリのフォルダ> <出力フォルダ>` で作り、`node tide-current-map/rental/test/compare.mjs <アプリのフォルダ>` で今の版と比べられます（Node 22 と PHP が必要）。
