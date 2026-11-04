<?php
// Shared code for /api/current, /api/tide and /api/map-config on the rental server.
// A port of the app's worker/api.js, worker/map-config.js and the /api/* handler in
// scripts/build.mjs: same validation, JSON shape, messages, upstream URLs and 12 s timeout.
// The Worker's in-memory memo becomes a small file cache (1 h). Runs on PHP 7.4+, using
// curl when available and allow_url_fopen otherwise.

ini_set('serialize_precision', '-1');
ini_set('display_errors', '0');

const TIDE_ORIGIN = 'https://www1.kaiho.mlit.go.jp';
const TIDE_UPSTREAM_TIMEOUT = 12;
const TIDE_CACHE_TTL = 3600;
const TIDE_USER_AGENT = 'SHIO-TokyoBay/1.0';

class UpstreamError extends Exception {}

// ---------- JavaScript-compatible helpers ----------

// String.prototype.trim(): JS whitespace and line terminators.
function js_trim($s) {
 $t = preg_replace('/^[\s\x{00A0}\x{1680}\x{2000}-\x{200A}\x{2028}\x{2029}\x{202F}\x{205F}\x{3000}\x{FEFF}]+|[\s\x{00A0}\x{1680}\x{2000}-\x{200A}\x{2028}\x{2029}\x{202F}\x{205F}\x{3000}\x{FEFF}]+$/u', '', $s);
 return $t === null ? $s : $t;
}

// Number(value) for a string or null (null -> 0, '' -> 0, junk -> NAN).
function js_number($s) {
 if ($s === null) return 0.0;
 $t = preg_replace('/^[\s\x{00A0}\x{1680}\x{2000}-\x{200A}\x{2028}\x{2029}\x{202F}\x{205F}\x{3000}\x{FEFF}]+|[\s\x{00A0}\x{1680}\x{2000}-\x{200A}\x{2028}\x{2029}\x{202F}\x{205F}\x{3000}\x{FEFF}]+$/u', '', (string)$s);
 if ($t === null) return NAN;
 if ($t === '') return 0.0;
 if (preg_match('/^([+-]?)Infinity$/D', $t, $m)) return $m[1] === '-' ? -INF : INF;
 if (preg_match('/^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/D', $t)) return (float)$t;
 if (preg_match('/^0[xX]([0-9a-fA-F]+)$/D', $t, $m)) return (float)hexdec($m[1]);
 if (preg_match('/^0[oO]([0-7]+)$/D', $t, $m)) return (float)octdec($m[1]);
 if (preg_match('/^0[bB]([01]+)$/D', $t, $m)) return (float)bindec($m[1]);
 return NAN;
}

// parseInt(s, 10): leading digits after optional whitespace and sign, else NAN.
function js_parse_int($s) {
 if (!preg_match('/^[\s\x{00A0}\x{FEFF}]*([+-]?\d+)/u', $s, $m) && !preg_match('/^\s*([+-]?\d+)/', $s, $m)) return NAN;
 return (int)$m[1];
}

function js_is_integer($n) { return is_float($n) ? is_finite($n) && floor($n) == $n : is_int($n); }

// String.prototype.slice(a, b) for ASCII text (PHP 7.4 substr returns false past the end).
function js_slice($s, $a, $b) { if ($a >= strlen($s)) return ''; $r = substr($s, $a, $b - $a); return $r === false ? '' : $r; }

// URLSearchParams.get(): first value, '+' as space, percent-decoded; null when absent.
function query_param($name) {
 $qs = isset($_SERVER['QUERY_STRING']) ? $_SERVER['QUERY_STRING'] : '';
 if ($qs === '') return null;
 foreach (explode('&', $qs) as $pair) {
  if ($pair === '') continue;
  $eq = strpos($pair, '=');
  $k = $eq === false ? $pair : substr($pair, 0, $eq);
  $v = $eq === false ? '' : (string)substr($pair, $eq + 1);
  if (rawurldecode(str_replace('+', ' ', $k)) === $name) return rawurldecode(str_replace('+', ' ', $v));
 }
 return null;
}

