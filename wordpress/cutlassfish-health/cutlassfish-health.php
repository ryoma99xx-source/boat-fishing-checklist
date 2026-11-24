<?php
/**
 * Plugin Name: cutlassfish サイトの点検窓口
 * Description: 定期メンテナンス（Claude の点検）用に、管理者だけが読める点検結果を返します：WordPress 本体・プラグイン・テーマの更新の有無、本体ファイルが公式と同じか、アップロード置き場の PHP ファイル、最近書き換わったファイル、管理者の一覧（REST：/wp-json/cfhealth/v1/status、manage_options が必要。読むだけ）。あわせて、WordPress.org のプラグイン・テーマを WordPress 標準の自動更新に任せます（失敗したら元に戻るしくみ）。
 * Version: 1.1.0
 * Author: 3rd-Penguin Fishing Lab.
 */
if (!defined('ABSPATH')) { exit; }

// 自動更新：WordPress.org のプラグイン・テーマは WordPress 標準の自動更新で入れる（オーナーの OK 2026-11-24）。本体は小さな更新（セキュリティ修正）だけ自動（WordPress の初期設定のまま）
add_filter('auto_update_plugin', '__return_true');
add_filter('auto_update_theme', '__return_true');

add_action('rest_api_init', function () {
    register_rest_route('cfhealth/v1', '/status', array(
        'methods' => 'GET',
        'permission_callback' => function () { return current_user_can('manage_options'); },
        'callback' => 'cfhealth_status',
    ));
});

function cfhealth_status() {
    require_once ABSPATH . 'wp-admin/includes/update.php';
    require_once ABSPATH . 'wp-admin/includes/plugin.php';
    require_once ABSPATH . 'wp-admin/includes/file.php';
    @set_time_limit(60);
    global $wp_version;
    // 更新の有無（WordPress.org に問い合わせ直す）
    wp_version_check(); wp_update_plugins(); wp_update_themes();
    $core = array();
    foreach ((array) get_core_updates() as $u) { if (!empty($u->response) && $u->response === 'upgrade') { $core[] = $u->current; } }
    $plugins = array();
    $up = get_site_transient('update_plugins');
    foreach (get_plugins() as $file => $p) {
        $row = array('file' => $file, 'name' => $p['Name'], 'version' => $p['Version'], 'active' => is_plugin_active($file));
        if ($up && isset($up->response[$file])) { $row['update'] = $up->response[$file]->new_version; }
        $plugins[] = $row;
    }
    $themes = array(); $ut = get_site_transient('update_themes');
    foreach (wp_get_themes() as $slug => $t) {
        $row = array('slug' => $slug, 'name' => $t->get('Name'), 'version' => $t->get('Version'), 'active' => get_stylesheet() === $slug);
        if ($ut && isset($ut->response[$slug])) { $row['update'] = $ut->response[$slug]['new_version']; }
        $themes[] = $row;
    }
    // 本体ファイルが公式の配布物と同じか（wp core verify-checksums と同じ考え方）
    $changed = array(); $missing = array(); $ck = get_core_checksums($wp_version, get_locale() ?: 'en_US');
    if (!$ck) { $ck = get_core_checksums($wp_version, 'en_US'); }
    if (is_array($ck)) {
        foreach ($ck as $f => $md5) {
            if (strpos($f, 'wp-content/') === 0) { continue; }
            $path = ABSPATH . $f;
            if (!file_exists($path)) { $missing[] = $f; continue; }
            if (md5_file($path) !== $md5) {
                // 本体は英語版のまま、表示だけ日本語にしているサイトでは、version.php だけが日本語版の照合値と違う（英語版とは同じ）。その差は問題にしない
                if ($f === 'wp-includes/version.php') { $en = get_core_checksums($wp_version, 'en_US'); if (is_array($en) && isset($en[$f]) && md5_file($path) === $en[$f]) { continue; } }
                $changed[] = $f;
            }
        }
    }
    // アップロード置き場に PHP があってはいけない。ここ7日で書き換わったプラグイン・テーマのファイル
    $up_dir = wp_get_upload_dir(); $uploads_php = array(); $recent = array(); $since = time() - 7 * 86400;
    $scan = function ($dir, $cb) { if (!is_dir($dir)) return; $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS)); foreach ($it as $f) { $cb($f); } };
    $scan($up_dir['basedir'], function ($f) use (&$uploads_php, $up_dir) { if (preg_match('/\.(php\d?|phtml|phar)$/i', $f->getFilename())) { $uploads_php[] = substr($f->getPathname(), strlen($up_dir['basedir'])); } });
    foreach (array(WP_PLUGIN_DIR, get_theme_root()) as $root) {
        $scan($root, function ($f) use (&$recent, $since) { if ($f->getMTime() >= $since && preg_match('/\.(php|js|htaccess)$/i', $f->getFilename())) { $recent[] = array(substr($f->getPathname(), strlen(WP_CONTENT_DIR)), gmdate('c', $f->getMTime())); } });
    }
    $root_extra = array();
    foreach (glob(ABSPATH . '*.php') ?: array() as $f) { $b = basename($f); if (!is_array($ck) || !isset($ck[$b])) { if ($b !== 'wp-config.php') { $root_extra[] = $b; } } }
    $admins = array();
    foreach (get_users(array('role' => 'administrator')) as $u) { $admins[] = array('login' => $u->user_login, 'registered' => $u->user_registered); }
    return array(
        'time' => gmdate('c'), 'wp' => $wp_version, 'php' => PHP_VERSION, 'core_updates' => $core,
        'plugins' => $plugins, 'themes' => $themes,
        'core_files' => array('checked' => is_array($ck) ? count($ck) : 0, 'changed' => array_slice($changed, 0, 50), 'missing' => array_slice($missing, 0, 50)),
        'root_extra_php' => $root_extra, 'uploads_php' => array_slice($uploads_php, 0, 50),
        'recent_files' => array_slice($recent, 0, 200), 'admins' => $admins,
        'auto_update_core_minor' => !defined('WP_AUTO_UPDATE_CORE') || WP_AUTO_UPDATE_CORE !== false,
    );
}


