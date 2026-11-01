# 東京湾の潮と流れマップ（作業用ソース）

`app/` は https://tide-current-map.cutlassfish.tokyo/ のソース（v17エクスポート）に、横須賀沿岸の高解像度潮流モデルの作業を加えたものです。
ホスティング設定（`.openai/`）は含めていません。

- `app/scripts/tidelib.py` / `app/harmonic.js`：潮汐の調和解析・合成（気象庁の調和定数と一致を確認）
- `app/scripts/nested_model.py`：外側（東京湾250m）＋内側（横須賀沿岸50m）の入れ子潮流モデル
- `app/scripts/harmonic-export.py`：計算結果から格子点ごとの調和定数を書き出し（任意日時の流れを合成）
- `app/scripts/ferry-extract.py` / `ferry-harmonics.py`：港湾空港技術研究所の東京湾フェリーADCPから実測流速を取り出し・解析
- `app/scripts/validate-tide.py`：気象庁潮位局との比較

## 現在の状態（2026-11-01）

- 自作モデルの調和定数（`app/data/harmonic-{inner,mid,outer}.*`）は 2026-10-01〜10-31 の30日計算から作成。任意の日時に合成して表示。
  - inner：横須賀沿岸 50m（35.195–35.345N, 139.625–139.815E）
  - mid：観音崎以北・海堡・中ノ瀬・木更津沖 100m（35.20–35.46N, 139.66–139.96E）
  - outer：東京湾・浦賀水道 250m
- 境界の潮位は油壺・館山・岡田・伊東の気象庁天文潮位から求めた調和定数（布良は湾口外で約14分早く、湾内の時刻がずれるため不使用）。
- 検証結果の要約は `app/data/model-validation.json`、詳細は `app/data/validation-detail.json`。
- 未解決：観音崎北側の強い流れ（公式推算 平均0.8kn・最大1.8kn）をモデルは弱く出す（平均0.4〜0.55kn）。湾口の岸寄りは潮汐以外の流れが大きい。
- 再計算：`python scripts/nested_model.py --days 30 --spinup 48 --start 2026-10-01T00:00 --out run.npz`（50m、約2.5時間）、
  100m は `--inner-bounds 35.20,35.46,139.66,139.96 --inner-dx 100 --inner-dt 20 --inner-nu 2`。書き出しは `scripts/harmonic-export.py`。
- `scripts/qa-*.cjs` は旧UI（10/24事例）前提のままで未更新。
