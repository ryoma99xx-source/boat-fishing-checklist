<?php
/**
 * Plugin Name: cutlassfish ブラウザで開く案内（有効版）
 * Description: Instagram・Threads・LINE などのアプリの中のブラウザで開かれたときに「Safari／Chrome で開く」案内を、ブラウザで2回目に来た人に「ホーム画面に追加」の案内を、画面の下に出します。3つの釣果カウンターと同じ inapp.js（https://dragon-counter.cutlassfish.tokyo/inapp.js）を読み込むだけです。ホーム画面から開いているときは何も出しません。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab
 */
if (!defined('ABSPATH')) { exit; }

add_action('wp_footer', function () {
    if (is_admin() || is_feed()) { return; }
    // inapp.js はサーバーが「毎回確認して読み込む」設定で返すので、直したらすぐ反映される
    echo '<script src="https://dragon-counter.cutlassfish.tokyo/inapp.js" data-kind="site" data-name="東京湾の魚・釣り" defer></script>' . "\n";
}, 99);
