<?php
// Same 404 as the Worker: plain "Not found".
if (function_exists('header_remove')) header_remove('X-Powered-By');
http_response_code(404);
header('Content-Type: text/plain;charset=UTF-8');
echo 'Not found';
