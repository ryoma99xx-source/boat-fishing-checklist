# 東京湾の潮と流れ：引き継ぎ（第2セッション → 第3セッション）

作成日：2026年11月1日

## 最初にやること

1. ユーザーが添付する `tide-current-map-handoff-2026-11-01.zip` を新しい空のディレクトリに展開し、中の `HANDOFF.md` を読む（公開構成・モデルの限界・Google Maps・WordPressの注意点はそちらが正）。添付がなければ、ユーザーに再添付を頼む。
2. `SHA256SUMS.txt` でハッシュを照合する。
3. 下の「ネットワーク確認」を実行し、どのサイトに届くか確かめる。

## 前セッションで確認したこと

- ZIP内4ファイルのハッシュはすべて一致。
- `app-source-v17.zip` を展開して `npm test`：11ファイル・44ケースすべて合格。`npm run build` も成功（`dist/server/index.js`、約8.5MB）。
- `.openai/hosting.json` のプロジェクトIDは HANDOFF.md と一致。
- プラグインは1.2.1。同梱の初期原稿（`article-data.php`）には「Claudeが。」の文が無い。この文はユーザーが公開記事に後から書いたものと判断（公開本文が正）。
- 前セッションは `cutlassfish.tokyo` など外部サイトへの接続がネットワーク設定で拒否され、公開記事・アプリ・釣果ページは読めていない。
- このリポジトリ（boat-fishing-checklist）は潮アプリのGit履歴ではない。アプリのソースはまだどこにもコミットしていない（置き場所はユーザー未決定）。
- Sitesへの公開権限はクラウドセッションには無い。ここで出来るのはソース修正・テスト・ビルドまで。

## 未完了：記事のリンク（ユーザーがWordPressで貼る）

HANDOFF.md のコードのまま提示済み。まだ貼られていない。

```html
<p>
  <del>このあたりは、また考えてみようと思います。Claudeが。</del>
  <a href="https://cutlassfish.tokyo/catch/#:~:text=この月のラベル"
     style="color:#4fd0d6;text-decoration:underline;text-underline-offset:3px;">
    とりあえず仮対応してみました
  </a>
</p>
```

接続できるようになったら、公開記事と `/catch/` を読み直して、文の位置と「この月のラベル」の文字列が実在するかを確認する。

## ユーザーの新しい要望

1. ユーザーが送った相模湾の潮流アプリ（流れる線のアニメーション、「実測0.3kt」等の矢印付き観測点、「沖の山（仮）」等の釣り場の囲み）のような見た目の東京湾版を作りたい。そのアプリは気象庁のデータを使っているとのこと（アプリ名は不明。分かればデータ源を正確に確認できる）。
2. **一番やりたいのは沿岸部（新安浦・猿島・馬堀・観音崎周辺）の細かな流れの把握。** そのためのモデルやデータを徹底的に探す依頼を受けた。

## 調査結果（検索結果ベース。ページ本文は未確認）

### 結論

岸際を100m程度で出している公開予測は見つからなかった。岸際は自前の高解像度計算が必要。外側の流れの境界条件と、答え合わせの実測を外部から取るのが現実的。

### 予測・推算の候補

| 候補 | 解像度 | 時間変化 | メモ |
|---|---|---|---|
| JAMSTEC JCOPE-T TSS500（東京湾・相模湾・駿河湾） https://www.jamstec.go.jp/jcope/vwp/tss500/ | 名称から約500m（未確認） | 毎時予測 | 最有力。試験公開。数値データ提供は要問い合わせ |
| JCOPE-T 1ks（JAXA「海中天気予報」1km版） https://www.eorc.jaxa.jp/ptree/documents/JCOPE-T-1ks.docs_JP_20250314.pdf | 1/120度（約900m） | 毎時、46層、潮汐11分潮 | 2025年3月から試験公開。東京湾の比較図あり |
| 日本水路協会 MIRC 東京湾 http://www.mirc.jha.or.jp/cgi-bin/w/w-tcp?AREA=tokyo | 30秒メッシュ（約800m） | 10分間隔、潮汐のみ（調和定数） | 閲覧無料。販売はPDF/紙（基本料4,510円＋1枚110円）で数値ではない |
| 海上保安庁「海しる」潮流推算（東京湾）v2 https://www.msil.go.jp/meta/10043j.pdf | 不明 | 潮汐のみ | 仕様書未確認。海しるAPIの有無も要確認 |
| 気象庁 日本沿岸海況監視予測システム | 約2km | 10日先まで | 潮汐あり。気象業務支援センター経由で有料。岸際には粗い |

