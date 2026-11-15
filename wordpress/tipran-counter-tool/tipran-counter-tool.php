<?php
/**
 * Plugin Name: Tiprun Counter — Tool 06
 * Description: サイトのツール一覧とメニューに「ティップランカウンター（TOOL 06）」へのリンクを追加します。アプリ本体は https://dragon-counter.cutlassfish.tokyo/tipran/ で動きます（このプラグインはリンクだけ）。紹介記事（スラッグ tipran-counter）が公開されると「READ ARTICLE」も出ます。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

define('TIPRAN_COUNTER_TOOL_URL', 'https://dragon-counter.cutlassfish.tokyo/tipran/');

add_action('wp_enqueue_scripts', function () {
    $p = get_page_by_path('tipran-counter', OBJECT, array('tachiuo_post', 'post'));
    $article = ($p && $p->post_status === 'publish') ? get_permalink($p) : '';
    wp_enqueue_script('tipran-counter-tool-06', plugins_url('tool-06.js', __FILE__), array(), '1.0.0', true);
    wp_localize_script('tipran-counter-tool-06', 'TipranCounterTool', array(
        'url' => TIPRAN_COUNTER_TOOL_URL,
        'articleUrl' => $article ? esc_url_raw($article) : '',
    ));
});
