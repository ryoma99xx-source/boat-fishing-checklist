<?php
/**
 * Plugin Name: Tenya Catalog（テンヤカタログの絞り込み・検索）
 * Description: テンヤカタログの記事で、号数・新商品・メーカーの絞り込み、色や製品名の検索、釣れ筋テンヤとランキングを動かします。ドラゴンカウンターのツール版カタログ（https://dragon-counter.cutlassfish.tokyo/tenya-catalog/）と同じ catalog.js を読み込むだけで、データは記事の本文に入っています。本文に data-tcat の印がある記事でだけ読み込みます。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

add_action('wp_enqueue_scripts', function () {
    if (!is_singular()) { return; }
    $post = get_post();
    if (!$post || strpos($post->post_content, 'data-tcat') === false) { return; }
    // 日付を版にして、catalog.js を直したら翌日までに入れ替わるようにする
    wp_enqueue_script('cf-tenya-catalog', 'https://dragon-counter.cutlassfish.tokyo/tenya-catalog/catalog.js', array(), gmdate('Ymd'), true);
});
