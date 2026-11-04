<?php
// GET /api/map-config — Google Maps browser key for same-origin page loads only.
// The key comes from config.php next to this file (written at deploy time, never committed):
//   <?php return ['GOOGLE_MAPS_BROWSER_KEY' => '...', 'GOOGLE_MAPS_ENABLED' => 'true'];
require dirname(__DIR__) . '/_lib/common.php';
handle_map_config();
