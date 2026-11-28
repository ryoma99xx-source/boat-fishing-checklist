<?php
/**
 * Plugin Name: Cutlassfish プラグインの中身を取り出す（一時用・停止済み）
 * Description: 2026-11-28 に釣果速報のプラグイン（TBT Catch Collector AI）の中身を一度取り出すために使いました。いまは何もしません（取り出し口は外してあります）。管理画面を開くと自分を無効にします。消してかまいません。
 * Version: 1.0.3
 * Author: 3rd-Penguin Fishing Lab.
 */
if (!defined('ABSPATH')) exit;
register_activation_hook(__FILE__, function () { delete_option('cf_plugin_export_until'); });
add_action('init', function () { if (get_option('cf_plugin_export_until', null) !== null) { delete_option('cf_plugin_export_until'); } });
add_action('admin_init', function () { deactivate_plugins(plugin_basename(__FILE__)); });
