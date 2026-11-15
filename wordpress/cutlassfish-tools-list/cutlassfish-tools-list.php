<?php
/**
 * Plugin Name: Cutlassfish ツール一覧の追加
 * Description: テーマのツール一覧（トップの TOOLS・ツールのページ・メニュー）に、潮と流れマップ・ドラゴンカウンター・ティップランカウンターを足します。テーマの仕組み（tbt_tools）に足すので、テーマ本体は変えません。紹介記事は公開されているものだけ「READ ARTICLE」を出します。以前の「Tool 04」「Tool 05」プラグインの表示は、二重にならないよう止めます。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

/** 足すツール（並べる順） */
function cftl_tools() {
    return array(
        array(
            'en'   => 'TIDE & CURRENT MAP',
            'name' => '東京湾の潮と流れ',
            'lead' => '地図で場所ごとの流れと1日の潮位を見る無料ツール。50m・100m・250m格子の自作モデルを、海上保安庁の潮流推算と重ねて比較できます。自作モデルは潮汐のみの参考計算です。',
            'url'  => 'https://tide-current-map.cutlassfish.tokyo/',
            'post' => 'tokyo-bay-tide-current-map',
        ),
        array(
            'en'   => 'DRAGON COUNTER',
            'name' => 'ドラゴンカウンター',
            'lead' => 'タチウオの釣果を時間の経過と共に、テンヤ・潮・船の向きと一緒に記録する無料ツール。釣り場を選ぶと潮回りと満潮・干潮が自動で入り、ドラゴン（120cm以上）や大漁も残せます。記録は端末に保存され、釣果データは匿名で集計に使います。',
            'url'  => 'https://dragon-counter.cutlassfish.tokyo/',
            'post' => 'dragon-counter',
        ),
        array(
            'en'   => 'TIPRUN COUNTER',
            'name' => 'ティップランカウンター',
            'lead' => 'アオリイカの釣果を時間と一緒に、エギ・シンカー・潮・船の向きと一緒に記録する無料ツール。エギ・シンカー・竿・リールは写真付きのカタログから選べ、釣り場を選ぶと潮回りと満潮・干潮が自動で入ります。記録は端末に保存され、釣果データは匿名で集計に使います。',
            'url'  => 'https://dragon-counter.cutlassfish.tokyo/tipran/',
            'post' => 'tipran-counter',
        ),
    );
}

add_filter('tbt_tools', function ($tools) {
    $have = array();
    foreach ((array) $tools as $t) { $have[untrailingslashit($t['url'] ?? '')] = true; }
    foreach (cftl_tools() as $t) {
        if (isset($have[untrailingslashit($t['url'])])) { continue; }   // テーマ側に入ったら足さない
        // 紹介記事は公開中のものだけ（下書きのリンクを出さない）
        $p = get_page_by_path($t['post'], OBJECT, 'tachiuo_post');
        if (!$p || $p->post_status !== 'publish') { $t['post'] = ''; }
        $tools[] = $t;
    }
    return $tools;
}, 20);

// 以前のプラグイン（画面に後からカードとメニューを足す方式）の表示は二重になるので止める
add_action('wp_enqueue_scripts', function () {
    foreach (array('tide-current-map-tool-04', 'dragon-counter-tool-05', 'tipran-counter-tool-06') as $h) {
        wp_dequeue_script($h);
    }
}, 100);
