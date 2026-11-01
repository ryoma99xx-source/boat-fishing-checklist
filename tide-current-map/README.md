# 東京湾の潮と流れマップ（作業用ソース）

`app/` は https://tide-current-map.cutlassfish.tokyo/ のソース（v17エクスポート）に、横須賀沿岸の高解像度潮流モデルの作業を加えたものです。
ホスティング設定（`.openai/`）は含めていません。

- `app/scripts/tidelib.py` / `app/harmonic.js`：潮汐の調和解析・合成（気象庁の調和定数と一致を確認）
- `app/scripts/nested_model.py`：外側（東京湾250m）＋内側（横須賀沿岸50m）の入れ子潮流モデル
- `app/scripts/harmonic-export.py`：計算結果から格子点ごとの調和定数を書き出し（任意日時の流れを合成）
- `app/scripts/ferry-extract.py` / `ferry-harmonics.py`：港湾空港技術研究所の東京湾フェリーADCPから実測流速を取り出し・解析
- `app/scripts/validate-tide.py`：気象庁潮位局との比較
