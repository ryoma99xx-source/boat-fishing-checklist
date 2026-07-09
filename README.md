# 釣り持ち物チェックリスト

釣行メンバー用の持ち物チェックと、共有できる「レンタル確認」ページです。

## Supabase設定

1. SupabaseのSQL Editorで `supabase/rental_checks.sql` を実行します。
2. VercelのEnvironment Variablesに次の2つを設定します。

```text
VITE_SUPABASE_URL
VITE_SUPABASE_ANON_KEY
```

値はSupabaseのProject Settings > APIから確認できます。

## ローカル起動

```bash
npm install
npm run dev
```

## デプロイ

Vercelにこのフォルダを接続すれば、`npm run build` で `dist` が作られます。
