<?php
/**
 * Plugin Name: SEO Basics（説明文・共有画像・公開日・書いた人）
 * Description: テーマが出していない分だけを足します。①一覧ページ（カテゴリー・トピックなど）の説明文（meta description / og:description）、②記事以外のページのSNS共有画像（og:image）、③記事の公開日・更新日（検索エンジン向けの情報と、記事の下の表示）、④記事の下の「書いた人」。テーマがすでに出しているものは重ねて出しません。
 * Version: 1.2.2
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

/* サイトマップ（/wp-sitemap.xml）の整理。オーナー指示 2026-11-24
   - 投稿者（ユーザー）の一覧を出さない（ログイン名の手がかりになるため）
   - 「未分類」カテゴリーを出さない（そのページは表示されず 404 のため） */
add_filter('wp_sitemaps_add_provider', function ($provider, $name) { return $name === 'users' ? false : $provider; }, 10, 2);
add_filter('wp_sitemaps_taxonomies_query_args', function ($args, $taxonomy) {
    if ($taxonomy === 'category') { $args['exclude'] = array_merge((array) ($args['exclude'] ?? array()), array((int) get_option('default_category'))); }
    return $args;
}, 10, 2);

// 5f2544f5

/* ---------- /llms.txt：AI 向けの案内（サイトの説明と主なページの一覧）。オーナー指示 2026-11-26 ----------
   記事はトピックごとに新しい順（公開日つき）。記事・魚種が増えると自動で入る。ツールの一覧だけはここに書いてある。 */
