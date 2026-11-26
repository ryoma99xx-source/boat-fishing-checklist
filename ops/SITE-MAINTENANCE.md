# サイトの定期メンテナンス（点検の手順）

オーナー指示 2026-11-24。cutlassfish.tokyo（WordPress）と dragon-counter.cutlassfish.tokyo（3つのカウンター・カタログ・リンク集）、
tide-current-map.cutlassfish.tokyo（東京湾の潮と流れ）、小さなツール3つ（reel-line-manager・dont-forget-anything・tenya-simulator）を、Claude の定期作業で点検する。

**この点検は読むだけ。** サイトのファイル・設定・記事は変えない。問題を見つけたら報告し、直すのはオーナーの OK をもらってから（別の作業として）。

## 道具

| 道具 | 何をみるか |
|---|---|
| `node ops/sitecheck/sitecheck.cjs --daily` | 主なページをスマホ幅で開く：開けるか・画面のエラー・自分のサイトの部品が読めないもの・横のはみ出し・あるはずの部品。ドラゴンカウンターと、小さなツール3つ（リール糸管理・持ち物チェック・テンヤシミュレーター）の配信ファイルがリポジトリと同じか（改ざん・公開し忘れ）。6つのサイトの robots.txt（全部お断りになっていないか）・サイトマップ・llms.txt が読めるか（2026-11-26 追加） |
| `node ops/sitecheck/sitecheck.cjs --weekly` | ↑に加えて、サイトマップの全ページと主なページのリンク先（404 探し）、画面の最初の1枚を基準（`ops/sitecheck/baseline/`）とくらべる |
| `python3 ops/sitecheck/wp_health.py` | WordPress の中（プラグイン `cutlassfish-health` の管理者だけの窓口）：本体・プラグイン・テーマの更新、本体ファイルが公式と同じか、サイトのいちばん上の見覚えのない PHP、アップロード置き場の PHP、ここ7日で書き換わったプラグイン・テーマのファイル、管理者の人数 |

- スクリーンショットは `SITECHECK_OUT`（なければ一時フォルダ）に出る。
- `wp_health.py` は環境変数 `WP_USER`・`WP_APP_PASSWORD` を使う（値は表示しない・保存しない）。**結果をリポジトリに書かない**（公開リポジトリのため。管理者のログイン名などが含まれる）。

## 毎日

1. `git fetch origin claude/relaxed-mayer-1u2nhq && git checkout claude/relaxed-mayer-1u2nhq`
2. `SITECHECK_OUT=<作業用の一時フォルダ> node ops/sitecheck/sitecheck.cjs --daily`
3. `python3 ops/sitecheck/wp_health.py`
4. 報告：両方とも問題なし（更新があるだけは問題に数えない）なら「異常なし」とだけ。問題があれば、どのページ・何が起きているか・考えられる原因を3行以内。
   - 配信ファイルの違いは、その日に公開（DEPLOY の push）があったなら反映待ちのことがあるので、10分ほど待ってもう一度だけ確かめる（Monitor で待つ。sleep はしない）。
   - 画面のエラーが広告・外部サービスだけのものなら、そう書く。

## 毎週

1. 毎日の 1〜3 を `--weekly` で行う。
2. 見た目が大きく変わったページは、スクリーンショットと基準を見くらべ、崩れか、ただの記事の入れ替わりかを判断する。ただの入れ替わりなら報告に書くだけ（基準は作り直さない。作り直すのはオーナーが言ったとき：`--update-baseline` → コミット）。
3. 更新のあるプラグイン・テーマを一覧にする。WordPress.org のプラグイン・テーマは WordPress 標準の自動更新で入る（オーナーの OK 2026-11-24。プラグイン cutlassfish-health）。1週間以上入らずに残っているものがあれば、そう書く。
4. 報告（5行以内）：ページ・リンク・配信ファイル・WordPress の中・更新、それぞれ「問題なし／何件」。

## 見つかっている既知のこと

- サイトマップから「未分類」カテゴリー（404 だった）と投稿者の一覧を外した（2026-11-24、プラグイン cutlassfish-seo-basics 1.1.0）。
- 日本語表示の WordPress だが本体は英語版のため、`wp-includes/version.php` は英語版の照合値と同じ（問題ではない。`cutlassfish-health` が考慮済み）。
- Independent Analytics は自分で設定ファイル（`iawp-click-config.php`）を書き換える（問題ではない）。
- AI・検索向けの印（2026-11-26）：各サイトに robots.txt・サイトマップ・llms.txt を置いた。作り方は、ドラゴンカウンターのサイト＝`sites/dragon-counter/tools/seo_extras.py`（ページを作るたびに自動）、小さなツール3つ＝`sites/seo_static.py`、東京湾の潮と流れ＝`tide-current-map/rental/build-rental.mjs`、cutlassfish.tokyo の llms.txt＝プラグイン cutlassfish-seo-basics。
