<?php
/**
 * Plugin Name: Dragon Counter Data
 * Description: ドラゴンカウンター（TOOL 05）とティップランカウンターから匿名で届いた釣果データを、管理画面（ツール → ドラゴンカウンターのデータ）でダッシュボード・一覧・ダウンロード・削除します。上のタブでアプリを切り替えます。データはサーバーの .data/trips/（ティップランは tipran/.data/trips/）にあるものを読むだけで、外には出しません。
 * Version: 1.2.1
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) exit;

final class DCD_Admin {
    const SLUG = 'dragon-counter-data';
    const OPT = 'dcd_data_dir';
    /** アプリごとの違い（データの場所・数え方・言葉） */
    const APPS = [
        'dc' => ['name' => 'ドラゴンカウンター', 'id' => 'dragon-counter', 'sub' => '', 'fish' => 'タチウオ', 'unit' => '本', 'big' => 'ドラゴン', 'rig' => 'テンヤ', 'file' => 'dragon-counter-data'],
        'tipran' => ['name' => 'ティップランカウンター', 'id' => 'tipran-counter', 'sub' => '/tipran', 'fish' => 'アオリイカ', 'unit' => '杯', 'big' => 'キロアップ', 'rig' => 'エギ', 'file' => 'tipran-counter-data'],
    ];
    private static $app = 'dc';
    private static function A($k) { return self::APPS[self::$app][$k]; }
    private static function pick_app() { $a = sanitize_key($_REQUEST['app'] ?? 'dc'); self::$app = isset(self::APPS[$a]) ? $a : 'dc'; }

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
        if (self::$app !== 'dc') {
            $app = self::$app; self::$app = 'dc'; $base = self::dir(); self::$app = $app;
            if (!$base) return '';
            $d = dirname(dirname($base)) . self::A('sub') . '/.data/trips';
            return is_dir($d) && is_readable($d) ? $d : '';
        }
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
            'catch' => $n['catch'], 'dragon' => $dr, 'gmax' => self::gmax($ev), 'bite' => $n['bite'], 'lost' => $n['lost'], 'gedo' => $n['gedo'],
            'wx' => !empty($j['wx']) ? trim(($j['wx']['weather'] ?? '') . ' 水温' . ($j['wx']['sst'] ?? '?') . '℃') : '',
            'tackle' => implode(' / ', $tk), 'points' => count((array)($j['points'] ?? [])),
        ];
    }
    private static function gmax($ev) { $m = 0; foreach ($ev as $e) if (($e['kind'] ?? '') === 'catch') $m = max($m, (float)($e['size'] ?? 0)); return $m; }
    private static function since($per) { return $per === 'all' ? '' : wp_date('Y-m-d', time() - (int)$per * 86400); }
    private static function rows($dir, $per = 'all') {
        $out = []; $from = self::since($per);
        foreach ((array)glob($dir . '/*.json') as $f) { $r = self::row($f); if ($r && (!$from || $r['date'] >= $from)) $out[] = $r; }
        usort($out, function ($a, $b) { return strcmp($b['received'], $a['received']); });
        return $out;
    }

    /** 全釣行を読み込んで集計する */
    private static function load($dir, $per) {
        $from = self::since($per); $all = [];
        foreach ((array)glob($dir . '/*.json') as $f) { $j = json_decode((string)@file_get_contents($f), true); if (is_array($j) && (!$from || ($j['date'] ?? '') >= $from)) $all[] = $j; }
        return $all;
    }
    private static function bars($title, $data, $unit = '本', $note = '', $max_rows = 12) {
        echo '<div class="dcd-card"><h3>' . esc_html($title) . '</h3>';
        if (!$data) { echo '<p class="description">データがありません。</p></div>'; return; }
        $mx = max(array_map(function ($v) { return is_array($v) ? $v[0] : $v; }, $data)) ?: 1; $i = 0;
        foreach ($data as $k => $v) {
            if (++$i > $max_rows) break;
            $val = is_array($v) ? $v[0] : $v; $sub = is_array($v) ? $v[1] : '';
            echo '<div class="dcd-bar"><span class="dcd-k" title="' . esc_attr($k) . '">' . esc_html($k) . '</span><span class="dcd-t"><i style="width:' . max(2, round($val / $mx * 100)) . '%"></i></span><b>' . esc_html(rtrim(rtrim(number_format((float)$val, 1, '.', ''), '0'), '.') . $unit) . '</b><small>' . esc_html($sub) . '</small></div>';
        }
        if ($note) echo '<p class="description">' . esc_html($note) . '</p>';
        echo '</div>';
    }
    private static function dashboard($dir, $per) {
        $T = self::load($dir, $per); $tz = new DateTimeZone('Asia/Tokyo');
        $n = count($T); $catch = 0; $dragon = 0; $bite = 0; $lost = 0; $hrs = 0;
        $byDay = []; $byHour = array_fill(0, 24, 0); $spot = []; $boat = []; $tide = []; $rig = []; $skirt = []; $U = self::A('unit'); $sa = []; $ka = []; $rod = []; $reel = []; $sst = []; $mode = ['simple' => 0, 'detail' => 0];
        $SA = ['maki-move' => '巻き・誘い中', 'maki-stay' => '巻き・ステイ中', 'tata-move' => '叩き・誘い中', 'tata-stay' => '叩き・ステイ中', 'fall' => 'フォール中', 'oki' => '置き竿']; $KA = ['soku' => '即掛け', 'fuka' => '深追い'];
        $avgAdd = function (&$arr, $k, $v) { if ($k === '' || $k === null) return; if (!isset($arr[$k])) $arr[$k] = [0, 0]; $arr[$k][0] += $v; $arr[$k][1]++; };
        foreach ($T as $t) {
            $c = 0;
            foreach ((array)($t['events'] ?? []) as $e) {
                $k = $e['kind'] ?? '';
                if ($k === 'catch') { $c++; if (!empty($e['dragon'])) $dragon++;
                    $d = new DateTime('@' . intdiv((int)($e['t'] ?? 0), 1000)); $d->setTimezone($tz); $byHour[(int)$d->format('G')]++;
                    if (!empty($e['rigName'])) $rig[$e['rigName']] = ($rig[$e['rigName']] ?? 0) + 1;
                    if (self::$app === 'tipran') { $sk = !empty($e['skirtName']) ? $e['skirtName'] : 'なし'; $skirt[$sk] = ($skirt[$sk] ?? 0) + 1; } }
                if ($k === 'bite') $bite++; if ($k === 'lost') $lost++;
                if (!empty($e['sa']) && in_array($k, ['catch', 'bite', 'lost'], true)) { $l = $SA[$e['sa']] ?? $e['sa']; $sa[$l] = $sa[$l] ?? ['catch' => 0, 'bite' => 0, 'lost' => 0]; $sa[$l][$k]++; }
                if (!empty($e['ka']) && in_array($k, ['catch', 'lost'], true)) { $l = $KA[$e['ka']] ?? $e['ka']; $ka[$l] = $ka[$l] ?? ['catch' => 0, 'bite' => 0, 'lost' => 0]; $ka[$l][$k]++; }
            }
            $catch += $c; $h = max(0, ((int)($t['end'] ?? 0) - (int)($t['start'] ?? 0)) / 3600000); $hrs += $h;
            $day = $t['date'] ?? ''; if (!isset($byDay[$day])) $byDay[$day] = [0, 0]; $byDay[$day][0] += $c; $byDay[$day][1]++;
            $avgAdd($spot, $t['spot']['name'] ?? '', $c); $avgAdd($boat, $t['boat'] ?? '', $c); $avgAdd($tide, $t['tide'] ?? '', $c);
            foreach ((array)($t['tackle'] ?? []) as $tk) { if (!empty($tk['rod'])) $rod[$tk['rod']] = ($rod[$tk['rod']] ?? 0) + 1; if (!empty($tk['reel'])) $reel[$tk['reel']] = ($reel[$tk['reel']] ?? 0) + 1; }
            if (isset($t['wx']['sst']) && $t['wx']['sst'] !== null) $avgAdd($sst, floor((float)$t['wx']['sst']) . '℃台', $c);
            $mode[($t['mode'] ?? '') === 'detail' ? 'detail' : 'simple']++;
        }
        $pct = function ($a, $b) { return $b ? round($a / $b * 100, 1) . '%' : '―'; };
        echo '<style>.dcd-kpis{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;max-width:1100px}.dcd-kpi{background:#fff;border:1px solid #dcdcde;border-radius:8px;padding:10px 12px}.dcd-kpi span{display:block;color:#646970;font-size:12px}.dcd-kpi b{font-size:24px}.dcd-kpi small{display:block;color:#646970}.dcd-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px;max-width:1100px;margin-top:12px}.dcd-card{background:#fff;border:1px solid #dcdcde;border-radius:8px;padding:10px 14px}.dcd-card h3{margin:4px 0 10px;font-size:14px}.dcd-bar{display:grid;grid-template-columns:minmax(0,9em) 1fr auto;gap:8px;align-items:center;font-size:13px;margin:4px 0}.dcd-bar small{grid-column:2/4;color:#646970;margin-top:-4px}.dcd-k{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.dcd-t{background:#f0f0f1;border-radius:4px;height:10px;overflow:hidden}.dcd-t i{display:block;height:100%;background:#2271b1}.dcd-hours{display:flex;align-items:flex-end;gap:2px;height:120px}.dcd-hours div{flex:1;background:#2271b1;min-height:1px;position:relative}.dcd-hl{display:flex;gap:2px;font-size:10px;color:#646970}.dcd-hl span{flex:1;text-align:center}.dcd-tb{border-collapse:collapse;width:100%;font-size:13px}.dcd-tb td,.dcd-tb th{padding:4px 6px;border-bottom:1px solid #f0f0f1;text-align:right}.dcd-tb td:first-child,.dcd-tb th:first-child{text-align:left}</style>';
        echo '<div class="dcd-kpis">';
        foreach ([['釣行', $n . '件', '詳細モード ' . $mode['detail'] . '件'], ['釣れた合計', $catch . $U, ''], ['1釣行あたり', $n ? round($catch / $n, 1) . $U : '―', ''], ['1時間あたり', $hrs ? round($catch / $hrs, 1) . $U : '―', '釣行時間 計' . round($hrs) . '時間'], [self::A('big'), $dragon . $U, '釣れたうち ' . $pct($dragon, $catch)], ['アタリ', $bite . '回', ''], ['バラシ', $lost . '回', '取り込み率 ' . $pct($catch, $catch + $lost)]] as $k)
            echo '<div class="dcd-kpi"><span>' . esc_html($k[0]) . '</span><b>' . esc_html($k[1]) . '</b><small>' . esc_html($k[2]) . '</small></div>';
        echo '</div><div class="dcd-grid">';
        ksort($byDay); $days = array_slice($byDay, -30, null, true); $dd = [];
        foreach ($days as $d => $v) $dd[substr($d, 5)] = [$v[0], $v[1] . '釣行'];
        self::bars('日ごとの釣れた数（直近30日分）', array_reverse($dd, true), $U, '', 30);
        $mh = max($byHour) ?: 1;
        echo '<div class="dcd-card"><h3>時間帯ごとの釣れた数</h3><div class="dcd-hours">';
        for ($h = 0; $h < 24; $h++) echo '<div title="' . $h . '時台 ' . $byHour[$h] . $U . '" style="height:' . round($byHour[$h] / $mh * 100) . '%"></div>';
        echo '</div><div class="dcd-hl">'; for ($h = 0; $h < 24; $h++) echo '<span>' . ($h % 3 === 0 ? $h : '') . '</span>'; echo '</div></div>';
        $avg = function ($arr) { $o = []; foreach ($arr as $k => $v) $o[$k] = [round($v[0] / $v[1], 1), $v[1] . '釣行']; uasort($o, function ($a, $b) { return $b[0] <=> $a[0]; }); return $o; };
        self::bars('釣り場ごとの平均', $avg($spot), $U);
        self::bars('船ごとの平均', $avg($boat), $U);
        self::bars('潮回りごとの平均', $avg($tide), $U);
        if ($sst) { $o = $avg($sst); ksort($o); self::bars('水温ごとの平均', $o, $U); }
        arsort($rig); self::bars('よく釣れた' . self::A('rig'), $rig, $U, self::A('rig') . 'を選んで記録された分だけ。');
        if ($skirt) { arsort($skirt); self::bars('シンカー（増し錘）ごとの釣れた数', $skirt, $U); }
        foreach (['誘いごと（詳細モードの分）' => $sa, '掛け方ごと（詳細モードの分）' => $ka] as $ttl => $arr) {
            echo '<div class="dcd-card"><h3>' . esc_html($ttl) . '</h3>';
            if (!$arr) { echo '<p class="description">データがありません。</p></div>'; continue; }
            echo '<table class="dcd-tb"><tr><th></th><th>釣れた</th><th>アタリ</th><th>バラシ</th><th>取り込み</th></tr>';
            foreach ($arr as $k => $v) echo '<tr><td>' . esc_html($k) . '</td><td>' . (int)$v['catch'] . '</td><td>' . (int)$v['bite'] . '</td><td>' . (int)$v['lost'] . '</td><td>' . esc_html($pct($v['catch'], $v['catch'] + $v['lost'])) . '</td></tr>';
            echo '</table></div>';
        }
        arsort($rod); self::bars('使われたロッド（釣行数）', $rod, '件');
        arsort($reel); self::bars('使われたリール（釣行数）', $reel, '件');
        echo '</div><p class="description">利用者の記録をそのまま集計しています（テストの釣行は「一覧」で消すと外れます）。1人が何回も使うと、その人の釣り方に寄ります。日数・件数が少ないうちは、傾向として読みすぎないようにしてください。</p>';
    }

    public static function page() {
        if (!current_user_can('manage_options')) return;
        self::pick_app();
        $dir = self::dir();
        $notice = get_transient('dcd_notice_' . get_current_user_id()); if ($notice) delete_transient('dcd_notice_' . get_current_user_id());
        echo '<div class="wrap"><h1>釣果アプリのデータ</h1><h2 class="nav-tab-wrapper" style="margin-bottom:10px">';
        foreach (self::APPS as $k => $a) echo '<a class="nav-tab' . (self::$app === $k ? ' nav-tab-active' : '') . '" href="' . esc_url(admin_url('tools.php?page=' . self::SLUG . '&app=' . $k)) . '">' . esc_html($a['name']) . '</a>';
        echo '</h2>';
        if ($notice) echo '<div class="notice notice-info is-dismissible"><p>' . esc_html($notice) . '</p></div>';
        echo '<p class="description">' . esc_html(self::A('name')) . 'で「沖上がり」まで記録された釣行が、匿名（名前・メモなし）で届いたものです。アプリで釣行を消しても、ここには残ります。テストの釣行などは「消す」で取り除けます。</p>';
        if (!$dir && self::$app !== 'dc') { echo '<p>まだ届いていません（データの置き場所 <code>tipran/.data/trips</code> がまだできていません）。</p></div>'; return; }
        if (!$dir) {
            echo '<div class="notice notice-warning"><p>データの置き場所が見つかりませんでした。ドラゴンカウンターの公開フォルダの中の <code>.data/trips</code> の場所（サーバー上のフルパス）を入れてください。WordPress と別のサーバーアカウントにある場合は読めません。</p></div>';
            self::dir_form('');
            echo '</div>'; return;
        }
        $tab = ($_GET['tab'] ?? 'dash') === 'list' ? 'list' : 'dash';
        $per = in_array($_GET['per'] ?? '', ['30', '90', 'all'], true) ? $_GET['per'] : 'all';
        $base = admin_url('tools.php?page=' . self::SLUG . '&app=' . self::$app);
        echo '<h2 class="nav-tab-wrapper">';
        foreach (['dash' => 'ダッシュボード', 'list' => '一覧'] as $k => $l) echo '<a class="nav-tab' . ($tab === $k ? ' nav-tab-active' : '') . '" href="' . esc_url($base . '&tab=' . $k . '&per=' . $per) . '">' . esc_html($l) . '</a>';
        echo '</h2><p>期間：';
        foreach (['all' => 'すべて', '90' => '直近90日', '30' => '直近30日'] as $k => $l) echo $per === $k ? '<strong>' . esc_html($l) . '</strong>　' : '<a href="' . esc_url($base . '&tab=' . $tab . '&per=' . $k) . '">' . esc_html($l) . '</a>　';
        echo '</p>';
        if ($tab === 'dash') { self::dashboard($dir, $per); echo '</div>'; return; }
        $rows = self::rows($dir, $per);
        $sum = ['catch' => 0, 'dragon' => 0]; foreach ($rows as $r) { $sum['catch'] += $r['catch']; $sum['dragon'] += $r['dragon']; }
        echo '<p>届いた釣行：<strong>' . count($rows) . '件</strong>（' . esc_html(self::A('fish') . ' ' . (int)$sum['catch'] . self::A('unit') . '・' . self::A('big') . ' ' . (int)$sum['dragon'] . self::A('unit')) . '）';
        echo '　<a class="button" href="' . esc_url(wp_nonce_url(admin_url('admin-post.php?action=dcd_download&fmt=csv&app=' . self::$app), 'dcd_download')) . '">CSVでダウンロード</a> ';
        echo '<a class="button" href="' . esc_url(wp_nonce_url(admin_url('admin-post.php?action=dcd_download&fmt=json&app=' . self::$app), 'dcd_download')) . '">JSON（全項目）でダウンロード</a></p>';
        echo '<div style="overflow-x:auto"><table class="widefat striped" style="min-width:1100px"><thead><tr>';
        foreach (['届いた日時', '釣行日', '釣り場', '船・席', '時間', '潮', '記録', '釣れた', self::A('big'), 'アタリ', 'バラシ', '外道', '天気', 'タックル', '場所記録', ''] as $h) echo '<th>' . esc_html($h) . '</th>';
        echo '</tr></thead><tbody>';
        foreach ($rows as $r) {
            echo '<tr><td>' . esc_html($r['received']) . '</td><td>' . esc_html($r['date']) . '</td><td>' . esc_html($r['spot']) . '</td><td>' . esc_html($r['boat'] . ' ' . $r['seat']) . '</td><td>' . esc_html($r['time']) . '</td><td>' . esc_html($r['tide']) . '</td><td>' . esc_html($r['mode']) . '</td>';
            echo '<td><strong>' . (int)$r['catch'] . '</strong></td><td>' . (int)$r['dragon'] . (self::$app === 'tipran' && $r['gmax'] ? '<br><small>最大 ' . esc_html(round($r['gmax'])) . 'g</small>' : '') . '</td><td>' . (int)$r['bite'] . '</td><td>' . (int)$r['lost'] . '</td><td>' . (int)$r['gedo'] . '</td><td>' . esc_html($r['wx']) . '</td><td style="max-width:260px">' . esc_html($r['tackle']) . '</td><td>' . ($r['points'] ? (int)$r['points'] . '点' : '') . '</td>';
            echo '<td><form method="post" action="' . esc_url(admin_url('admin-post.php')) . '" onsubmit="return confirm(\'この釣行のデータを消しますか？（元に戻せません）\')">';
            wp_nonce_field('dcd_delete'); echo '<input type="hidden" name="action" value="dcd_delete"><input type="hidden" name="app" value="' . esc_attr(self::$app) . '"><input type="hidden" name="uid" value="' . esc_attr($r['uid']) . '"><button class="button button-small">消す</button></form></td></tr>';
        }
        if (!$rows) echo '<tr><td colspan="16">まだ届いていません。</td></tr>';
        echo '</tbody></table></div>';
        echo '<p class="description">置き場所：<code>' . esc_html($dir) . '</code></p>';
        if (self::$app === 'dc') self::dir_form($dir);
        echo '</div>';
    }
    private static function dir_form($dir) {
        echo '<form method="post" action="' . esc_url(admin_url('admin-post.php')) . '" style="margin-top:8px">';
        wp_nonce_field('dcd_dir');
        echo '<input type="hidden" name="action" value="dcd_dir"><label>置き場所を指定 <input type="text" name="dir" class="regular-text" value="' . esc_attr($dir) . '" placeholder="/home/…/dragon-counter.cutlassfish.tokyo/.data/trips"></label> <button class="button">保存</button></form>';
    }
    private static function back($msg) { set_transient('dcd_notice_' . get_current_user_id(), $msg, 120); wp_safe_redirect(admin_url('tools.php?page=' . self::SLUG . '&app=' . self::$app)); exit; }

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
        self::pick_app();
        $uid = sanitize_text_field(wp_unslash($_POST['uid'] ?? ''));
        $dir = self::dir();
        if (!$dir || !preg_match('/^[a-z0-9]{8,40}$/', $uid)) self::back('消せませんでした。');
        $f = $dir . '/' . $uid . '.json';
        self::back(is_file($f) && @unlink($f) ? '1件消しました。' : '消せませんでした（書き込みの権限が無い可能性があります）。');
    }
    public static function download() {
        if (!current_user_can('manage_options')) wp_die('権限がありません。');
        check_admin_referer('dcd_download');
        self::pick_app();
        $dir = self::dir(); if (!$dir) wp_die('データの置き場所が見つかりません。');
        $fmt = ($_GET['fmt'] ?? '') === 'json' ? 'json' : 'csv';
        nocache_headers();
        $name = self::A('file') . '-' . wp_date('Ymd-Hi') . '.' . $fmt;
        header('Content-Disposition: attachment; filename="' . $name . '"');
        if ($fmt === 'json') {
            header('Content-Type: application/json; charset=utf-8');
            $all = []; foreach ((array)glob($dir . '/*.json') as $f) { $j = json_decode((string)@file_get_contents($f), true); if (is_array($j)) $all[] = $j; }
            echo wp_json_encode($all, JSON_UNESCAPED_UNICODE); exit;
        }
        header('Content-Type: text/csv; charset=utf-8');
        $o = fopen('php://output', 'w'); fwrite($o, "\xEF\xBB\xBF");
        $rows = self::rows($dir);
        fputcsv($o, ['届いた日時', '釣行日', '釣り場', '船', '席', '時間', '潮', '記録', '釣れた', self::A('big'), 'アタリ', 'バラシ', '外道', '天気', 'タックル', '場所記録', 'ID']);
        foreach ($rows as $r) fputcsv($o, [$r['received'], $r['date'], $r['spot'], $r['boat'], $r['seat'], $r['time'], $r['tide'], $r['mode'], $r['catch'], $r['dragon'] . (self::$app === 'tipran' && $r['gmax'] ? '（最大' . round($r['gmax']) . 'g）' : ''), $r['bite'], $r['lost'], $r['gedo'], $r['wx'], $r['tackle'], $r['points'], $r['uid']]);
        exit;
    }
}
DCD_Admin::init();