// JSON.stringify-compatible encoding: integral floats print as integers, NaN/Infinity as null.
function js_normalize($v) {
 if (is_float($v)) {
  if (!is_finite($v)) return null;
  if (floor($v) == $v && abs($v) < 9007199254740992) return (int)$v;
  return $v;
 }
 if (is_array($v)) { foreach ($v as $k => $x) $v[$k] = js_normalize($x); return $v; }
 return $v;
}
function js_json($v) {
 $s = json_encode(js_normalize($v), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_LINE_TERMINATORS | JSON_INVALID_UTF8_SUBSTITUTE);
 return $s === false ? 'null' : $s;
}

// Response.json(body, {status, headers})
function send_json_text($json, $status = 200, $headers = array()) {
 if (function_exists('header_remove')) header_remove('X-Powered-By');
 http_response_code($status);
 header('Content-Type: application/json');
 foreach ($headers as $k => $v) header($k . ': ' . $v);
 echo $json;
}
function send_json($value, $status = 200, $headers = array()) { send_json_text(js_json($value), $status, $headers); }

// ---------- worker/api.js ----------

function valid_date($s) {
 if (!is_string($s) || !preg_match('/^(\d{4})-(\d{2})-(\d{2})$/D', $s, $m)) return false;
 return checkdate((int)$m[2], (int)$m[3], (int)$m[1]);
}

function tide_stations() {
 static $st = null;
 if ($st === null) $st = json_decode(file_get_contents(__DIR__ . '/stations.json'), true);
 return $st;
}

// upstream(url): GET with a 12 s timeout; non-2xx -> 公式データの取得に失敗しました (status).
function upstream($url) {
 if (function_exists('curl_init')) {
  $ch = curl_init($url);
  curl_setopt_array($ch, array(
   CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => true, CURLOPT_MAXREDIRS => 20,
   CURLOPT_TIMEOUT => TIDE_UPSTREAM_TIMEOUT, CURLOPT_CONNECTTIMEOUT => TIDE_UPSTREAM_TIMEOUT,
   CURLOPT_USERAGENT => TIDE_USER_AGENT, CURLOPT_ENCODING => '',
  ));
  $body = curl_exec($ch);
  $errno = curl_errno($ch);
  $status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
  curl_close($ch);
  if ($errno === 28) throw new UpstreamError('The operation was aborted due to timeout');
  if ($body === false || $errno) throw new UpstreamError('');
 } elseif (filter_var(ini_get('allow_url_fopen'), FILTER_VALIDATE_BOOLEAN)) {
  $ctx = stream_context_create(array('http' => array(
   'method' => 'GET', 'timeout' => TIDE_UPSTREAM_TIMEOUT, 'user_agent' => TIDE_USER_AGENT,
   'follow_location' => 1, 'max_redirects' => 20, 'ignore_errors' => true,
  )));
  $started = microtime(true);
  $body = @file_get_contents($url, false, $ctx);
  $status = 0;
  if (isset($http_response_header)) foreach ($http_response_header as $h) if (preg_match('#^HTTP/\S+\s+(\d{3})#', $h, $m)) $status = (int)$m[1];
  if ($body === false || !$status) throw new UpstreamError(microtime(true) - $started >= TIDE_UPSTREAM_TIMEOUT ? 'The operation was aborted due to timeout' : '');
 } else {
  throw new UpstreamError('');
 }
 if ($status < 200 || $status > 299) throw new UpstreamError('公式データの取得に失敗しました (' . $status . ')');
 return $body;
}

function parse_stations($html) {
 preg_match_all('/coords\s*=\s*["\']?(\d+),(\d+),\d+\s+ALT=["\']([\d.]+)kn\./i', $html, $all, PREG_SET_ORDER);
 $out = array();
 foreach ($all as $m) {
  $x = js_number($m[1]); $y = js_number($m[2]);
  $out[] = array('x' => $x, 'y' => $y, 'lat' => 35 + (631 - $y) / 840, 'lon' => 139.5 + ($x - 30) / 675, 'speed' => js_number($m[3]));
 }
 return $out;
}

