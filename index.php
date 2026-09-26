<?php
/**
 * Kroniclez Dedicated Digital TV Menu Board Engine
 * Hostinger / cPanel Production Router (PHP 7.4 - 8.3+)
 */

// Enable CORS and disable browser caching so TVs always display real-time inventory
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");
header("Cache-Control: no-cache, no-store, must-revalidate");
header("Pragma: no-cache");
header("Expires: 0");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Extract clean request path relative to this script
$request_uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$script_name = $_SERVER['SCRIPT_NAME'];
$base_dir = rtrim(dirname($script_name), '/\\');

// Calculate relative path inside this folder (e.g. /kwc/tv1 -> /tv1)
$rel_path = '/';
if ($base_dir !== '' && strpos($request_uri, $base_dir) === 0) {
    $rel_path = substr($request_uri, strlen($base_dir));
} else {
    $rel_path = $request_uri;
}
if (strpos($rel_path, '/index.php') === 0) {
    $rel_path = substr($rel_path, strlen('/index.php'));
}
$rel_path = '/' . ltrim($rel_path, '/');

// Determine Screen ID
$screen = isset($_GET['screen']) ? intval($_GET['screen']) : 1;
if ($rel_path === '/tv1' || $rel_path === '/screen1' || strpos($rel_path, '/tv1') === 0) {
    $screen = 1;
} elseif ($rel_path === '/tv2' || $rel_path === '/screen2' || strpos($rel_path, '/tv2') === 0) {
    $screen = 2;
} elseif ($rel_path === '/tv3' || $rel_path === '/screen3' || strpos($rel_path, '/tv3') === 0) {
    $screen = 3;
}
if ($screen < 1 || $screen > 3) $screen = 1;

// --------------------------------------------------------------------------
// 1. API Endpoint: Live TV Menu Feed (/api/tv-menu)
// --------------------------------------------------------------------------
if ($rel_path === '/api/tv-menu' || isset($_GET['api'])) {
    header("Content-Type: application/json; charset=utf-8");
    
    $cache_file = sys_get_temp_dir() . "/kroniclez_tv_feed_s{$screen}.json";
    
    // Check in-memory local disk cache (valid for 20 seconds)
    if (file_exists($cache_file) && (time() - filemtime($cache_file) < 20)) {
        echo file_get_contents($cache_file);
        exit;
    }
    
    // Fetch from live backend engine
    $backend_url = "https://kroniclez-tv-menu-2cmv.onrender.com/api/tv-menu?screen={$screen}&store=1&_t=" . time();
    $ctx = stream_context_create([
        'http' => [
            'timeout' => 9,
            'header' => "User-Agent: Kroniclez-Hostinger-Proxy/1.0\r\n"
        ]
    ]);
    $json = @file_get_contents($backend_url, false, $ctx);
    
    if ($json && ($data = json_decode($json, true)) && !empty($data['success'])) {
        @file_put_contents($cache_file, $json);
        echo $json;
        exit;
    }
    
    // Fallback: served cached file if cloud is temporarily waking up
    if (file_exists($cache_file)) {
        echo file_get_contents($cache_file);
        exit;
    }
    
    // Fallback 2: fetch from local teamhub feed
    $th_url = "https://teamhub.kroniclez.com/api/tv_menu_feed.php?store=1&screen={$screen}";
    $th_json = @file_get_contents($th_url, false, $ctx);
    if ($th_json) {
        echo $th_json;
        exit;
    }
    
    echo json_encode([
        "success" => false, 
        "message" => "Inventory feed connecting... please wait"
    ]);
    exit;
}

// --------------------------------------------------------------------------
// 2. Staff Admin Portal (/admin)
// --------------------------------------------------------------------------
if ($rel_path === '/admin' || $rel_path === '/portal' || $rel_path === '/override' || $rel_path === '/overrides') {
    header("Content-Type: text/html; charset=utf-8");
    $admin_file = __DIR__ . '/static/admin.html';
    if (file_exists($admin_file)) {
        $admin_html = file_get_contents($admin_file);
        $asset_base = ($base_dir !== '') ? $base_dir . '/static/' : '/static/';
        $admin_html = str_replace('/static/', $asset_base, $admin_html);
        echo $admin_html;
        exit;
    }
    echo "Admin portal file not found at static/admin.html";
    exit;
}

