<?php
/**
 * Plugin Name: Cutlassfish 記事取り込み API
 * Description: 「記事・写真まとめて取り込み」と同じ記事パックZIPを、アプリケーションパスワードで認証した REST API から下書きとして取り込みます（Claude Code などの外部ツール用）。公開はしません。
 * Version: 1.0.0
 * Requires at least: 6.2
 * Requires PHP: 7.4
 * Author: Cutlassfish
 */
if (!defined('ABSPATH')) { exit; }

final class Cutlassfish_Article_Import_API {
    const NS = 'cfai/v1';
    const MAX_ZIP = 52428800; // 50MB, same as the admin importer

    public static function routes() {
        register_rest_route(self::NS, '/ping', array(
            'methods' => 'GET',
            'callback' => array(__CLASS__, 'ping'),
            'permission_callback' => array(__CLASS__, 'can'),
        ));
        register_rest_route(self::NS, '/import', array(
            'methods' => 'POST',
            'callback' => array(__CLASS__, 'import'),
            'permission_callback' => array(__CLASS__, 'can'),
            'args' => array('post_type' => array('type' => 'string', 'required' => true)),
        ));
    }

    public static function can() {
        if (!is_user_logged_in()) {
            return new WP_Error('rest_forbidden', '認証が必要です（ユーザー名とアプリケーションパスワード）。', array('status' => 401));
        }
        if (!current_user_can('edit_posts') || !current_user_can('upload_files')) {
            return new WP_Error('rest_forbidden', '投稿の編集とメディアのアップロード権限が必要です。', array('status' => 403));
        }
        return true;
    }

    private static function max_bytes() { return min(wp_max_upload_size(), self::MAX_ZIP); }

    // Same rule as the admin importer: post types with an editor that this user may create.
    public static function types() {
        return array_filter(get_post_types(array('show_ui' => true), 'objects'), function ($t) {
            $cap = isset($t->cap->create_posts) ? $t->cap->create_posts : $t->cap->edit_posts;
            return !in_array($t->name, array('attachment', 'wp_block', 'wp_navigation', 'wp_template', 'wp_template_part'), true)
                && post_type_supports($t->name, 'editor') && current_user_can($cap);
        });
    }

    public static function ping() {
        $types = array();
        foreach (self::types() as $t) { $types[] = array('name' => $t->name, 'label' => $t->labels->name); }
        return array(
            'ok' => true,
            'user' => wp_get_current_user()->user_login,
            'zip_extension' => class_exists('ZipArchive'),
            'max_bytes' => self::max_bytes(),
            'post_types' => $types,
            'admin_importer_active' => class_exists('Cutlassfish_Article_Importer'),
        );
    }

    private static function fail($message) { throw new RuntimeException($message); }
    private static function text($data, $key, $default = '') {
        if (!isset($data[$key])) { return $default; }
        if (!is_string($data[$key])) { self::fail($key . ' は文字列で指定してください。'); }
        return $data[$key];
    }

    // Copy of Cutlassfish_Article_Importer::validate (v1.0.0). The admin importer's own
    // version is used instead when it is active, so both paths accept the same packs.
    private static function validate_own($zip) {
        if ($zip->numFiles > 100) { self::fail('ZIP内のファイル数が多すぎます。'); }
        $entries = array(); $total = 0;
        for ($i = 0; $i < $zip->numFiles; $i++) {
            $s = $zip->statIndex($i);
            if (!$s) { self::fail('ZIPを読み取れません。'); }
            $name = $s['name'];
            if (!preg_match('~\A(?:article\.json|article\.html|images/|images/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|gif|webp))\z~', $name)) {
                self::fail('記事パックに未対応のファイルがあります：' . $name);
            }
            if (isset($entries[$name])) { self::fail('ZIP内に重複したファイル名があります。'); }
            $total += $s['size'];
            $limit = strpos($name, 'images/') === 0 ? 20 * MB_IN_BYTES : MB_IN_BYTES;
            if ($s['size'] > $limit || $total > 100 * MB_IN_BYTES) { self::fail('展開後のデータが大きすぎます。'); }
            $entries[$name] = $s;
        }
        if (!isset($entries['article.json'], $entries['article.html'])) { self::fail('article.json と article.html が必要です。'); }
        $m = json_decode($zip->getFromName('article.json'), true);
        if (!is_array($m) || ($m['version'] ?? null) !== 1) { self::fail('記事パックの形式が違います。version は 1 が必要です。'); }
        if (trim(self::text($m, 'title')) === '') { self::fail('記事タイトルがありません。'); }
        self::text($m, 'excerpt');
        $html = $zip->getFromName('article.html');
        if (!is_string($html) || trim($html) === '') { self::fail('記事本文が空です。'); }
        $images = $m['images'] ?? array();
        if (!is_array($images) || count($images) > 30) { self::fail('画像は30枚までです。'); }
        $seen = array();
        foreach ($images as $im) {
            if (!is_array($im)) { self::fail('画像情報が不正です。'); }
            $id = self::text($im, 'id'); $file = self::text($im, 'file');
            if (!preg_match('/\A[a-zA-Z0-9_-]+\z/', $id) || isset($seen[$id]) || !isset($entries[$file]) || $file === 'images/' || strpos($file, 'images/') !== 0) { self::fail('画像IDまたは画像ファイルが不正です。'); }
            foreach (array('alt', 'caption', 'title') as $k) { self::text($im, $k); }
            $seen[$id] = true;
        }
        preg_match_all('/\{\{image:([^}]+)\}\}/', $html, $matches);
        foreach ($matches[1] as $id) { if (!isset($seen[$id])) { self::fail('本文にある画像が見つかりません：' . $id); } }
        $featured = self::text($m, 'featured_image');
        if ($featured !== '' && !isset($seen[$featured])) { self::fail('アイキャッチ画像が見つかりません。'); }
        return array($m, $html, $images);
    }

