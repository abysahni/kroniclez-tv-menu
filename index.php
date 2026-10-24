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
// 1. API Endpoint: Live TV Menu Feed (/api/tv-menu or /api/tv_menu_feed.php)
// --------------------------------------------------------------------------
if ($rel_path === '/api/tv-menu' || $rel_path === '/api/tv_menu_feed.php' || isset($_GET['api'])) {
    $_GET['api'] = '1';
    $_GET['screen'] = $screen;
    if (file_exists(__DIR__ . '/tv_menu.php')) {
        require __DIR__ . '/tv_menu.php';
        exit;
    }
    
    header("Content-Type: application/json; charset=utf-8");
    echo json_encode([
        "success" => false, 
        "total_in_stock" => 0,
        "message" => "tv_menu.php engine not found"
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
    $ov_file = __DIR__ . '/product_overrides.json';
    
    // 3a. Admin Inventory Endpoint
    if ($rel_path === '/api/admin/inventory') {
        $pin = $_GET['pin'] ?? ($_POST['pin'] ?? '');
        if ($pin !== '4200') {
            http_response_code(401);
            echo json_encode(["success" => false, "message" => "Unauthorized: Invalid Staff PIN"]);
            exit;
        }

        if (!defined('TV_MENU_FUNCS_ONLY')) define('TV_MENU_FUNCS_ONLY', true);
        if (file_exists(__DIR__ . '/tv_menu.php')) {
            require_once __DIR__ . '/tv_menu.php';
        }
        
        global $TENDY_CONFIG, $POTENCY_MAP;
        $raw_items = function_exists('fetchTendyInventory') && isset($TENDY_CONFIG) ? fetchTendyInventory($TENDY_CONFIG) : [];
        $local_ov = file_exists($ov_file) ? json_decode(file_get_contents($ov_file), true) : [];
        if (!is_array($local_ov)) $local_ov = [];
        
        $species_ov = $local_ov['species_overrides'] ?? [];
        $highlight_ov = $local_ov['highlight_overrides'] ?? [];
        $thc_ov = $local_ov['thc_overrides'] ?? [];
        $cat_ov = $local_ov['category_overrides'] ?? [];

        $admin_items = [];
        foreach ($raw_items as $it) {
            $cat = $it['categoryName'] ?? ($it['category']['name'] ?? '');
            $name = $it['name'] ?? '';
            $brand = $it['brand']['name'] ?? (is_string($it['brand'] ?? null) ? $it['brand'] : '');
            $pricing = $it['productPricing'] ?? [];
            $price = floatval($pricing['sale_price'] ?? 0.0);
            $full_name = trim("$brand $name");
            
            $cat_l = strtolower($cat);
            if (strpos($cat_l, 'pre-roll') !== false || strpos($cat_l, 'preroll') !== false || strpos($cat_l, 'blunt') !== false) {
                $screen_num = 1;
            } elseif (strpos($cat_l, 'flower') !== false || strpos($cat_l, 'vape') !== false || strpos($cat_l, 'cartridge') !== false) {
                $screen_num = 2;
            } else {
                $screen_num = 3;
            }

            $spec = function_exists('getExactStrain') ? getExactStrain($it) : 'HYBRID';
            $full_l = strtolower($full_name);
            $name_l = strtolower($name);
            $sp_val = null;
            $hl_val = null;
            $cat_val = null;
            foreach ($species_ov as $k => $v) {
                if ($k !== '' && (strpos($full_l, $k) !== false || strpos($name_l, $k) !== false)) { $sp_val = $v; break; }
            }
            foreach ($highlight_ov as $k => $v) {
                if ($k !== '' && (strpos($full_l, $k) !== false || strpos($name_l, $k) !== false)) { $hl_val = $v; break; }
            }
            foreach ($cat_ov as $k => $v) {
                if ($k !== '' && (strpos($full_l, $k) !== false || strpos($name_l, $k) !== false)) { $cat_val = $v; break; }
            }

            $pot = function_exists('lookupPotency') && isset($POTENCY_MAP) ? lookupPotency($name, $brand, $POTENCY_MAP, '28.0%') : ['thc' => '28.0%', 'cbd' => '<1.0%'];

            $admin_items[] = [
                'id' => strval($it['id'] ?? ($it['barcode'] ?? $name)),
                'name' => $name,
                'brand' => $brand,
                'full_name' => $full_name,
                'category' => $cat,
                'screen' => $screen_num,
                'species' => $sp_val ?: $spec,
                'thc' => $pot['thc'],
                'price' => $price,
                'tag' => $hl_val,
                'is_sale' => false,
                'has_override' => boolval($sp_val || $hl_val || $cat_val),
                'highlight_value' => $hl_val
            ];
        }

        echo json_encode([
            'success' => true,
            'items' => $admin_items,
            'overrides' => $local_ov
        ]);
        exit;
    }
    
    // 3b. Admin Override POST Endpoint
    $method = $_SERVER['REQUEST_METHOD'];
    if ($method === 'POST') {
        $post_body = file_get_contents('php://input');
        $payload = json_decode($post_body, true);
        
        if (!$payload || !isset($payload['pin']) || $payload['pin'] !== '4200') {
            http_response_code(401);
            echo json_encode(["success" => false, "message" => "Unauthorized: Invalid Staff PIN"]);
            exit;
        }

        $local_ov = file_exists($ov_file) ? json_decode(file_get_contents($ov_file), true) : [
            'species_overrides' => [],
            'highlight_overrides' => [],
            'thc_overrides' => [],
            'category_overrides' => [],
            'screen_text_scale' => ['1' => 98, '2' => 100, '3' => 100]
        ];
        if (!is_array($local_ov)) {
            $local_ov = ['species_overrides' => [], 'highlight_overrides' => [], 'thc_overrides' => [], 'category_overrides' => [], 'screen_text_scale' => ['1' => 98, '2' => 100, '3' => 100]];
        }
        
        $action = $payload['action'] ?? '';
        $pattern = strtolower(trim($payload['pattern'] ?? ''));
        $val = strtoupper(trim($payload['value'] ?? ''));
        
        if ($action === 'set_text_scale') {
            $scr = isset($payload['screen']) ? strval($payload['screen']) : '1';
            $sval = isset($payload['value']) ? intval($payload['value']) : 100;
            $sval = max(70, min(130, $sval));
            if (!isset($local_ov['screen_text_scale'])) $local_ov['screen_text_scale'] = ['1' => 98, '2' => 100, '3' => 100];
            $local_ov['screen_text_scale'][$scr] = $sval;
        } elseif ($action === 'set_species' && $pattern) {
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
            foreach (['species_overrides', 'highlight_overrides', 'thc_overrides', 'category_overrides', 'screen_text_scale'] as $grp) {
                if (isset($payload['overrides'][$grp]) && is_array($payload['overrides'][$grp])) {
                    $local_ov[$grp] = array_merge($local_ov[$grp] ?? [], $payload['overrides'][$grp]);
                }
            }
        }
        $local_ov['last_updated'] = date('c');
        @file_put_contents($ov_file, json_encode($local_ov, JSON_PRETTY_PRINT));

        // Invalidate temporary inventory cache files
        $tmp_files = glob(sys_get_temp_dir() . '/tendy_tv_cache_*');
        if (is_array($tmp_files)) {
            foreach ($tmp_files as $f) { @unlink($f); }
        }
        for ($s = 1; $s <= 3; $s++) {
            $cf = sys_get_temp_dir() . "/kroniclez_tv_feed_s{$s}.json";
            if (file_exists($cf)) @unlink($cf);
        }

        echo json_encode([
            "success" => true,
            "message" => "Override saved successfully!",
            "screen_text_scale" => $local_ov['screen_text_scale'] ?? null
        ]);
        exit;
    } else {
        // GET /api/admin/overrides
        $local_ov = file_exists($ov_file) ? json_decode(file_get_contents($ov_file), true) : [];
        echo json_encode(["success" => true, "overrides" => $local_ov]);
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

$ov_file = __DIR__ . '/product_overrides.json';
$screen_text_scale = ($screen === 1) ? 98 : 100;
if (file_exists($ov_file)) {
    $ov_data = json_decode(@file_get_contents($ov_file), true);
    if (!empty($ov_data['screen_text_scale']) && isset($ov_data['screen_text_scale'][strval($screen)])) {
        $screen_text_scale = intval($ov_data['screen_text_scale'][strval($screen)]);
    }
}

// Inject initial screen configuration & text scale
$script_injection = "<script id='tv-preloaded-data'>\n";
$script_injection .= "window.__INITIAL_SCREEN_ID__ = {$screen};\n";
$script_injection .= "window.__INITIAL_TEXT_SCALE__ = {$screen_text_scale};\n";
$script_injection .= "</script>\n</head>";
$html = str_replace('</head>', $script_injection, $html);

// Dynamic asset cache-busting
$cache_buster = '?v=60_' . time();
$html = preg_replace('/tv_menu\.css\?v=[^\s"\'>]+/', 'tv_menu.css' . $cache_buster, $html);
$html = preg_replace('/tv_menu\.js\?v=[^\s"\'>]+/', 'tv_menu.js' . $cache_buster, $html);

// Adjust asset paths for subfolder deployment (e.g. /kwc/static/...)
$asset_base = ($base_dir !== '') ? $base_dir . '/static/' : '/static/';
$html = str_replace('/static/', $asset_base, $html);

header("Content-Type: text/html; charset=utf-8");
echo $html;
exit;
