<?php
/**
 * Plugin Name: ムラサキイカの記事に魚種「イカ」を付ける
 * Description: 有効にしたときに一度だけ、記事 1311（むらさきいか（ムラサキイカ）とはどんなイカ？）に魚種（species）の「イカ」（スラッグ ika）を足して、自分を無効にします。ほかの分類は変えません。オーナー指示 2026-11-26。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 */
if (!defined('ABSPATH')) exit;
register_activation_hook(__FILE__, function () {
    $t = get_term_by('slug', 'ika', 'species');
    $p = get_post(1311);
    if (!$t || is_wp_error($t) || !$p) { update_option('cf_species_murasaki_result', 'term or post not found'); return; }
    $r = wp_set_object_terms(1311, array((int) $t->term_id), 'species', true);   // true＝足すだけ
    clean_post_cache(1311);
    update_option('cf_species_murasaki_result', is_wp_error($r) ? $r->get_error_message() : 'ok');
});
add_action('admin_init', function () {
    deactivate_plugins(plugin_basename(__FILE__));
});