function tide_value($s) { $v = js_parse_int($s); return (is_float($v) && is_nan($v)) || $v === 999 ? null : $v; }

function tide_find_line($lines, $d) {
 $p = explode('-', $d); $y = (int)$p[0]; $m = (int)$p[1]; $day = (int)$p[2];
 foreach ($lines as $l) {
  if (js_number(js_slice($l, 72, 74)) == $y % 100 && js_number(js_slice($l, 74, 76)) == $m && js_number(js_slice($l, 76, 78)) == $day) return $l;
 }
 return null;
}

function tide_events($row, $offset) {
 $out = array();
 if ($row === null) return $out;
 foreach (array(array(80, 'high'), array(108, 'low')) as $st) {
  list($start, $type) = $st;
  for ($i = 0; $i < 4; $i++) {
   $b = $start + $i * 7;
   $h = js_parse_int(js_slice($row, $b, $b + 2)); $m = js_parse_int(js_slice($row, $b + 2, $b + 4)); $height = tide_value(js_slice($row, $b + 4, $b + 7));
   if (is_float($h) || is_float($m) || $height === null || $h < 0 || $m < 0 || $h > 24 || $m > 59 || ($h === 24 && $m !== 0)) continue;
   $out[] = array('type' => $type, 'hour' => $offset + $h + $m / 60, 'height' => $height, 'time' => str_pad((string)$h, 2, '0', STR_PAD_LEFT) . ':' . str_pad((string)$m, 2, '0', STR_PAD_LEFT));
  }
 }
 // Array.prototype.sort is stable; PHP 7 usort is not, so keep the original order on ties.
 $keyed = array(); foreach ($out as $i => $e) $keyed[] = array($e, $i);
 usort($keyed, function ($a, $b) { $d = $a[0]['hour'] - $b[0]['hour']; return $d < 0 ? -1 : ($d > 0 ? 1 : $a[1] - $b[1]); });
 return array_map(function ($x) { return $x[0]; }, $keyed);
}

function parse_tides($raw, $date, $code = 'TK') {
 $stations = tide_stations();
 if (!isset($stations[$code])) throw new UpstreamError('対応していない潮位地点です。');
 $lines = preg_split('/\r?\n/', $raw);
 $line = tide_find_line($lines, $date); $year = substr($date, 0, 4);
 if ($line === null) throw new UpstreamError('この日付の潮位表が見つかりません。');
 $hours = array();
 for ($i = 0; $i < 24; $i++) $hours[] = tide_value(js_slice($line, $i * 3, $i * 3 + 3));
 $next = new DateTime($date . 'T00:00:00Z', new DateTimeZone('UTC')); $next->modify('+1 day');
 $nextLine = tide_find_line($lines, $next->format('Y-m-d'));
 $dayHours = $hours; $dayHours[] = $nextLine !== null ? tide_value(js_slice($nextLine, 0, 3)) : null;
 return array('date' => $date, 'code' => $code, 'station' => $stations[$code]['name'], 'coordinates' => $stations[$code], 'hours' => $hours,
  'dayHours' => $dayHours, 'events' => tide_events($line, 0), 'nextDayEvents' => tide_events($nextLine, 24), 'timezone' => 'JST',
  'datum' => '潮位表基準面からの高さ', 'source' => 'https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/' . $year . '/' . $code . '.txt');
}

