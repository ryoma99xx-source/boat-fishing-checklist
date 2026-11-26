<?php
/**
 * Plugin Name: 見本のページ（Sample Page）をゴミ箱へ
 * Description: 有効にしたときに一度だけ、WordPress に最初から入っている見本の固定ページ「Sample Page」（スラッグ sample-page）をゴミ箱に入れて、自分を無効にします。完全には消さないので、管理画面の「固定ページ → ゴミ箱」から30日間は戻せます。題と中身が見本のままのときだけ動きます。オーナー指示 2026-11-26。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 */
if (!defined('ABSPATH')) exit;
register_activation_hook(__FILE__, function () {
    $p = get_page_by_path('sample-page', OBJECT, 'page');
    if (!$p) { update_option('cf_trash_sample_result', 'not found'); return; }
    // 見本のままのページだけ（題が Sample Page で、本文が見本の書き出し）。書き換えてあったら何もしない
    $is_sample = ($p->post_title === 'Sample Page') && (strpos($p->post_content, 'This is an example page.') !== false);
    if (!$is_sample) { update_option('cf_trash_sample_result', 'skipped: not the default sample'); return; }
    $r = wp_trash_post($p->ID);
    update_option('cf_trash_sample_result', $r ? 'trashed ' . $p->ID : 'failed');
});
add_action('admin_init', function () {
    deactivate_plugins(plugin_basename(__FILE__));
});
