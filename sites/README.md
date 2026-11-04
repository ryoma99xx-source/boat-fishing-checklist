# 小さなツール3つ — レンタルサーバーへの引っ越し

## これは何か

今 ChatGPT Sites で公開している次の3つのツールを、お名前.com レンタルサーバー（cutlassfish.tokyo の WordPress と同じサーバー）に引っ越すためのファイル一式です。**URL は今と同じ**です。

| ツール | URL | フォルダ | 秘密情報の名前に使う記号 |
| --- | --- | --- | --- |
| リール糸管理 | https://reel-line-manager.cutlassfish.tokyo/ | `reel-line-manager/` | `REEL` |
| 持ち物チェック（Don't forget anything） | https://dont-forget-anything.cutlassfish.tokyo/ | `dont-forget-anything/` | `DFA` |
| テンヤ海中挙動シミュレーター | https://tenya-simulator.cutlassfish.tokyo/ | `tenya-simulator/` | `TENYA` |

- 3つとも、サーバー側のプログラム（PHP など）は不要です。ファイルを置くだけで動きます。
- 中身は、今公開されているサイトをそのまま写したもの（ミラー）です。手を加えたのは1点だけで、Cloudflare（ChatGPT Sites の配信元）が HTML の最後に自動で差し込んでいる監視用の `<script>` を取り除いています（Cloudflare の外では読み込みエラーになるだけのものです）。
- 持ち物チェックの「共有」機能は、もともと WordPress 側の `https://cutlassfish.tokyo/dont-forget-anything-share/share.php` を使っています。これは今のまま変わりません。
- ChatGPT Sites のプロジェクトには何も変更を加えません。DNS を切り替えるまで、公開中のサイトはそのままです。

中身：

| ファイル | 役割 |
| --- | --- |
| `<サブドメイン>/public/` | サーバーに置くファイル一式（`.htaccess` 付き） |
| `<サブドメイン>/mirror-manifest.json` | 写したファイルの一覧（URL・種類・大きさ・取り込み時の変更点） |
| `mirror.py` | 公開中のサイトから `public/` を作り直すスクリプト（`python3 sites/mirror.py`） |
| `test/` | 写したサイトの確認用（ブラウザでの表示比較・Apache での動作確認） |
| `../.github/workflows/deploy-sites-rental.yml` | GitHub からサーバーへ FTPS でアップロードする手順 |

## ブラウザに保存したデータについて

リール糸管理・持ち物チェック・テンヤの保存した条件は、利用者のブラウザの中に保存されています。ブラウザはこれを **URL（https://〜.cutlassfish.tokyo）ごと** に覚えているので、URL が変わらない今回の引っ越しでは、**保存したデータはそのまま残ります**。利用者が何かをする必要はありません。

## 1. GitHub に秘密情報を登録する（最初の1回だけ）

GitHub のこのリポジトリで **Settings → Secrets and variables → Actions → New repository secret** を開き、次を追加します。
`FTP_SERVER` は「東京湾の潮と流れ」のときに登録済みなら、そのままで構いません。

| 名前 | 入れる値 |
| --- | --- |
| `FTP_SERVER` | FTP サーバー名（例：`www1066.onamae.ne.jp`） |
| `FTP_USERNAME_REEL` / `FTP_PASSWORD_REEL` | リール糸管理用に作った FTP アカウントのユーザー名 / パスワード |
| `FTP_USERNAME_DFA` / `FTP_PASSWORD_DFA` | 持ち物チェック用の FTP アカウント |
| `FTP_USERNAME_TENYA` / `FTP_PASSWORD_TENYA` | テンヤシミュレーター用の FTP アカウント |

- サイトごとに別の FTP アカウントにします。そのアカウントは自分のサブドメインのフォルダしか触れないので、WordPress や他のツールを誤って変更する心配がありません。
- 秘密情報が足りないと、アップロードは「Missing repository secrets: 〜」と表示して止まります（サーバーには何も書き込みません）。

## 2. サイトごとの切り替え手順（お名前.com）

1サイトずつ行えます。下の `<サブドメイン>` は `reel-line-manager`・`dont-forget-anything`・`tenya-simulator` のどれかです。

