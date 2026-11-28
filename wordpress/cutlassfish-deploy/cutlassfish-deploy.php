<?php
/**
 * Plugin Name: Cutlassfish プラグイン更新の受け口
 * Description: このサイトの自作プラグイン（名前が決まったものだけ）を、REST API から zip で「置き換え」インストールします。管理者のアプリケーションパスワードでだけ使えます。テーマや他社のプラグインは触れません。削除・無効化の機能はありません。入れた記録は「ツール → プラグイン更新の記録」で見られます。
 * Version: 1.0.1
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

final class CF_Deploy {
    const NS  = 'cfdeploy/v1';
    const LOG = 'cfdeploy_log';
    /** 入れてよいプラグイン（フォルダ名）。ここに無いものは受け付けない */
    const ALLOW = '/\A(?:cutlassfish-[a-z0-9-]+|cf-gear-deals|dragon-counter-[a-z0-9-]+|tbt-site-insights-patch|tbt-catch-collector-ai)\z/';   // tbt-catch-collector-ai：釣果速報の天気の直し（オーナー指示 2026-11-28）

    public static function init() {
        add_action('rest_api_init', function () {
            register_rest_route(self::NS, '/plugins', array(
                'methods' => 'GET', 'callback' => array(__CLASS__, 'list_plugins'), 'permission_callback' => array(__CLASS__, 'can'),
            ));
            register_rest_route(self::NS, '/install', array(
                'methods' => 'POST', 'callback' => array(__CLASS__, 'install'), 'permission_callback' => array(__CLASS__, 'can'),
            ));
        });
        add_action('admin_menu', function () {
            add_management_page('プラグイン更新の記録', 'プラグイン更新の記録', 'manage_options', 'cfdeploy-log', array(__CLASS__, 'page'));
        });
    }

    public static function can() {
        return current_user_can('install_plugins') && current_user_can('update_plugins') && current_user_can('activate_plugins');
    }

    private static function load() {
        require_once ABSPATH . 'wp-admin/includes/file.php';
        require_once ABSPATH . 'wp-admin/includes/plugin.php';
        require_once ABSPATH . 'wp-admin/includes/misc.php';
        require_once ABSPATH . 'wp-admin/includes/class-wp-upgrader.php';
    }

    /** フォルダ名 → [file, version, active] */
    private static function mine() {
        self::load();
        $out = array();
        foreach (get_plugins() as $file => $p) {
            $dir = dirname($file);
            if ($dir === '.' || !preg_match(self::ALLOW, $dir)) { continue; }
            $out[$dir] = array('file' => $file, 'name' => $p['Name'], 'version' => $p['Version'], 'active' => is_plugin_active($file));
        }
        return $out;
    }

    public static function list_plugins() {
        return rest_ensure_response(array('plugins' => self::mine()));
    }

    private static function err($msg, $code = 400) {
        return new WP_Error('cfdeploy', $msg, array('status' => $code));
    }

    public static function install(WP_REST_Request $req) {
        $slug = sanitize_key((string) $req->get_param('slug'));
        if (!preg_match(self::ALLOW, $slug)) { return self::err('このプラグインは入れられません: ' . $slug, 403); }
        $data = $req->get_body();
        if (strlen($data) < 100 || substr($data, 0, 2) !== 'PK') { return self::err('zip が届いていません'); }
        if (strlen($data) > 20 * 1024 * 1024) { return self::err('zip が大きすぎます'); }
        if (!class_exists('ZipArchive')) { return self::err('サーバーで zip を確かめられません（ZipArchive なし）', 500); }

        self::load();
        $tmp = wp_tempnam($slug . '.zip');
        file_put_contents($tmp, $data);
        // 中身を確かめる：全部が <slug>/ の下、../ や絶対パスなし、プラグインの見出し（Plugin Name）がある php が1つ以上
        $z = new ZipArchive();
        if ($z->open($tmp) !== true) { @unlink($tmp); return self::err('zip を開けません'); }
        $main = '';
        for ($i = 0; $i < $z->numFiles; $i++) {
            $n = $z->getNameIndex($i);
            if (strpos($n, $slug . '/') !== 0 || strpos($n, '..') !== false || strpos($n, '\\') !== false) {
                $z->close(); @unlink($tmp); return self::err('zip の中に ' . $slug . '/ 以外のものがあります: ' . $n);
            }
            if (!$main && preg_match('#\A' . preg_quote($slug, '#') . '/[^/]+\.php\z#', $n) && preg_match('/Plugin Name:/', (string) $z->getFromIndex($i, 8192))) {
                $main = $n;
            }
        }
        $z->close();
        if (!$main) { @unlink($tmp); return self::err('プラグインの本体（Plugin Name のある php）が見つかりません'); }

        $before = self::mine();
        $was    = $before[$slug] ?? null;
        $skin   = new WP_Ajax_Upgrader_Skin();
        $up     = new Plugin_Upgrader($skin);
        $res    = $up->install($tmp, array('overwrite_package' => true, 'clear_update_cache' => true));
        @unlink($tmp);
        if (is_wp_error($res)) { return self::err('インストールに失敗: ' . $res->get_error_message(), 500); }
        if (!$res) {
            $e = $skin->get_errors();
            return self::err('インストールに失敗: ' . (is_wp_error($e) && $e->has_errors() ? $e->get_error_message() : '原因不明（ファイルを書けない設定かもしれません）'), 500);
        }
        wp_clean_plugins_cache(true);
        $after  = self::mine();
        $now    = $after[$slug] ?? null;
        $active = false;
        $want   = $was ? $was['active'] : (bool) $req->get_param('activate');
        if ($now && $want) {
            $a = activate_plugin($now['file']);
            if (is_wp_error($a)) { return self::err('入れましたが、有効化に失敗: ' . $a->get_error_message(), 500); }
            $active = true;
        } elseif ($now) {
            $active = is_plugin_active($now['file']);
        }
        $row = array(
            'time' => current_time('mysql'), 'user' => wp_get_current_user()->user_login, 'slug' => $slug,
            'from' => $was ? $was['version'] : '（新規）', 'to' => $now ? $now['version'] : '?', 'active' => $active,
        );
        $log = (array) get_option(self::LOG, array());
        array_unshift($log, $row);
        update_option(self::LOG, array_slice($log, 0, 100), false);
        return rest_ensure_response(array('ok' => true) + $row);
    }

    public static function page() {
        echo '<div class="wrap"><h1>プラグイン更新の記録</h1><p>REST API（cfdeploy/v1/install）から入れた自作プラグインの記録です。新しい順に100件まで。</p>';
        echo '<table class="widefat striped"><thead><tr><th>日時</th><th>ユーザー</th><th>プラグイン</th><th>前</th><th>後</th><th>有効</th></tr></thead><tbody>';
        foreach ((array) get_option(self::LOG, array()) as $r) {
            printf('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>', esc_html($r['time']), esc_html($r['user']), esc_html($r['slug']), esc_html($r['from']), esc_html($r['to']), $r['active'] ? '有効' : '—');
        }
        echo '</tbody></table></div>';
    }
}
CF_Deploy::init();
