<?php
/**
 * Plugin Name: cutlassfish 問い合わせのロボット確認
 * Description: お問い合わせフォーム（/contact/ の tbt_contact）に、スパム対策を3つ付けます。①見えないわな（ボットだけが入力する欄）②送信までの時間（開いてすぐの送信はボット）③Cloudflare Turnstile のロボット確認（「設定 → 問い合わせのロボット確認」でサイトキーとシークレットキーを入れたときだけ）。ボットと判断した送信は、メールを送らずに止めます。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 */
if (!defined('ABSPATH')) { exit; }

const CFCG_OPT = 'cfcg_turnstile';   // array('site' => サイトキー, 'secret' => シークレットキー)。管理画面でオーナーが入れる（リポジトリには書かない）

function cfcg_keys() { $o = get_option(CFCG_OPT, array()); return array(trim($o['site'] ?? ''), trim($o['secret'] ?? '')); }
function cfcg_sign($t) { return hash_hmac('sha256', 'cfcg|' . $t, wp_salt('nonce')); }

/* 送信を受ける前に確かめる（テーマの受け口より先に動くよう、init のいちばん早い順） */
add_action('init', function () {
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST' || !isset($_POST['tbt_contact_nonce'])) { return; }
    $why = '';
    if (!empty($_POST['c_url'])) { $why = 'honeypot'; }                                   // ① 見えない欄に入力がある
    $t = (int) ($_POST['c_t'] ?? 0); $sig = (string) ($_POST['c_ts'] ?? '');
    if (!$why && (!$t || !hash_equals(cfcg_sign($t), $sig))) { $why = 'no-js'; }          // ② 時刻の印が無い・偽物（ページを開かずに直接送った）
    if (!$why && time() - $t < 4) { $why = 'too-fast'; }                                  //    開いて4秒以内
    if (!$why && time() - $t > 86400) { $why = 'stale'; }
    list($site, $secret) = cfcg_keys();
    if (!$why && $site && $secret) {                                                      // ③ Turnstile
        $tok = sanitize_text_field(wp_unslash($_POST['cf-turnstile-response'] ?? ''));
        $r = $tok ? wp_remote_post('https://challenges.cloudflare.com/turnstile/v0/siteverify', array('timeout' => 10, 'body' => array('secret' => $secret, 'response' => $tok, 'remoteip' => $_SERVER['REMOTE_ADDR'] ?? ''))) : null;
        $ok = $r && !is_wp_error($r) && !empty(json_decode(wp_remote_retrieve_body($r), true)['success']);
        if (!$ok) { $why = 'turnstile'; }
    }
    if (!$why) { return; }
    $n = (array) get_option('cfcg_blocked', array()); $n[$why] = ($n[$why] ?? 0) + 1; update_option('cfcg_blocked', $n, false);
    if ($why === 'turnstile' || $why === 'stale') {
        wp_die('<p>ロボットではないことの確認ができませんでした。</p><p><a href="' . esc_url(home_url('/contact/')) . '">お問い合わせのページに戻って、もう一度お試しください</a>。</p>', 'お問い合わせ', array('response' => 403));
    }
    wp_safe_redirect(home_url('/contact/')); exit;   // ボットには何も知らせない
}, -1000);

/* 時刻の印は、ページを開いたときにここから取る（ページがキャッシュされても古くならないように） */
add_action('rest_api_init', function () {
    register_rest_route('cfcg/v1', '/t', array('methods' => 'GET', 'permission_callback' => '__return_true', 'callback' => function () {
        $t = time(); $r = new WP_REST_Response(array('t' => $t, 's' => cfcg_sign($t))); $r->header('Cache-Control', 'no-store'); return $r;
    }));
});

/* フォームに、見えないわな・時刻の印・Turnstile を足す（/contact/ のページだけ） */
add_action('wp_footer', function () {
    if (!is_page('contact')) { return; }
    list($site, $secret) = cfcg_keys();
    $ts = ($site && $secret) ? '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>' : '';
    ?>
<script>(function(){var f=document.querySelector('form.contact-form');if(!f)return;
var w=document.createElement('div');w.setAttribute('aria-hidden','true');w.style.cssText='position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden';
w.innerHTML='<label>URL<input type="text" name="c_url" tabindex="-1" autocomplete="off"></label>';f.appendChild(w);
var a=document.createElement('input');a.type='hidden';a.name='c_t';f.appendChild(a);var b=document.createElement('input');b.type='hidden';b.name='c_ts';f.appendChild(b);
fetch('<?php echo esc_js(rest_url('cfcg/v1/t')); ?>',{cache:'no-store',credentials:'omit'}).then(function(r){return r.json()}).then(function(d){a.value=d.t;b.value=d.s}).catch(function(){});
<?php if ($site && $secret) : ?>var c=document.createElement('div');c.className='cf-turnstile';c.setAttribute('data-sitekey','<?php echo esc_js($site); ?>');c.setAttribute('data-language','ja');c.style.margin='12px 0';
var s=f.querySelector('button[type=submit],input[type=submit]');f.insertBefore(c,s||null);<?php endif; ?>
})();</script><?php echo $ts; ?>
<?php
}, 99);

/* 設定：設定 → 問い合わせのロボット確認 */
add_action('admin_menu', function () {
    add_options_page('問い合わせのロボット確認', '問い合わせのロボット確認', 'manage_options', 'cfcg', function () {
        if (isset($_POST['cfcg_save']) && check_admin_referer('cfcg')) {
            update_option(CFCG_OPT, array('site' => sanitize_text_field(wp_unslash($_POST['site'] ?? '')), 'secret' => sanitize_text_field(wp_unslash($_POST['secret'] ?? ''))), false);
            echo '<div class="updated"><p>保存しました。</p></div>';
        }
        list($site, $secret) = cfcg_keys(); $n = (array) get_option('cfcg_blocked', array());
        echo '<div class="wrap"><h1>問い合わせのロボット確認</h1>';
        echo '<p>お問い合わせフォームには、見えないわなと送信時間の確認が、いつも付いています。下のキーを入れると、Cloudflare Turnstile のロボット確認も付きます（無料。Cloudflare のダッシュボード → Turnstile → ウィジェットを追加、ホスト名に cutlassfish.tokyo）。</p>';
        echo '<form method="post">'; wp_nonce_field('cfcg');
        echo '<table class="form-table"><tr><th>サイトキー</th><td><input type="text" name="site" class="regular-text" value="' . esc_attr($site) . '"></td></tr>';
        echo '<tr><th>シークレットキー</th><td><input type="password" name="secret" class="regular-text" value="' . esc_attr($secret) . '" autocomplete="off"><p class="description">シークレットキーはこのサイトの中にだけ保存されます。</p></td></tr></table>';
        echo '<p><button class="button button-primary" name="cfcg_save" value="1">保存</button></p></form>';
        echo '<h2>止めた送信の数</h2><p>見えないわな ' . (int) ($n['honeypot'] ?? 0) . '件・直接送信 ' . (int) ($n['no-js'] ?? 0) . '件・送信が早すぎ ' . (int) ($n['too-fast'] ?? 0) . '件・Turnstile ' . (int) ($n['turnstile'] ?? 0) . '件</p></div>';
    });
});