1. **DNS**：お名前.com の DNS 設定で、そのサブドメインの CNAME レコード（値が `custom-domains.chatgpt.site`）を削除する。
   - ここから手順4のアップロードが終わるまでの数分〜数十分、そのツールは開けなくなります。作業は利用の少ない時間に。
   - 一度でも開いたことのある人のブラウザは、ツールが自分で保存した控え（サービスワーカー）で表示されることがあります（リール糸管理・持ち物チェック）。
2. **サブドメインを追加**：レンタルサーバーのコントロールパネルで `<サブドメイン>.cutlassfish.tokyo` を追加する（公開フォルダは `public_html/<サブドメイン>/`）。
3. **無料SSL**：そのサブドメインに無料SSLを設定する（DNS がサーバーを向いてから発行されるので、少し待つことがあります）。
4. **FTP アカウント**：「ファイル管理」→ FTP アカウントの追加で、ユーザー名 `deploy`（実際には `deploy@〜` のような名前になることがあります。表示されたものをそのまま使います）、**接続先ディレクトリ `public_html/<サブドメイン>/`** で作る。
   そのユーザー名とパスワードを、上の表の `FTP_USERNAME_〜` / `FTP_PASSWORD_〜` に登録する。
5. **アップロード**：Claude に「<ツール名> をデプロイして」と伝えてください（下の「3. アップロード」）。
6. **確認**：スマホとパソコンで URL を開き、表示・保存データ・ボタンの動きを確認する。

## 3. アップロード（デプロイ）のしかた

作業ブランチ（`claude/relaxed-mayer-1u2nhq`）の `sites/<サブドメイン>/DEPLOY` というファイルが更新されると、そのサイトだけが自動でアップロードされます（Claude Code が更新します）。

- 送るのは `sites/<サブドメイン>/public/` の中身だけです。変わったファイルだけを送ります。
- サーバー上でファイルを消すのは「前回このワークフローが置いて、今回は無くなったファイル」だけです。それ以外のファイルや `.well-known/`（無料SSLの確認用）には触れません。
- 経過は GitHub の **Actions → Deploy small sites to rental server** で見られます。

## 4. 元に戻すとき

お名前.com の DNS で、そのサブドメインの CNAME（値 `custom-domains.chatgpt.site`）を元どおり登録し直すだけです。ChatGPT Sites のプロジェクトはそのまま残っているので、DNS が戻れば以前のサイトがそのまま表示されます（反映まで数分〜数時間）。保存データも URL が同じなので残ります。

## 5. サーバーの設定（.htaccess）について

- ファイルの種類（JavaScript・CSS・マニフェストなど）を正しく伝える設定と、キャッシュの設定だけを書いています。お名前.com で使えない書き方（`Options` など、使うと 500 エラーになるもの）は入れていません。
- キャッシュ：ページ（HTML）は毎回最新を確認、アイコンや画像は1日、テンヤの `/_next/static/`（名前に版番号が入ったファイル）は1年です。
- 存在しないページは「404 見つかりません」になります（テンヤはアプリ自身の 404 ページ）。今の ChatGPT Sites では、リール糸管理・持ち物チェックは存在しない URL でもトップページを表示していますが、ツール内のリンクはすべて実在するページなので影響はありません。
- テンヤの古い版のページ（`/versions/1.4.0` 〜 `/versions/1.5.4`）も今と同じ URL で開けます。

## 6. テンヤ海中挙動シミュレーターを今後直すときの注意

テンヤのミラーは、ChatGPT が作った元のプログラムを「組み立て（コンパイル）済み」の形で写したものです。読みやすい元のプログラムは入っていないため、**この中身を直接直すことはできません**。

今後、内容を変えたくなったら：

1. ChatGPT で、そのプロジェクトの **ソースコード一式を ZIP で書き出してもらう**（「このプロジェクトのソースをZIPでエクスポートして」と頼む）。
2. その ZIP を Claude に渡す → 修正して組み立て直し、`sites/tenya-simulator/public/` を作り直します。

リール糸管理・持ち物チェックは、写したファイルがそのまま元のプログラム（HTML・JavaScript・CSS）なので、ここで直接直せます。

## 7. 写し直すとき（ChatGPT Sites 側を更新した場合）

ChatGPT Sites 側でツールを更新したら、切り替え前であれば `python3 sites/mirror.py <サブドメイン>` で写し直せます（Claude に頼めば実行・確認・アップロードまで行います）。切り替え後は ChatGPT Sites 側の URL がこちらを向かなくなるので、更新はこのリポジトリで行います。
