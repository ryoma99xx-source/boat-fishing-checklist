<?php
/**
 * Plugin Name: New Article Card（トップの新着記事カード）
 * Description: サイトのトップ（流れる帯の下、釣果速報の上）に、新着記事を大きなカードで出します。「設定 → 新着記事カード」で記事を指定するとその記事を、指定しなければいちばん新しい記事（投稿・記事）を出します。釣果速報は対象外です。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

const CFNA_OPT = 'cfna_pin';                     // 指定した記事の ID（0 = 指定なし → 最新）
const CFNA_TYPES = array('post', 'tachiuo_post'); // 出す対象（釣果速報 tbt_catch・動画は出さない）

/** 出す記事：指定があり、公開中ならそれ。なければ最新の1本 */
function cfna_pick() {
    $id = (int) get_option(CFNA_OPT, 0);
    if ($id) {
        $p = get_post($id);
        if ($p && $p->post_status === 'publish' && in_array($p->post_type, CFNA_TYPES, true)) { return $p; }
    }
    $l = get_posts(array('post_type' => CFNA_TYPES, 'post_status' => 'publish', 'numberposts' => 1, 'orderby' => 'date', 'order' => 'DESC', 'suppress_filters' => false));
    return $l ? $l[0] : null;
}

/** 記事のトピック名（英語の表記があればそれ） */
function cfna_label($p) {
    foreach (array('topic', 'category', 'tachiuo_cat') as $tax) {
        if (!taxonomy_exists($tax)) { continue; }
        $t = get_the_terms($p, $tax);
        if ($t && !is_wp_error($t)) { return strtoupper($t[0]->slug === 'resources' ? 'RESOURCES' : $t[0]->name); }
    }
    return '';
}

add_action('wp_enqueue_scripts', function () {
    if (!is_front_page()) { return; }
    $p = cfna_pick();
    if (!$p) { return; }
    $ex = has_excerpt($p) ? get_the_excerpt($p) : wp_trim_words(wp_strip_all_tags($p->post_content), 60, '…');
    $data = array(
        'url'   => get_permalink($p),
        'title' => get_the_title($p),
        'img'   => get_the_post_thumbnail_url($p, 'large') ?: '',
        'label' => cfna_label($p),
        'date'  => get_the_date('n月j日', $p),
        'ex'    => mb_strimwidth(wp_strip_all_tags($ex), 0, 150, '…'),
        'pinned'=> (int) get_option(CFNA_OPT, 0) === $p->ID,
    );
    wp_register_script('cfna', '', array(), '1.0.0', true);
    wp_enqueue_script('cfna');
    wp_add_inline_script('cfna', 'window.CFNA=' . wp_json_encode($data) . ';' . cfna_js());
    wp_register_style('cfna', false, array(), '1.0.0');
    wp_enqueue_style('cfna');
    wp_add_inline_style('cfna', cfna_css());
});

function cfna_js() {
    return <<<'JS'
(()=>{const d=window.CFNA;if(!d||!d.url)return;
const esc=s=>String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const html=`<section class="section cfna-sec"><div class="wrap"><a class="cfna-card" href="${esc(d.url)}">
 ${d.img?`<span class="cfna-img"><img src="${esc(d.img)}" alt="" loading="eager" decoding="async"></span>`:''}
 <span class="cfna-text"><span class="cfna-label en"><b>NEW</b>新着記事${d.label?` ／ ${esc(d.label)}`:''}${d.date?` ／ ${esc(d.date)}`:''}</span>
 <span class="cfna-title">${esc(d.title)}</span>${d.ex?`<span class="cfna-ex">${esc(d.ex)}</span>`:''}
 <span class="tool-cta-btn en cfna-btn">記事を読む →</span></span></a></div></section>`;
const run=()=>{if(document.querySelector('.cfna-sec'))return;
  const cc=document.querySelector('.catch-card'),sec=cc&&cc.closest('section');
  if(sec){sec.insertAdjacentHTML('beforebegin',html);return}
  const flow=document.querySelector('.hero-flow .ticker');if(flow){flow.insertAdjacentHTML('afterend',html);return}
  const main=document.querySelector('main')||document.body;main.insertAdjacentHTML('afterbegin',html)};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run()})();
JS;
}

