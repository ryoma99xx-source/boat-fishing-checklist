Cutlassfish 記事取り込み API v1.1.0

「記事・写真まとめて取り込み」と同じ記事パックZIPを、外部ツール（Claude Code など）から
REST API で送って下書きにするための追加プラグインです。既存の取り込みプラグインは変更しません。
v1.1.0 から、既存記事の読み出し・本文の差し替え・公開／下書き戻しもできます。

できること
- 記事パックZIPを受け取り、写真をメディアに登録して、下書きを作ります（公開はしません）
- 同じZIPは二重に取り込まず、既存の下書きを返します
- 失敗したときは、その回に作った下書きと画像を消します
- （v1.1.0）記事の一覧と中身の読み出し（「オーナー記入」「要確認」などの書き残しも一覧に出します）
- （v1.1.0）既存記事のタイトル・抜粋・本文を記事パックZIPで差し替え（変更前の内容は保存）
- （v1.1.0）公開（スラッグ・トピック・日時の指定つき）と、下書きへの戻し
- 記事や既存の画像を削除することはありません

使える人
- アプリケーションパスワードで認証したユーザーのうち、「投稿の編集」と「メディアのアップロード」権限がある人（編集者以上）
- 記事ごとに、その記事を編集できるかも確認します。公開は「公開」権限が必要です
- 購読者などは拒否します
- 対象は 記事（tachiuo_post）と 投稿（post）だけです。固定ページなどは扱いません

入口
- GET  /wp-json/cfai/v1/ping                     … 認証確認と、投稿先（post_type）の一覧
- POST /wp-json/cfai/v1/import?post_type=<名前>   … 本文に ZIP（application/zip）か、multipart の article_pack
- GET  /wp-json/cfai/v1/articles?status=draft|publish|any&per_page=20&page=1&search=語&post_type=…
                                                   … 記事の一覧（文字数、トピック、書き残しの一覧つき）
- GET  /wp-json/cfai/v1/articles/<ID>             … 記事の中身（本文、抜粋、使っている画像）
- POST /wp-json/cfai/v1/articles/<ID>/content      … 記事パックZIPで本文などを差し替え（公開状態は変えません）
       ・本文で {{image:写真ID}}（ZIP内の新しい画像）と {{media:メディアID}}（既にある画像）が使えます
       ・article.json の featured_image に "写真ID" か "media:メディアID" を書くとアイキャッチを変更
       ・書き込む前にリビジョンを保存し、変更前の内容を投稿メタ _cfai_prev_content_<時刻> に残します（最新5件）
       ・公開済み・予約済みの記事は ?allow_published=1 が無いと拒否します（HTTP 409）
- POST /wp-json/cfai/v1/articles/<ID>/publish      … JSON {"slug":"…","topics":["fishing"],"date":"2026-11-05T07:00"}
       ・どれも省略可。topics は「トピック」（tachiuo_cat）のスラッグ。無いスラッグは HTTP 400
       ・date が未来なら予約公開になります
- POST /wp-json/cfai/v1/articles/<ID>/unpublish    … 下書きに戻す

インストール・更新
WordPress 管理画面 → プラグイン → 新規追加 → プラグインのアップロード で
cutlassfish-article-import-api.zip を選びます。v1.0.0 が入っている場合は
「現在のものをアップロードしたもので置き換える」を押します（設定やアプリケーションパスワードはそのままです）。
