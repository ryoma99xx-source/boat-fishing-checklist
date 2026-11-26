<?php
/**
 * Plugin Name: イカの記事2本を元に戻す（関連記事の枠つき）
 * Description: 有効にしたときに一度だけ動いて、自分を無効にします。2026-11-26 に Claude が記事 590（ムラサキイカの釣行記）と 602（イカの食べ比べ）へ関連記事の枠を足したとき、取り込みの仕組みが元からあった YouTube の埋め込みとブロックの印を消してしまった。取り込みの仕組みが残していた「直前の中身」（投稿メタ _cfai_prev_content_*）から元の本文に戻し、関連記事の枠だけを足し直す。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 */
if (!defined('ABSPATH')) exit;
register_activation_hook(__FILE__, function () {
    $img = wp_get_attachment_url(591);
    $box = '<div class="essay">' . "\n" . '  <span class="k">FROM 3RD PENGUIN</span>' . "\n"
        . '  <p>ムラサキイカがどんなイカなのか（正体・味・食べ方・釣れる時期と釣り方）は、こちらの記事にまとめています。</p>' . "\n"
        . '  <div class="cf-related" style="margin:18px 0 14px">' . "\n"
        . '<a href="https://cutlassfish.tokyo/article/murasakiika/" style="display:flex;gap:14px;align-items:center;margin:14px 0;padding:12px;border:2px solid #41c9c6;border-radius:14px;background:#0f1a28;color:#ffffff !important;text-decoration:none">' . "\n"
        . ($img ? '  <img src="' . esc_url($img) . '" alt="" loading="lazy" style="flex:none;width:84px;height:105px;object-fit:cover;border-radius:8px;margin:0">' . "\n" : '')
        . '  <span style="display:block;min-width:0"><span style="display:block;font-size:12px;letter-spacing:.12em;color:#41c9c6;font-weight:700">関連記事</span><span style="display:block;font-size:16px;font-weight:700;line-height:1.5;color:#ffffff">むらさきいか（ムラサキイカ）とはどんなイカ？味・食べ方から釣り方まで</span><span style="display:block;font-size:13px;color:#9fb4c6;margin-top:4px">記事を読む →</span></span>' . "\n"
        . '</a>' . "\n" . '</div>' . "\n" . '  <p class="sign">ペンギン1号@3rd Penguin Fishing Lab</p>' . "\n" . '</div>' . "\n\n";
    $out = array();
    foreach (array(590, 602) as $id) {
        $post = get_post($id);
        if (!$post) { $out[$id] = 'no post'; continue; }
        // いちばん新しい「直前の中身」で、元のブロックの印があり、今回の枠がまだ入っていないもの
        $cands = array();
        foreach (get_post_meta($id) as $k => $v) {
            if (!preg_match('/\A_cfai_prev_content_(\d+)\z/', $k, $m)) continue;
            $d = maybe_unserialize($v[0]);
            if (is_array($d) && isset($d['content']) && strpos($d['content'], '<!-- wp:embed') !== false && strpos($d['content'], 'article/murasakiika/') === false) {
                $cands[(int) $m[1]] = $d['content'];
            }
        }
        if (!$cands) { $out[$id] = 'no snapshot'; continue; }
        krsort($cands);
        $orig = reset($cands);
        if (substr_count($orig, '</article>') !== 1) { $out[$id] = 'unexpected content'; continue; }
        $new = str_replace('</article>', $box . '</article>', $orig);
        kses_remove_filters();   // 元からある iframe やブロックの印を消さない
        $r = wp_update_post(wp_slash(array('ID' => $id, 'post_content' => $new)), true);
        $out[$id] = is_wp_error($r) ? $r->get_error_message() : 'restored ' . strlen($orig) . ' -> ' . strlen($new);
        clean_post_cache($id);
    }
    update_option('cf_restore_ika_result', $out);
});
add_action('admin_init', function () {
    deactivate_plugins(plugin_basename(__FILE__));
});
