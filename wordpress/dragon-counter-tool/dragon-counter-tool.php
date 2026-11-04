<?php
/**
 * Plugin Name: Dragon Counter — Tool 05
 * Description: サイトのツール一覧とメニューに「ドラゴンカウンター（TOOL 05）」へのリンクを追加します。アプリ本体は https://dragon-counter.cutlassfish.tokyo/ で動きます（このプラグインはリンクだけ）。
 * Version: 1.0.1
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

define('DRAGON_COUNTER_TOOL_URL', 'https://dragon-counter.cutlassfish.tokyo/');
define('DRAGON_COUNTER_ARTICLE_URL', 'https://cutlassfish.tokyo/article/dragon-counter/');

add_action('wp_enqueue_scripts', function () {
    wp_enqueue_script('dragon-counter-tool-05', plugins_url('tool-05.js', __FILE__), array(), '1.0.1', true);
    wp_localize_script('dragon-counter-tool-05', 'DragonCounterTool', array(
        'url' => DRAGON_COUNTER_TOOL_URL,
        'articleUrl' => esc_url_raw(get_option('dragon_counter_article_url', '') ?: DRAGON_COUNTER_ARTICLE_URL),
    ));
});