    private static function validate($zip) {
        if (class_exists('Cutlassfish_Article_Importer') && is_callable(array('Cutlassfish_Article_Importer', 'validate'))) {
            return Cutlassfish_Article_Importer::validate($zip);
        }
        return self::validate_own($zip);
    }

    private static function result($post, $existing) {
        return array(
            'post_id' => (int) $post,
            'status' => get_post_status($post),
            'existing' => $existing,
            'edit_link' => get_edit_post_link($post, 'raw'),
            'preview_link' => get_preview_post_link($post),
            'title' => get_the_title($post),
        );
    }

    public static function import(WP_REST_Request $req) {
        $own_tmp = '';
        // REST requests do not load the admin file helpers (wp_tempnam, media_handle_sideload).
        require_once ABSPATH . 'wp-admin/includes/file.php';
        require_once ABSPATH . 'wp-admin/includes/media.php';
        require_once ABSPATH . 'wp-admin/includes/image.php';
        try {
            if (!class_exists('ZipArchive')) { self::fail('PHP ZIP拡張が有効になっていません。'); }
            $types = self::types(); $type = sanitize_key((string) $req->get_param('post_type'));
            if (!isset($types[$type])) { self::fail('post_type が使えません：' . $type . '（/cfai/v1/ping で一覧を確認）'); }

            // Accept either multipart field "article_pack" or a raw application/zip body.
            $files = $req->get_file_params();
            if (!empty($files['article_pack'])) {
                $f = $files['article_pack'];
                if (!is_string($f['tmp_name']) || $f['error'] !== UPLOAD_ERR_OK || !is_uploaded_file($f['tmp_name'])) { self::fail('ZIPをアップロードできませんでした。'); }
                $path = $f['tmp_name'];
            } else {
                $body = $req->get_body();
                if (!is_string($body) || $body === '') { self::fail('ZIPが送られていません。'); }
                if (strlen($body) > self::max_bytes()) { self::fail('ZIPがアップロード上限を超えています。'); }
                $own_tmp = wp_tempnam('cfai-pack.zip');
                if (!$own_tmp || file_put_contents($own_tmp, $body) !== strlen($body)) { self::fail('一時ファイルを作成できません。'); }
                unset($body);
                $path = $own_tmp;
            }
            if (filesize($path) > self::max_bytes()) { self::fail('ZIPがアップロード上限を超えています。'); }
            $res = self::import_file($path, $type);
            return new WP_REST_Response($res, $res['existing'] ? 200 : 201);
        } catch (Throwable $e) {
            return new WP_Error('cfai_import_failed', '取り込めませんでした：' . $e->getMessage(), array('status' => 400));
        } finally {
            if ($own_tmp && is_file($own_tmp)) { wp_delete_file($own_tmp); }
        }
    }

