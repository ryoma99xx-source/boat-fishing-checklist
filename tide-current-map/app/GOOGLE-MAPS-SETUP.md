# Google Mapsの設定と課金対策

このアプリに必要なのは **Maps JavaScript API** です。Places、Routes、Geocoding、Elevation、Map Tiles APIや、有料の月額サブスクリプションは今回の機能には使いません。海底の水深データはGoogle Mapsから取得しません。

## Google Cloud側の操作

1. [Google Cloud Console](https://console.cloud.google.com/)で、潮アプリ専用のプロジェクトを作成します。例：`tide-current-map`。本番用キーでは請求先アカウントの登録・紐付けが必要です。Demo Keyは公開運用向けではありません。
2. [Maps JavaScript API](https://console.cloud.google.com/apis/library/maps-backend.googleapis.com)を有効にします。
3. 「APIとサービス → 認証情報 → 認証情報を作成 → APIキー」で、潮アプリ専用キーを作ります。
4. キーの「アプリケーションの制限」は「ウェブサイト」を選び、許可URLに `https://tide-current-map.cutlassfish.tokyo/*` を設定します。ワイルドカードで全サイトや全サブドメインを許可しません。
5. 「APIの制限」は「キーを制限」を選び、**Maps JavaScript APIのみ**を許可します。WordPressのドメインやローカル開発用URLを追加する必要はありません。公開URLの変更時は見直します。
6. 「Google Maps Platform → 割り当て」で、Maps JavaScript APIの地図読み込みの上限を引き下げます。最初は「1分あたりの地図読み込み」を10程度とし、コンソールに「1日あたりの地図読み込み」の項目がある場合は200程度を目安にします。実際に表示される割り当て項目を確認してください。現在の公式資料にはプロジェクト別・IP別の分間上限が載っており、日次上限が常に設定できるとは限りません。分間上限だけでは月間の総額は制限できません。
7. 請求の「予算とアラート」も設定します。**通常の予算アラートは通知であり、自動停止ではありません。** 使用量アラートも併用してください。

## アプリへの反映

WordPress、プラグイン、お名前.comのDNSへキーを入力する作業はありません。アプリのホスティング（Sites）の環境変数として設定します。

| 名前 | 値 |
| --- | --- |
| `GOOGLE_MAPS_BROWSER_KEY` | 上記で利用制限したMaps専用キー |
| `GOOGLE_MAPS_ENABLED` | `true` |

このチャットからSitesの環境変数の反映と再公開を行えます。Google側の利用制限・割り当てを設定してから有効にします。キーは環境変数の管理上はsecretとして保存できますが、Maps JavaScript APIのキーは閲覧者のブラウザへ渡す仕様です。ウェブサイト制限とAPI制限が必須です。

## 追加済みのアプリ側対策

- 同じページ内ではGoogleの地図を1回だけ生成します。潮の時刻や地点を変える操作では作り直しません。同時に接続処理が走っても同じ処理を共有します。
- 同じブラウザで、Google地図の新規生成は直近1分に3回、直近1時間に20回まで。ブラウザが対応していれば複数タブ間でもロックを共有します。
- 制限中、ブラウザ保存が使えない場合、Googleの読み込み・認証に失敗した場合は地理院地図を使います。潮の計算は独立して続きます。
- Googleのキーは本番の独自URLの設定応答だけに含めます。通常のクロスサイト要求には渡しません。これは補助チェックで、偽装したHTTPヘッダーへの完全な防御ではありません。
- 緊急時は `GOOGLE_MAPS_ENABLED=false` として再公開します。以後、新しく開いたページではGoogleを読み込みません。既に読み込まれたキーの不正利用を止めるには、Google Cloud側でキーを無効化・再発行するか、Maps JavaScript APIを無効にします。

## 制限と費用の目安

2026年10月27日に確認した公式の従量課金表では、Dynamic Mapsは月10,000回までの無料枠があり、その次の料金帯は1,000回あたり7米ドルです。請求先アカウントに紐付く他プロジェクトの同じサービスの利用も考慮が必要です。

このアプリの回数制限は、同じブラウザでの異常な再読み込みを減らすためのものです。ストレージ削除・別端末・別ブラウザや、取り出したキーでこのアプリを経由しない利用には、そのまま適用できません。サイト全体の月間上限や、Googleの請求額の上限を保証する機能ではありません。

公開サイトを使うボットへの追加対策には、Firebase App Checkの導入・Google側での強制適用を検討できます。これはまだ設定していません。Google Mapsで完全に課金ゼロを保証する構成にはしていません。Googleの有料APIを利用せず地理院地図を使う場合は、Google Mapsの料金は発生しません。

## 公式資料

- [キーの作成と利用制限](https://developers.google.com/maps/documentation/javascript/get-api-key)
- [Maps JavaScript APIの割り当て・利用料金](https://developers.google.com/maps/documentation/javascript/usage-and-billing)
- [公式料金表](https://developers.google.com/maps/billing-and-pricing/pricing)
- [費用管理・予算通知と割り当ての違い](https://developers.google.com/maps/billing-and-pricing/manage-costs)
- [APIキーの保護](https://developers.google.com/maps/api-security-best-practices)
- [Firebase App Check](https://developers.google.com/maps/documentation/javascript/places-app-check)
