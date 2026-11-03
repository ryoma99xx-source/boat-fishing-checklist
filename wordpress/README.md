# WordPress（cutlassfish.tokyo）への記事登録

Claude Code が記事を WordPress に**下書き**として登録するための手順です。公開はオーナーが WordPress で行います。

## 仕組み
- 記事は「記事パックZIP」（`article.json` / `article.html` / `images/`）にまとめる。形式は ChatGPT 版の
  取り込みプラグイン「記事・写真まとめて取り込み」と同じ。
- サイトに入れた追加プラグイン `cutlassfish-article-import-api` の REST API に送ると、同じ処理で下書きになる。

## 必要な環境変数（Claude Code の作業環境に設定）
- `WP_USER`：Claude 用の WordPress ユーザー名（権限は編集者）
- `WP_APP_PASSWORD`：そのユーザーのアプリケーションパスワード
- `WP_URL`：省略時 `https://cutlassfish.tokyo`

値は表示・ログ・コミットに絶対に出さないこと。

## 手順
```bash
python3 wordpress/article-pack/cfpack.py ping                         # 認証と投稿先（post_type）を確認
python3 wordpress/article-pack/cfpack.py build <記事フォルダ> -o pack.zip # 写真を約1MBに縮めてZIP化・形式チェック
python3 wordpress/article-pack/cfpack.py upload pack.zip --type <post_type>
```
- 釣行記の投稿先は、ping の一覧にある「釣り記事」の post_type を使う（分からなければ報告で確認する）。
- 結果の `edit_link` と `preview_link` を完了報告に書く。

## 記事パックの書き方
- `article.json`：`{"version":1,"title":"…","excerpt":"…","images":[{"id":"photo1","file":"images/photo1.jpg","alt":"…","caption":"…","title":"…"}],"featured_image":"photo1"}`
- `article.html`：画像は `src="{{image:photo1}}"`。キャプションは figcaption にも書く。h1 は不要（タイトルは投稿タイトルに入る）。
- 画像ファイル名と ID は英数字・ハイフン・アンダースコアのみ。JPEG/PNG/GIF/WebP、30枚まで。
- 本文はカスタムHTMLブロックになる。見た目はインラインスタイルで付ける（既存記事 `article.html` の書き方に合わせる）。

## 環境変数が無いとき
ZIP を作って形式チェックまで行い、オーナーが「ツール → 記事・写真取り込み」から手で上げられるよう、
ZIP名と SHA256 を完了報告に書く。
