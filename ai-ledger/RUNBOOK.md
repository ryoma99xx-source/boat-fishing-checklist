# 制作台帳：司令塔 Claude の手順書（RUNBOOK）

台帳：https://claude.ai/artifact/T4YTywvucGbbGSaWmu3VFQ （オーナー専用。データは台帳の DB、ツールは `ArtifactData`。ToolSearch で `select:ArtifactData` を読み込む）
作業用リポジトリ：`ryoma99xx-source/boat-fishing-checklist`、ブランチ `claude/relaxed-mayer-1u2nhq`、環境 `env_01Df8t8p4B9CdL8XSUWAWj1t`

この手順は、司令塔の Claude 本体（台帳へのコメントで起きるセッション）と、1時間ごとの見回りセッションの両方が使う。

## 1. 依頼の中継（requests → Claude Code）

台帳の「送る」は `requests/<id>` に `{prompt, fid, title, site, src, at, status:'pending'}` を書き、コメント「【台帳依頼】<id>」で司令塔を起こす。

1. `ArtifactData get requests/<id>` で依頼文を読む（status が `pending` のものだけ扱う）
2. `create_session`：`source_url=https://github.com/<src.repo>`、`source_revision=<src.branch>`（無ければ上の既定）、`title="<site>｜<title>"`、`prompt=<prompt そのまま>`、`environment_id` は上の環境
3. `features/<fid>` を `update`（既存は `if_version` 付き）：`cc={sessionId,url:'https://claude.ai/code/'+sessionId,sentAt,state:'作業中',relayMsg:'Claude Code が作業中（HH:MM 開始）'}`、`chats` にセッションを追加
4. `requests/<id>` を `{status:'sent',sessionId,sentAt}` に更新。コメントのスレッドには一言返して resolve
5. **3分後の確認を予約する**（`send_later`、`delay_minutes:3`、メッセージ「<fid> のセッション <sessionId> を確認」）。終わるまで3分おきに繰り返す

### 1-a. 添付画像

依頼文に「## 添付画像」があれば、画像は台帳の保管庫（assets）にある。`Artifact` ツールの `read` で `url` に台帳の URL、`path` に書かれた id を渡すと画像ファイルが保存される（1枚ずつ）。自分で作業するときは必ず見てから始める。子セッションに渡すときは依頼文にそのまま含める（取り出し方も書いてある）。

## 2. 進み具合の確認（3分おき）

1. `get_session` で `status_bucket` を見る。`list_events`（kinds: assistant / result）で最新の文を読む
2. 作業中なら `features/<fid>.cc.relayMsg` を今の様子に更新（40字まで）。子セッションが `progress/<fid>` を書いていれば台帳が自動で表示するので、relayMsg は触らなくてよい
3. 返事に `【完了報告】` があれば：`features/<fid>` の `cc` に `{state:'報告', reportText:<【記事状況】から末尾まで>, relayMsg:'完了'}` を書く（台帳が開かれたとき、ログ・状態・次の一手・記事一覧に自動で反映される）。`requests/<id>` を `done` に。確認事項があればオーナーに伝える
4. `BLOCKED`（質問待ち）なら、その質問に答えられる範囲で `send_message` で答える。オーナーの判断が要るものはオーナーに聞く
5. `FAILED` なら中身を読み、直せるなら新しいセッションで再実行。無理なら `cc.state:'保留'`＋`relayMsg` に理由

## 3. 心拍（heartbeat）

依頼を扱ったとき、確認を回したとき、見回りをしたときに `meta/heartbeat` を `set`：`{at:<ISO 現在時刻>, note:'中継'|'確認'|'見回り'}`。台帳の「いまの作業」の上に「最終確認 ◯分前」と出る（90分で黄、180分で赤）。

## 4. 見回り（9・12・15・18・21時（日本時間）・新しいセッション）

定期タスク「台帳の見回り」が日本時間の 9:07・12:07・15:07・18:07・21:07 に新しいセッションでこの手順を回す（0〜8時は動かない）。

**静かな日の判定（最初に行う）**：直近の動き（features.updatedAt／requests.at／progress.at／meta.heartbeat.at のうち note が「見回り」以外、の最新）が24時間より前なら「静かな日」。静かな日で `meta/patrol.date` が今日（日本時間）なら、その日の見回りは済みなので何もせず終える。つまり静かな日は1日1回（9:07）だけ動く。見回りの最後に `meta/patrol` を `{at, date, quiet}` で更新する。見回りのセッションには `create_session` / `get_session` などの道具が無いことがあるので、**他のセッションに頼らず自分で片付ける**。

1. `ArtifactData list requests` で `status=='pending'` を探す。10分以上前のものがあれば、司令塔本体が止まっている。古い順に1件ずつ、**その依頼文を自分がそのまま実行する**（依頼文は Claude Code 向けの作業指示になっている）。取り掛かる前に `features/<fid>.cc` を `{state:'作業中', sentAt, relayMsg:'見回りのセッションが作業中（HH:MM 開始）', sessionId:<自分のセッション ID が分かれば>}` に、`requests/<id>` を `{status:'sent'}` に更新。終わったら 2-3 のとおり報告を書き戻し、`requests/<id>` を `done` に
2. `features` で `cc.state=='作業中'` のものを見る。`progress/<fid>` に `reportText` があれば 2-3 のとおり `cc` に書き戻す。`progress` も `relayMsg` も2時間以上更新が無ければ `cc.relayMsg` を「2時間以上動きがありません。セッションを開いて確認してください」にする（セッションの中身は見られないので、それ以上は触らない）
3. 1日1回（`backups/latest.at` が20時間より古いとき）：全コレクション（features, roles, requests, articles, sitemap, sites, inbox, chat, progress, meta）を `list` で読み、`backups/latest` と `backups/<YYYY-MM-DD>` に `{at, data:{...}}` で `set`。`backups/<日付>` は新しい7件だけ残して古いものは `delete`
4. `meta/heartbeat` を `{at, note:'見回り'}`、`meta/patrol` を `{at, date, quiet}` で更新
5. 何もなければ一言「異常なし」で終える。代わりに作業した・エラーがあったときだけ、やったことを短く報告する。`ArtifactData` が使えなかったときは、その旨を最後に書く

## 5. 守ること

- 鍵・パスワード（WP_APP_PASSWORD / OPENAI_API_KEY など）の値は読まない・書かない・台帳に残さない
- 台帳のデータを消さない（`backups/<日付>` の古い分だけ例外）。`set` で既存の doc を上書きするときは必ず `get` → `if_version`
- 公開中の記事や本番サイトを変える作業は、依頼文に明記されているときだけ
- リポジトリは公開（public）。台帳の中身（依頼文・ログ・チャット）をリポジトリに書かない
- 返事はすべて日本語

## 6. ChatGPT の【カタログ追加】

オーナーが台帳の「報告」に貼って「カタログに追加する」を押すと、通常の依頼として `requests` に入る。中継は 1. と同じ。子セッションは `sites/dragon-counter/CATALOG-UPDATE.md` と `tools/catalog_add.py` に従う（足すだけ・表記は変えない）。
