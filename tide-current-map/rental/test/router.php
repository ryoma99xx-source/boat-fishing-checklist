<?php
// Router for `php -S` (tests only): emulates what Apache does with the shipped .htaccess
// files — directory-index PHP for /api/<name>, the same content types / cache headers, and
// 404 for implementation files and directories. The real .htaccess is tested under Apache.
$root = rtrim($_SERVER['DOCUMENT_ROOT'], '/');
$path = rawurldecode((string)parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH));

function not_found($root) { require $root . '/_errors/404.php'; return true; }

if (preg_match('#^/api/(current|tide|map-config)$#D', $path, $m)) {
 $script = $root . '/api/' . $m[1] . '.php';
 $_SERVER['SCRIPT_FILENAME'] = $script; $_SERVER['SCRIPT_NAME'] = '/api/' . $m[1] . '.php';
 chdir(dirname($script));
 require $script;
 return true;
}
if ($path === '/') $path = '/index.html';
if (strpos($path, '..') !== false || preg_match('#(^|/)\.#', $path) || preg_match('#^/(api/_lib|cache|_errors)(/|$)#', $path)
 || preg_match('#\.php$#', $path) || !is_file($root . $path)) return not_found($root);

$name = basename($path);
$headers = array();
$types = array('js' => 'text/javascript; charset=utf-8', 'css' => 'text/css; charset=utf-8', 'html' => 'text/html; charset=utf-8',
 'json' => 'application/json; charset=utf-8', 'webmanifest' => 'application/manifest+json; charset=utf-8', 'ico' => 'image/x-icon',
 'png' => 'image/png', 'webp' => 'image/webp', 'gz' => 'application/octet-stream', 'bin' => 'application/octet-stream');
$ext = pathinfo($name, PATHINFO_EXTENSION);
if (!isset($types[$ext])) return not_found($root);
$headers['Content-Type'] = $types[$ext];
if (strpos($path, '/api/harmonic/') === 0) {
 $headers['Cache-Control'] = $name === 'index.json' ? 'no-cache' : 'public, max-age=31536000, immutable';
} elseif (preg_match('/^(index\.html|app\.js|geometry\.js|coverage\.js|chart\.js|tide\.js|clock\.js|google-guard\.js|map-gestures\.js|harmonic\.js|currents\.js|spots\.js|flow-layer\.js|site\.webmanifest)$/', $name)) {
 $headers['Cache-Control'] = 'no-cache';
} elseif (preg_match('/^(favicon\.ico|favicon-32\.png|apple-touch-icon\.png|icon-192\.png|icon-512\.png|brand-logo\.png)$/', $name)) {
 $headers['Cache-Control'] = 'public, max-age=86400';
} elseif (preg_match('/^(coastal-map\.json|overview-map\.webp|coastal-map\.webp)$/', $name)) {
 $headers['Cache-Control'] = 'public, max-age=3600';
}
if ($name === 'index.html' || preg_match('/^(favicon|apple-touch-icon|icon-)/', $name)) $headers['X-Content-Type-Options'] = 'nosniff';
if ($name === 'index.html') $headers['Referrer-Policy'] = 'strict-origin-when-cross-origin';
header_remove('X-Powered-By');
foreach ($headers as $k => $v) header($k . ': ' . $v);
header('Content-Length: ' . filesize($root . $path));
readfile($root . $path);
return true;