function cfsb_llms_txt() {
    $o   = array();
    $o[] = '# 東京湾の魚・釣り（3rd-Penguin Fishing Lab.）';
    $o[] = '';
    $o[] = '> 東京湾の船釣り（タチウオのテンヤ釣りを中心に、マダイのタイラバ、アオリイカのティップラン、サワラ、トラフグなど）の釣行記・釣り方・考察・レシピと、無料の釣りツール（釣果記録アプリ、テンヤ・エギ・タイラバのカタログ、東京湾の潮と流れ）を公開している個人サイトです。釣行記は実際の釣行の記録で、考察は仮説として書いています。';
    $o[] = '';
    $o[] = '## 無料ツールとカタログ';
    foreach (array(
        array('ドラゴンカウンター', 'https://dragon-counter.cutlassfish.tokyo/', 'タチウオの釣果を時間の経過と共に、テンヤ・潮・船の向きと一緒に記録する無料ツール'),
        array('ティップランカウンター', 'https://dragon-counter.cutlassfish.tokyo/tipran/', 'ティップランのアオリイカの釣果を時間と一緒に、エギ・シンカー・潮・船の向きと一緒に記録する無料ツール'),
        array('タイラバカウンター', 'https://dragon-counter.cutlassfish.tokyo/tairaba/', 'マダイの釣果を時間と一緒に、タイラバ（ヘッド・ネクタイ・針・スカート）・潮・流れと一緒に記録する無料ツール'),
        array('船タチウオテンヤ カタログ', 'https://dragon-counter.cutlassfish.tokyo/tenya-catalog/', 'メーカー・製品ごとに全部の色を写真で一覧'),
        array('ティップラン用エギ・シンカー カタログ', 'https://dragon-counter.cutlassfish.tokyo/egi-catalog/', 'メーカー・製品ごとに全部の色を写真で一覧'),
        array('タイラバ ヘッド・スカート カタログ', 'https://dragon-counter.cutlassfish.tokyo/tairaba-catalog/', '重さ・素材（タングステン）・色を写真で一覧'),
        array('タイラバ ネクタイ カタログ', 'https://dragon-counter.cutlassfish.tokyo/tairaba-catalog/ties/', 'メーカー・製品ごとに形と全部の色を写真で一覧'),
        array('東京湾の潮と流れ', 'https://tide-current-map.cutlassfish.tokyo/', '地図で場所ごとの流れと1日の潮位を見る無料ツール。自作の潮汐モデルを海上保安庁の潮流推算と重ねて比較できる（自作モデルは潮汐のみの参考計算）'),
        array('テンヤシミュレーター（テンヤ海中挙動シミュレーター）', 'https://tenya-simulator.cutlassfish.tokyo/', '叩き方や海況を設定して、海中でテンヤがどう動くかを見比べる無料ツール（ダイワ型とシマノ型の比較）'),
        array('リール糸管理ツール', 'https://reel-line-manager.cutlassfish.tokyo/', 'リールの糸種・号数・巻き量・巻き替え時期をまとめて記録する無料ツール'),
        array("釣り持ち物チェックツール（Don't forget anything）", 'https://dont-forget-anything.cutlassfish.tokyo/', '釣り方ごとの持ち物をチェックして、準備の抜け漏れをなくす無料ツール'),
        array('ツールの一覧', home_url('/topic/tools/'), 'このサイトのツールをまとめたページ'),
    ) as $t) {
        $o[] = '- [' . $t[0] . '](' . $t[1] . '): ' . $t[2];
    }

    // 記事：トピック（tachiuo_cat）ごと。1本の記事は1か所だけに出す（下の順で最初に当てはまるトピック）
    $q = get_posts(array('post_type' => 'tachiuo_post', 'post_status' => 'publish', 'numberposts' => 300, 'orderby' => 'date', 'order' => 'DESC'));
    $pick  = array('shopping', 'recipe', 'tools', 'tokyobay', 'fish', 'fishing', 'resources');   // 割り当ての優先順（細かいトピックを先に）
    $show  = array('fishing', 'fish', 'tokyobay', 'recipe', 'resources', 'shopping', 'tools');   // 並べる順
    $group = array();
    foreach ($q as $p) {
        $slugs = wp_get_post_terms($p->ID, 'tachiuo_cat', array('fields' => 'slugs'));
        $slugs = is_wp_error($slugs) ? array() : $slugs;
        $key   = '';
        foreach ($pick as $s) {
            if (in_array($s, $slugs, true)) { $key = $s; break; }
        }
        if ($key === '' && $slugs) $key = $slugs[0];
        $ex = trim(preg_replace('/\s+/u', ' ', wp_strip_all_tags($p->post_excerpt)));
        if (mb_strlen($ex) > 120) $ex = mb_substr($ex, 0, 120) . '…';
        $title = str_replace(array('[', ']'), array('［', '］'), wp_strip_all_tags(get_the_title($p)));
        $group[$key][] = '- [' . $title . '](' . get_permalink($p) . ')（' . get_the_date('Y-m-d', $p) . '）' . ($ex !== '' ? ': ' . $ex : '');
    }
    $order = array_merge($show, array_diff(array_keys($group), $show));
    foreach ($order as $slug) {
        if (empty($group[$slug])) continue;
        $term = $slug !== '' ? get_term_by('slug', $slug, 'tachiuo_cat') : null;
        $o[]  = '';
        $o[]  = '## 記事：' . ($term && !is_wp_error($term) ? $term->name : 'そのほか');
        foreach ($group[$slug] as $line) $o[] = $line;
    }

    // 魚ごとの記事一覧
    $sp = get_terms(array('taxonomy' => 'species', 'hide_empty' => true));
    if ($sp && !is_wp_error($sp)) {
        $o[] = '';
        $o[] = '## 魚ごとの記事一覧';
        foreach ($sp as $t) {
            $l = get_term_link($t);
            if (!is_wp_error($l)) $o[] = '- [' . $t->name . '](' . $l . ')';
        }
    }
    $o[] = '';
    $o[] = '## そのほか';
    $o[] = '- [すべての記事の一覧](' . home_url('/articles/') . ')';
    $o[] = '- [サイトマップ](' . home_url('/wp-sitemap.xml') . ')';
    return implode("\n", $o) . "\n";
}
add_action('template_redirect', function () {
    $path = parse_url($_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH);
    if ($path !== '/llms.txt') return;
    $body = cfsb_llms_txt();
    status_header(200);
    header_remove('Expires');
    header_remove('Pragma');
    header('Content-Type: text/plain; charset=UTF-8');
    header('Cache-Control: public, max-age=3600');
    echo $body;
    exit;
}, 0);
