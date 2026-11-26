<?php
/**
 * Plugin Name: 免責事項に Amazon アソシエイトの一文を足す
 * Description: 有効にしたときに一度だけ、固定ページ「免責事項」（スラッグ disclaimer）の「広告・アフィリエイトについて」の段落の最後に、Amazon アソシエイトの決まり文句を足して、自分を無効にします。すでに入っていれば何もしません。変更は固定ページのリビジョンに残るので、管理画面から元に戻せます。オーナー指示 2026-11-26。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 */
if (!defined('ABSPATH')) exit;
register_activation_hook(__FILE__, function () {
    $p = get_page_by_path('disclaimer', OBJECT, 'page');
    if (!$p) { update_option('cf_disclaimer_amazon_result', 'not found'); return; }
    $add  = 'Amazonのアソシエイトとして、当サイトは適格販売により収入を得ています。';
    $mark = '当サイトが所定の紹介料を受け取ることがあります。';
    $c    = $p->post_content;
    if (strpos($c, '適格販売により収入を得ています') !== false) { update_option('cf_disclaimer_amazon_result', 'already there'); return; }
    if (substr_count($c, $mark) !== 1) { update_option('cf_disclaimer_amazon_result', 'mark not found in content'); return; }
    $r = wp_update_post(array('ID' => $p->ID, 'post_content' => wp_slash(str_replace($mark, $mark . $add, $c))), true);
    update_option('cf_disclaimer_amazon_result', is_wp_error($r) ? $r->get_error_message() : 'ok ' . $p->ID);
});
add_action('admin_init', function () {
    deactivate_plugins(plugin_basename(__FILE__));
});
