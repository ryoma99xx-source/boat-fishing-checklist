Cutlassfish 記事取り込み API v1.0.0

「記事・写真まとめて取り込み」と同じ記事パックZIPを、外部ツール（Claude Code など）から
REST API で送って下書きにするための追加プラグインです。既存の取り込みプラグインは変更しません。

できること
- 記事パックZIPを受け取り、写真をメディアに登録して、下書きを作ります（公開はしません）
- 同じZIPは二重に取り込まず、既存の下書きを返します
- 失敗したときは、その回に作った下書きと画像を消します

使える人
- アプリケーションパスワードで認証したユーザーのうち、「投稿の編集」と「メディアのアップロード」権限がある人（編集者以上）
- 購読者などは拒否します

入口
- GET  /wp-json/cfai/v1/ping                     … 認証確認と、投稿先（post_type）の一覧
- POST /wp-json/cfai/v1/import?post_type=<名前>   … 本文に ZIP（application/zip）か、multipart の article_pack

インストール
WordPress 管理画面 → プラグイン → 新規追加 → プラグインのアップロード で
cutlassfish-article-import-api.zip を選び、有効化します。
