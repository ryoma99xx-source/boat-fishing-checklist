# ドラゴンカウンターを「タックル登録」より前に戻す

`index-before-tackle.html` は、タックル登録（ロッド・リール・組み合わせ、リール糸管理からの取り込み）を入れる直前の公開版です（コミットは `before-tackle.commit`）。

戻すとき（Claude に「タックル前に戻して」と頼めば同じことをします）：

```sh
cd sites/dragon-counter
cp rollback/index-before-tackle.html public/index.html
(cd tools && python3 -c "import catalog_add; catalog_add.refresh_hashes('index.html')")
# DEPLOY の Last request 行を書き換えて commit → push（1〜2分で公開）
```

- 戻しても利用者の記録は消えません。タックルの登録（S.cfg.tackle）や釣行のタックル（tr.tk）は保存されたまま残り、古い版はそれを読まないだけです。もう一度新しい版に戻せば、そのまま出てきます。
- タックル版の後に入れた別の修正があれば、戻すと一緒に消えるので、必要なら入れ直します。
