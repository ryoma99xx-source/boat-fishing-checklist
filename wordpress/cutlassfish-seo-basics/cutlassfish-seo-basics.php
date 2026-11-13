<?php
/**
 * Plugin Name: SEO Basics（説明文・共有画像・公開日・書いた人）
 * Description: テーマが出していない分だけを足します。①一覧ページ（カテゴリー・トピックなど）の説明文（meta description / og:description）、②記事以外のページのSNS共有画像（og:image）、③記事の公開日・更新日（検索エンジン向けの情報と、記事の下の表示）、④記事の下の「書いた人」。テーマがすでに出しているものは重ねて出しません。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

const CFSB_NAME  = '3rd-Penguin Fishing Lab.';         // 書いた人・運営者
const CFSB_TYPES = array('post', 'tachiuo_post');     // 記事として扱う投稿タイプ

/** 一覧ページの説明文：カテゴリー等の「説明」があればそれ。なければ名前と新しい記事3本から作る */
function cfsb_archive_desc() {
    if (!(is_category() || is_tag() || is_tax())) { return ''; }
    $t = get_queried_object();
    if (!$t || empty($t->name)) { return ''; }
    $d = trim(wp_strip_all_tags(term_description($t)));
    if ($d !== '') { return mb_strimwidth(preg_replace('/\s+/u', ' ', $d), 0, 160, '…'); }
    $q = get_posts(array('post_type' => CFSB_TYPES, 'numberposts' => 3, 'tax_query' => array(array('taxonomy' => $t->taxonomy, 'terms' => $t->term_id)), 'suppress_filters' => false));
    $titles = array_map(function ($p) { return '「' . get_the_title($p) . '」'; }, $q);
    $s = '東京湾の魚・釣りの「' . $t->name . '」の記事一覧です。';
    if ($titles) { $s .= implode('', $titles) . 'などを載せています。'; }
    return mb_strimwidth($s, 0, 160, '…');
}

/** 記事以外・アイキャッチの無い記事のときの共有画像 */
function cfsb_default_image() {
    return plugins_url('og-default.jpg', __FILE__);
}

/* テーマの <head> 出力を見て、無いものだけ足す */
add_action('wp_head', function () { ob_start(); }, 0);
add_action('wp_head', function () {
    $head = ob_get_clean();
    $add  = '';
    $has  = function ($re) use ($head) { return (bool) preg_match($re, $head); };

    if (!$has('/<meta[^>]+name=["\']description["\']/i')) {
        $d = cfsb_archive_desc();
        if ($d !== '') {
            $add .= '<meta name="description" content="' . esc_attr($d) . '">' . "\n";
            if (!$has('/<meta[^>]+property=["\']og:description["\']/i')) {
                $add .= '<meta property="og:description" content="' . esc_attr($d) . '">' . "\n";
            }
        }
    }
    if (!$has('/<meta[^>]+property=["\']og:image["\']/i')) {
        $add .= '<meta property="og:image" content="' . esc_url(cfsb_default_image()) . '">' . "\n";
        $add .= '<meta property="og:image:width" content="1200">' . "\n" . '<meta property="og:image:height" content="628">' . "\n";
    }

    if (is_singular(CFSB_TYPES)) {
        $p   = get_queried_object();
        $pub = get_post_time('c', false, $p);
        $mod = get_post_modified_time('c', false, $p);
        if (!$has('/article:published_time/i')) {
            $add .= '<meta property="article:published_time" content="' . esc_attr($pub) . '">' . "\n";
            $add .= '<meta property="article:modified_time" content="' . esc_attr($mod) . '">' . "\n";
        }
        if (!$has('/application\/ld\+json/i')) {
            $img = get_the_post_thumbnail_url($p, 'large');
            $ld  = array(
                '@context'         => 'https://schema.org',
                '@type'            => 'BlogPosting',
                'headline'         => wp_strip_all_tags(get_the_title($p)),
                'datePublished'    => $pub,
                'dateModified'     => $mod,
                'author'           => array('@type' => 'Organization', 'name' => CFSB_NAME, 'url' => home_url('/')),
                'publisher'        => array('@type' => 'Organization', 'name' => CFSB_NAME, 'url' => home_url('/')),
                'mainEntityOfPage' => get_permalink($p),
                'image'            => $img ? $img : cfsb_default_image(),
            );
            $ex = has_excerpt($p) ? wp_strip_all_tags(get_the_excerpt($p)) : '';
            if ($ex !== '') { $ld['description'] = mb_strimwidth($ex, 0, 160, '…'); }
            $add .= '<script type="application/ld+json">' . wp_json_encode($ld, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . '</script>' . "\n";
        }
    }
    echo $head . $add; // phpcs:ignore WordPress.Security.EscapeOutput
}, PHP_INT_MAX);

/* 記事の下：公開日・更新日と書いた人 */
add_filter('the_content', function ($html) {
    if (!is_singular(CFSB_TYPES) || !in_the_loop() || !is_main_query() || get_the_ID() !== get_queried_object_id()) { return $html; }
    $p   = get_post();
    $pub = get_the_date('Y.m.d', $p);
    $mod = get_the_modified_date('Y.m.d', $p);
    $dates = '公開 <time datetime="' . esc_attr(get_post_time('c', false, $p)) . '">' . esc_html($pub) . '</time>';
    if ($mod !== $pub) {
        $dates .= '　更新 <time datetime="' . esc_attr(get_post_modified_time('c', false, $p)) . '">' . esc_html($mod) . '</time>';
    }
    $box = '<aside class="cfsb-byline"><span class="cfsb-who">書いた人：<a href="' . esc_url(home_url('/')) . '">' . esc_html(CFSB_NAME) . '</a>（運営者）</span><span class="cfsb-dates">' . $dates . '</span></aside>';
    return $html . $box;
}, 20);

add_action('wp_enqueue_scripts', function () {
    if (!is_singular(CFSB_TYPES)) { return; }
    wp_register_style('cfsb', false, array(), '1.0.0');
    wp_enqueue_style('cfsb');
    wp_add_inline_style('cfsb', '.cfsb-byline{display:flex;flex-wrap:wrap;gap:4px 16px;justify-content:space-between;margin:32px 0 8px;padding:12px 0;border-top:1px solid rgba(128,128,128,.35);font-size:13px;line-height:1.6;opacity:.85}.cfsb-byline a{color:inherit;text-decoration:underline}');
});
