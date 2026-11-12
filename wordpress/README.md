# WordPress（cutlassfish.tokyo）への記事登録と修正

Claude Code が記事を WordPress に**下書き**として登録し、既存記事を書き直すための手順です。
公開は、オーナーがはっきり指示したときだけ行います。

## 仕組み
- 記事は「記事パックZIP」（`article.json` / `article.html` / `images/`）にまとめる。形式は ChatGPT 版の
  取り込みプラグイン「記事・写真まとめて取り込み」と同じ。
- サイトに入れた追加プラグイン `cutlassfish-article-import-api`（v1.1.0）の REST API（`/wp-json/cfai/v1/…`）に送る。
  新規は下書きになり、既存記事の差し替えも公開状態は変えない。記事や画像を削除する機能は無い。
- 対象は 記事（`tachiuo_post`）と 投稿（`post`）だけ。

## 必要な環境変数（Claude Code の作業環境に設定）
- `WP_USER`：Claude 用の WordPress ユーザー名（権限は編集者）
- `WP_APP_PASSWORD`：そのユーザーのアプリケーションパスワード
- `WP_URL`：省略時 `https://cutlassfish.tokyo`
- `OPENAI_API_KEY`：画像や文章を OpenAI で作るときだけ（下の「GPT ヘルパー」）

値は表示・ログ・コミットに絶対に出さないこと。

## コマンド一覧（`python3 wordpress/article-pack/cfpack.py …`）
| コマンド | 内容 |
|---|---|
| `ping` | 認証と投稿先（post_type）を確認 |
| `build <フォルダ> -o pack.zip` | 写真を約1MBに縮めてZIP化・形式チェック |
| `check pack.zip` | ZIPの形式チェックだけ |
| `upload pack.zip --type <post_type>` | 新しい下書きとして登録 |
| `list [--status draft\|publish\|any] [--search 語] [--type tachiuo_post]` | 記事の一覧（JSON） |
| `get <ID> [--out <フォルダ>]` | 記事の中身（JSON）。`--out` で編集用フォルダを作る |
| `update <ID> pack.zip [--allow-published]` | 既存記事のタイトル・抜粋・本文を差し替え |
| `publish <ID> [--slug s] [--topics fishing,tokyobay] [--date 2026-11-05T07:00]` | 公開（未来の日時なら予約公開） |
| `unpublish <ID>` | 下書きに戻す（公開ミスの取り消し） |

- 結果は JSON で表示される。`edit_link` と `preview_link` を完了報告に書く。
- `list` の `todo` には、本文に残っている「（オーナー記入…」「（要確認…」などの書き残しが前後の文と一緒に出る。
- `word_count` は文字数（空白を除く）。
- トピック（`--topics`）のスラッグ：fishing, fish, tokyobay, resources, tools, shopping, recipe。無いスラッグはエラーになる。

## 新しい記事を登録する
```bash
python3 wordpress/article-pack/cfpack.py ping
python3 wordpress/article-pack/cfpack.py build <記事フォルダ> -o pack.zip
python3 wordpress/article-pack/cfpack.py upload pack.zip --type tachiuo_post
```

## 既存の記事を書き直す（安全な手順）
1. `list` で対象の記事 ID を探す（`--search` や `--status draft`）。
2. `get <ID> --out work/<ID>` で編集用フォルダを作る。
   - `article.json`（タイトル・抜粋・アイキャッチ）と `article.html`（本文）ができる。`source.json` は参照用で、ZIP には入らない。
   - 本文中の既存画像は `{{media:メディアID}}` に置き換わっている。そのまま残せば、画像を上げ直さずに同じ画像が使われる。
3. オーナーの指示どおりに `article.html` / `article.json` を直す。
   - 新しい画像を足すときは `images/` にファイルを置き、`article.json` の `images` に登録して、本文では `src="{{image:写真ID}}"`。
   - アイキャッチを変えるときは `featured_image` に `"写真ID"` か `"media:メディアID"`。書かなければ今のまま。
   - 指示されていない部分は変えない。
4. `build work/<ID> -o work/<ID>.zip`（`{{media:N}}` を使ったZIPは update 専用、という注意が出る）。
5. `update <ID> work/<ID>.zip` で下書きのまま差し替える。
   - 変更前の内容はリビジョン（`revision_id`）と投稿メタ `_cfai_prev_content_<時刻>`（最新5件）に残る。戻すときは管理画面のリビジョンか、この保存内容を使う。