    // Same steps as the admin importer's run(): register photos, swap {{image:id}} URLs,
    // save as one Custom HTML block draft, set the featured image, never publish.
    private static function import_file($path, $type) {
        $zip = null; $opened = false; $post = 0; $attachments = array(); $temps = array(); $lock = ''; $locked = false; $success = false;
        try {
            $hash = hash_file('sha256', $path);
            $existing = get_posts(array('post_type' => $type, 'post_status' => array('draft', 'pending', 'publish', 'future', 'private', 'trash'), 'meta_key' => '_cfai_pack_hash', 'meta_value' => $hash, 'numberposts' => 1));
            if ($existing) {
                if (!current_user_can('edit_post', $existing[0]->ID)) { self::fail('同じ記事はすでに取り込まれています。'); }
                if ($existing[0]->post_status === 'trash') { self::fail('同じ記事はゴミ箱にあります。復元してから編集してください。'); }
                $success = true;
                return self::result($existing[0]->ID, true);
            }
            $lock = 'cfai_lock_' . $hash;
            $locked = add_option($lock, time(), '', false);
            if (!$locked) { self::fail('同じZIPの取り込みが処理中、または中断されています。'); }
            $zip = new ZipArchive();
            if ($zip->open($path) !== true) { self::fail('ZIPを開けません。'); }
            $opened = true;
            list($m, $html, $images) = self::validate($zip);
            require_once ABSPATH . 'wp-admin/includes/file.php';
            require_once ABSPATH . 'wp-admin/includes/media.php';
            require_once ABSPATH . 'wp-admin/includes/image.php';
            $prepared = array();
            foreach ($images as $im) {
                $tmp = wp_tempnam(basename($im['file']));
                if (!$tmp) { self::fail('一時ファイルを作成できません。'); }
                $temps[] = $tmp;
                $bytes = $zip->getFromName($im['file']);
                if ($bytes === false || file_put_contents($tmp, $bytes) !== strlen($bytes)) { self::fail('画像を読み取れません。'); }
                unset($bytes);
                $mime = wp_get_image_mime($tmp);
                $allowed = array('jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'png' => 'image/png', 'gif' => 'image/gif', 'webp' => 'image/webp');
                $ext = strtolower(pathinfo($im['file'], PATHINFO_EXTENSION));
                $size = @getimagesize($tmp);
                if (!$size || !isset($allowed[$ext]) || $mime !== $allowed[$ext] || $size[0] * $size[1] > 40000000) { self::fail('画像の種類または解像度が未対応です：' . $im['file']); }
                $prepared[] = array($im, $tmp);
            }
            $post = wp_insert_post(wp_slash(array('post_type' => $type, 'post_status' => 'draft', 'post_title' => sanitize_text_field($m['title']), 'post_excerpt' => sanitize_textarea_field($m['excerpt'] ?? ''), 'post_author' => get_current_user_id())), true);
            if (is_wp_error($post)) { $msg = $post->get_error_message(); $post = 0; self::fail($msg); }
            $replace = array(); $by_id = array();
            foreach ($prepared as $item) {
                list($im, $tmp) = $item;
                $id = media_handle_sideload(array('name' => basename($im['file']), 'tmp_name' => $tmp, 'error' => 0, 'size' => filesize($tmp)), $post, null, wp_slash(array('post_title' => sanitize_text_field($im['title'] ?? $im['id']), 'post_excerpt' => sanitize_textarea_field($im['caption'] ?? ''))));
                if (is_wp_error($id)) { self::fail($id->get_error_message()); }
                $attachments[] = $id; $by_id[$im['id']] = $id;
                update_post_meta($id, '_wp_attachment_image_alt', sanitize_text_field($im['alt'] ?? ''));
                $url = wp_get_attachment_url($id);
                if (!$url) { self::fail('画像URLを取得できません。'); }
                $replace['{{image:' . $im['id'] . '}}'] = esc_url($url);
            }
            $html = wp_kses_post(strtr($html, $replace));
            $html = preg_replace('/<!--\s*\/?wp:.*?-->/s', '', $html);
            $updated = wp_update_post(wp_slash(array('ID' => $post, 'post_status' => 'draft', 'post_content' => "<!-- wp:html -->\n" . $html . "\n<!-- /wp:html -->")), true);
            if (is_wp_error($updated)) { self::fail($updated->get_error_message()); }
            if (!empty($m['featured_image'])) { set_post_thumbnail($post, $by_id[$m['featured_image']]); }
            update_post_meta($post, '_cfai_pack_hash', $hash);
            update_post_meta($post, '_cfai_via', 'api');
            $success = true;
            return self::result($post, false);
        } finally {
            if ($opened) { $zip->close(); }
            foreach ($temps as $tmp) { if (is_file($tmp)) { wp_delete_file($tmp); } }
            if (!$success) {
                foreach ($attachments as $id) { wp_delete_attachment($id, true); }
                if ($post) { wp_delete_post($post, true); }
            }
            if ($locked) { delete_option($lock); }
        }
    }
}
add_action('rest_api_init', array('Cutlassfish_Article_Import_API', 'routes'));
