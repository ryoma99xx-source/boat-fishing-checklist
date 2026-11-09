<?php
/**
 * Plugin Name: Dragon Counter Data
 * Description: ドラゴンカウンター（TOOL 05）から匿名で届いた釣果データを、管理画面（ツール → ドラゴンカウンターのデータ）で一覧・ダウンロード・削除します。データはドラゴンカウンターのサーバーの .data/trips/ にあるものを読むだけで、外には出しません。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) exit;

final class DCD_Admin {
    const SLUG = 'dragon-counter-data';
    const OPT = 'dcd_data_dir';

    public static function init() {
        add_action('admin_menu', function () {
            add_management_page('ドラゴンカウンターのデータ', 'ドラゴンカウンターのデータ', 'manage_options', self::SLUG, [__CLASS__, 'page']);
        });
        add_action('admin_post_dcd_delete', [__CLASS__, 'delete']);
        add_action('admin_post_dcd_dir', [__CLASS__, 'save_dir']);
        add_action('admin_post_dcd_download', [__CLASS__, 'download']);
    }

    /** データの置き場所を探す（WordPress と同じサーバーアカウントの中） */
    public static function dir() {
        $saved = get_option(self::OPT, '');
        if ($saved && self::is_dc_dir($saved)) return $saved;
        $roots = array_unique(array_filter([dirname(ABSPATH), dirname(ABSPATH, 2), dirname(ABSPATH, 3), getenv('HOME') ?: '']));
        foreach ($roots as $r) {
            foreach (['/*/.data/trips', '/*/*/.data/trips', '/*/*/*/.data/trips'] as $pat) {
                foreach ((array)glob($r . $pat, GLOB_ONLYDIR | GLOB_NOSORT) as $d) {
                    if (stripos($d, 'dragon') !== false && self::is_dc_dir($d)) { update_option(self::OPT, $d, false); return $d; }
                }
            }
        }
        return '';
    }
    private static function is_dc_dir($d) {
        if (!is_dir($d) || !is_readable($d)) return false;
        $f = glob(rtrim($d, '/') . '/*.json');
        if (!$f) return is_file(dirname(dirname($d)) . '/collect.php');
        $j = json_decode((string)@file_get_contents($f[0]), true);
        return is_array($j) && ($j['app'] ?? '') === 'dragon-counter';
    }

    /** 1釣行を一覧用にまとめる */
    private static function row($file) {
        $j = json_decode((string)@file_get_contents($file), true);
        if (!is_array($j)) return null;
        $ev = (array)($j['events'] ?? []);
        $n = ['catch' => 0, 'bite' => 0, 'lost' => 0, 'gedo' => 0]; $dr = 0;
        foreach ($ev as $e) { $k = $e['kind'] ?? ''; if (isset($n[$k])) $n[$k]++; if ($k === 'catch' && !empty($e['dragon'])) $dr++; }
        $tk = [];
        foreach ((array)($j['tackle'] ?? []) as $t) $tk[] = trim(($t['rod'] ?? '') . ' × ' . ($t['reel'] ?? '') . (!empty($t['line']) ? '（' . $t['line'] . '）' : ''));
        $tz = new DateTimeZone('Asia/Tokyo');
        $hm = function ($ms) use ($tz) { if (!$ms) return ''; $d = new DateTime('@' . intdiv((int)$ms, 1000)); $d->setTimezone($tz); return $d->format('H:i'); };
        $rec = '';
        if (!empty($j['received'])) { try { $d = new DateTime($j['received']); $d->setTimezone($tz); $rec = $d->format('Y-m-d H:i'); } catch (Exception $e) {} }
        return [
            'uid' => $j['uid'] ?? basename($file, '.json'), 'received' => $rec, 'date' => $j['date'] ?? '',
            'spot' => $j['spot']['name'] ?? '', 'boat' => $j['boat'] ?? '', 'seat' => (($j['side'] ?? '') === 'L' ? '左舷' : (($j['side'] ?? '') === 'R' ? '右舷' : '')) . ($j['seat'] ?? ''),
            'time' => $hm($j['start'] ?? 0) . '〜' . $hm($j['end'] ?? 0), 'tide' => $j['tide'] ?? '', 'mode' => ($j['mode'] ?? '') === 'detail' ? '詳細' : 'シンプル',
            'catch' => $n['catch'], 'dragon' => $dr, 'bite' => $n['bite'], 'lost' => $n['lost'], 'gedo' => $n['gedo'],
            'wx' => !empty($j['wx']) ? trim(($j['wx']['weather'] ?? '') . ' 水温' . ($j['wx']['sst'] ?? '?') . '℃') : '',
            'tackle' => implode(' / ', $tk), 'points' => count((array)($j['points'] ?? [])),
        ];
    }
    private static function rows($dir) {
        $out = [];
        foreach ((array)glob($dir . '/*.json') as $f) { $r = self::row($f); if ($r) $out[] = $r; }
        usort($out, function ($a, $b) { return strcmp($b['received'], $a['received']); });
        return $out;
    }

    public static function page() {
        if (!current_user_can('manage_options')) return;
        $dir = self::dir();
        $notice = get_transient('dcd_notice_' . get_current_user_id()); if ($notice) delete_transient('dcd_notice_' . get_current_user_id());
        echo '<div class="wrap"><h1>ドラゴンカウンターのデータ</h1>';
        if ($notice) echo '<div class="notice notice-info is-dismissible"><p>' . esc_html($notice) . '</p></div>';
        echo '<p class="description">ドラゴンカウンターで「沖上がり」まで記録された釣行が、匿名（名前・メモなし）で届いたものです。アプリで釣行を消しても、ここには残ります。テストの釣行などは「消す」で取り除けます。</p>';
        if (!$dir) {
            echo '<div class="notice notice-warning"><p>データの置き場所が見つかりませんでした。ドラゴンカウンターの公開フォルダの中の <code>.data/trips</code> の場所（サーバー上のフルパス）を入れてください。WordPress と別のサーバーアカウントにある場合は読めません。</p></div>';
            self::dir_form('');
            echo '</div>'; return;
        }
        $rows = self::rows($dir);
        $sum = ['catch' => 0, 'dragon' => 0]; foreach ($rows as $r) { $sum['catch'] += $r['catch']; $sum['dragon'] += $r['dragon']; }
        echo '<p>届いた釣行：<strong>' . count($rows) . '件</strong>（タチウオ ' . (int)$sum['catch'] . '本・ドラゴン ' . (int)$sum['dragon'] . '本）';
        echo '　<a class="button" href="' . esc_url(wp_nonce_url(admin_url('admin-post.php?action=dcd_download&fmt=csv'), 'dcd_download')) . '">CSVでダウンロード</a> ';
        echo '<a class="button" href="' . esc_url(wp_nonce_url(admin_url('admin-post.php?action=dcd_download&fmt=json'), 'dcd_download')) . '">JSON（全項目）でダウンロード</a></p>';
        echo '<div style="overflow-x:auto"><table class="widefat striped" style="min-width:1100px"><thead><tr>';
        foreach (['届いた日時', '釣行日', '釣り場', '船・席', '時間', '潮', '記録', '釣れた', 'ドラゴン', 'アタリ', 'バラシ', '外道', '天気', 'タックル', '場所記録', ''] as $h) echo '<th>' . esc_html($h) . '</th>';
        echo '</tr></thead><tbody>';
        foreach ($rows as $r) {
            echo '<tr><td>' . esc_html($r['received']) . '</td><td>' . esc_html($r['date']) . '</td><td>' . esc_html($r['spot']) . '</td><td>' . esc_html($r['boat'] . ' ' . $r['seat']) . '</td><td>' . esc_html($r['time']) . '</td><td>' . esc_html($r['tide']) . '</td><td>' . esc_html($r['mode']) . '</td>';
            echo '<td><strong>' . (int)$r['catch'] . '</strong></td><td>' . (int)$r['dragon'] . '</td><td>' . (int)$r['bite'] . '</td><td>' . (int)$r['lost'] . '</td><td>' . (int)$r['gedo'] . '</td><td>' . esc_html($r['wx']) . '</td><td style="max-width:260px">' . esc_html($r['tackle']) . '</td><td>' . ($r['points'] ? (int)$r['points'] . '点' : '') . '</td>';
            echo '<td><form method="post" action="' . esc_url(admin_url('admin-post.php')) . '" onsubmit="return confirm(\'この釣行のデータを消しますか？（元に戻せません）\')">';
            wp_nonce_field('dcd_delete'); echo '<input type="hidden" name="action" value="dcd_delete"><input type="hidden" name="uid" value="' . esc_attr($r['uid']) . '"><button class="button button-small">消す</button></form></td></tr>';
        }
        if (!$rows) echo '<tr><td colspan="16">まだ届いていません。</td></tr>';
        echo '</tbody></table></div>';
        echo '<p class="description">置き場所：<code>' . esc_html($dir) . '</code></p>';
        self::dir_form($dir);
        echo '</div>';
    }
    private static function dir_form($dir) {
        echo '<form method="post" action="' . esc_url(admin_url('admin-post.php')) . '" style="margin-top:8px">';
        wp_nonce_field('dcd_dir');
        echo '<input type="hidden" name="action" value="dcd_dir"><label>置き場所を指定 <input type="text" name="dir" class="regular-text" value="' . esc_attr($dir) . '" placeholder="/home/…/dragon-counter.cutlassfish.tokyo/.data/trips"></label> <button class="button">保存</button></form>';
    }
    private static function back($msg) { set_transient('dcd_notice_' . get_current_user_id(), $msg, 120); wp_safe_redirect(admin_url('tools.php?page=' . self::SLUG)); exit; }

    public static function save_dir() {
        if (!current_user_can('manage_options')) wp_die('権限がありません。');
        check_admin_referer('dcd_dir');
        $d = rtrim(sanitize_text_field(wp_unslash($_POST['dir'] ?? '')), '/');
        if ($d === '') { delete_option(self::OPT); self::back('置き場所を自動で探すようにしました。'); }
        if (!self::is_dc_dir($d)) self::back('その場所はドラゴンカウンターのデータとして読めませんでした。');
        update_option(self::OPT, $d, false); self::back('置き場所を保存しました。');
    }
    public static function delete() {
        if (!current_user_can('manage_options')) wp_die('権限がありません。');
        check_admin_referer('dcd_delete');
        $uid = sanitize_text_field(wp_unslash($_POST['uid'] ?? ''));
        $dir = self::dir();
        if (!$dir || !preg_match('/^[a-z0-9]{8,40}$/', $uid)) self::back('消せませんでした。');
        $f = $dir . '/' . $uid . '.json';
        self::back(is_file($f) && @unlink($f) ? '1件消しました。' : '消せませんでした（書き込みの権限が無い可能性があります）。');
    }
    public static function download() {
        if (!current_user_can('manage_options')) wp_die('権限がありません。');
        check_admin_referer('dcd_download');
        $dir = self::dir(); if (!$dir) wp_die('データの置き場所が見つかりません。');
        $fmt = ($_GET['fmt'] ?? '') === 'json' ? 'json' : 'csv';
        nocache_headers();
        $name = 'dragon-counter-data-' . wp_date('Ymd-Hi') . '.' . $fmt;
        header('Content-Disposition: attachment; filename="' . $name . '"');
        if ($fmt === 'json') {
            header('Content-Type: application/json; charset=utf-8');
            $all = []; foreach ((array)glob($dir . '/*.json') as $f) { $j = json_decode((string)@file_get_contents($f), true); if (is_array($j)) $all[] = $j; }
            echo wp_json_encode($all, JSON_UNESCAPED_UNICODE); exit;
        }
        header('Content-Type: text/csv; charset=utf-8');
        $o = fopen('php://output', 'w'); fwrite($o, "\xEF\xBB\xBF");
        $rows = self::rows($dir);
        fputcsv($o, ['届いた日時', '釣行日', '釣り場', '船', '席', '時間', '潮', '記録', '釣れた', 'ドラゴン', 'アタリ', 'バラシ', '外道', '天気', 'タックル', '場所記録', 'ID']);
        foreach ($rows as $r) fputcsv($o, [$r['received'], $r['date'], $r['spot'], $r['boat'], $r['seat'], $r['time'], $r['tide'], $r['mode'], $r['catch'], $r['dragon'], $r['bite'], $r['lost'], $r['gedo'], $r['wx'], $r['tackle'], $r['points'], $r['uid']]);
        exit;
    }
}
DCD_Admin::init();