// --------------------------------------------------------------------------
// 3. Admin API Endpoints (/api/admin/...)
// --------------------------------------------------------------------------
if (strpos($rel_path, '/api/admin/') === 0) {
    header("Content-Type: application/json; charset=utf-8");
    
    $backend_admin_url = "https://kroniclez-tv-menu-2cmv.onrender.com" . $rel_path;
    if (!empty($_SERVER['QUERY_STRING'])) {
        $backend_admin_url .= '?' . $_SERVER['QUERY_STRING'];
    }
    
    $method = $_SERVER['REQUEST_METHOD'];
    if ($method === 'POST') {
        $post_body = file_get_contents('php://input');
        
        // Also save override locally to product_overrides.json
        $payload = json_decode($post_body, true);
        if ($payload && isset($payload['pin']) && $payload['pin'] === '4200') {
            $ov_file = __DIR__ . '/product_overrides.json';
            $local_ov = file_exists($ov_file) ? json_decode(file_get_contents($ov_file), true) : [
                'species_overrides' => [],
                'highlight_overrides' => [],
                'thc_overrides' => [],
                'category_overrides' => []
            ];
            if (!is_array($local_ov)) {
                $local_ov = ['species_overrides' => [], 'highlight_overrides' => [], 'thc_overrides' => [], 'category_overrides' => []];
            }
            
            $action = $payload['action'] ?? '';
            $pattern = strtolower(trim($payload['pattern'] ?? ''));
            $val = strtoupper(trim($payload['value'] ?? ''));
            
            if ($action === 'set_species' && $pattern) {
                $local_ov['species_overrides'][$pattern] = $val;
            } elseif ($action === 'set_highlight' && $pattern) {
                if (in_array($val, ['NONE', 'REGULAR', 'STANDARD'])) {
                    unset($local_ov['highlight_overrides'][$pattern]);
                } else {
                    $local_ov['highlight_overrides'][$pattern] = $val;
                }
            } elseif ($action === 'set_category' && $pattern) {
                if (in_array($val, ['DEFAULT', 'RESET', 'NONE'])) {
                    unset($local_ov['category_overrides'][$pattern]);
                } else {
                    $local_ov['category_overrides'][$pattern] = $val;
                }
            } elseif ($action === 'delete_all_for_pattern' && $pattern) {
                foreach (['species_overrides', 'highlight_overrides', 'thc_overrides', 'category_overrides'] as $grp) {
                    if (isset($local_ov[$grp]) && is_array($local_ov[$grp])) {
                        foreach (array_keys($local_ov[$grp]) as $k) {
                            if ($k === $pattern || strpos($k, $pattern) !== false || strpos($pattern, $k) !== false) {
                                unset($local_ov[$grp][$k]);
                            }
                        }
                    }
                }
            } elseif ($action === 'import_overrides' && !empty($payload['overrides']) && is_array($payload['overrides'])) {
                foreach (['species_overrides', 'highlight_overrides', 'thc_overrides', 'category_overrides'] as $grp) {
                    if (isset($payload['overrides'][$grp]) && is_array($payload['overrides'][$grp])) {
                        $local_ov[$grp] = array_merge($local_ov[$grp] ?? [], $payload['overrides'][$grp]);
                    }
                }
            }
            $local_ov['last_updated'] = date('c');
            @file_put_contents($ov_file, json_encode($local_ov, JSON_PRETTY_PRINT));
        }

        $opts = [
            'http' => [
                'method' => 'POST',
                'header' => "Content-Type: application/json\r\n",
                'content' => $post_body,
                'timeout' => 9
            ]
        ];
        $resp = @file_get_contents($backend_admin_url, false, stream_context_create($opts));
        
        // Invalidate local disk caches immediately when an override is saved
        for ($s = 1; $s <= 3; $s++) {
            $cf = sys_get_temp_dir() . "/kroniclez_tv_feed_s{$s}.json";
            if (file_exists($cf)) @unlink($cf);
        }
        
        if ($resp) {
            echo $resp;
        } else {
            echo json_encode(["success" => true, "message" => "Override saved to Hostinger local storage!"]);
        }
        exit;
    } else {
        $resp = @file_get_contents($backend_admin_url);
        if ($resp) {
            echo $resp;
        } else {
            $ov_file = __DIR__ . '/product_overrides.json';
            if (file_exists($ov_file)) {
                $local_ov = json_decode(file_get_contents($ov_file), true);
                echo json_encode(["success" => true, "overrides" => $local_ov]);
            } else {
                echo json_encode(["success" => false, "message" => "Sync server connecting..."]);
            }
        }
        exit;
    }
}

// --------------------------------------------------------------------------
// 4. Default: Serve TV Menu Board (static/index.html with pre-injected state)
// --------------------------------------------------------------------------
$index_file = __DIR__ . '/static/index.html';
if (!file_exists($index_file)) {
    http_response_code(404);
    echo "Error: static/index.html was not found. Please ensure the static/ folder is uploaded.";
    exit;
}

$html = file_get_contents($index_file);

// Inject initial screen configuration
$script_injection = "<script id='tv-preloaded-data'>\n";
$script_injection .= "window.__INITIAL_SCREEN_ID__ = {$screen};\n";
$script_injection .= "</script>\n</head>";
$html = str_replace('</head>', $script_injection, $html);

// Dynamic asset cache-busting
$cache_buster = '?v=57_' . time();
$html = preg_replace('/tv_menu\.css\?v=[^\s"\'>]+/', 'tv_menu.css' . $cache_buster, $html);
$html = preg_replace('/tv_menu\.js\?v=[^\s"\'>]+/', 'tv_menu.js' . $cache_buster, $html);

// Adjust asset paths for subfolder deployment (e.g. /kwc/static/...)
$asset_base = ($base_dir !== '') ? $base_dir . '/static/' : '/static/';
$html = str_replace('/static/', $asset_base, $html);

header("Content-Type: text/html; charset=utf-8");
echo $html;
exit;
