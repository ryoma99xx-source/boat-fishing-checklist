<?php
/**
 * Plugin Name: タチウオの釣行記（1674）に魚種「太刀魚」を付ける
 * Description: 有効にしたときに一度だけ、記事 1674（【釣行記】26-11-28 タチウオ）に魚種（species）の「太刀魚」（スラッグ tachiuo）を足して、自分を無効にします。ほかの分類は変えません。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 */
if (!defined('ABSPATH')) exit;
register_activation_hook(__FILE__, function () {
    $t = get_term_by('slug', 'tachiuo', 'species');
    $p = get_post(1674);
    if (!$t || is_wp_error($t) || !$p) { update_option('cf_species_tachiuo1128_result', 'term or post not found'); return; }
    $r = wp_set_object_terms(1674, array((int) $t->term_id), 'species', true);   // true＝足すだけ
    clean_post_cache(1674);
    update_option('cf_species_tachiuo1128_result', is_wp_error($r) ? $r->get_error_message() : 'ok');
});
add_action('admin_init', function () {
    deactivate_plugins(plugin_basename(__FILE__));
});
