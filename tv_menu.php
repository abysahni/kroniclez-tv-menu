<?php
/**
 * Kroniclez Digital TV Menu Board - Production Standalone PHP Engine
 * Compatible with Hostinger / cPanel / Apache / Nginx (PHP 7.4 - 8.3+)
 * 
 * Routes:
 *   - /tv_menu.php?screen=1  -> Screen 1: Pre-Rolls & Infused
 *   - /tv_menu.php?screen=2  -> Screen 2: Vapes & Flower
 *   - /tv_menu.php?screen=3  -> Screen 3: Edibles, Drinks & Concentrates
 *   - /tv_menu.php?api=1&screen=1 -> Live JSON API Feed (for 25s background polling)
 */

// Disable browser caching so TVs always display live prices and inventory
header("Cache-Control: no-cache, no-store, must-revalidate");
header("Pragma: no-cache");
header("Expires: 0");

// Configuration
$TENDY_CONFIG = [
    'product_api_url' => 'https://product.api.tendypos.net/api/inventory-snapshots/getReportData',
    'auth_token'      => 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJidXNpbmVzc0lkIjoiZGIzODQ1NzItMTZkMi00NWE3LTgwZmEtODczMGFlODllMTdlIiwibG9jYXRpb25JZCI6ImRjOTQ0OWE3LTk1M2ItNDdhMS05ZGNjLWZmZTNjNjRiZThjOSIsInVzZXJJZCI6IjhiMGVlYTE4LTgyNDgtNGUzYS05ODFhLTM1Yzc1MmY0NzIxOSIsImlhdCI6MTc4NzYyNzI3OSwianRpIjoiMTc4NzYyNzI3OTcwOSJ9.1NGP779FBA0VEw25zr3qj00X4q7KOHwwmWchIqE12rQ',
    'product_token'   => 'laymXDAzvJ8lW24jNxZKivmkTFnZBi42',
    'location_id'     => 'dc9449a7-953b-47a1-9dcc-ffe3c64be8c9',
    $store_param = isset($_GET['store']) ? strtolower(trim($_GET['store'])) : 'waterloo';
$is_waterloo = ($store_param !== 'kitchener' && $store_param !== '1');
$current_store_name = $is_waterloo ? 'Kroniclez - Waterloo' : 'Kroniclez - Kitchener';
$current_loc_title  = $is_waterloo ? 'WATERLOO' : 'KITCHENER';
$current_qr_svg     = $is_waterloo ? 'static/qr_code_waterloo.svg' : 'static/qr_code.svg';
$current_qr_title   = $is_waterloo ? '📱 WATERLOO PICKUP' : '📱 EXPRESS PICKUP';
$current_qr_sub     = $is_waterloo ? '62 Balsam St • Scan to Order' : 'Scan to Order on Phone';

$TENDY_CONFIG = [
    'product_api_url' => 'https://product.api.tendypos.net/api/inventory-snapshots/getReportData',
    'auth_token'      => 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJidXNpbmVzc0lkIjoiZGIzODQ1NzItMTZkMi00NWE3LTgwZmEtODczMGFlODllMTdlIiwibG9jYXRpb25JZCI6ImRjOTQ0OWE3LTk1M2ItNDdhMS05ZGNjLWZmZTNjNjRiZThjOSIsInVzZXJJZCI6IjhiMGVlYTE4LTgyNDgtNGUzYS05ODFhLTM1Yzc1MmY0NzIxOSIsImlhdCI6MTc4NzYyNzI3OSwianRpIjoiMTc4NzYyNzI3OTcwOSJ9.1NGP779FBA0VEw25zr3qj00X4q7KOHwwmWchIqE12rQ',
    'product_token'   => 'laymXDAzvJ8lW24jNxZKivmkTFnZBi42',
    'location_id'     => 'dc9449a7-953b-47a1-9dcc-ffe3c64be8c9',
    'store_name'      => $current_store_name,
    'cache_ttl'       => 25 // seconds
];

// Determine screen and mode
$screen = isset($_GET['screen']) ? intval($_GET['screen']) : 1;
if ($screen < 1 || $screen > 3) $screen = 1;
$is_api = isset($_GET['api']) && $_GET['api'] == '1';

// Potency & Strain Database
$REGULAR_PRICES = [
    "00882464077381" => 22.99,
    "102323_10x0.35g___" => 22.99,
    "pineapple nuken pre-rolls" => 22.99,
    "00843087001733" => 9.52,
    "105400_2x1g___" => 9.52,
    "sativa pre-roll 2x1g" => 9.52,
    "00843087003928" => 9.94,
    "105059_2x1g___" => 9.94,
    "indica pre-roll 2x1g" => 9.94,
    "00835861000353" => 6.65,
    "103234_1x1g___" => 6.65,
    "zombie kush pre-roll 1x1g" => 6.65,
    "00684074001080" => 7.35,
    "110332_1x1g___" => 7.35,
    "dutchy blunt 1x1g" => 7.35,
    "00628120720709" => 66.66,
    "108741_14g___" => 66.66,
    "moon drifter 14g" => 66.66,
    "00800129905541" => 40.54,
    "108743_7g___" => 40.54,
    "blueberry muffinz 7g" => 40.54,
    "00628186000920" => 45.65,
    "305278_1.2g___" => 45.65,
    "rainbow melon boosted aio 1.2g" => 45.65,
    "00628090650914" => 36.71,
    "303100_1g___" => 36.71,
    "poppin peach live rosin 510 1g" => 36.71,
    "00628045101331" => 32.9,
    "300641_1g___" => 32.9,
    "mosa x blood orange 510 1g" => 32.9,
    "00826061000519" => 39.58,
    "309559_0.95g___" => 39.58,
    "peach lemonade disposable pen 0.95g" => 39.58,
    "00826061000441" => 38.88,
    "309532_0.95g___" => 38.88,
    "watermelon ice disposable pen 0.95g" => 38.88,
    "00990309000729" => 31.78,
    "307198_0.95g___" => 31.78,
    "high potency 92+ hawaiian za 510 0.95g" => 31.78,
    "00629108384227" => 44.53,
    "308085_1.2g___" => 44.53,
    "cherry liquid diamond 510 1.2g" => 44.53,
    "00628045101829" => 35.94,
    "303135_1g___" => 35.94,
    "blue zello liquid diamond 510 1g" => 35.94,
    "00628110180247" => 48.91,
    "113126_50 caps___" => 48.91,
    "spark thc moonrocks 50 caps" => 48.91,
];

$POTENCY_MAP = [
    // Pre-rolls
    "animal face" => ["thc" => "31.5%", "cbd" => "<1.0%"],
    "white rntz" => ["thc" => "29.5%", "cbd" => "<1.0%"],
    "pink kush" => ["thc" => "27.0%", "cbd" => "<1.0%"],
    "wes coast kush" => ["thc" => "32.0%", "cbd" => "<1.0%"],
    "dank craft space cake" => ["thc" => "33.0%", "cbd" => "<1.0%"],
    "redeecan wappa" => ["thc" => "24.5%", "cbd" => "<1.0%"],
    "ghost og" => ["thc" => "28.0%", "cbd" => "<1.0%"],
    "death bubba" => ["thc" => "29.0%", "cbd" => "<1.0%"],
    "gelato 33" => ["thc" => "28.5%", "cbd" => "<1.0%"],
    "mac 1" => ["thc" => "27.5%", "cbd" => "<1.0%"],
    "slurricane" => ["thc" => "26.5%", "cbd" => "<1.0%"],
    "kush mints" => ["thc" => "30.0%", "cbd" => "<1.0%"],
    "sour diesel" => ["thc" => "26.0%", "cbd" => "<1.0%"],
    "cuban linx" => ["thc" => "29.0%", "cbd" => "<1.0%"],
    "jack herer" => ["thc" => "24.0%", "cbd" => "<1.0%"],
    "jean guy" => ["thc" => "25.5%", "cbd" => "<1.0%"],
    "ultra sour" => ["thc" => "27.0%", "cbd" => "<1.0%"],
    "strawberry cough" => ["thc" => "38.5%", "cbd" => "<1.0%"],
    "pineapple express" => ["thc" => "42.0%", "cbd" => "<1.0%"],
    "macchiato gold" => ["thc" => "56.0%", "cbd" => "<1.0%"],
    "blue dream" => ["thc" => "50.5%", "cbd" => "<1.0%"],
    "baby jeeter" => ["thc" => "40.0%", "cbd" => "<1.0%"],
    "big bang berry" => ["thc" => "61.0%", "cbd" => "<1.0%"],
    "fully charged party pack" => ["thc" => "40.0%", "cbd" => "<1.0%"],
    "heavy hitter" => ["thc" => "50.0%", "cbd" => "<1.0%"],
    "diamond infused strawberry" => ["thc" => "54.0%", "cbd" => "<1.0%"],
    "red jasper" => ["thc" => "40.5%", "cbd" => "<1.0%"],
    "northern lights" => ["thc" => "60.0%", "cbd" => "<1.0%"],
    // Vapes
    "blue zello" => ["thc" => "98.0%", "cbd" => "<1.0%"],
    "hawaiian za" => ["thc" => "97.5%", "cbd" => "<1.0%"],
    "wild berry" => ["thc" => "92.5%", "cbd" => "<1.0%"],
    "jungle fruit" => ["thc" => "94.0%", "cbd" => "<1.0%"],
    "mango sour" => ["thc" => "82.0%", "cbd" => "<1.0%"],
    "cloudberry" => ["thc" => "98.0%", "cbd" => "<1.0%"],
    "strawberry lemonade" => ["thc" => "93.0%", "cbd" => "<1.0%"],
    "blueberry octane" => ["thc" => "26.0%", "cbd" => "<1.0%"],
    "poppin peach" => ["thc" => "87.5%", "cbd" => "<1.0%"],
    "acapulco gold" => ["thc" => "90.0%", "cbd" => "<1.0%"],
    "blue ragg fuel cell" => ["thc" => "92.0%", "cbd" => "<1.0%"],
    // Edibles & Drinks
    "molly's pineapple orange" => ["thc" => "10mg", "cbd" => "10mg"],
    "deep space orange kraze" => ["thc" => "10mg", "cbd" => "0mg"],
    "collective project" => ["thc" => "10mg", "cbd" => "10mg"],
    "xmg blue raspberry" => ["thc" => "10mg", "cbd" => "0mg"],
    "versus neon rush" => ["thc" => "10mg", "cbd" => "0mg"],
    "sweet justice" => ["thc" => "10mg", "cbd" => "0mg"],
    "bhang" => ["thc" => "10mg", "cbd" => "10mg"],
    "chowie wowie" => ["thc" => "10mg", "cbd" => "10mg"],
    "sourz" => ["thc" => "10mg", "cbd" => "0mg"],
    "pearls" => ["thc" => "10mg", "cbd" => "10mg"],
    "canna bops" => ["thc" => "10mg", "cbd" => "0mg"],
    "spinach fully blasted" => ["thc" => "10mg", "cbd" => "0mg"],
    "monjour" => ["thc" => "2.5mg", "cbd" => "20mg"],
    "shatterizer shatter" => ["thc" => "78.0%", "cbd" => "<1.0%"],
    "community live rosin" => ["thc" => "74.0%", "cbd" => "<1.0%"],
    "wholehemp cbd cream" => ["thc" => "0mg", "cbd" => "500mg"],
    "aspire spark thc moonrocks" => ["thc" => "500mg", "cbd" => "0mg"]
];

function fetchTendyInventory($config) {
    $cache_file = sys_get_temp_dir() . '/tendy_tv_cache_' . md5($config['location_id']) . '.json';
    
    // Check local disk cache
    if (file_exists($cache_file) && (time() - filemtime($cache_file) < $config['cache_ttl'])) {
        $raw = file_get_contents($cache_file);
        $data = json_decode($raw, true);
        if (is_array($data) && count($data) > 0) return $data;
    }

    $payload = json_encode([
        'locationId' => $config['location_id'],
        'page' => 1,
        'limit' => 500,
        'status' => 'IN_STOCK'
    ]);

    $headers = [
        'Content-Type: application/json',
        'Authorization: ' . $config['auth_token'],
        'token: ' . $config['product_token'],
        'User-Agent: Kroniclez-TV-Menu/2.0'
    ];

    $ch = curl_init($config['product_api_url']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);

    $resp = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($http_code == 200 && $resp) {
        $res = json_decode($resp, true);
        $items = isset($res['data']) ? $res['data'] : (isset($res['items']) ? $res['items'] : []);
        if (is_array($items) && count($items) > 0) {
            file_put_contents($cache_file, json_encode($items));
            return $items;
        }
    }

    // Fallback to expired cache if API is temporarily unreachable
    if (file_exists($cache_file)) {
        return json_decode(file_get_contents($cache_file), true);
    }

    return [];
}

function cleanTitle($name, $brand = '', $variant = '', $screen = 1) {
    $b = trim(strtoupper($brand));
    $n = trim($name);
    $v = trim($variant);

    $n = preg_replace('/\s+Pre-Rolls?/i', '', $n);
    $n = preg_replace('/\s+510 Thread Cartridge/i', '', $n);
    $n = preg_replace('/\s+510 Thread/i', '', $n);
    $n = preg_replace('/\s+510 Cartridge/i', '', $n);
    $n = preg_replace('/\s+510 Vape Cart/i', '', $n);
    $n = preg_replace('/\s+All-in-One Vape/i', '', $n);
    $n = preg_replace('/\s+All-in-One/i', '', $n);
    $n = preg_replace('/\s+Disposable/i', '', $n);
    $n = preg_replace('/\s+Dried Flower/i', '', $n);
    $n = preg_replace('/\s*-\s*/', ' ', $n);

    if ($v !== '') {
        $n = str_ireplace(["($v)", "- $v", $v], '', $n);
        $n = trim($n);
        $final = $b ? "$b • $n $v" : "$n $v";
    } else {
        $final = $b ? "$b • $n" : $n;
    }
    return preg_replace('/\s+/', ' ', trim($final));
}

function lookupPotency($name, $brand, $map, $default_thc = '28%') {
    $full = strtolower("$brand $name");
    foreach ($map as $k => $pot) {
        if (strpos($full, $k) !== false) return $pot;
    }
    return ["thc" => $default_thc, "cbd" => "<1.0%"];
}

function isHappyHourActive() {
    $tz = new DateTimeZone('America/Toronto');
    $now = new DateTime('now', $tz);
    $hour = (int)$now->format('H');
    return ($hour >= 13 && $hour < 16);
}

function classifyStrain($name, $brand) {
    $full = strtolower("$brand $name");
    
    // Explicit Sativa overrides
    if (strpos($full, "blueberry dream") !== false) return "SATIVA";
    if (strpos($full, "pink rozay") !== false) return "SATIVA";
    if (strpos($full, "cherry boat") !== false) return "SATIVA";
    if (strpos($full, "juicy blunt") !== false) return "SATIVA";
    if (strpos($full, "fruit punch") !== false) return "SATIVA";
    if (strpos($full, "double up") !== false || strpos($full, "double dutchies") !== false) return "SATIVA";
    if (strpos($full, "pineapple nuken") !== false) return "SATIVA";

    // Explicit Hybrid overrides
    if (strpos($full, "10th planet") !== false) return "HYBRID";
    if (strpos($full, "sour kush") !== false) return "HYBRID";
    if (strpos($full, "blue magic") !== false) return "HYBRID";
    if (strpos($full, "panama gold") !== false) return "HYBRID";
    if (strpos($full, "peggys puff") !== false) return "HYBRID";
    if (strpos($full, "sgt. pineapple") !== false || strpos($full, "sgt pineapple") !== false) return "HYBRID";
    if (strpos($full, "plg #7") !== false || strpos($full, "pink lemon gas") !== false) return "HYBRID";

    // Explicit Indica overrides
    if (strpos($full, "junior j") !== false) return "INDICA";
    if (strpos($full, "animal rntz") !== false) return "INDICA";
    if (strpos($full, "diesel pocket puffs") !== false) return "INDICA";
    if (strpos($full, "bahama berry") !== false) return "INDICA";
    if (strpos($full, "dutchy") !== false) return "INDICA";

    // Generic keyword fallback
    if (preg_replace('/(sativa|lemon|sour|haze|diesel|tangie|mango|sunshine|cough|acapulco|jack|linx|grapefruit|shockwave|sticky)/', '', $full) !== $full) return 'SATIVA';
    if (preg_replace('/(indica|kush|pink|purple|bubba|berry|og|punch|sleep|lights|zello|venom|freeze|tiger|cherry)/', '', $full) !== $full) return 'INDICA';
    return 'HYBRID';
}

// Build structured menus
$raw = fetchTendyInventory($TENDY_CONFIG);

if ($screen === 1) {
    // Screen 1: Pre-Rolls
    $ind = []; $hyb = []; $sat = []; $inf = []; $inf_ind = []; $inf_hyb = []; $inf_sat = [];
    foreach ($raw as $it) {
        $cat = isset($it['category']['name']) ? $it['category']['name'] : '';
        $name = isset($it['name']) ? $it['name'] : '';
        $brand = isset($it['brand']['name']) ? $it['brand']['name'] : '';
        $var = isset($it['variantName']) ? $it['variantName'] : '';
        $pricing = isset($it['productPricing']) ? $it['productPricing'] : [];
        $price = isset($pricing['sale_price']) ? floatval($pricing['sale_price']) : 0.0;
        $stock = isset($pricing['stock']) ? intval($pricing['stock']) : 0;
        if ($stock <= 0 || stripos($cat, 'accessories') !== false) continue;
        if (stripos($cat, 'pre-roll') !== false || stripos($cat, 'cartridge') !== false || stripos($cat, 'disposable') !== false || stripos($cat, 'flower') !== false || stripos($cat, 'milled') !== false) continue;
        if (stripos($name, 'joint') !== false || stripos($name, 'blunt') !== false || stripos($name, 'vape') !== false || stripos($name, 'cartridge') !== false || stripos($name, '510 ') !== false) continue;

        $p_title = cleanTitle($name, $brand, $var, 1);
        $pot = lookupPotency($name, $brand, $POTENCY_MAP, '28.5%');
        $sku_id = isset($it['id']) ? strval($it['id']) : (isset($it['sku']) ? strval($it['sku']) : '');
        $cost = isset($pricing["cost"]) ? floatval($pricing["cost"]) : 0.0;
        $markup = isset($pricing["markup"]) ? floatval($pricing["markup"]) : 0.0;
        $reg_p = ($cost > 0 && $markup > 0) ? round($cost * (1.0 + ($markup / 100.0)), 2) : $price;
        if ($reg_p > $price && ($reg_p - $price) >= 0.05) {
            $is_promo = true;
            $old_price = $reg_p;
        } else {
            $is_promo = false;
            $old_price = null;
        }
        $entry = [
            'product_name' => $p_title,
            'price' => $price,
            'old_price' => $old_price,
            'brand' => $brand,
            'thc' => $pot['thc'],
            'cbd' => $pot['cbd'],
            'is_sale' => $is_promo
        ];

        if (stripos($cat, 'Infused') !== false || stripos($name, 'infused') !== false) {
            $spec = classifyStrain($name, $brand);
            $entry['species'] = $spec;
            if ($spec === 'SATIVA') $inf_sat[] = $entry;
            elseif ($spec === 'INDICA') $inf_ind[] = $entry;
            else $inf_hyb[] = $entry;
            $inf[] = $entry;
        } elseif (stripos($cat, 'Pre-Roll') !== false) {
            $spec = classifyStrain($name, $brand);
            $entry['species'] = $spec;
            if ($spec === 'INDICA') $ind[] = $entry;
            elseif ($spec === 'SATIVA') $sat[] = $entry;
            else $hyb[] = $entry;
        }
    }
    $structured = [
        'indica' => ['title' => 'INDICA', 'color' => 'indica', 'items' => $ind],
        'hybrid' => ['title' => 'HYBRID & BLENDS', 'color' => 'hybrid', 'items' => $hyb],
        'sativa' => ['title' => 'SATIVA', 'color' => 'sativa', 'items' => $sat],
        'infused' => [
            'title' => 'INFUSED PRE-ROLLS',
            'color' => 'infused',
            'items' => $inf,
            'indica_items' => $inf_ind,
            'hybrid_items' => $inf_hyb,
            'sativa_items' => $inf_sat
        ]
    ];
} elseif ($screen === 2) {
    // Screen 2: Flower & Vapes
    $f_ind = []; $f_ind_m = []; $f_hyb = []; $f_hyb_m = []; $f_sat = []; $f_sat_m = [];
    $v_ind = []; $v_hyb = []; $v_sat = []; $d_ind = []; $d_hyb = []; $d_sat = [];

    foreach ($raw as $it) {
        $cat = isset($it['category']['name']) ? $it['category']['name'] : '';
        $name = isset($it['name']) ? $it['name'] : '';
        $brand = isset($it['brand']['name']) ? $it['brand']['name'] : '';
        $var = isset($it['variantName']) ? $it['variantName'] : '';
        $pricing = isset($it['productPricing']) ? $it['productPricing'] : [];
        $price = isset($pricing['sale_price']) ? floatval($pricing['sale_price']) : 0.0;
        $stock = isset($pricing['stock']) ? intval($pricing['stock']) : 0;
        if ($stock <= 0 || stripos($cat, 'accessories') !== false) continue;
        if (stripos($cat, 'pre-roll') !== false || stripos($cat, 'cartridge') !== false || stripos($cat, 'disposable') !== false || stripos($cat, 'flower') !== false || stripos($cat, 'milled') !== false) continue;
        if (stripos($name, 'joint') !== false || stripos($name, 'blunt') !== false || stripos($name, 'vape') !== false || stripos($name, 'cartridge') !== false || stripos($name, '510 ') !== false) continue;

        $p_title = cleanTitle($name, $brand, $var, 2);
        $pot = lookupPotency($name, $brand, $POTENCY_MAP, '88.0%');
        $n_low = strtolower($name);
        $is_promo = (strpos($n_low, 'sapphire kush') === false && strpos($n_low, 'dragon cake') === false);
        $old_price = ($is_promo && $price > 0) ? round($price / 0.90, 2) : null;
        $entry = [
            'product_name' => $p_title,
            'price' => $price,
            'old_price' => $old_price,
            'brand' => $brand,
            'thc' => $pot['thc'],
            'cbd' => $pot['cbd'],
            'is_sale' => $is_promo
        ];

        if (stripos($cat, 'Dried Flower') !== false || stripos($cat, 'Milled') !== false) {
            $spec = classifyStrain($name, $brand);
            $entry['species'] = $spec;
            $is_milled = stripos($cat, 'Milled') !== false || stripos($name, 'milled') !== false;
            if ($spec === 'INDICA') { if ($is_milled) $f_ind_m[] = $entry; else $f_ind[] = $entry; }
            elseif ($spec === 'SATIVA') { if ($is_milled) $f_sat_m[] = $entry; else $f_sat[] = $entry; }
            else { if ($is_milled) $f_hyb_m[] = $entry; else $f_hyb[] = $entry; }
        } elseif (stripos($cat, '510') !== false || (stripos($cat, 'Cartridge') !== false && stripos($cat, 'Disposable') === false)) {
            $spec = classifyStrain($name, $brand);
            $entry['species'] = $spec;
            if ($spec === 'INDICA') $v_ind[] = $entry;
            elseif ($spec === 'SATIVA') $v_sat[] = $entry;
            else $v_hyb[] = $entry;
        } elseif (stripos($cat, 'Disposable') !== false || stripos($name, 'disposable') !== false || stripos($name, 'all-in-one') !== false) {
            $spec = classifyStrain($name, $brand);
            $entry['species'] = $spec;
            if ($spec === 'INDICA') $d_ind[] = $entry;
            elseif ($spec === 'SATIVA') $d_sat[] = $entry;
            else $d_hyb[] = $entry;
        }
    }
    $structured = [
        'flower' => [
            'indica_dried' => ['title' => 'Indica Dried Flower', 'items' => $f_ind],
            'indica_milled' => ['title' => 'Indica Milled', 'items' => $f_ind_m],
            'hybrid_dried' => ['title' => 'Hybrid Dried Flower', 'items' => $f_hyb],
            'hybrid_milled' => ['title' => 'Hybrid Milled', 'items' => $f_hyb_m],
            'sativa_dried' => ['title' => 'Sativa Dried Flower', 'items' => $f_sat],
            'sativa_milled' => ['title' => 'Sativa Milled', 'items' => $f_sat_m]
        ],
        'vapes' => [
            'vapes_510_indica' => ['title' => '510 Indica', 'items' => $v_ind],
            'vapes_510_hybrid' => ['title' => '510 Hybrid', 'items' => $v_hyb],
            'vapes_510_sativa' => ['title' => '510 Sativa', 'items' => $v_sat],
            'disp_indica' => ['title' => 'Disposable Indica', 'items' => $d_ind],
            'disp_hybrid' => ['title' => 'Disposable Hybrid', 'items' => $d_hyb],
            'disp_sativa' => ['title' => 'Disposable Sativa', 'items' => $d_sat]
        ]
    ];
} else {
    // Screen 3: Edibles, Drinks & Concentrates
    $bev = []; $g_ind_hyb = []; $g_sat = []; $choc = []; $conc = []; $well = [];

    foreach ($raw as $it) {
        $cat = isset($it['category']['name']) ? $it['category']['name'] : '';
        $name = isset($it['name']) ? $it['name'] : '';
        $brand = isset($it['brand']['name']) ? $it['brand']['name'] : '';
        $var = isset($it['variantName']) ? $it['variantName'] : '';
        $pricing = isset($it['productPricing']) ? $it['productPricing'] : [];
        $price = isset($pricing['sale_price']) ? floatval($pricing['sale_price']) : 0.0;
        $stock = isset($pricing['stock']) ? intval($pricing['stock']) : 0;
        if ($stock <= 0 || stripos($cat, 'accessories') !== false) continue;
        if (stripos($cat, 'pre-roll') !== false || stripos($cat, 'cartridge') !== false || stripos($cat, 'disposable') !== false || stripos($cat, 'flower') !== false || stripos($cat, 'milled') !== false) continue;
        if (stripos($name, 'joint') !== false || stripos($name, 'blunt') !== false || stripos($name, 'vape') !== false || stripos($name, 'cartridge') !== false || stripos($name, '510 ') !== false) continue;

        $p_title = cleanTitle($name, $brand, $var, 3);
        $pot = lookupPotency($name, $brand, $POTENCY_MAP, '10mg');
        $spec = classifyStrain($name, $brand);
        $entry = [
            'product_name' => $p_title,
            'species' => $spec,
            'price' => $price,
            'brand' => $brand,
            'thc' => $pot['thc'],
            'cbd' => $pot['cbd'],
            'is_sale' => true
        ];

        if (stripos($cat, 'Beverage') !== false || stripos($cat, 'Drink') !== false) {
            $bev[] = $entry;
        } elseif (stripos($cat, 'Chocolate') !== false || stripos($name, 'chocolate') !== false) {
            $choc[] = $entry;
        } elseif (stripos($cat, 'Soft Chew') !== false || stripos($cat, 'Gummies') !== false || stripos($cat, 'Edible') !== false) {
            if ($spec === 'SATIVA') $g_sat[] = $entry;
            else $g_ind_hyb[] = $entry;
        } elseif (stripos($cat, 'Concentrate') !== false || stripos($cat, 'Extract') !== false || stripos($cat, 'Rosin') !== false || stripos($cat, 'Shatter') !== false) {
            $conc[] = $entry;
        } elseif (stripos($cat, 'Topical') !== false || stripos($cat, 'Oil') !== false || stripos($cat, 'Capsule') !== false) {
            $well[] = $entry;
        }
    }
    $structured = [
        'concentrates' => ['title' => 'CONCENTRATES & EXTRACTS', 'color' => 'gold', 'subtitle' => 'DIAMONDS • LIVE ROSIN • SHATTER', 'items' => $conc],
        'beverages' => ['title' => 'INFUSED BEVERAGES', 'color' => 'cyan', 'subtitle' => 'SPARKLING SODAS • ICED TEAS • TONICS', 'items' => $bev],
        'gummies_ind_hyb' => ['title' => 'SOFT CHEWS & GUMMIES', 'color' => 'pink', 'subtitle' => 'INDICA & HYBRID • ALL SIZES', 'items' => $g_ind_hyb],
        'gummies_sativa' => ['title' => 'SOFT CHEWS & GUMMIES', 'color' => 'orange', 'subtitle' => 'SATIVA • ALL SIZES', 'items' => $g_sat],
        'chocolates' => ['title' => 'ARTISAN CHOCOLATES', 'color' => 'purple', 'subtitle' => 'GOURMET MILK & DARK CHOCOLATE', 'items' => $choc],
        'wellness' => ['title' => 'OILS, DROPS & WELLNESS', 'color' => 'cyan', 'subtitle' => 'TINCTURES • TOPICALS • 1:1 DROPS', 'items' => $well]
    ];
}

$response_payload = [
    'success' => true,
    'screen' => $screen,
    'store' => $TENDY_CONFIG['store_name'],
    'updated_at' => date('h:i:s A'),
    'structured' => $structured
];

// Return JSON if requested as API
if ($is_api) {
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($response_payload);
    exit;
}

// Otherwise render complete standalone HTML page
$json_injected = json_encode($response_payload);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Kroniclez Live Digital TV Menu Board</title>
    
    <!-- High Performance Fonts & Icons -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800;900&family=JetBrains+Mono:wght@600;700;800&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css" rel="stylesheet">
    
    <style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    user-select: none;
    -webkit-user-select: none;
}

