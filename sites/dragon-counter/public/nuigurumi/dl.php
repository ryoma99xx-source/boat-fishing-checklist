<?php
// タチウオのぬいぐるみの型紙PDFのダウンロード口。1回ごとに記録してからPDFへ移す。
// 記録するのは日時・どの型紙か・どこから来たか（サイト名だけ）・端末の種類・2回目以降か。
// IPアドレスや端末を特定できる情報は保存しない。記録は ../.data/downloads（外から読めない）。
ini_set('display_errors', '0');
$files = [
  'paper'  => 'tachiuo-pattern-paper-v21.pdf',
  'fabric' => 'tachiuo-pattern-fabric-sa3mm-v21.pdf',
];
$f = $_GET['f'] ?? '';
if (!isset($files[$f])) { http_response_code(404); exit; }
$ua = (string)($_SERVER['HTTP_USER_AGENT'] ?? '');
$bot = $ua === '' || preg_match('/bot|crawl|spider|slurp|preview|facebookexternalhit|curl|wget|python|headless/i', $ua);
if (!$bot) {
  $dev = preg_match('/iPad|Tablet/i', $ua) ? 'タブレット' : (preg_match('/Mobile|iPhone|Android/i', $ua) ? 'スマホ' : 'PC');
  $os = preg_match('/iPhone|iPad|iPod/i', $ua) ? 'iOS' : (preg_match('/Android/i', $ua) ? 'Android' : (preg_match('/Windows/i', $ua) ? 'Windows' : (preg_match('/Macintosh|Mac OS X/i', $ua) ? 'Mac' : 'その他')));
  $ref = parse_url((string)($_SERVER['HTTP_REFERER'] ?? ''), PHP_URL_HOST) ?: '';
  $rep = !empty($_COOKIE['tnp_dl']);
  $line = json_encode(['t' => gmdate('c'), 'f' => $f, 'ref' => substr($ref, 0, 80), 'dev' => $dev, 'os' => $os, 'rep' => $rep], JSON_UNESCAPED_UNICODE) . "\n";
  $dir = dirname(__DIR__) . '/.data/downloads';
  if (is_dir($dir) || @mkdir($dir, 0700, true)) @file_put_contents($dir . '/pattern.jsonl', $line, FILE_APPEND | LOCK_EX);
  setcookie('tnp_dl', '1', ['expires' => time() + 365 * 86400, 'path' => '/nuigurumi/', 'secure' => true, 'httponly' => true, 'samesite' => 'Lax']);
}
header('Cache-Control: no-store');
header('Location: /nuigurumi/' . $files[$f], true, 302);
