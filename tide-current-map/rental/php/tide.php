<?php
// GET /api/tide?date=YYYY-MM-DD&station=TK — 気象庁 潮位表 (bundled 2026 tables or live).
require __DIR__ . '/_lib/common.php';
handle_tide_api('/api/tide');