function current_prediction($date, $hour) {
 $p = explode('-', $date); $year = (int)$p[0]; $month = (int)$p[1]; $day = (int)$p[2];
 $source = TIDE_ORIGIN . '/TIDE/pred2/cgi-bin/CurrPredCgi_K.cgi?area=01&year=' . $year . '&month=' . $month . '&day=' . $day . '&hour=' . $hour;
 $html = upstream($source); $stations = parse_stations($html);
 if (count($stations) < 20) throw new UpstreamError('公式推算図を読み取れませんでした。時間をおいて再取得してください。');
 $expected = '01_' . str_replace('-', '', $date) . str_pad((string)$hour, 2, '0', STR_PAD_LEFT) . '_.png';
 if (strpos($html, $expected) === false) throw new UpstreamError('要求時刻と推算図の時刻が一致しません。');
 $image = upstream(TIDE_ORIGIN . '/TIDE/pred2/CurrPred/curr_img/' . $expected);
 $now = microtime(true);
 return array('date' => $date, 'hour' => $hour, 'stations' => $stations, 'image' => 'data:image/png;base64,' . base64_encode($image), 'source' => $source,
  'generatedAt' => gmdate('Y-m-d\TH:i:s', (int)floor($now)) . sprintf('.%03dZ', (int)floor(($now - floor($now)) * 1000)));
}

// ---------- small file cache (replaces the Worker's in-memory memo) ----------

function cache_dir() {
 static $dir = false;
 if ($dir !== false) return $dir;
 foreach (array(dirname(__DIR__, 2) . '/cache', rtrim(sys_get_temp_dir(), '/\\') . '/tide-current-map-cache') as $d) {
  if (!is_dir($d)) @mkdir($d, 0755, true);
  if (is_dir($d) && is_writable($d)) {
   if (!file_exists($d . '/.htaccess')) @file_put_contents($d . '/.htaccess', "Require all denied\n");
   return $dir = $d;
  }
 }
 return $dir = null;
}
function cache_get($key) {
 $d = cache_dir(); if ($d === null) return null;
 $f = $d . '/' . sha1($key) . '.json';
 if (!is_file($f) || filemtime($f) < time() - TIDE_CACHE_TTL) return null;
 $s = @file_get_contents($f);
 return $s === false || $s === '' ? null : $s;
}
function cache_put($key, $json) {
 $d = cache_dir(); if ($d === null) return;
 $f = $d . '/' . sha1($key) . '.json'; $tmp = $f . '.' . getmypid() . '.tmp';
 if (@file_put_contents($tmp, $json) !== false) @rename($tmp, $f);
 if (mt_rand(1, 20) === 1) foreach ((array)glob($d . '/*.json') as $old) if (@filemtime($old) < time() - TIDE_CACHE_TTL) @unlink($old);
}

// ---------- /api/current and /api/tide (the handler in scripts/build.mjs) ----------

function handle_tide_api($path) {
 try {
  $date = query_param('date'); if ($date === null || $date === '') $date = '';
  $hour = js_number(query_param('hour'));
  $y = (int)substr($date, 0, 4);
  if (!valid_date($date) || $y < 1900 || $y > 2100 || !js_is_integer($hour) || $hour < 0 || $hour > 23) return send_json(array('error' => '日付または時刻が不正です。'), 400);
  $hour = (int)$hour;
  $station = query_param('station'); if ($station === null || $station === '') $station = 'TK';
  $stations = tide_stations();
  if ($path === '/api/tide' && !isset($stations[$station])) return send_json(array('error' => '対応していない潮位地点です。'), 400);
  $ok = array('Cache-Control' => 'public, max-age=3600');
  if ($path === '/api/current') {
   $snapshot = __DIR__ . '/snapshots/' . $date . '_' . $hour . '.json';
   if (is_file($snapshot)) return send_json_text(file_get_contents($snapshot), 200, $ok);
  } elseif (substr($date, 0, 4) === '2026' && is_file(__DIR__ . '/tide/' . $station . '-2026.txt')) {
   return send_json(parse_tides(file_get_contents(__DIR__ . '/tide/' . $station . '-2026.txt'), $date, $station), 200, $ok);
  }
  $key = $path . $date . $hour . ($path === '/api/tide' ? $station : '');
  $cached = cache_get($key);
  if ($cached !== null) return send_json_text($cached, 200, $ok);
  if ($path === '/api/current') $result = current_prediction($date, $hour);
  else $result = parse_tides(upstream('https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/' . substr($date, 0, 4) . '/' . $station . '.txt'), $date, $station);
  $json = js_json($result);
  cache_put($key, $json);
  return send_json_text($json, 200, $ok);
 } catch (Exception $e) {
  return send_json(array('error' => $e->getMessage() !== '' ? $e->getMessage() : 'データを取得できません。'), 502);
 } catch (Error $e) {
  return send_json(array('error' => 'データを取得できません。'), 502);
 }
}

