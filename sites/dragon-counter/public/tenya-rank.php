<?php
// テンヤカタログ（/tenya-catalog/）のランキング。ドラゴンカウンターに匿名で集まった釣行（.data/trips）から作る。
// 回数・人数は出さず、順位（製品＋色。号数はまとめる）だけを返す。10位まで埋まらないランキングは空にする。
// top：釣れ筋（釣れた数の上位3つ。件数が少なくても出す。決め方はページには書かない）。
// 集計は1時間ごと（.data/tenya-rank2.json に控える）。
ini_set('display_errors', '0');
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: public, max-age=600');
header('X-Content-Type-Options: nosniff');
// cutlassfish.tokyo のテンヤカタログの記事からも読む（プラグイン cutlassfish-tenya-catalog）
header('Access-Control-Allow-Origin: https://cutlassfish.tokyo');
header('Vary: Origin');

$cache = __DIR__ . '/.data/tenya-rank2.json';
if (is_file($cache) && time() - filemtime($cache) < 3600) { readfile($cache); exit; }

$map = json_decode((string)@file_get_contents(__DIR__ . '/tenya-catalog/rank-map.json'), true);
if (!is_array($map)) $map = [];
$catch = []; $use = [];
foreach (glob(__DIR__ . '/.data/trips/*.json') ?: [] as $f) {
  $d = json_decode((string)@file_get_contents($f), true);
  if (!is_array($d)) continue;
  $seen = [];
  foreach (($d['events'] ?? []) as $e) {
    if (!is_array($e)) continue;
    $k = $map[$e['rig'] ?? ''] ?? null;
    if ($k === null) continue;
    $seen[$k] = 1;
    if (($e['kind'] ?? '') === 'catch' && ($e['sp'] ?? '') === 'tachiuo') $catch[$k] = ($catch[$k] ?? 0) + 1;
  }
  foreach (($d['gear'] ?? []) as $g) {
    if (!is_array($g)) continue;
    $k = $map[$g['rig'] ?? ''] ?? null;
    if ($k !== null) $seen[$k] = 1;
  }
  foreach ($seen as $k => $_) $use[$k] = ($use[$k] ?? 0) + 1;   // 使った釣行の数
}
function top10($a) { arsort($a); return count($a) >= 10 ? array_slice(array_keys($a), 0, 10) : []; }
$top = $catch; arsort($top);
$out = json_encode(['top' => array_slice(array_keys($top), 0, 3), 'catch' => top10($catch), 'use' => top10($use)], JSON_UNESCAPED_UNICODE);
if (is_dir(__DIR__ . '/.data')) @file_put_contents($cache, $out, LOCK_EX);
echo $out;