### 実測（検証用）の候補

- **港湾空港技術研究所 東京湾フェリー（久里浜〜金谷）ADCP**：2003年から継続、湾口の流速を測定・公開。観音崎のすぐ南で最も有用。https://pari.mpat.go.jp/bdhome/ferry/ ／ https://www.pari.go.jp/unit/kaikj/tokyo-bay-ferry/ ／ 論文 https://www.tandfonline.com/doi/full/10.1080/21664250.2022.2122300
- **東京湾環境情報センター 海洋短波レーダー**：1.5km、毎時、ダウンロードあり。局は大黒・千葉・船橋で、横須賀沖は範囲外の可能性が高い。https://www.tbeic.go.jp/radar_tbeic/Top
- **神奈川県水産技術センター**：金田湾ブイ（2026年3月追加、流速の有無は未確認）、城ケ島沖ブイ（流向流速あり）。https://kanagawapref.kansoku-data.net/ ／ 東京湾口海況図 https://sui-kanagawa.jp/Kaikyozu/TokyoWanko/
- ユーザーの10月24日の観察（HANDOFF.md 参照）。

### 自前の高解像度化の材料

- 非構造格子モデル（FVCOM / SCHISM）なら岸際を30〜50mにできる。東大の研究室が東京湾向けの格子生成ツールを公開：https://github.com/estuarine-utokyo/fvcom-mesh-tools
- 参考研究：第三海堡付近の局所三次元計算（100m格子） https://www.jstage.jst.go.jp/article/proce1970/27/0/27_0_443/_pdf/-char/ja ／ 港空研 https://www.pari.go.jp/PDF/no1276.pdf

## 提案済みの進め方（ユーザー未承認）

1. JAMSTECにTSS500の数値データ提供・利用条件を問い合わせる（ユーザーが連絡）。
2. その予測を外側の境界条件にして、横須賀沿岸を細かく再計算する（既存の100m/250m計算の延長、または非構造格子への移行）。
3. フェリーADCPと10/24の観察で検証する。
4. 並行して、表示を流れる線のアニメーション＋観測点の矢印に作り替える（今のデータのままで可能）。

最初の作業候補：フェリーの実測を取得して、今のモデル（10/24の試験計算）と比較する。

## ネットワーク確認

新しいセッションで次に届くか確認する（`curl -sS -o /dev/null -w "%{http_code}\n" URL`）。

- cutlassfish.tokyo / tide-current-map.cutlassfish.tokyo
- www.jamstec.go.jp / www.eorc.jaxa.jp
- www.pari.go.jp / pari.mpat.go.jp
- www.tbeic.go.jp
- www.msil.go.jp / portal.msil.go.jp
- www.mirc.jha.or.jp
- sui-kanagawa.jp / kanagawapref.kansoku-data.net

届かなければ、環境設定のネットワークアクセスを全許可にするか、上記を許可ドメインに追加するようユーザーに伝える。

## ユーザーについて

- 長い待ち時間と確認の繰り返しを嫌う。許可済みの作業は進め、短い進捗を出す。
- スマートフォンから操作している。
- 「実測未検証の参考計算」という説明を維持。公開記事を初期原稿で上書きしない。キーや個人情報を公開資料に出さない。
