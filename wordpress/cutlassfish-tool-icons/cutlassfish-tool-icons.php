<?php
/**
 * Plugin Name: Cutlassfish ツールアイコン
 * Description: サイトのツール一覧（.tools-stack）の各カードで、ツール名の左に各ツールのアイコンを表示します。「OPEN TOOL」のリンク先からツールを判別します。
 * Version: 1.0.0
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

add_action('wp_enqueue_scripts', function () {
    $base = plugins_url('icons/', __FILE__);
    wp_enqueue_style('cutlassfish-tool-icons', plugins_url('tool-icons.css', __FILE__), array(), '1.0.0');
    wp_enqueue_script('cutlassfish-tool-icons', plugins_url('tool-icons.js', __FILE__), array(), '1.0.0', true);
    wp_localize_script('cutlassfish-tool-icons', 'CutlassfishToolIcons', array(
        'icons' => array(
            'reel-line-manager.cutlassfish.tokyo'    => $base . 'reel.webp',
            'dont-forget-anything.cutlassfish.tokyo' => $base . 'dfa.webp',
            'tenya-simulator.cutlassfish.tokyo'      => $base . 'tenya.webp',
            'tide-current-map.cutlassfish.tokyo'     => $base . 'tide.webp',
            'dragon-counter.cutlassfish.tokyo'       => $base . 'dragon.webp',
        ),
    ));
});
