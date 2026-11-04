<?php
// GET /api/current?date=YYYY-MM-DD&hour=H — 海上保安庁 潮流推算 (bundled snapshot or live).
require __DIR__ . '/_lib/common.php';
handle_tide_api('/api/current');