// ---------- /api/map-config (worker/map-config.js) ----------

const MAP_ALLOWED_ORIGINS = array('https://tide-current-map.cutlassfish.tokyo', 'https://tide-stg.cutlassfish.tokyo');

function url_origin($url) {
 $p = @parse_url($url);
 if (!is_array($p) || empty($p['scheme'])) return null;
 $scheme = strtolower($p['scheme']);
 if (!in_array($scheme, array('http', 'https'), true)) return 'null';
 if (empty($p['host'])) return null;
 $port = isset($p['port']) ? (int)$p['port'] : null;
 $default = $scheme === 'https' ? 443 : 80;
 return $scheme . '://' . strtolower($p['host']) . ($port !== null && $port !== $default ? ':' . $port : '');
}

// Origin of the URL the browser requested (TLS may end at a front proxy).
function request_origin() {
 $https = (!empty($_SERVER['HTTPS']) && strtolower($_SERVER['HTTPS']) !== 'off')
  || (isset($_SERVER['REQUEST_SCHEME']) && strtolower($_SERVER['REQUEST_SCHEME']) === 'https')
  || (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && strtolower(trim(explode(',', $_SERVER['HTTP_X_FORWARDED_PROTO'])[0])) === 'https')
  || (isset($_SERVER['HTTP_X_FORWARDED_SSL']) && strtolower($_SERVER['HTTP_X_FORWARDED_SSL']) === 'on')
  || (isset($_SERVER['SERVER_PORT']) && (string)$_SERVER['SERVER_PORT'] === '443');
 $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : '';
 if ($host === '' || !preg_match('/^[A-Za-z0-9.\-]+(:\d+)?$/D', $host)) return null;
 return url_origin(($https ? 'https' : 'http') . '://' . $host . '/');
}

function handle_map_config() {
 $config = array();
 $file = dirname(__DIR__) . '/map-config/config.php';
 if (is_file($file)) { $c = include $file; if (is_array($c)) $config = $c; }
 $key = isset($config['GOOGLE_MAPS_BROWSER_KEY']) && is_string($config['GOOGLE_MAPS_BROWSER_KEY']) ? js_trim($config['GOOGLE_MAPS_BROWSER_KEY']) : '';
 $en = isset($config['GOOGLE_MAPS_ENABLED']) ? $config['GOOGLE_MAPS_ENABLED'] : '';
 $enabled = strtolower(js_trim($en === true ? 'true' : (is_scalar($en) ? (string)$en : ''))) === 'true';
 $origins = isset($config['ALLOWED_ORIGINS']) && is_array($config['ALLOWED_ORIGINS']) ? $config['ALLOWED_ORIGINS'] : MAP_ALLOWED_ORIGINS;

 $origin = request_origin();
 $allowed = isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] === 'GET' && $origin !== null && in_array($origin, $origins, true);
 $supplied = isset($_SERVER['HTTP_ORIGIN']) ? $_SERVER['HTTP_ORIGIN'] : '';
 if ($supplied !== '' && $supplied !== $origin) $allowed = false;
 if (isset($_SERVER['HTTP_SEC_FETCH_SITE']) && $_SERVER['HTTP_SEC_FETCH_SITE'] === 'cross-site') $allowed = false;
 $referrer = isset($_SERVER['HTTP_REFERER']) ? $_SERVER['HTTP_REFERER'] : '';
 if ($referrer !== '' && url_origin($referrer) !== $origin) $allowed = false;
 // These checks reduce unwanted key delivery. Google must also enforce website and API
 // restrictions on the key; request headers are not a budget.
 send_json($enabled && $key !== '' && $allowed ? array('provider' => 'google', 'apiKey' => $key) : array('provider' => 'standard'), 200,
  array('Cache-Control' => 'no-store', 'X-Content-Type-Options' => 'nosniff'));
}