6. 完了報告に `preview_link` を書き、オーナーにプレビューで確認してもらう。
7. **公開はオーナーが「公開して」とはっきり指示したときだけ** `publish <ID> --slug … --topics …` を実行する。
   間違えて公開したら `unpublish <ID>` ですぐ下書きに戻す。

### HTTP 403（SiteGuard の「閲覧できません」）が出たとき
- 圧縮したZIPのバイト列が、たまたまサーバーのファイアウォールに引っかかることがある（内容の問題ではない）。
- `article.html` の**先頭**に空白を1つ足して `build` し直すと、圧縮後のバイト列が変わって通る（末尾に足しても前半は同じなので通らない）。
- 送り直しても公開状態は変わらない。

### `{{media:N}}` について
- N は WordPress のメディアID（数字）。`get` の `images` に一覧が出る。
- 新規の `upload` では使えない（エラーになる）。既存記事の `update` 専用。
- 本文の画像URLがサイズ違い（例：`-300x200.jpg`）や外部URLのときは、URLのまま残る（そのままで表示される）。

## 公開済み記事の修正
- 公開中・予約中の記事は、`update` が拒否される（HTTP 409）。
- `--allow-published` は、オーナーが「公開中のこの記事を直して」と**はっきり指示したときだけ**使う。付けると即座にサイトに反映される。
- 迷ったら、先にオーナーに確認する。変更前の内容は下書き修正と同じように保存される。

## GPT ヘルパー（`python3 wordpress/gpt/gpt.py …`）
OpenAI の API で記事用の画像や文章を作る。環境変数 `OPENAI_API_KEY` が必要（値は表示・保存しない）。

```bash
python3 wordpress/gpt/gpt.py usage-note                     # 料金の注意を表示
python3 wordpress/gpt/gpt.py image "夜明けの東京湾でタチウオを釣り上げる様子、写真風" \
    -o work/123/images/ai-dawn.png --size 1536x1024 --quality medium --jpeg
python3 wordpress/gpt/gpt.py text "次の文章を読みやすく直して" --context work/123/article.html
```
- **API の利用料は ChatGPT のプラン（Plus など）とは別に請求される。** 画像は1枚ごとに課金。確認用は `--quality low` か `medium`。
- 画像モデルは `OPENAI_IMAGE_MODEL`、文章モデルは `OPENAI_TEXT_MODEL` で指定できる。指定が無ければ自動で選ぶ。
- `--jpeg` を付けると、同じ名前の `.jpg`（品質85%・約1MB以下）も作る。記事にはこちらを使う。
- 作った画像は、編集用フォルダの `images/` に置いて `article.json` の `images` に登録し、本文で `{{image:写真ID}}` として使う。
  そのあと `build` → `update` の流れは上と同じ。
- AI で作った画像は、実際の釣果写真と誤解されないよう、キャプションに「イメージ（AI生成）」などと書く。

## 記事パックの書き方
- `article.json`：`{"version":1,"title":"…","excerpt":"…","images":[{"id":"photo1","file":"images/photo1.jpg","alt":"…","caption":"…","title":"…"}],"featured_image":"photo1"}`
- `article.html`：画像は `src="{{image:photo1}}"`（既存記事の修正では `src="{{media:123}}"` も可）。キャプションは figcaption にも書く。h1 は不要（タイトルは投稿タイトルに入る）。
- 画像ファイル名と ID は英数字・ハイフン・アンダースコアのみ。JPEG/PNG/GIF/WebP、30枚まで。
- 本文はカスタムHTMLブロック1つになる。見た目はインラインスタイルで付ける（既存記事 `article.html` の書き方に合わせる）。
  もともとブロックが複数ある記事を `update` すると、1つのカスタムHTMLブロックにまとまる。

## 環境変数が無いとき
ZIP を作って形式チェックまで行い、オーナーが「ツール → 記事・写真取り込み」から手で上げられるよう、
ZIP名と SHA256 を完了報告に書く（既存記事の修正は手作業になるので、変更内容を報告にまとめる）。