function cfna_css() {
    return <<<'CSS'
.cfna-sec{padding-bottom:0!important}
.cfna-card{display:grid;grid-template-columns:minmax(0,1fr);gap:0;overflow:hidden;border:2px solid var(--accent,#41c9c6);border-radius:18px;
  background:linear-gradient(160deg,rgba(65,201,198,.16),rgba(6,8,15,.92) 55%);color:#fff;text-decoration:none;
  box-shadow:0 0 0 6px rgba(65,201,198,.08),0 18px 44px rgba(4,18,26,.55);transition:transform .3s,box-shadow .3s}
.cfna-card:hover{transform:translateY(-4px);box-shadow:0 0 0 6px rgba(65,201,198,.16),0 22px 50px rgba(4,18,26,.6)}
.cfna-img{display:block;aspect-ratio:16/9;overflow:hidden;background:#0b1422}
.cfna-img img{display:block;width:100%;height:100%;object-fit:cover;object-position:center}
.cfna-text{display:flex;flex-direction:column;gap:10px;padding:22px 22px 24px}
.cfna-label{font-size:12px;letter-spacing:.14em;color:var(--accent,#41c9c6)}
.cfna-label b{display:inline-block;margin-right:10px;padding:2px 10px;border-radius:4px;background:#e5577f;color:#fff;letter-spacing:.16em;animation:cfnaPulse 2.4s ease-in-out infinite}
@keyframes cfnaPulse{0%,100%{box-shadow:0 0 0 0 rgba(229,87,127,.55)}50%{box-shadow:0 0 0 7px rgba(229,87,127,0)}}
.cfna-title{display:block;font-size:clamp(20px,4.6vw,30px);font-weight:700;line-height:1.35;color:#fff}
.cfna-ex{display:block;font-size:14px;line-height:1.7;color:var(--silver,#c5d3e8)}
.cfna-btn{align-self:flex-start;margin-top:4px;background:var(--accent,#41c9c6)!important;color:#04121a!important;font-weight:700}
@media(min-width:820px){.cfna-card{grid-template-columns:minmax(0,1.1fr) minmax(0,1fr)}.cfna-img{aspect-ratio:auto;height:100%;max-height:420px}.cfna-text{justify-content:center;padding:30px}}
@media(prefers-reduced-motion:reduce){.cfna-label b{animation:none}}
CSS;
}

/* ---------- 設定：設定 → 新着記事カード ---------- */
add_action('admin_init', function () {
    register_setting('cfna', CFNA_OPT, array('type' => 'integer', 'sanitize_callback' => 'absint', 'default' => 0));
});
add_action('admin_menu', function () {
    add_options_page('新着記事カード', '新着記事カード', 'edit_others_posts', 'cfna', function () {
        $pin = (int) get_option(CFNA_OPT, 0);
        $list = get_posts(array('post_type' => CFNA_TYPES, 'post_status' => 'publish', 'numberposts' => 80, 'orderby' => 'date', 'order' => 'DESC'));
        $cur = cfna_pick();
        echo '<div class="wrap"><h1>新着記事カード</h1>';
        echo '<p>サイトのトップ（流れる帯の下、釣果速報の上）に出す記事を選びます。「指定しない」にすると、いちばん新しい記事が自動で出ます。</p>';
        echo '<p>いま出ている記事：<strong>' . ($cur ? esc_html(get_the_title($cur)) : '（なし）') . '</strong>' . ($cur && $cur->ID === $pin ? '（指定）' : '（最新を自動）') . '</p>';
        echo '<form method="post" action="options.php">';
        settings_fields('cfna');
        echo '<select name="' . esc_attr(CFNA_OPT) . '" style="max-width:100%"><option value="0"' . selected($pin, 0, false) . '>指定しない（最新の記事を自動で出す）</option>';
        foreach ($list as $p) {
            echo '<option value="' . (int) $p->ID . '"' . selected($pin, $p->ID, false) . '>' . esc_html(get_the_date('Y-m-d', $p) . '　' . get_the_title($p)) . '</option>';
        }
        echo '</select>';
        submit_button('保存');
        echo '</form></div>';
    });
});
add_filter('plugin_action_links_' . plugin_basename(__FILE__), function ($l) {
    array_unshift($l, '<a href="' . esc_url(admin_url('options-general.php?page=cfna')) . '">設定</a>');
    return $l;
});
