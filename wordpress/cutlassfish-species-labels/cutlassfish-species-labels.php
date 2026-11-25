<?php
/**
 * Plugin Name: 魚種の表示名（トラフグ・湾フグ）
 * Description: 魚種「トラフグ」を「トラフグ・湾フグ」と表示します。魚種の名前そのものは変更済みですが、テーマの見出し・メニュー・パンくず・トップのタイルなどに「トラフグ」と直接書かれているところを、表示のときに置き換えます。本文の文章（「トラフグ釣り」など）は変えません。URL（/fish/torafugu/）も変えません。オーナー指示 2026-11-25。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 */
if (!defined('ABSPATH')) exit;
add_action('template_redirect', function () {
    if (is_admin() || wp_doing_ajax() || (defined('REST_REQUEST') && REST_REQUEST) || is_feed()) return;
    ob_start(function ($html) {
        $n = 'トラフグ・湾フグ';
        $map = array(
            'TORAFUGU<small>トラフグ</small>' => 'TORAFUGU<small>' . $n . '</small>',
            'fish/torafugu/">トラフグ</a>' => 'fish/torafugu/">' . $n . '</a>',
            '<span>トラフグ<br><small' => '<span>' . $n . '<br><small',
        );
        if (is_tax('species', 'torafugu')) {
            $map += array(
                '<p class="ja">トラフグ ― 釣る・知る・味わう</p>' => '<p class="ja">' . $n . ' ― 釣る・知る・味わう</p>',
                '<span>トラフグ</span></p>' => '<span>' . $n . '</span></p>',
                '<h2 class="en">トラフグ × FISHING</h2>' => '<h2 class="en">' . $n . ' × FISHING</h2>',
                '<p class="ja">トラフグの釣行記・ノウハウ</p>' => '<p class="ja">' . $n . 'の釣行記・ノウハウ</p>',
                '<h2 class="en">トラフグ × YOUTUBE</h2>' => '<h2 class="en">' . $n . ' × YOUTUBE</h2>',
                '<p class="ja">トラフグの関連動画</p>' => '<p class="ja">' . $n . 'の関連動画</p>',
            );
        }
        return strtr($html, $map);
    });
});
