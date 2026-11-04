<?php
/**
 * Plugin Name: Cutlassfish 記事取り込み API
 * Description: 「記事・写真まとめて取り込み」と同じ記事パックZIPを、アプリケーションパスワードで認証した REST API から下書きとして取り込みます（Claude Code などの外部ツール用）。v1.1.0 から、既存記事の読み出し・本文の差し替え（下書き）と、指示があったときの公開／下書き戻しもできます。記事や画像の削除はしません。
 * Version: 1.1.0
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
        self::routes_v11();
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
    // $allow_media (update only): featured_image may also be "media:<attachment_id>".
    private static function validate_own($zip, $allow_media = false) {
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
        if ($featured !== '' && !isset($seen[$featured]) && !($allow_media && preg_match('/\Amedia:[1-9][0-9]*\z/', $featured))) { self::fail('アイキャッチ画像が見つかりません。'); }
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

    // ---------------------------------------------------------------------------------
    // v1.1.0: read, rewrite and publish existing articles (tachiuo_post / post only).
    // ---------------------------------------------------------------------------------
    const EDIT_TYPES = array('tachiuo_post', 'post');
    const TOPIC_TAX = 'tachiuo_cat';
    const PREV_META = '_cfai_prev_content_';
    const PREV_KEEP = 5;
    const TODO_RE = '/[（(]\s*(オーナー記入|要確認|要追記|TODO)/u';

    public static function routes_v11() {
        $id = '(?P<id>\d+)';
        register_rest_route(self::NS, '/articles', array(
            'methods' => 'GET',
            'callback' => array(__CLASS__, 'list_articles'),
            'permission_callback' => array(__CLASS__, 'can'),
        ));
        register_rest_route(self::NS, '/articles/' . $id, array(
            'methods' => 'GET',
            'callback' => array(__CLASS__, 'get_article'),
            'permission_callback' => array(__CLASS__, 'can'),
        ));
        register_rest_route(self::NS, '/articles/' . $id . '/content', array(
            'methods' => 'POST',
            'callback' => array(__CLASS__, 'update_content'),
            'permission_callback' => array(__CLASS__, 'can'),
        ));
        register_rest_route(self::NS, '/articles/' . $id . '/publish', array(
            'methods' => 'POST',
            'callback' => array(__CLASS__, 'publish_article'),
            'permission_callback' => array(__CLASS__, 'can'),
        ));
        register_rest_route(self::NS, '/articles/' . $id . '/unpublish', array(
            'methods' => 'POST',
            'callback' => array(__CLASS__, 'unpublish_article'),
            'permission_callback' => array(__CLASS__, 'can'),
        ));
    }

    private static function err($code, $message, $status) {
        return new WP_Error($code, $message, array('status' => $status));
    }

    private static function edit_types() {
        return array_values(array_filter(self::EDIT_TYPES, 'post_type_exists'));
    }

    // Returns the post, or a WP_Error (404 when missing / other type, 403 when not editable).
    private static function load_post($id) {
        $post = get_post((int) $id);
        if (!$post || !in_array($post->post_type, self::edit_types(), true) || in_array($post->post_status, array('trash', 'auto-draft', 'inherit'), true)) {
            return self::err('cfai_not_found', '記事が見つかりません（記事または投稿のIDを指定してください）。', 404);
        }
        if (!current_user_can('edit_post', $post->ID)) {
            return self::err('cfai_forbidden', 'この記事を編集する権限がありません。', 403);
        }
        return $post;
    }

    // Inner HTML of a single Custom HTML block, else the raw post_content.
    private static function split_content($content) {
        if (preg_match('~\A\s*<!-- wp:html -->\n?(.*?)\n?<!-- /wp:html -->\s*\z~s', $content, $m) && strpos($m[1], '<!-- /wp:html -->') === false && strpos($m[1], '<!-- wp:') === false) {
            return array($m[1], 'wp_html_block');
        }
        return array($content, 'raw');
    }

    private static function plain_text($html) {
        $text = wp_strip_all_tags(preg_replace('/<!--.*?-->/s', '', $html));
        return trim(preg_replace('/\s+/u', ' ', html_entity_decode($text, ENT_QUOTES, 'UTF-8')));
    }

    private static function todos($html) {
        $text = self::plain_text($html);
        $out = array();
        if (!preg_match_all(self::TODO_RE, $text, $m, PREG_OFFSET_CAPTURE)) { return $out; }
        foreach ($m[0] as $i => $hit) {
            $pos = mb_strlen(substr($text, 0, $hit[1]), 'UTF-8'); // byte offset -> char offset
            $start = max(0, $pos - 20);
            $out[] = array(
                'marker' => $m[1][$i][0],
                'snippet' => ($start > 0 ? '…' : '') . mb_substr($text, $start, 80, 'UTF-8') . '…',
            );
            if (count($out) >= 50) { break; }
        }
        return $out;
    }

    private static function topics($post) {
        if (!taxonomy_exists(self::TOPIC_TAX) || !is_object_in_taxonomy($post->post_type, self::TOPIC_TAX)) { return array(); }
        $terms = wp_get_object_terms($post->ID, self::TOPIC_TAX, array('fields' => 'slugs'));
        return is_wp_error($terms) ? array() : array_values($terms);
    }

    private static function summary($post) {
        $post = get_post($post);
        $thumb = (int) get_post_thumbnail_id($post);
        $species = array();
        if (taxonomy_exists('species') && is_object_in_taxonomy($post->post_type, 'species')) {
            $t = wp_get_object_terms($post->ID, 'species', array('fields' => 'slugs'));
            if (!is_wp_error($t)) { $species = array_values($t); }
        }
        $text = self::plain_text($post->post_content);
        return array(
            'id' => (int) $post->ID,
            'title' => get_the_title($post),
            'status' => $post->post_status,
            'modified' => get_post_modified_time('c', true, $post),
            'date' => $post->post_status === 'draft' ? null : get_post_time('c', true, $post),
            'link' => get_permalink($post),
            'edit_link' => get_edit_post_link($post->ID, 'raw'),
            'preview_link' => get_preview_post_link($post),
            'post_type' => $post->post_type,
            'topics' => self::topics($post),
            'species' => $species,
            'slug' => $post->post_name,
            'featured_image' => $thumb ? wp_get_attachment_url($thumb) : null,
            'featured_image_id' => $thumb ?: null,
            // Japanese text has no spaces, so this is the number of characters (without whitespace).
            'word_count' => mb_strlen(preg_replace('/\s+/u', '', $text), 'UTF-8'),
            'todo' => self::todos($post->post_content),
        );
    }

    private static function image_info($id, $in_content) {
        $file = get_attached_file($id);
        return array(
            'id' => (int) $id,
            'url' => wp_get_attachment_url($id),
            'alt' => (string) get_post_meta($id, '_wp_attachment_image_alt', true),
            'caption' => (string) wp_get_attachment_caption($id),
            'title' => get_the_title($id),
            'filename' => $file ? wp_basename($file) : '',
            'parent' => (int) get_post_field('post_parent', $id),
            'in_content' => $in_content,
        );
    }

    // Images attached to the post, the featured image, and library images used in the body.
    private static function images($post) {
        $ids = array();
        foreach (get_attached_media('image', $post->ID) as $a) { $ids[(int) $a->ID] = true; }
        $thumb = (int) get_post_thumbnail_id($post);
        if ($thumb) { $ids[$thumb] = true; }
        preg_match_all('/<img[^>]+src=["\']([^"\']+)["\']/i', $post->post_content, $m);
        $urls = array_unique($m[1]);
        foreach ($urls as $url) {
            $aid = attachment_url_to_postid($url);
            if ($aid) { $ids[$aid] = true; }
        }
        $out = array();
        foreach (array_keys($ids) as $aid) {
            if (get_post_type($aid) !== 'attachment' || !wp_attachment_is_image($aid)) { continue; }
            $out[] = self::image_info($aid, in_array(wp_get_attachment_url($aid), $urls, true));
        }
        return $out;
    }

    public static function list_articles(WP_REST_Request $req) {
        $status = (string) ($req->get_param('status') ?: 'any');
        $map = array('draft' => array('draft'), 'pending' => array('pending'), 'future' => array('future'), 'private' => array('private'), 'publish' => array('publish'),
            'any' => array('draft', 'pending', 'future', 'private', 'publish'));
        if (!isset($map[$status])) { return self::err('cfai_bad_status', 'status は draft / publish / pending / future / private / any のどれかです。', 400); }
        $types = self::edit_types();
        $type = (string) $req->get_param('post_type');
        if ($type !== '') {
            if (!in_array($type, $types, true)) { return self::err('cfai_bad_type', 'post_type は ' . implode(' / ', $types) . ' のどれかです。', 400); }
            $types = array($type);
        }
        $per_page = max(1, min(100, (int) ($req->get_param('per_page') ?: 20)));
        $page = max(1, (int) ($req->get_param('page') ?: 1));
        $args = array('post_type' => $types, 'post_status' => $map[$status], 'posts_per_page' => $per_page, 'paged' => $page,
            'orderby' => 'modified', 'order' => 'DESC', 'perm' => 'editable', 'ignore_sticky_posts' => true);
        $search = trim((string) $req->get_param('search'));
        if ($search !== '') { $args['s'] = $search; }
        $q = new WP_Query($args);
        $items = array();
        foreach ($q->posts as $p) {
            if (current_user_can('edit_post', $p->ID)) { $items[] = self::summary($p); }
        }
        return array('total' => (int) $q->found_posts, 'total_pages' => (int) $q->max_num_pages, 'page' => $page, 'per_page' => $per_page, 'articles' => $items);
    }

    public static function get_article(WP_REST_Request $req) {
        $post = self::load_post($req['id']);
        if (is_wp_error($post)) { return $post; }
        list($content, $format) = self::split_content($post->post_content);
        return array_merge(self::summary($post), array(
            'excerpt' => $post->post_excerpt,
            'content' => $content,
            'content_format' => $format,
            'images' => self::images($post),
        ));
    }

    // Shared by import-style uploads: multipart field "article_pack" or a raw application/zip body.
    // Returns array(path, own_tmp).
    private static function upload_path(WP_REST_Request $req) {
        $files = $req->get_file_params();
        if (!empty($files['article_pack'])) {
            $f = $files['article_pack'];
            if (!is_string($f['tmp_name']) || $f['error'] !== UPLOAD_ERR_OK || !is_uploaded_file($f['tmp_name'])) { self::fail('ZIPをアップロードできませんでした。'); }
            $path = $f['tmp_name']; $own = '';
        } else {
            $body = $req->get_body();
            if (!is_string($body) || $body === '') { self::fail('ZIPが送られていません。'); }
            if (strlen($body) > self::max_bytes()) { self::fail('ZIPがアップロード上限を超えています。'); }
            $own = wp_tempnam('cfai-pack.zip');
            if (!$own || file_put_contents($own, $body) !== strlen($body)) { self::fail('一時ファイルを作成できません。'); }
            unset($body);
            $path = $own;
        }
        if (filesize($path) > self::max_bytes()) { self::fail('ZIPがアップロード上限を超えています。'); }
        return array($path, $own);
    }

    // An existing image attachment that {{media:N}} / featured_image "media:N" may point to.
    private static function media_ok($id) {
        $id = (int) $id;
        return $id > 0 && get_post_type($id) === 'attachment' && wp_attachment_is_image($id) && current_user_can('read_post', $id);
    }

    // Same rules as validate_own() (images optional), plus {{media:N}} placeholders and featured_image "media:N".
    private static function validate_update($zip) {
        list($m, $html, $images) = self::validate_own($zip, true);
        $featured = $m['featured_image'] ?? '';
        if (is_string($featured) && strpos($featured, 'media:') === 0 && !self::media_ok(substr($featured, 6))) { self::fail('アイキャッチ画像（既存画像）が見つかりません：' . $featured); }
        preg_match_all('/\{\{media:([^}]*)\}\}/', $html, $mm);
        foreach (array_unique($mm[1]) as $aid) {
            if (!preg_match('/\A[1-9][0-9]*\z/', $aid) || !self::media_ok($aid)) { self::fail('本文にある既存画像が見つかりません：media:' . $aid); }
        }
        return array($m, $html, $images);
    }


    // Unpack and check pack images (same checks as import_file). Returns array of array($im, $tmp).
    private static function prepare_images($zip, $images, &$temps) {
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
        return $prepared;
    }

    private static function lock($key) {
        if (add_option($key, time(), '', false)) { return true; }
        $t = (int) get_option($key);
        if ($t && $t < time() - 600) { delete_option($key); return add_option($key, time(), '', false); }
        return false;
    }

    // Keep the previous title/excerpt/content in post meta; only the newest PREV_KEEP are kept.
    private static function save_prev($post) {
        $ts = time();
        while (metadata_exists('post', $post->ID, self::PREV_META . $ts)) { $ts++; }
        $key = self::PREV_META . $ts;
        add_post_meta($post->ID, $key, wp_slash(array(
            'title' => $post->post_title,
            'excerpt' => $post->post_excerpt,
            'content' => $post->post_content,
            'status' => $post->post_status,
            'thumbnail_id' => (int) get_post_thumbnail_id($post),
            'saved_at' => gmdate('c', $ts),
            'user' => wp_get_current_user()->user_login,
        )), true);
        $keys = array();
        foreach (array_keys(get_post_meta($post->ID)) as $k) {
            if (preg_match('/\A' . preg_quote(self::PREV_META, '/') . '(\d+)\z/', $k, $mm)) { $keys[(int) $mm[1]] = $k; }
        }
        ksort($keys);
        while (count($keys) > self::PREV_KEEP) { delete_post_meta($post->ID, array_shift($keys)); }
        return $key;
    }

    public static function update_content(WP_REST_Request $req) {
        $post = self::load_post($req['id']);
        if (is_wp_error($post)) { return $post; }
        if (in_array($post->post_status, array('publish', 'future'), true) && !in_array((string) $req->get_param('allow_published'), array('1', 'true'), true)) {
            return self::err('cfai_published', 'この記事は公開済み（または予約済み）です。オーナーの指示がある場合だけ allow_published=1 を付けて更新してください。', 409);
        }
        require_once ABSPATH . 'wp-admin/includes/file.php';
        require_once ABSPATH . 'wp-admin/includes/media.php';
        require_once ABSPATH . 'wp-admin/includes/image.php';
        $own_tmp = ''; $zip = null; $opened = false; $temps = array(); $attachments = array(); $success = false;
        $lock = 'cfai_update_lock_' . $post->ID; $locked = false;
        try {
            if (!class_exists('ZipArchive')) { self::fail('PHP ZIP拡張が有効になっていません。'); }
            list($path, $own_tmp) = self::upload_path($req);
            $locked = self::lock($lock);
            if (!$locked) { self::fail('この記事の更新が処理中です。少し待ってからやり直してください。'); }
            $zip = new ZipArchive();
            if ($zip->open($path) !== true) { self::fail('ZIPを開けません。'); }
            $opened = true;
            list($m, $html, $images) = self::validate_update($zip);
            $prepared = self::prepare_images($zip, $images, $temps);

            $replace = array(); $by_id = array();
            foreach ($prepared as $item) {
                list($im, $tmp) = $item;
                $aid = media_handle_sideload(array('name' => basename($im['file']), 'tmp_name' => $tmp, 'error' => 0, 'size' => filesize($tmp)), $post->ID, null, wp_slash(array('post_title' => sanitize_text_field($im['title'] ?? $im['id']), 'post_excerpt' => sanitize_textarea_field($im['caption'] ?? ''))));
                if (is_wp_error($aid)) { self::fail($aid->get_error_message()); }
                $attachments[] = $aid; $by_id[$im['id']] = $aid;
                update_post_meta($aid, '_wp_attachment_image_alt', sanitize_text_field($im['alt'] ?? ''));
                $url = wp_get_attachment_url($aid);
                if (!$url) { self::fail('画像URLを取得できません。'); }
                $replace['{{image:' . $im['id'] . '}}'] = esc_url($url);
            }
            preg_match_all('/\{\{media:([1-9][0-9]*)\}\}/', $html, $mm);
            foreach (array_unique($mm[1]) as $aid) {
                $url = wp_get_attachment_url((int) $aid);
                if (!$url) { self::fail('既存画像のURLを取得できません：media:' . $aid); }
                $replace['{{media:' . $aid . '}}'] = esc_url($url);
            }
            $html = wp_kses_post(strtr($html, $replace));
            $html = preg_replace('/<!--\s*\/?wp:.*?-->/s', '', $html);

            // Snapshot the current state before writing: a revision (when the type supports
            // revisions) and our own meta copy (always).
            $revision_id = null;
            if (wp_revisions_enabled($post)) {
                $rev = wp_save_post_revision($post->ID);
                if ($rev && !is_wp_error($rev)) { $revision_id = (int) $rev; }
                else { $revs = wp_get_post_revisions($post->ID, array('posts_per_page' => 1)); if ($revs) { $revision_id = (int) key($revs); } }
            }
            $prev_key = self::save_prev($post);

            $updated = wp_update_post(wp_slash(array(
                'ID' => $post->ID,
                'post_title' => sanitize_text_field($m['title']),
                'post_excerpt' => sanitize_textarea_field($m['excerpt'] ?? ''),
                'post_content' => "<!-- wp:html -->\n" . $html . "\n<!-- /wp:html -->",
            )), true);
            if (is_wp_error($updated)) { delete_post_meta($post->ID, $prev_key); self::fail($updated->get_error_message()); }
            $success = true; // the post is written; keep the new images from here on

            $featured = $m['featured_image'] ?? '';
            if (is_string($featured) && $featured !== '') {
                set_post_thumbnail($post->ID, strpos($featured, 'media:') === 0 ? (int) substr($featured, 6) : $by_id[$featured]);
            }
            update_post_meta($post->ID, '_cfai_last_update', gmdate('c'));
            clean_post_cache($post->ID);
            return array_merge(self::summary($post->ID), array(
                'excerpt' => get_post_field('post_excerpt', $post->ID),
                'images' => self::images(get_post($post->ID)),
                'revision_id' => $revision_id,
                'prev_content_meta' => $prev_key,
                'new_images' => $by_id,
            ));
        } catch (Throwable $e) {
            return self::err('cfai_update_failed', '更新できませんでした：' . $e->getMessage(), 400);
        } finally {
            if ($opened) { $zip->close(); }
            foreach ($temps as $tmp) { if (is_file($tmp)) { wp_delete_file($tmp); } }
            // Only images uploaded by this failed request are removed; existing media is never touched.
            if (!$success) { foreach ($attachments as $aid) { wp_delete_attachment($aid, true); } }
            if ($own_tmp && is_file($own_tmp)) { wp_delete_file($own_tmp); }
            if ($locked) { delete_option($lock); }
        }
    }

    private static function json_params(WP_REST_Request $req) {
        $p = $req->get_json_params();
        if ($p === null) {
            $body = trim((string) $req->get_body());
            if ($body !== '') {
                $p = json_decode($body, true);
                if (!is_array($p)) { return self::err('cfai_bad_json', '本文は JSON で送ってください。', 400); }
            } else { $p = array(); }
        }
        return is_array($p) ? $p : self::err('cfai_bad_json', '本文は JSON で送ってください。', 400);
    }

    public static function publish_article(WP_REST_Request $req) {
        $post = self::load_post($req['id']);
        if (is_wp_error($post)) { return $post; }
        $type = get_post_type_object($post->post_type);
        if (!current_user_can($type->cap->publish_posts)) { return self::err('cfai_forbidden', 'この投稿タイプを公開する権限がありません。', 403); }
        $p = self::json_params($req);
        if (is_wp_error($p)) { return $p; }
        $data = array('ID' => $post->ID, 'post_status' => 'publish');

        if (isset($p['slug'])) {
            if (!is_string($p['slug'])) { return self::err('cfai_bad_slug', 'slug は文字列で指定してください。', 400); }
            $slug = sanitize_title($p['slug']);
            if ($slug === '') { return self::err('cfai_bad_slug', 'slug が空か、使えない文字だけです。', 400); }
            $data['post_name'] = $slug;
        }

        $term_ids = null;
        if (isset($p['topics'])) {
            if (!is_array($p['topics'])) { return self::err('cfai_bad_topics', 'topics はスラッグの配列で指定してください。', 400); }
            if (!taxonomy_exists(self::TOPIC_TAX) || !is_object_in_taxonomy($post->post_type, self::TOPIC_TAX)) {
                return self::err('cfai_bad_topics', 'この投稿タイプにはトピック（' . self::TOPIC_TAX . '）がありません。', 400);
            }
            $term_ids = array();
            foreach ($p['topics'] as $s) {
                $term = is_string($s) ? get_term_by('slug', $s, self::TOPIC_TAX) : false;
                if (!$term) { return self::err('cfai_bad_topics', 'トピックが見つかりません：' . (is_string($s) ? $s : gettype($s)), 400); }
                $term_ids[] = (int) $term->term_id;
            }
        }

        if (isset($p['date']) && $p['date'] !== '') {
            $d = is_string($p['date']) ? rest_get_date_with_gmt($p['date']) : null;
            if (empty($d)) { return self::err('cfai_bad_date', 'date の形式が違います（例：2026-11-05T07:00:00 または 2026-11-05 07:00）。', 400); }
            $data['post_date'] = $d[0];
            $data['post_date_gmt'] = $d[1];
            $data['edit_date'] = true;
            if (strtotime($d[1] . ' UTC') > time()) { $data['post_status'] = 'future'; }
        }

        if ($term_ids !== null) {
            $r = wp_set_object_terms($post->ID, $term_ids, self::TOPIC_TAX);
            if (is_wp_error($r)) { return self::err('cfai_terms_failed', 'トピックを設定できません：' . $r->get_error_message(), 400); }
        }
        $r = wp_update_post(wp_slash($data), true);
        if (is_wp_error($r)) { return self::err('cfai_publish_failed', '公開できませんでした：' . $r->get_error_message(), 400); }
        clean_post_cache($post->ID);
        $s = self::summary($post->ID);
        return array(
            'id' => $s['id'], 'status' => $s['status'], 'link' => $s['link'], 'slug' => $s['slug'], 'topics' => $s['topics'],
            'date' => get_post_time('c', true, $post->ID), 'edit_link' => $s['edit_link'],
            'message' => $s['status'] === 'future' ? '予約公開にしました。' : '公開しました。',
        );
    }

    public static function unpublish_article(WP_REST_Request $req) {
        $post = self::load_post($req['id']);
        if (is_wp_error($post)) { return $post; }
        $r = wp_update_post(array('ID' => $post->ID, 'post_status' => 'draft'), true);
        if (is_wp_error($r)) { return self::err('cfai_unpublish_failed', '下書きに戻せませんでした：' . $r->get_error_message(), 400); }
        clean_post_cache($post->ID);
        $s = self::summary($post->ID);
        return array('id' => $s['id'], 'status' => $s['status'], 'link' => $s['link'], 'preview_link' => $s['preview_link'], 'edit_link' => $s['edit_link'], 'message' => '下書きに戻しました。');
    }
}
add_action('rest_api_init', array('Cutlassfish_Article_Import_API', 'routes'));
