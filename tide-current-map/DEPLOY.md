# 公開版（Sites v17）を新モデル版に置き換える手順

対象：https://tide-current-map.cutlassfish.tokyo/ （Sites プロジェクトID `appgprj_6add2cbb45b481919ec5e41b49cb1067`、公開範囲 public）

新しいソース：GitHub `ryoma99xx-source/boat-fishing-checklist` のブランチ `claude/funny-dijkstra-n8oyg0` の `tide-current-map/app/`（2026-11-02 時点の最新コミットを使う。`npm test` 61件合格、`npm run build` 成功、`dist/server/index.js` 約7.45MB を確認済み）
（`.openai/hosting.json` は含めていない。既存チェックアウトのものをそのまま使う）

## 手順（OpenAI側の環境で実行）

```sh
# 1. 既存チェックアウトの状態を確認（v17 = b102e465...）
cd /workspace/sites/shio-tokyo
git status && git log --oneline -1
cat .openai/hosting.json   # プロジェクトIDが上と同じことを確認

# 2. 新ソースを取得して上書き（.openai は触らない）
git checkout -b current-model-v18
curl -L -o /tmp/src.zip https://github.com/ryoma99xx-source/boat-fishing-checklist/archive/refs/heads/claude/funny-dijkstra-n8oyg0.zip
rm -rf /tmp/src && mkdir /tmp/src && unzip -q /tmp/src.zip -d /tmp/src
rsync -a --delete --exclude .openai --exclude .git --exclude node_modules --exclude dist \
  /tmp/src/*/tide-current-map/app/ ./

# 3. テストとビルド
npm test
npm run build          # dist/server/index.js（約7.5MB）

# 4. ローカル確認
npm run dev            # http://localhost:4173 で地図・流れ・切替を確認

# 5. コミット
git add -A && git commit -m "Harmonic tidal current model (50/100/250 m) with flow animation"
```

6. Sites のスキル／手順に従い、既存プロジェクトID・public・独自ドメインを維持したまま「ソース同期 → ビルド → 保存 → デプロイ」。新規プロジェクトは作らない。

## 公開後の確認

- https://tide-current-map.cutlassfish.tokyo/ を開き、流れのアニメーション、3つの切替（自作モデル／海上保安庁／重ねて比較）、今日の日付が初期表示になることを確認。
- 50m格子データの転送量：ブラウザの開発ツールで `/api/harmonic/inner-*.bin.gz` が約1.9MBで読み込まれていること（これが通常。`.bin.gz` ではなく `.bin` が7MB前後で読まれている場合は、ブラウザが古いか配信側で `.bin.gz` が壊れている）。
- 3つの切替（自作モデル／海上保安庁 潮流推算／重ねて比較）が動くこと。海保側は海上保安庁のサーバーへ Worker から取得するので、`/api/current` が200を返すこと。
- 参考点（猿島沖・台船（馬堀沖）・観音崎北・第二海堡・中ノ瀬・木更津沖）と赤破線の囲みが出ること。
- Google地図の表示（本番キーでのみ確認可能）。

## 戻す場合

Sites の保存版 v17（`appgprj_6add2cbb45b481919ec5e41b49cb1067~appgver_306a718a34a88191b4b7078d85736b6e`）を再デプロイする。

## 注意

- `scripts/qa-*.cjs` は旧UI前提のため失敗する。`npm test` と上の手動確認で判断する。
- 紹介記事の「10/24の事例から見る」「Googleマップを設定」の記述は新画面と合わない。記事はユーザーがWordPressで直す。
