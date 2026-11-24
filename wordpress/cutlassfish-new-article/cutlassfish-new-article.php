<?php
/**
 * Plugin Name: New Article Card（トップの新着記事カード）
 * Description: サイトのトップ（流れる帯の下、釣果速報の上）に、新着記事を大きなカードで出します。最新の記事5本を、横にスワイプするか5秒おきに順に出します。「設定 → 新着記事カード」で記事を指定すると、その記事を先頭にします。釣果速報は対象外です。
 * Version: 1.2.0
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

const CFNA_OPT = 'cfna_pin';                     // 指定した記事の ID（0 = 指定なし → 最新）
const CFNA_TYPES = array('post', 'tachiuo_post'); // 出す対象（釣果速報 tbt_catch・動画は出さない）

const CFNA_N = 5;   // カードに順に出す記事の数（オーナー指示 2026-11-24）

/** 出す記事：指定した記事（公開中なら）を先頭に、最新の記事から合わせて CFNA_N 本 */
function cfna_list() {
    $out = array(); $pin = (int) get_option(CFNA_OPT, 0);
    if ($pin) { $p = get_post($pin); if ($p && $p->post_status === 'publish' && in_array($p->post_type, CFNA_TYPES, true)) { $out[] = $p; } }
    $l = get_posts(array('post_type' => CFNA_TYPES, 'post_status' => 'publish', 'numberposts' => CFNA_N + 1, 'orderby' => 'date', 'order' => 'DESC', 'suppress_filters' => false));
    foreach ($l as $p) { if (count($out) >= CFNA_N) { break; } if (!$out || $p->ID !== $out[0]->ID) { $out[] = $p; } }
    return $out;
}

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
    $list = cfna_list();
    if (!$list) { return; }
    $data = array();
    foreach ($list as $p) {
        $ex = has_excerpt($p) ? get_the_excerpt($p) : wp_trim_words(wp_strip_all_tags($p->post_content), 60, '…');
        $data[] = array(
            'url'   => get_permalink($p),
            'title' => get_the_title($p),
            'img'   => get_the_post_thumbnail_url($p, 'large') ?: '',
            'label' => cfna_label($p),
            'date'  => get_the_date('n月j日', $p),
            'ex'    => mb_strimwidth(wp_strip_all_tags($ex), 0, 150, '…'),
            'new'   => (time() - get_post_time('U', true, $p)) < 14 * 86400,   // 2週間以内なら NEW
        );
    }
    wp_register_script('cfna', '', array(), '1.0.0', true);
    wp_enqueue_script('cfna');
    wp_add_inline_script('cfna', 'window.CFNA=' . wp_json_encode($data) . ';' . cfna_js());
    wp_register_style('cfna', false, array(), '1.0.0');
    wp_enqueue_style('cfna');
    wp_add_inline_style('cfna', cfna_css());
});

function cfna_js() {
    return <<<'JS'
(()=>{const d=window.CFNA;if(!d||(Array.isArray(d)?!d.length:!d.url))return;
const esc=s=>String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

const L=Array.isArray(d)?d:[d];
const card=(x,i)=>`<div class="cfna-slide" role="group" aria-roledescription="スライド" aria-label="${i+1} / ${L.length}"><a class="cfna-card" href="${esc(x.url)}">
 ${x.img?`<span class="cfna-img"><img src="${esc(x.img)}" alt="" loading="${i?'lazy':'eager'}" decoding="async"></span>`:''}
 <span class="cfna-text"><span class="cfna-label en">${x.new?'<b>NEW</b>':''}${i?'記事':'新着記事'}${x.label?` ／ ${esc(x.label)}`:''}${x.date?` ／ ${esc(x.date)}`:''}</span>
 <span class="cfna-title">${esc(x.title)}</span>${x.ex?`<span class="cfna-ex">${esc(x.ex)}</span>`:''}
 <span class="tool-cta-btn en cfna-btn">記事を読む →</span></span></a></div>`;
const html=`<section class="section cfna-sec"><div class="wrap"><div class="cfna-head"><span class="cfna-eb en">LATEST ARTICLES</span><span class="cfna-h">最新の記事${L.length>1?` ${L.length}本`:''}</span>${L.length>1?'<span class="cfna-hint">横にスワイプ・5秒ごとに次の記事へ</span>':''}</div><div class="cfna-car" aria-roledescription="カルーセル" aria-label="新着記事"><div class="cfna-track">${L.map(card).join('')}</div>
 ${L.length>1?`<div class="cfna-dots">${L.map((x,i)=>`<button type="button" aria-label="${i+1}本目の記事" class="${i?'':'on'}"></button>`).join('')}</div>`:''}</div></div></section>`;
/* 横にスワイプ、または5秒おきに次の記事へ（触っている間・画面を見ていない間・動きを減らす設定のときは止める） */
const carousel=()=>{const car=document.querySelector('.cfna-car');if(!car||L.length<2)return;const tr=car.querySelector('.cfna-track'),dots=[...car.querySelectorAll('.cfna-dots button')];
  let i=0,hold=0;const go=n=>{i=(n+L.length)%L.length;tr.scrollTo({left:i*tr.clientWidth,behavior:'smooth'});mark()};
  const mark=()=>dots.forEach((b,k)=>b.classList.toggle('on',k===i));
  tr.addEventListener('scroll',()=>{const n=Math.round(tr.scrollLeft/Math.max(1,tr.clientWidth));if(n!==i){i=n;mark()}},{passive:true});
  dots.forEach((b,k)=>b.addEventListener('click',()=>{hold=Date.now();go(k)}));
  ['pointerdown','touchstart','wheel','focusin','mouseenter'].forEach(e=>car.addEventListener(e,()=>{hold=Date.now()},{passive:true}));
  if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  setInterval(()=>{if(document.hidden||Date.now()-hold<8000)return;go(i+1)},5000)};
const run=()=>{if(document.querySelector('.cfna-sec'))return;
  const cc=document.querySelector('.catch-card'),sec=cc&&cc.closest('section');
  if(sec)sec.insertAdjacentHTML('beforebegin',html);
  else{const flow=document.querySelector('.hero-flow .ticker');if(flow)flow.insertAdjacentHTML('afterend',html);else{const main=document.querySelector('main')||document.body;main.insertAdjacentHTML('afterbegin',html)}}
  carousel()};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run()})();
JS;
}

function cfna_css() {
    return <<<'CSS'
.cfna-sec{padding-bottom:0!important}
.cfna-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px;margin:0 8px 4px}
.cfna-eb{flex:0 0 100%;font-size:12px;letter-spacing:.18em;color:var(--accent,#41c9c6)}
.cfna-h{font-size:clamp(20px,5vw,26px);font-weight:700;color:#fff}
.cfna-hint{font-size:13px;color:var(--silver,#9cabbd)}
.cfna-track{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;-webkit-overflow-scrolling:touch;padding:8px 0 14px}
.cfna-track::-webkit-scrollbar{display:none}
.cfna-slide{flex:0 0 100%;min-width:0;scroll-snap-align:start;padding:0 8px;box-sizing:border-box;display:flex}
.cfna-slide .cfna-card{width:100%;align-content:start;grid-template-rows:auto 1fr}
.cfna-card:hover{transform:none!important}
.cfna-dots{display:flex;justify-content:center;gap:10px;margin:2px 0 0}
.cfna-dots button{width:10px;height:10px;padding:0;border:0;border-radius:999px;background:rgba(255,255,255,.3);cursor:pointer;transition:width .3s,background .3s}
.cfna-dots button.on{width:26px;background:var(--accent,#41c9c6)}
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

// 4b493f15
