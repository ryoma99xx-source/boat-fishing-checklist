<?php
// 釣果データの受け口（匿名）。タイラバカウンターが沖上がり後の釣行を送ってくる。
// 1釣行＝1ファイル（.data/trips/<shareId>.json）。同じ shareId は上書き、delete:true なら消す。
// IPアドレスや端末の情報は保存しない。.data はドットで始まるので .htaccess により外から読めない（404）。
ini_set('display_errors', '0');
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function out($code, $body) { http_response_code($code); echo json_encode($body); exit; }

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') out(405, ['ok' => false, 'error' => 'POST only']);
if (($_SERVER['HTTP_ORIGIN'] ?? '') !== 'https://dragon-counter.cutlassfish.tokyo') out(403, ['ok' => false, 'error' => 'origin']);

$raw = file_get_contents('php://input', false, null, 0, 300001);
if ($raw === false || strlen($raw) > 300000) out(413, ['ok' => false, 'error' => 'too large']);
$d = json_decode($raw, true);
if (!is_array($d) || ($d['app'] ?? '') !== 'tairaba-counter' || !is_string($d['uid'] ?? null) || !preg_match('/^[a-z0-9]{16,40}$/D', $d['uid'])) {
  out(400, ['ok' => false, 'error' => 'bad request']);
}

$dir = __DIR__ . '/.data/trips';
if (!is_dir($dir) && !@mkdir($dir, 0700, true)) out(500, ['ok' => false, 'error' => 'store']);
$file = $dir . '/' . $d['uid'] . '.json';

if (!empty($d['delete'])) { if (is_file($file)) @unlink($file); out(200, ['ok' => true, 'deleted' => true]); }
if (!is_array($d['events'] ?? null) || count($d['events']) > 3000) out(400, ['ok' => false, 'error' => 'bad events']);
if (!is_file($file) && count(glob($dir . '/*.json')) >= 50000) out(507, ['ok' => false, 'error' => 'full']);

$d['received'] = gmdate('c');
$tmp = $file . '.' . bin2hex(random_bytes(4)) . '.tmp';
if (file_put_contents($tmp, json_encode($d, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), LOCK_EX) === false || !rename($tmp, $file)) {
  @unlink($tmp); out(500, ['ok' => false, 'error' => 'write']);
}
out(200, ['ok' => true]);