html {
    background: #000000;
    font-size: 16px;
    height: 100%;
}

body {
    background: #000000;
    color: #ffffff;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    width: 100vw;
    min-height: 100vh;
    padding: 6px 8px 36px 8px;
    display: flex;
    flex-direction: column;
}

#menuMount {
    width: 100%;
    flex: 1;
    display: flex;
    flex-direction: column;
}

/* ========================================================================== */
/* SCREEN CONTAINERS & GRID LAYOUTS                                           */
/* ========================================================================== */

/* Screen 1 (Pre-Rolls & Infused): 4 Balanced Columns */
.container-prerolls {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1.22fr;
    gap: 8px;
    width: 100%;
    align-items: start;
}

/* Screen 2 (Flower & Vapes): 4 Balanced Columns */
.container-vapes-flower {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr;
    gap: 8px;
    width: 100%;
    align-items: start;
}

/* Screen 3 (Soft Chews, Drinks & Concentrates): 3 Deck Columns */
.container-softchews {
    display: grid;
    grid-template-columns: 1fr 1.05fr 1.05fr;
    gap: 8px;
    width: 100%;
    align-items: start;
}

.column-deck {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
}

/* ========================================================================== */
/* PANELS & CARDS                                                             */
/* ========================================================================== */

/* Standard Panels (TV Screens 1 & 2) */
.panel {
    background: #141414;
    border-radius: 6px;
    padding: 4px 6px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Soft Cards (TV Screen 3) */
.soft-card {
    background: #0d1217;
    border: 1px solid #1c2a36;
    border-radius: 6px;
    padding: 4px 6px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
    width: 100%;
}

.card-head-title {
    text-align: center;
    font-size: 16px;
    line-height: 1.1;
    font-weight: 900;
    text-transform: uppercase;
    margin-bottom: 1px;
    letter-spacing: 0.5px;
}

.card-head-sub {
    text-align: center;
    color: #a0a0a0;
    font-size: 8.5px;
    line-height: 1;
    font-weight: 800;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
    text-transform: uppercase;
}

.card-gold .card-head-title { color: #facc15; }
.card-cyan .card-head-title { color: #38bdf8; }
.card-purple .card-head-title { color: #c084fc; }
.card-pink .card-head-title { color: #f472b6; }
.card-orange .card-head-title { color: #fb923c; }

/* Category Headings for Screens 1 & 2 */
.title {
    font-size: 16px;
    font-weight: 900;
    text-align: center;
    padding-bottom: 2px;
    margin-bottom: 2px;
    border-bottom: 1px solid #333333;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

.title-count {
    display: inline-block;
    font-size: 0.88em;
    font-weight: 800;
    margin-left: 2px;
    opacity: 0.9;
}

.indica { color: #4ade80; }
.hybrid { color: #facc15; }
.sativa { color: #f87171; }
.infused { color: #38bdf8; }
.vapes510 { color: #60a5fa; }
.disposable { color: #f472b6; }
.milled { color: #a3e635; }
.beverages { color: #38bdf8; }
.edibles { color: #fb7185; }
.concentrates { color: #fbbf24; }

/* Subheadings */
.subhead {
    font-size: 11px;
    margin: 2.5px 0 1px;
    padding-bottom: 1px;
    border-bottom: 1px solid #3a3a3a;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* ========================================================================== */
/* TABLE HEADERS & ROWS (FULL WRAP TEXT — NO TRUNCATION)                      */
/* ========================================================================== */

.table-header {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 52px 64px;
    column-gap: 3px;
    margin: 1px 0;
    padding-bottom: 1px;
    border-bottom: 1px solid #383838;
    font-size: 9px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}

.table-header-soft {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 50px 40px 36px 64px;
    column-gap: 3px;
    align-items: center;
    font-size: 9px;
    font-weight: 900;
    text-transform: uppercase;
    padding-bottom: 2px;
    margin-bottom: 1px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.18);
}

.card-gold .table-header-soft { color: #facc15; }
.card-cyan .table-header-soft { color: #38bdf8; }
.card-purple .table-header-soft { color: #c084fc; }
.card-pink .table-header-soft { color: #f472b6; }
.card-orange .table-header-soft { color: #fb923c; }

.h-name { color: #ffffff; text-align: left; }
.h-thc { color: #4ade80; text-align: right; }
.h-price { color: #facc15; text-align: right; }

/* Standard Product Row (Screens 1 & 2) */
.p-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 52px 64px;
    column-gap: 3px;
    align-items: center;
    padding: 1.2px 0;
    min-height: 0;
    height: auto;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.p-row:last-child {
    border-bottom: none;
}

/* Full text wrap for product names */
.p-name {
    min-width: 0;
    white-space: normal !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
    font-size: 12px;
    font-weight: 700;
    padding-right: 3px;
    color: #ffffff;
    line-height: 1.15;
}

.p-thc {
    text-align: right;
    color: #4ade80;
    font-family: 'JetBrains Mono', monospace;
}

/* Screen 1 Enhanced Typography & Visibility (Pre-Rolls) */
.container-prerolls {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1.25fr;
    gap: 8px;
    width: 100%;
}
.container-prerolls .p-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 58px 70px;
    column-gap: 4px;
    align-items: center;
    padding: 2.4px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.container-prerolls .p-name {
    font-size: 14.5px;
    font-weight: 750;
    line-height: 1.22;
    padding-right: 4px;
}
.container-prerolls .p-thc {
    font-size: 14.5px;
    font-weight: 800;
}
.container-prerolls .p-price .regular {
    font-size: 15.5px;
    font-weight: 900;
}
.container-prerolls .p-price .sale {
    font-size: 16px;
    font-weight: 900;
}
.container-prerolls .p-price .old {
    font-size: 10.5px;
    font-weight: 700;
}
.container-prerolls .title {
    font-size: 19px;
    font-weight: 900;
    padding-bottom: 4px;
    margin-bottom: 4px;
    letter-spacing: 0.5px;
}
.container-prerolls .subhead {
    font-size: 12.5px;
    font-weight: 800;
    margin: 4px 0 2px;
    padding-bottom: 2px;
}
.container-prerolls .table-header {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 58px 70px;
    column-gap: 4px;
    font-size: 10.5px;
    font-weight: 800;
    margin: 2px 0;
    padding-bottom: 2px;
}
.container-prerolls .panel {
    padding: 6px 8px;
    border-radius: 8px;
}

/* Screen 2 Targeted Micro-Adjustment (Indica & Hybrid Flower Column Fit) */
.container-vapes-flower .p-row {
    padding: 0.7px 0;
}
.container-vapes-flower .p-name {
    font-size: 11.5px;
    line-height: 1.1;
}
.container-vapes-flower .p-thc {
    font-size: 11.5px;
}
.container-vapes-flower .subhead {
    font-size: 10px;
    margin: 1.5px 0 0.5px;
    padding-bottom: 0.5px;
}
.container-vapes-flower .title {
    font-size: 15px;
    padding-bottom: 1.5px;
    margin-bottom: 1.5px;
}
.container-vapes-flower .table-header {
    font-size: 8.5px;
    margin: 0.5px 0;
    padding-bottom: 0.5px;
}
.container-vapes-flower .panel {
    padding: 3px 5px;
}

/* Soft Chews Product Row (Screen 3) */
.soft-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 50px 40px 36px 64px;
    column-gap: 3px;
    align-items: center;
    padding: 1.4px 1px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    font-size: 12px;
}

.soft-row:last-child { border-bottom: none; }
.soft-row:nth-child(even) { background: rgba(255, 255, 255, 0.02); }

/* Full text wrap for soft product names */
.soft-name {
    min-width: 0;
    white-space: normal !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
    color: #ffffff;
    font-weight: 700;
    font-size: 12px;
    line-height: 1.15;
    padding-right: 3px;
}

.soft-meta {
    text-align: center;
    font-size: 9.5px;
    font-weight: 800;
    white-space: nowrap;
}
.meta-indica { color: #4ade80 !important; }
.meta-hybrid { color: #facc15 !important; }
.meta-sativa { color: #f87171 !important; }

.soft-thc {
    text-align: center;
    color: #4ade80;
    font-weight: 800;
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    white-space: nowrap;
}

.soft-cbd {
    text-align: center;
    color: #cbd5e1;
    font-size: 10.5px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    white-space: nowrap;
}

/* Price Styling */
.p-price {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: center;
    line-height: 1;
    white-space: nowrap;
    text-align: right;
}

.p-price .regular {
    color: #facc15;
    font-size: 14.5px;
    font-weight: 900;
    font-family: 'JetBrains Mono', monospace;
}

.p-price .sale {
    color: #ef4444;
    font-size: 15px;
    font-weight: 900;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.1;
}

.p-price .old {
    color: #facc15;
    font-size: 9.5px;
    font-weight: 700;
    text-decoration: line-through;
    margin-top: 1px;
    font-family: 'JetBrains Mono', monospace;
    opacity: 0.8;
}

/* Strain Badges */
.badge-strain {
    font-size: 8px;
    font-weight: 800;
    padding: 1px 3.5px;
    border-radius: 3px;
    margin-right: 3px;
    text-transform: uppercase;
    display: inline-block;
}
.b-indica { background: rgba(74, 222, 128, 0.2); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.5); }
.b-hybrid { background: rgba(250, 204, 21, 0.2); color: #facc15; border: 1px solid rgba(250, 204, 21, 0.5); }
.b-sativa { background: rgba(248, 113, 113, 0.2); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.5); }
.badge-featured { font-size: 8px; font-weight: 900; padding: 1px 4px; border-radius: 3px; margin-left: 4px; text-transform: uppercase; display: inline-block; background: linear-gradient(135deg, #ef4444, #b91c1c); color: #ffffff; letter-spacing: 0.4px; box-shadow: 0 0 6px rgba(239, 68, 68, 0.4); vertical-align: middle; }
.badge-size {
    font-size: 7.5px;
    font-weight: 850;
    padding: 1px 4px;
    border-radius: 3px;
    margin-left: 4px;
    display: inline-block;
    vertical-align: middle;
    letter-spacing: 0.3px;
    text-transform: uppercase;
}
.size-10pk { background: rgba(56, 189, 248, 0.22); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.5); }
.size-5pk { background: rgba(168, 85, 247, 0.22); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.5); }
.size-2pk { background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.45); }
.size-oz { background: rgba(234, 179, 8, 0.25); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.6); font-weight: 900; }
.size-halfoz { background: rgba(34, 197, 94, 0.22); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.55); font-weight: 900; }
.size-multipk { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.5); }

.badge-staff-pick { font-size: 8px; font-weight: 900; padding: 1px 4.5px; border-radius: 3px; margin-left: 4px; background: linear-gradient(135deg, #facc15, #eab308); color: #000000; letter-spacing: 0.3px; display: inline-block; vertical-align: middle; box-shadow: 0 0 6px rgba(250, 204, 21, 0.4); }
.badge-low-stock { font-size: 7.5px; font-weight: 850; padding: 1px 4px; border-radius: 3px; margin-left: 4px; background: rgba(245, 158, 11, 0.22); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.5); display: inline-block; vertical-align: middle; }
.p-row.row-featured, .soft-row.row-featured { background: linear-gradient(90deg, rgba(239, 68, 68, 0.20) 0%, rgba(185, 28, 28, 0.05) 100%) !important; border-left: 3.5px solid #ef4444 !important; border-radius: 3px; padding-left: 4px !important; margin: 1px 0; box-shadow: 0 0 10px rgba(239, 68, 68, 0.18); }
.p-row.row-staff-pick, .soft-row.row-staff-pick { background: linear-gradient(90deg, rgba(234, 179, 8, 0.20) 0%, rgba(202, 138, 4, 0.05) 100%) !important; border-left: 3.5px solid #eab308 !important; border-radius: 3px; padding-left: 4px !important; margin: 1px 0; box-shadow: 0 0 10px rgba(234, 179, 8, 0.20); }
.p-row.row-low-stock, .soft-row.row-low-stock { background: linear-gradient(90deg, rgba(245, 158, 11, 0.18) 0%, rgba(217, 119, 6, 0.04) 100%) !important; border-left: 3.5px solid #f59e0b !important; border-radius: 3px; padding-left: 4px !important; margin: 1px 0; box-shadow: 0 0 10px rgba(245, 158, 11, 0.16); }
.badge-cbn { font-size: 7.5px; font-weight: 800; padding: 1px 4px; border-radius: 3px; margin-left: 4px; background: rgba(147, 51, 234, 0.25); color: #c084fc; border: 1px solid rgba(147, 51, 234, 0.5); display: inline-block; vertical-align: middle; }
.badge-cbg { font-size: 7.5px; font-weight: 800; padding: 1px 4px; border-radius: 3px; margin-left: 4px; background: rgba(14, 165, 233, 0.25); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.5); display: inline-block; vertical-align: middle; }
.badge-cbd { font-size: 7.5px; font-weight: 800; padding: 1px 4px; border-radius: 3px; margin-left: 4px; background: rgba(34, 197, 94, 0.25); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.5); display: inline-block; vertical-align: middle; }
.badge-balance { font-size: 7.5px; font-weight: 800; padding: 1px 4px; border-radius: 3px; margin-left: 4px; background: rgba(234, 179, 8, 0.25); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.5); display: inline-block; vertical-align: middle; }
.badge-featured { font-size: 8px; font-weight: 900; padding: 1px 4px; border-radius: 3px; margin-left: 4px; text-transform: uppercase; display: inline-block; background: linear-gradient(135deg, #ef4444, #b91c1c); color: #ffffff; letter-spacing: 0.4px; box-shadow: 0 0 6px rgba(239, 68, 68, 0.4); vertical-align: middle; }
.badge-size {
    font-size: 7.5px;
    font-weight: 850;
    padding: 1px 4px;
    border-radius: 3px;
    margin-left: 4px;
    display: inline-block;
    vertical-align: middle;
    letter-spacing: 0.3px;
    text-transform: uppercase;
}
.size-10pk { background: rgba(56, 189, 248, 0.22); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.5); }
.size-5pk { background: rgba(168, 85, 247, 0.22); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.5); }
.size-2pk { background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.45); }
.size-oz { background: rgba(234, 179, 8, 0.25); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.6); font-weight: 900; }
.size-halfoz { background: rgba(34, 197, 94, 0.22); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.55); font-weight: 900; }
.size-multipk { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.5); }

.badge-staff-pick { font-size: 8px; font-weight: 900; padding: 1px 4.5px; border-radius: 3px; margin-left: 4px; background: linear-gradient(135deg, #facc15, #eab308); color: #000000; letter-spacing: 0.3px; display: inline-block; vertical-align: middle; box-shadow: 0 0 6px rgba(250, 204, 21, 0.4); }
.badge-low-stock { font-size: 7.5px; font-weight: 850; padding: 1px 4px; border-radius: 3px; margin-left: 4px; background: rgba(245, 158, 11, 0.22); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.5); display: inline-block; vertical-align: middle; }
.p-row.row-featured, .soft-row.row-featured { background: linear-gradient(90deg, rgba(239, 68, 68, 0.20) 0%, rgba(185, 28, 28, 0.05) 100%) !important; border-left: 3.5px solid #ef4444 !important; border-radius: 3px; padding-left: 4px !important; margin: 1px 0; box-shadow: 0 0 10px rgba(239, 68, 68, 0.18); }
.p-row.row-staff-pick, .soft-row.row-staff-pick { background: linear-gradient(90deg, rgba(234, 179, 8, 0.20) 0%, rgba(202, 138, 4, 0.05) 100%) !important; border-left: 3.5px solid #eab308 !important; border-radius: 3px; padding-left: 4px !important; margin: 1px 0; box-shadow: 0 0 10px rgba(234, 179, 8, 0.20); }
.p-row.row-low-stock, .soft-row.row-low-stock { background: linear-gradient(90deg, rgba(245, 158, 11, 0.18) 0%, rgba(217, 119, 6, 0.04) 100%) !important; border-left: 3.5px solid #f59e0b !important; border-radius: 3px; padding-left: 4px !important; margin: 1px 0; box-shadow: 0 0 10px rgba(245, 158, 11, 0.16); }

/* ========================================================================== */
/* FLOATING CONTROLS & STATUS                                                 */
/* ========================================================================== */

.tv-floating-nav {
    position: fixed;
    bottom: 8px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(18, 18, 18, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 999px;
    padding: 4px 12px;
    display: flex;
    align-items: center;
    gap: 6px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.8);
    z-index: 9999;
    backdrop-filter: blur(10px);
    transition: opacity 0.3s ease, transform 0.3s ease;
}

.tv-floating-nav.hidden {
    opacity: 0;
    pointer-events: none;
    transform: translate(-50%, 20px);
}

.nav-link-btn {
    color: #cbd5e1;
    font-size: 11px;
    font-weight: 700;
    text-decoration: none;
    padding: 4px 10px;
    border-radius: 999px;
    transition: all 0.2s ease;
}

.nav-link-btn:hover, .nav-link-btn.active {
    background: #3b82f6;
    color: #ffffff;
}

.nav-divider {
    width: 1px;
    height: 14px;
    background: rgba(255, 255, 255, 0.2);
}

.nav-fs-btn {
    background: none;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    font-size: 11px;
    display: flex;
    align-items: center;
    padding: 3px 6px;
}

.nav-fs-btn:hover {
    color: #ffffff;
}

.tv-sync-pill {
    position: fixed;
    top: 6px;
    right: 8px;
    background: rgba(0, 0, 0, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 999px;
    padding: 2px 8px;
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 9px;
    color: #94a3b8;
    font-weight: 700;
    z-index: 9998;
    pointer-events: none;
}

.sync-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 8px #22c55e;
}


/* ========================================================================== */
/* CONTINUOUS LIVE FOOTER TICKER                                              */
/* ========================================================================== */

.tv-ticker-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 30px;
    background: rgba(8, 8, 10, 0.98);
    border-top: 1.5px solid rgba(250, 204, 21, 0.45);
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.95);
    display: flex;
    align-items: center;
    overflow: hidden;
    z-index: 999;
    backdrop-filter: blur(12px);
}

.ticker-track {
    display: flex;
    width: max-content;
    animation: ticker-scroll 34s linear infinite;
}

.ticker-content {
    display: flex;
    align-items: center;
    white-space: nowrap;
    gap: 20px;
    padding-right: 20px;
}

@keyframes ticker-scroll {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

.ticker-item {
    font-size: 13px;
    font-weight: 750;
    color: #f1f5f9;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    letter-spacing: 0.3px;
}

.ticker-item strong { color: #fde047; font-weight: 900; }
.ticker-dot { color: #facc15; font-size: 12px; margin: 0 4px; }

.ticker-badge {
    font-size: 10px;
    font-weight: 900;
    padding: 2px 6px;
    border-radius: 3.5px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.ticker-badge.gold { background: rgba(250, 204, 21, 0.25); color: #facc15; border: 1px solid rgba(250, 204, 21, 0.6); }
.ticker-badge.green { background: rgba(74, 222, 128, 0.25); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.6); }
.ticker-badge.red { background: rgba(239, 68, 68, 0.3); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.6); }
.ticker-badge.cyan { background: rgba(56, 189, 248, 0.25); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.6); }
.ticker-badge.purple { background: rgba(192, 132, 252, 0.25); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.6); }
.ticker-badge.yellow { background: rgba(234, 179, 8, 0.25); color: #fbbf24; border: 1px solid rgba(234, 179, 8, 0.6); }
.ticker-badge.gray { background: rgba(148, 163, 184, 0.25); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.6); }

/* ========================================================================== */
/* TOP HEADER BAR (BRANDING, HAPPY HOUR BANNER, QR CODE & LIVE SYNC)         */
/* ========================================================================== */

.tv-top-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1px 4px 5px 4px;
    width: 100%;
    min-height: 32px;
}

.brand-block {
    display: flex;
    align-items: center;
    gap: 8px;
}

.brand-title {
    font-size: 14px;
    font-weight: 900;
    letter-spacing: 0.8px;
    color: #4ade80;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 5px;
}

.brand-loc {
    font-size: 10px;
    font-weight: 800;
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.08);
    padding: 1px 6px;
    border-radius: 3px;
    letter-spacing: 0.5px;
}

/* Dynamic Happy Hour Banner */
.happy-hour-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 2.5px 12px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 750;
    letter-spacing: 0.3px;
    transition: all 0.3s ease;
}

.happy-hour-pill.active {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.3), rgba(220, 38, 38, 0.15));
    border: 1px solid rgba(239, 68, 68, 0.7);
    color: #ffffff;
    box-shadow: 0 0 12px rgba(239, 68, 68, 0.4);
    animation: happy-hour-glow 2s ease-in-out infinite;
}

.happy-hour-pill.active strong {
    color: #fca5a5;
    font-weight: 900;
}

.happy-hour-pill.idle {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #cbd5e1;
}

.happy-hour-pill.idle strong {
    color: #facc15;
    font-weight: 800;
}

@keyframes happy-hour-glow {
    0%, 100% { box-shadow: 0 0 8px rgba(239, 68, 68, 0.4); }
    50% { box-shadow: 0 0 16px rgba(239, 68, 68, 0.8); }
}

.header-right-deck {
    display: flex;
    align-items: center;
    gap: 10px;
}

/* Express Pickup QR Card */
.wifi-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.4);
    padding: 2.5px 8px;
    border-radius: 6px;
    font-size: 9.5px;
    color: #cbd5e1;
    font-weight: 700;
}
.wifi-pill strong { color: #38bdf8; font-weight: 850; }

.qr-header-card {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(250, 204, 21, 0.4);
    padding: 2px 8px 2px 4px;
    border-radius: 6px;
    box-shadow: 0 0 8px rgba(0, 0, 0, 0.5);
}

.qr-img {
    width: 24px;
    height: 24px;
    background: #ffffff;
    padding: 1.5px;
    border-radius: 3px;
    display: block;
}

.qr-text {
    display: flex;
    flex-direction: column;
    line-height: 1.05;
}

.qr-title {
    font-size: 9.5px;
    font-weight: 900;
    color: #facc15;
    letter-spacing: 0.3px;
}

.qr-sub {
    font-size: 8px;
    font-weight: 700;
    color: #cbd5e1;
}

/* Ambient Particle Background Canvas */
.ambient-canvas {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: 0;
    pointer-events: none;
    opacity: 0.9;
}

.tv-top-header,
#menuMount,
.tv-floating-nav,
.tv-ticker-bar {
    position: relative;
    z-index: 1;
}

    </style>
</head>
<body>
    <!-- Ambient Luxury Floating Particles Canvas Background -->
    <canvas id="ambientCanvas" class="ambient-canvas"></canvas>

    <!-- TV Top Header Bar (Branding, Dynamic Happy Hour, QR Code, Sync Status) -->
    <header class="tv-top-header">
        <div class="brand-block">
            <div class="brand-title"><i class="bi bi-fire" style="color:#ef4444;"></i> KRONICLEZ</div>
            <div class="brand-loc" id="headerStoreLoc"><?= $current_loc_title ?></div>
        </div>

        <!-- Dynamic Happy Hour Banner -->
        <div id="happyHourBanner" class="happy-hour-pill idle">
            <i class="bi bi-clock-history" style="color:#facc15;"></i> Daily Happy Hour: <strong>1:00 PM – 4:00 PM</strong>
        </div>

        <div class="header-right-deck">
            <!-- Free Store Wi-Fi Pill -->
            <div class="wifi-pill" title="Guest Wi-Fi: KRONICKLUB | Pass: Kroniclub">
                <i class="bi bi-wifi" style="color:#38bdf8;"></i>
                <span><strong>Wi-Fi:</strong> KRONICKLUB <span style="color:#64748b; margin: 0 2px;">•</span> <strong>Pass:</strong> Kroniclub</span>
            </div>
            <!-- Express Pickup Mobile QR Code -->
            <div class="qr-header-card">
                <svg class="qr-img" version="1.1" viewBox="0 0 27 27" xmlns="http://www.w3.org/2000/svg"><path d="M1,1H2V2H1zM2,1H3V2H2zM3,1H4V2H3zM4,1H5V2H4zM5,1H6V2H5zM6,1H7V2H6zM7,1H8V2H7zM9,1H10V2H9zM11,1H12V2H11zM13,1H14V2H13zM15,1H16V2H15zM17,1H18V2H17zM19,1H20V2H19zM20,1H21V2H20zM21,1H22V2H21zM22,1H23V2H22zM23,1H24V2H23zM24,1H25V2H24zM25,1H26V2H25zM1,2H2V3H1zM7,2H8V3H7zM11,2H12V3H11zM13,2H14V3H13zM14,2H15V3H14zM15,2H16V3H15zM19,2H20V3H19zM25,2H26V3H25zM1,3H2V4H1zM3,3H4V4H3zM4,3H5V4H4zM5,3H6V4H5zM7,3H8V4H7zM9,3H10V4H9zM10,3H11V4H10zM11,3H12V4H11zM14,3H15V4H14zM15,3H16V4H15zM17,3H18V4H17zM19,3H20V4H19zM21,3H22V4H21zM22,3H23V4H22zM23,3H24V4H23zM25,3H26V4H25zM1,4H2V5H1zM3,4H4V5H3zM4,4H5V5H4zM5,4H6V5H5zM7,4H8V5H7zM10,4H11V5H10zM11,4H12V5H11zM12,4H13V5H12zM14,4H15V5H14zM15,4H16V5H15zM16,4H17V5H16zM17,4H18V5H17zM19,4H20V5H19zM21,4H22V5H21zM22,4H23V5H22zM23,4H24V5H23zM25,4H26V5H25zM1,5H2V6H1zM3,5H4V6H3zM4,5H5V6H4zM5,5H6V6H5zM7,5H8V6H7zM10,5H11V6H10zM12,5H13V6H12zM14,5H15V6H14zM15,5H16V6H15zM19,5H20V6H19zM21,5H22V6H21zM22,5H23V6H22zM23,5H24V6H23zM25,5H26V6H25zM1,6H2V7H1zM7,6H8V7H7zM9,6H10V7H9zM10,6H11V7H10zM11,6H12V7H11zM12,6H13V7H12zM14,6H15V7H14zM17,6H18V7H17zM19,6H20V7H19zM25,6H26V7H25zM1,7H2V8H1zM2,7H3V8H2zM3,7H4V8H3zM4,7H5V8H4zM5,7H6V8H5zM6,7H7V8H6zM7,7H8V8H7zM9,7H10V8H9zM11,7H12V8H11zM13,7H14V8H13zM15,7H16V8H15zM17,7H18V8H17zM19,7H20V8H19zM20,7H21V8H20zM21,7H22V8H21zM22,7H23V8H22zM23,7H24V8H23zM24,7H25V8H24zM25,7H26V8H25zM10,8H11V9H10zM11,8H12V9H11zM12,8H13V9H12zM15,8H16V9H15zM17,8H18V9H17zM1,9H2V10H1zM3,9H4V10H3zM7,9H8V10H7zM8,9H9V10H8zM11,9H12V10H11zM13,9H14V10H13zM16,9H17V10H16zM17,9H18V10H17zM20,9H21V10H20zM23,9H24V10H23zM25,9H26V10H25zM1,10H2V11H1zM2,10H3V11H2zM3,10H4V11H3zM4,10H5V11H4zM8,10H9V11H8zM11,10H12V11H11zM12,10H13V11H12zM13,10H14V11H13zM14,10H15V11H14zM16,10H17V11H16zM17,10H18V11H17zM18,10H19V11H18zM19,10H20V11H19zM20,10H21V11H20zM22,10H23V11H22zM24,10H25V11H24zM25,10H26V11H25zM1,11H2V12H1zM2,11H3V12H2zM4,11H5V12H4zM5,11H6V12H5zM6,11H7V12H6zM7,11H8V12H7zM8,11H9V12H8zM9,11H10V12H9zM11,11H12V12H11zM12,11H13V12H12zM16,11H17V12H16zM17,11H18V12H17zM18,11H19V12H18zM19,11H20V12H19zM22,11H23V12H22zM23,11H24V12H23zM25,11H26V12H25zM1,12H2V13H1zM3,12H4V13H3zM4,12H5V13H4zM6,12H7V13H6zM10,12H11V13H10zM11,12H12V13H11zM15,12H16V13H15zM17,12H18V13H17zM19,12H20V13H19zM21,12H22V13H21zM22,12H23V13H22zM1,13H2V14H1zM4,13H5V14H4zM5,13H6V14H5zM6,13H7V14H6zM7,13H8V14H7zM8,13H9V14H8zM10,13H11V14H10zM13,13H14V14H13zM17,13H18V14H17zM19,13H20V14H19zM20,13H21V14H20zM25,13H26V14H25zM3,14H4V15H3zM4,14H5V15H4zM5,14H6V15H5zM9,14H10V15H9zM10,14H11V15H10zM14,14H15V15H14zM16,14H17V15H16zM17,14H18V15H17zM19,14H20V15H19zM20,14H21V15H20zM24,14H25V15H24zM25,14H26V15H25zM1,15H2V16H1zM2,15H3V16H2zM3,15H4V16H3zM7,15H8V16H7zM8,15H9V16H8zM12,15H13V16H12zM14,15H15V16H14zM16,15H17V16H16zM22,15H23V16H22zM23,15H24V16H23zM25,15H26V16H25zM4,16H5V17H4zM6,16H7V17H6zM13,16H14V17H13zM15,16H16V17H15zM16,16H17V17H16zM18,16H19V17H18zM19,16H20V17H19zM20,16H21V17H20zM21,16H22V17H21zM22,16H23V17H22zM1,17H2V18H1zM2,17H3V18H2zM4,17H5V18H4zM6,17H7V18H6zM7,17H8V18H7zM9,17H10V18H9zM12,17H13V18H12zM15,17H16V18H15zM16,17H17V18H16zM17,17H18V18H17zM18,17H19V18H18zM19,17H20V18H19zM20,17H21V18H20zM21,17H22V18H21zM24,17H25V18H24zM9,18H10V19H9zM11,18H12V19H11zM12,18H13V19H12zM13,18H14V19H13zM14,18H15V19H14zM17,18H18V19H17zM21,18H22V19H21zM25,18H26V19H25zM1,19H2V20H1zM2,19H3V20H2zM3,19H4V20H3zM4,19H5V20H4zM5,19H6V20H5zM6,19H7V20H6zM7,19H8V20H7zM9,19H10V20H9zM10,19H11V20H10zM11,19H12V20H11zM12,19H13V20H12zM13,19H14V20H13zM17,19H18V20H17zM19,19H20V20H19zM21,19H22V20H21zM25,19H26V20H25zM1,20H2V21H1zM7,20H8V21H7zM10,20H11V21H10zM12,20H13V21H12zM13,20H14V21H13zM15,20H16V21H15zM16,20H17V21H16zM17,20H18V21H17zM21,20H22V21H21zM25,20H26V21H25zM1,21H2V22H1zM3,21H4V22H3zM4,21H5V22H4zM5,21H6V22H5zM7,21H8V22H7zM11,21H12V22H11zM13,21H14V22H13zM16,21H17V22H16zM17,21H18V22H17zM18,21H19V22H18zM19,21H20V22H19zM20,21H21V22H20zM21,21H22V22H21zM24,21H25V22H24zM1,22H2V23H1zM3,22H4V23H3zM4,22H5V23H4zM5,22H6V23H5zM7,22H8V23H7zM10,22H11V23H10zM12,22H13V23H12zM13,22H14V23H13zM14,22H15V23H14zM16,22H17V23H16zM18,22H19V23H18zM21,22H22V23H21zM23,22H24V23H23zM24,22H25V23H24zM1,23H2V24H1zM3,23H4V24H3zM4,23H5V24H4zM5,23H6V24H5zM7,23H8V24H7zM9,23H10V24H9zM11,23H12V24H11zM12,23H13V24H12zM14,23H15V24H14zM16,23H17V24H16zM18,23H19V24H18zM20,23H21V24H20zM21,23H22V24H21zM22,23H23V24H22zM24,23H25V24H24zM25,23H26V24H25zM1,24H2V25H1zM7,24H8V25H7zM11,24H12V25H11zM13,24H14V25H13zM15,24H16V25H15zM17,24H18V25H17zM18,24H19V25H18zM19,24H20V25H19zM20,24H21V25H20zM21,24H22V25H21zM1,25H2V26H1zM2,25H3V26H2zM3,25H4V26H3zM4,25H5V26H4zM5,25H6V26H5zM6,25H7V26H6zM7,25H8V26H7zM9,25H10V26H9zM10,25H11V26H10zM11,25H12V26H11zM12,25H13V26H12zM13,25H14V26H13zM17,25H18V26H17zM18,25H19V26H18zM22,25H23V26H22zM25,25H26V26H25z" id="qr-path" fill="#000000" fill-opacity="1" fill-rule="nonzero" stroke="none" /></svg>
                <div class="qr-text">
                    <span class="qr-title" id="headerQrTitle"><?= $current_qr_title ?></span>
                    <span class="qr-sub" id="headerQrSub"><?= $current_qr_sub ?></span>
                </div>
            </div>

            <!-- TV Live Sync Status -->
            <div class="tv-sync-status" style="position:static;">
                <span class="pulse-dot"></span>
                <span id="tv-sync-time">TENDY LIVE SYNC</span>
            </div>
        </div>
    </header>

    <!-- Main TV Screen Mount -->
    <main id="menuMount"></main>

    <!-- Floating Navigation Bar -->
        <!-- Floating TV Navigation Dock (Auto-hides on idle) -->
    <nav id="floatingNav" class="tv-floating-nav">
        <span style="font-size: 10px; font-weight: 900; color: #777; letter-spacing: 0.5px;">STORE:</span>
        <button type="button" id="nav-btn-loc-waterloo" class="nav-link-btn <?= $is_waterloo ? 'active' : '' ?>" onclick="switchStore('waterloo')">
            <i class="bi bi-geo-alt-fill" style="color:#38bdf8;"></i> Waterloo
        </button>
        <button type="button" id="nav-btn-loc-kitchener" class="nav-link-btn <?= !$is_waterloo ? 'active' : '' ?>" onclick="switchStore('kitchener')">
            <i class="bi bi-geo-alt-fill" style="color:#facc15;"></i> Kitchener
        </button>
        <span style="font-size: 10px; font-weight: 900; color: #777; letter-spacing: 0.5px; margin-left:6px;">DEDICATED TV:</span>
        <button type="button" id="nav-btn-screen1" class="nav-link-btn <?= $screen === 1 ? 'active' : '' ?>" onclick="switchScreen(1)">
            <i class="bi bi-fire"></i> TV 1: Pre-Rolls
        </button>
        <button type="button" id="nav-btn-screen2" class="nav-link-btn <?= $screen === 2 ? 'active' : '' ?>" onclick="switchScreen(2)">
            <i class="bi bi-flower1"></i> TV 2: Vapes & Flower
        </button>
        <button type="button" id="nav-btn-screen3" class="nav-link-btn <?= $screen === 3 ? 'active' : '' ?>" onclick="switchScreen(3)">
            <i class="bi bi-cup-straw"></i> TV 3: Edibles & Drinks
        </button>
        <button type="button" class="nav-link-btn" onclick="toggleFullscreen()" title="Toggle Fullscreen (F)">
            <i class="bi bi-fullscreen"></i>
        </button>
    </nav>

    <script>
        const initialData = <?= $json_injected ?>;
        const currentScreen = <?= $screen ?>;

        function formatCAD(val) {
            return '$' + (parseFloat(val) || 0.0).toFixed(2);
        }

        function renderRowHtml(it, showStrainBadge = false) {
            let badge = '';
            if (showStrainBadge) {
                const s = (it.species || 'HYBRID').toUpperCase();
                if (s.includes('INDICA')) badge = '<span class="badge-strain b-indica">IND</span>';
                else if (s.includes('SATIVA')) badge = '<span class="badge-strain b-sativa">SAT</span>';
                else badge = '<span class="badge-strain b-hybrid">HYB</span>';
            }
            let priceHtml = (it.is_sale && it.old_price) 
                ? `<span class="sale">${formatCAD(it.price)}</span><span class="old">${formatCAD(it.old_price)}</span>`
                : `<span class="regular">${formatCAD(it.price)}</span>`;

            return `
                <div class="p-row ${(it.tag === 'FEATURED' || (it.is_sale && it.old_price)) ? 'row-featured' : ''}">
                    <div class="p-name">${badge}${it.product_name || ''}</div>
                    <div class="p-thc">${it.thc || '28%'}</div>
                    <div class="p-price">${priceHtml}</div>
                </div>
            `;
        }

        function renderSoftRow(it) {
            const spec = (it.species || 'HYBRID').toUpperCase();
            let metaClass = 'meta-hybrid', metaText = 'Hybrid';
            if (spec.includes('INDICA')) { metaClass = 'meta-indica'; metaText = 'Indica'; }
            else if (spec.includes('SATIVA')) { metaClass = 'meta-sativa'; metaText = 'Sativa'; }

            let tagBadge = '';
            if (it.tag === 'STAFF PICK') {
                tagBadge = '<span class="badge-staff-pick">👑 STAFF PICK</span>';
            } else if (it.tag === 'FEATURED' || (it.is_sale && it.old_price)) {
                tagBadge = '<span class="badge-featured">⭐ FEATURED</span>';
            }

            let stockBadge = '';
            const stockNum = parseInt(it.stock, 10);
            if (stockNum > 0 && stockNum <= 3) {
                stockBadge = `<span class="badge-low-stock">⚠️ ${stockNum === 1 ? 'Last 1 Left!' : `Only ${stockNum} Left!`}</span>`;
            }

            let funcBadge = '';
            const pNameLow = (it.product_name || '').toLowerCase();
            if (pNameLow.includes('cbn')) funcBadge = '<span class="badge-cbn">🌙 CBN • SLEEP</span>';
            else if (pNameLow.includes('cbg')) funcBadge = '<span class="badge-cbg">⚡ CBG • FOCUS</span>';
            else if (pNameLow.includes('4:1') || pNameLow.includes('cbd bomb')) funcBadge = '<span class="badge-cbd">🌿 CBD • CALM</span>';
            else if (pNameLow.includes('1:1') && !pNameLow.includes('cbn')) funcBadge = '<span class="badge-balance">⚖️ 1:1 • BALANCED</span>';

            let priceHtml = (it.is_sale && it.old_price) 
                ? `<span class="sale">${formatCAD(it.price)}</span><span class="old">${formatCAD(it.old_price)}</span>`
                : `<span class="regular">${formatCAD(it.price)}</span>`;

            const isFeatured = (it.tag === 'FEATURED' || (it.is_sale && it.old_price));
            const isLowStock = (!isFeatured && stockNum > 0 && stockNum <= 3);
            const isStaffPick = (it.tag === 'STAFF PICK');
            const isLowStock = (!isFeatured && !isStaffPick && stockNum > 0 && stockNum <= 3);
            let rowClass = isFeatured ? 'row-featured' : (isStaffPick ? 'row-staff-pick' : (isLowStock ? 'row-low-stock' : ''));

            return `
                <div class="soft-row ${rowClass}">
                    const sizeBadge = getSizeBadge(it.product_name, it.variant);
            return `<div class="soft-row ${rowClass}"><div class="soft-name">${it.product_name}${sizeBadge}${funcBadge}${tagBadge}${stockBadge}</div>
                    <div class="soft-meta ${metaClass}">${metaText}</div>
                    <div class="soft-thc">${it.thc || '10mg'}</div>
                    <div class="soft-cbd">${it.cbd || '—'}</div>
                    <div class="p-price">${priceHtml}</div>
                </div>
            `;
        }

        function renderSoftCard(cardKey, dataObj) {
            const sec = dataObj[cardKey];
            if (!sec || !sec.items || sec.items.length === 0) return '';
            const count = sec.items.length;
            const subHtml = sec.subtitle ? `<div class="card-head-sub">${sec.subtitle}</div>` : '';

            if (cardKey === 'beverages') {
                const sodas = [];
                const seltzers = [];
                sec.items.forEach(it => {
                    const nl = (it.product_name || '').toLowerCase();
                    if (nl.includes('soda') || nl.includes('cola') || nl.includes('root beer') || nl.includes('cream soda')) {
                        sodas.push(it);
                    } else {
                        seltzers.push(it);
                    }
                });

                return `
                    <div class="soft-card card-cyan">
                        <div class="card-head-title">${sec.title} <span class="title-count">(${count})</span></div>
                        <div class="card-head-sub">${sec.subtitle || 'CRAFT SODAS • SPARKLING SELTZERS'}</div>
                        <div class="table-header-soft">
                            <div>BEVERAGE</div>
                            <div style="text-align:center;">TYPE</div>
                            <div style="text-align:center;">THC</div>
                            <div style="text-align:center;">CBD</div>
                            <div style="text-align:right;">PRICE</div>
                        </div>
                        ${sodas.length > 0 ? `
                            <div class="subhead" style="color:#38bdf8; margin: 3px 0 1px; font-size:11.5px; font-weight:800;"><span>🥤 Craft Sodas & Colas</span> <span style="font-size:10px; color:#888;">${sodas.length} SKUs</span></div>
                            ${sodas.map(it => renderSoftRow(it)).join('')}
                        ` : ''}
                        ${seltzers.length > 0 ? `
                            <div class="subhead" style="color:#2dd4bf; margin: 5px 0 1px; font-size:11.5px; font-weight:800;"><span>🍋 Seltzers, Teas & Lemonades</span> <span style="font-size:10px; color:#888;">${seltzers.length} SKUs</span></div>
                            ${seltzers.map(it => renderSoftRow(it)).join('')}
                        ` : ''}
                    </div>
                `;
            }

            return `
                <div class="soft-card card-${sec.color || 'gold'}">
                    <div class="card-head-title">${sec.title} <span class="title-count">(${count})</span></div>
                    ${subHtml}
                    <div class="table-header-soft">
                        <div>PRODUCT</div>
                        <div style="text-align:center;">STRAIN</div>
                        <div style="text-align:center;">THC</div>
                        <div style="text-align:center;">CBD</div>
                        <div style="text-align:right;">PRICE</div>
                    </div>
                    ${sec.items.map(it => renderSoftRow(it)).join('')}
                </div>
            `;
        }

        function renderScreen(res) {
            if (!res || !res.structured) return;
            const mount = document.getElementById('menuMount');
            if (!mount) return;

            if (currentScreen === 1) {
                const d = res.structured;
                const indItems = d.indica.items || [];
                const hybItems = d.hybrid.items || [];
                const satItems = d.sativa.items || [];

                let infHtml = '';
                const infInd = (d.infused && d.infused.indica_items) || [];
                const infHyb = (d.infused && d.infused.hybrid_items) || [];
                const infSat = (d.infused && d.infused.sativa_items) || [];
                const infTotal = (d.infused && d.infused.items) ? d.infused.items.length : (infInd.length + infHyb.length + infSat.length);

                if (infInd.length) {
                    infHtml += `<div class="subhead indica"><span style="color:#4CAF50;">Indica Infused</span> <span style="font-size:11px; color:#888;">${infInd.length} SKUs</span></div>`;
                    infHtml += infInd.map(it => renderRowHtml(it, false)).join('');
                }
                if (infHyb.length) {
                    infHtml += `<div class="subhead hybrid"><span style="color:#FFC107;">Hybrid Infused</span> <span style="font-size:11px; color:#888;">${infHyb.length} SKUs</span></div>`;
                    infHtml += infHyb.map(it => renderRowHtml(it, false)).join('');
                }
                if (infSat.length) {
                    infHtml += `<div class="subhead sativa"><span style="color:#FF6666;">Sativa Infused</span> <span style="font-size:11px; color:#888;">${infSat.length} SKUs</span></div>`;
                    infHtml += infSat.map(it => renderRowHtml(it, false)).join('');
                }

                mount.innerHTML = `
                    <div class="container-prerolls">
                        <div class="panel">
                            <div class="title indica">INDICA PRE-ROLLS <span class="title-count">(${indItems.length})</span></div>
                            <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                            ${indItems.map(it => renderRowHtml(it, false)).join('')}
                        </div>
                        <div class="panel">
                            <div class="title hybrid">HYBRID & BLENDS PRE-ROLLS <span class="title-count">(${hybItems.length})</span></div>
                            <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                            ${hybItems.map(it => renderRowHtml(it, false)).join('')}
                        </div>
                        <div class="panel">
                            <div class="title sativa">SATIVA PRE-ROLLS <span class="title-count">(${satItems.length})</span></div>
                            <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                            ${satItems.map(it => renderRowHtml(it, false)).join('')}
                        </div>
                        <div class="panel">
                            <div class="title infused">INFUSED PRE-ROLLS <span class="title-count">(${infTotal})</span></div>
                            <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                            ${infHtml}
                        </div>
                    </div>
                `;
            } else if (currentScreen === 2) {
                const f = res.structured.flower;
                const v = res.structured.vapes;
                const indTotal = f.indica_dried.items.length + f.indica_milled.items.length;
                const hybTotal = f.hybrid_dried.items.length + f.hybrid_milled.items.length;
                const col1Total = indTotal + hybTotal;

                let col1Html = '';
                if (indTotal > 0) {
                    col1Html += `<div class="subhead indica"><span style="color:#4CAF50;">Indica Dried Flower</span> <span style="font-size:11px; color:#888;">${f.indica_dried.items.length} SKUs</span></div>`;
                    col1Html += f.indica_dried.items.map(it => renderRowHtml(it, false)).join('');
                    if (f.indica_milled.items.length) {
                        col1Html += `<div style="font-size:10.5px; font-weight:800; color:#a3e635; margin:6px 0 2px 2px; text-transform:uppercase; display:flex; justify-content:space-between;"><span>Indica Milled</span> <span style="font-size:11px; color:#888;">${f.indica_milled.items.length} SKUs</span></div>`;
                        col1Html += f.indica_milled.items.map(it => renderRowHtml(it, false)).join('');
                    }
                }
                if (hybTotal > 0) {
                    col1Html += `<div class="subhead hybrid" style="margin-top:10px;"><span style="color:#FFC107;">Hybrid Dried Flower</span> <span style="font-size:11px; color:#888;">${f.hybrid_dried.items.length} SKUs</span></div>`;
                    col1Html += f.hybrid_dried.items.map(it => renderRowHtml(it, false)).join('');
                    if (f.hybrid_milled.items.length) {
                        col1Html += `<div style="font-size:10.5px; font-weight:800; color:#a3e635; margin:6px 0 2px 2px; text-transform:uppercase; display:flex; justify-content:space-between;"><span>Hybrid Milled</span> <span style="font-size:11px; color:#888;">${f.hybrid_milled.items.length} SKUs</span></div>`;
                        col1Html += f.hybrid_milled.items.map(it => renderRowHtml(it, false)).join('');
                    }
                }

                const satTotal = f.sativa_dried.items.length + f.sativa_milled.items.length;
                let col2Html = '';
                if (satTotal > 0) {
                    col2Html += `<div class="subhead sativa"><span style="color:#FF6666;">Sativa Dried Flower</span> <span style="font-size:11px; color:#888;">${f.sativa_dried.items.length} SKUs</span></div>`;
                    col2Html += f.sativa_dried.items.map(it => renderRowHtml(it, false)).join('');
                    if (f.sativa_milled.items.length) {
                        col2Html += `<div style="font-size:10.5px; font-weight:800; color:#a3e635; margin:6px 0 2px 2px; text-transform:uppercase; display:flex; justify-content:space-between;"><span>Sativa Milled</span> <span style="font-size:11px; color:#888;">${f.sativa_milled.items.length} SKUs</span></div>`;
                        col2Html += f.sativa_milled.items.map(it => renderRowHtml(it, false)).join('');
                    }
                }

                const v510Total = v.vapes_510_indica.items.length + v.vapes_510_hybrid.items.length;
                let col3Html = '';
                if (v.vapes_510_indica.items.length) {
                    col3Html += `<div class="subhead indica"><span style="color:#4CAF50;">510 Indica</span> <span style="font-size:11px; color:#888;">${v.vapes_510_indica.items.length} SKUs</span></div>`;
                    col3Html += v.vapes_510_indica.items.map(it => renderRowHtml(it, true)).join('');
                }
                if (v.vapes_510_hybrid.items.length) {
                    col3Html += `<div class="subhead hybrid" style="margin-top:10px;"><span style="color:#FFC107;">510 Hybrid</span> <span style="font-size:11px; color:#888;">${v.vapes_510_hybrid.items.length} SKUs</span></div>`;
                    col3Html += v.vapes_510_hybrid.items.map(it => renderRowHtml(it, true)).join('');
                }

                const dispTotal = v.disp_indica.items.length + v.disp_hybrid.items.length + v.disp_sativa.items.length;
                const col4Total = v.vapes_510_sativa.items.length + dispTotal;
                let col4Html = '';
                if (v.vapes_510_sativa.items.length) {
                    col4Html += `<div class="subhead sativa"><span style="color:#FF6666;">510 Sativa</span> <span style="font-size:11px; color:#888;">${v.vapes_510_sativa.items.length} SKUs</span></div>`;
                    col4Html += v.vapes_510_sativa.items.map(it => renderRowHtml(it, true)).join('');
                }
                if (dispTotal > 0) {
                    col4Html += `<div class="subhead disposable" style="margin-top:10px;"><span style="color:#f472b6;">All-in-One Disposables</span> <span style="font-size:11px; color:#888;">${dispTotal} SKUs</span></div>`;
                    col4Html += v.disp_indica.items.map(it => renderRowHtml(it, true)).join('');
                    col4Html += v.disp_hybrid.items.map(it => renderRowHtml(it, true)).join('');
                    col4Html += v.disp_sativa.items.map(it => renderRowHtml(it, true)).join('');
                }

                mount.innerHTML = `
                    <div class="container-vapes-flower">
                        <div class="panel">
                            <div class="title indica">INDICA & HYBRID FLOWER <span class="title-count">(${col1Total})</span></div>
                            <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                            ${col1Html}
                        </div>
                        <div class="panel">
                            <div class="title sativa">SATIVA FLOWER <span class="title-count">(${satTotal})</span></div>
                            <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                            ${col2Html}
                        </div>
                        <div class="panel">
                            <div class="title vapes510">510 CARTRIDGES <span class="title-count">(${v510Total})</span></div>
                            <div class="table-header"><div class="h-name">Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                            ${col3Html}
                        </div>
                        <div class="panel">
                            <div class="title disposable">VAPES & DISPOSABLES <span class="title-count">(${col4Total})</span></div>
                            <div class="table-header"><div class="h-name">Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                            ${col4Html}
                        </div>
                    </div>
                `;
            } else {
                // Screen 3: Edibles, Drinks & Concentrates
                const d = res.structured;
                const gSat = (d.gummies_sativa && d.gummies_sativa.items) || [];
                const choc = (d.chocolates && d.chocolates.items) || [];
                const col3EdiblesTotal = gSat.length + choc.length;

                const col3Html = `
                    <div class="soft-card card-pink">
                        <div class="card-head-title">SOFT CHEWS & CHOCOLATES <span class="title-count">(${col3EdiblesTotal})</span></div>
                        <div class="card-head-sub">SATIVA GUMMIES • ARTISAN CHOCOLATES</div>
                        <div class="table-header-soft">
                            <div>PRODUCT</div>
                            <div style="text-align:center;">STRAIN</div>
                            <div style="text-align:center;">THC</div>
                            <div style="text-align:center;">CBD</div>
                            <div style="text-align:right;">PRICE</div>
                        </div>
                        ${gSat.length > 0 ? `
                            <div class="subhead" style="color:#f472b6; margin: 4px 0 2px; font-size:12px;"><span>Sativa Soft Chews</span> <span style="font-size:11px; color:#888;">${gSat.length} SKUs</span></div>
                            ${gSat.map(it => renderSoftRow(it)).join('')}
                        ` : ''}
                        ${choc.length > 0 ? `
                            <div class="subhead" style="color:#fb923c; margin: 8px 0 2px; font-size:12px;"><span>Artisan Chocolates</span> <span style="font-size:11px; color:#888;">${choc.length} SKUs</span></div>
                            ${choc.map(it => renderSoftRow(it)).join('')}
                        ` : ''}
                    </div>
                `;

                mount.innerHTML = `
                    <div class="container-softchews">
                        <div class="column-deck">
                            ${renderSoftCard('concentrates', d)}
                            ${renderSoftCard('beverages', d)}
                        </div>
                        <div class="column-deck">
                            ${renderSoftCard('gummies_ind_hyb', d)}
                        </div>
                        <div class="column-deck">
                            ${col3Html}
                            ${renderSoftCard('wellness', d)}
                        </div>
                    </div>
                `;
            }

            document.getElementById('tv-sync-time').textContent = `TENDY LIVE • ${res.updated_at || ''}`;
            updateHappyHourBanner();
        }


        function updateHappyHourBanner() {
            const el = document.getElementById('happyHourBanner');
            if (!el) return;
            try {
                const now = new Date();
                const torontoHour = parseInt(new Intl.DateTimeFormat('en-US', { timeZone: 'America/Toronto', hour: 'numeric', hour12: false }).format(now), 10);
                const isActive = (torontoHour >= 13 && torontoHour < 16);

                if (isActive) {
                    el.className = 'happy-hour-pill active';
                    el.innerHTML = '<span style="color:#ef4444; font-size:12px;">⚡</span> <strong>HAPPY HOUR ACTIVE (1 PM – 4 PM)</strong> • SPECIAL PRICING IN EFFECT';
                } else {
                    el.className = 'happy-hour-pill idle';
                    el.innerHTML = '<i class="bi bi-clock-history" style="color:#facc15;"></i> Daily Happy Hour: <strong>1:00 PM – 4:00 PM</strong>';
                }
            } catch (e) {}
        }

        function pollLive() {
            fetch(`tv_menu.php?api=1&screen=${currentScreen}`)
                .then(r => r.json())
                .then(data => { if (data.success) renderScreen(data); })
                .catch(e => console.error(e));
        }

        function toggleFullscreen() {
            if (!document.fullscreenElement) document.documentElement.requestFullscreen().catch(() => {});
            else if (document.exitFullscreen) document.exitFullscreen();
        }

        // Auto-hide navigation on idle
        let idleTimer;
        function showNav() {
            const el = document.getElementById('floatingNav');
            if (el) el.classList.remove('hidden');
            clearTimeout(idleTimer);
            idleTimer = setTimeout(() => { if (el) el.classList.add('hidden'); }, 3500);
        }
        window.addEventListener('mousemove', showNav);
        window.addEventListener('touchstart', showNav);

        document.addEventListener('DOMContentLoaded', () => {
            renderScreen(initialData);
            setInterval(pollLive, 25000);
        });

        const SEASONAL_THEMES = {
            emerald: { name: '🌿 4/20 Emerald Cannabis', colors: ['rgba(34, 197, 94, ', 'rgba(74, 222, 128, ', 'rgba(16, 185, 129, ', 'rgba(250, 204, 21, '] },
            summer: { name: '☀️ Summer Gold & Sunset', colors: ['rgba(250, 204, 21, ', 'rgba(234, 179, 8, ', 'rgba(245, 158, 11, ', 'rgba(74, 222, 128, '] },
            halloween: { name: '🎃 Autumn Ember & Firefly', colors: ['rgba(249, 115, 22, ', 'rgba(234, 88, 12, ', 'rgba(245, 158, 11, ', 'rgba(239, 68, 68, '] },
            winter: { name: '❄️ Winter Crystal & Frost', colors: ['rgba(56, 189, 248, ', 'rgba(147, 197, 253, ', 'rgba(224, 242, 254, ', 'rgba(192, 132, 252, '] },
            velvet: { name: '🌹 Velvet Crimson Lounge', colors: ['rgba(239, 68, 68, ', 'rgba(244, 63, 94, ', 'rgba(250, 204, 21, ', 'rgba(168, 85, 247, '] }
        };

        function getAutoSeasonTheme() {
            const now = new Date();
            const month = now.getMonth() + 1;
            if (month === 4) return 'emerald';
            if (month >= 5 && month <= 8) return 'summer';
            if (month >= 9 && month <= 10) return 'halloween';
            if (month >= 11 || month === 1) return 'winter';
            if (month === 2) return 'velvet';
            if (month === 3) return 'emerald';
            return 'summer';
        }

        let currentThemeKey = 'auto';
        let ambientCanvasEngine = null;

        function setAmbientTheme(themeKey, showToast = true) {
            currentThemeKey = themeKey;
            const resolvedKey = (themeKey === 'auto' || !SEASONAL_THEMES[themeKey]) ? getAutoSeasonTheme() : themeKey;
            const themeConfig = SEASONAL_THEMES[resolvedKey];
            if (ambientCanvasEngine && ambientCanvasEngine.updateTheme) {
                ambientCanvasEngine.updateTheme(themeConfig);
            }
            if (showToast) {
                showThemeToast(themeConfig.name + (themeKey === 'auto' ? ' (Auto Calendar)' : ' (Manual)'));
            }
        }

        function showThemeToast(themeName) {
            let toast = document.getElementById('themeToast');
            if (!toast) {
                toast = document.createElement('div');
                toast.id = 'themeToast';
                toast.style.cssText = 'position:fixed; top:42px; left:50%; transform:translateX(-50%); background:rgba(0,0,0,0.88); border:1px solid rgba(250,204,21,0.5); color:#facc15; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:800; z-index:9999; pointer-events:none; transition:opacity 0.3s; box-shadow:0 4px 16px rgba(0,0,0,0.8);';
                document.body.appendChild(toast);
            }
            toast.textContent = `🎨 Ambiance: ${themeName}`;
            toast.style.opacity = '1';
            clearTimeout(toast._timer);
            toast._timer = setTimeout(() => { toast.style.opacity = '0'; }, 2400);
        }

        function initAmbientParticles(initialTheme = 'auto') {
            const canvas = document.getElementById('ambientCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            if (!ctx) return;

            let width = (canvas.width = window.innerWidth);
            let height = (canvas.height = window.innerHeight);

            window.addEventListener('resize', () => {
                width = canvas.width = window.innerWidth;
                height = canvas.height = window.innerHeight;
            });

            let currentResolved = (initialTheme === 'auto' || !SEASONAL_THEMES[initialTheme]) ? getAutoSeasonTheme() : initialTheme;
            let activeColors = SEASONAL_THEMES[currentResolved].colors;

            const particles = [];
            const particleCount = 38;

            for (let i = 0; i < particleCount; i++) {
                particles.push({
                    x: Math.random() * width,
                    y: Math.random() * height,
                    radius: Math.random() * 2.2 + 0.8,
                    baseAlpha: Math.random() * 0.35 + 0.12,
                    speedY: -(Math.random() * 0.32 + 0.1),
                    speedX: (Math.random() - 0.5) * 0.22,
                    color: activeColors[Math.floor(Math.random() * activeColors.length)],
                    pulseOffset: Math.random() * Math.PI * 2
                });
            }

            ambientCanvasEngine = {
                updateTheme: (themeConfig) => {
                    activeColors = themeConfig.colors;
                    for (let i = 0; i < particles.length; i++) {
                        particles[i].color = activeColors[Math.floor(Math.random() * activeColors.length)];
                    }
                }
            };

            let tick = 0;
            function animate() {
                ctx.clearRect(0, 0, width, height);
                tick += 0.018;

                for (let i = 0; i < particleCount; i++) {
                    const p = particles[i];
                    p.y += p.speedY;
                    p.x += p.speedX + Math.sin(tick + p.pulseOffset) * 0.15;

                    if (p.y < -10) { p.y = height + 10; p.x = Math.random() * width; }
                    if (p.x < -10) p.x = width + 10;
                    if (p.x > width + 10) p.x = -10;

                    const alpha = p.baseAlpha + Math.sin(tick * 1.5 + p.pulseOffset) * 0.08;

                    const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.radius * 2.6);
                    grad.addColorStop(0, p.color + Math.max(0, Math.min(1, alpha * 1.5)) + ')');
                    grad.addColorStop(0.5, p.color + Math.max(0, Math.min(1, alpha * 0.5)) + ')');
                    grad.addColorStop(1, p.color + '0)');

                    ctx.fillStyle = grad;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.radius * 2.6, 0, Math.PI * 2);
                    ctx.fill();
                }

                requestAnimationFrame(animate);
            }

            animate();
        }

    </script>
</body>
</html>
