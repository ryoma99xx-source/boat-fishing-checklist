<?php
/**
 * Plugin Name: 魚種名の変更（トラフグ → トラフグ・湾フグ）
 * Description: 有効にしたときに一度だけ、魚種（species）の「トラフグ」の名前を「トラフグ・湾フグ」に変えて、自分を無効にします。スラッグ（URL の /fish/torafugu/）は変えません。オーナー指示 2026-11-25。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 */
if (!defined('ABSPATH')) exit;
register_activation_hook(__FILE__, function () {
    $t = get_term_by('slug', 'torafugu', 'species');
    if ($t && !is_wp_error($t) && $t->name !== 'トラフグ・湾フグ') {
        $r = wp_update_term($t->term_id, 'species', array('name' => 'トラフグ・湾フグ'));
        update_option('cf_species_rename_result', is_wp_error($r) ? $r->get_error_message() : 'ok ' . $t->term_id);
    }
});
add_action('admin_init', function () {
    deactivate_plugins(plugin_basename(__FILE__));
});
