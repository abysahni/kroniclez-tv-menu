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
    'store_name'      => 'Kroniclez - Kitchener',
    'cache_ttl'       => 25 // seconds
];

// Determine screen and mode
$screen = isset($_GET['screen']) ? intval($_GET['screen']) : 1;
if ($screen < 1 || $screen > 3) $screen = 1;
$is_api = isset($_GET['api']) && $_GET['api'] == '1';

// Potency & Strain Database
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

function classifyStrain($name, $brand) {
    $full = strtolower("$brand $name");
    if (preg_replace('/\b(sativa|lemon|sour|haze|diesel|tangie|mango|sunshine|cough|acapulco|jack|linx|grapefruit|shockwave|sticky)\b/', '', $full) !== $full) return 'SATIVA';
    if (preg_replace('/\b(indica|kush|pink|purple|bubba|berry|og|punch|sleep|lights|zello|venom|freeze|tiger|cherry)\b/', '', $full) !== $full) return 'INDICA';
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

        $p_title = cleanTitle($name, $brand, $var, 1);
        $pot = lookupPotency($name, $brand, $POTENCY_MAP, '28.5%');
        $entry = [
            'product_name' => $p_title,
            'price' => $price,
            'brand' => $brand,
            'thc' => $pot['thc'],
            'cbd' => $pot['cbd'],
            'is_sale' => false
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

        $p_title = cleanTitle($name, $brand, $var, 2);
        $pot = lookupPotency($name, $brand, $POTENCY_MAP, '88.0%');
        $entry = [
            'product_name' => $p_title,
            'price' => $price,
            'brand' => $brand,
            'thc' => $pot['thc'],
            'cbd' => $pot['cbd'],
            'is_sale' => false
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
            'is_sale' => false
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
        * { margin: 0; padding: 0; box-sizing: border-box; user-select: none; -webkit-user-select: none; }
        html { background: #000000; font-size: 18px; }
        body { background: #000000; color: #ffffff; font-family: 'Plus Jakarta Sans', sans-serif; width: 100%; min-height: 100vh; overflow-x: hidden; overflow-y: auto; padding: 6px 8px; }
        
        .container-prerolls { display: grid; grid-template-columns: 1fr 1fr 1fr 1.25fr; gap: 8px; width: 100%; align-items: start; }
        .container-vapes-flower { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; width: 100%; align-items: start; }
        .container-softchews { display: grid; grid-template-columns: 1fr 1.05fr 1.05fr; gap: 8px; width: 100%; align-items: start; }
        .column-deck { display: flex; flex-direction: column; gap: 8px; min-width: 0; }

        .panel { background: #141414; border-radius: 8px; padding: 8px 10px; box-shadow: 0 4px 16px rgba(0,0,0,0.7); border: 1px solid rgba(255,255,255,0.08); }
        .soft-card { background: #0d1217; border: 1px solid #1c2a36; border-radius: 8px; padding: 8px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.5); width: 100%; }

        .card-head-title { text-align: center; font-size: 21px; line-height: 1.1; font-weight: 900; text-transform: uppercase; margin-bottom: 2px; letter-spacing: 0.6px; }
        .card-head-sub { text-align: center; color: #a0a0a0; font-size: 10px; line-height: 1; font-weight: 800; letter-spacing: 0.6px; margin-bottom: 6px; text-transform: uppercase; }

        .card-gold .card-head-title { color: #facc15; }
        .card-cyan .card-head-title { color: #38bdf8; }
        .card-purple .card-head-title { color: #c084fc; }
        .card-pink .card-head-title { color: #f472b6; }
        .card-orange .card-head-title { color: #fb923c; }

        .title { font-size: 21px; font-weight: 900; text-align: center; padding-bottom: 6px; margin-bottom: 6px; border-bottom: 1px solid #333333; letter-spacing: 0.6px; text-transform: uppercase; }
        .title-count { display: inline-block; font-size: 0.88em; font-weight: 800; margin-left: 3px; opacity: 0.9; }

        .indica { color: #4ade80; }
        .hybrid { color: #facc15; }
        .sativa { color: #f87171; }
        .infused { color: #38bdf8; }
        .vapes510 { color: #60a5fa; }
        .disposable { color: #f472b6; }

        .subhead { font-size: 14.5px; margin: 8px 0 4px; padding-bottom: 3px; border-bottom: 1px solid #3a3a3a; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; justify-content: space-between; }

        .table-header { display: grid; grid-template-columns: minmax(0, 1fr) 68px 74px; column-gap: 4px; margin: 3px 0; padding-bottom: 3px; border-bottom: 1px solid #383838; font-size: 11.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }
        .table-header-soft { display: grid; grid-template-columns: minmax(0, 1fr) 58px 46px 42px 70px; column-gap: 4px; align-items: center; font-size: 11px; font-weight: 900; text-transform: uppercase; padding-bottom: 4px; margin-bottom: 2px; border-bottom: 1px solid rgba(255,255,255,0.18); }

        .card-gold .table-header-soft { color: #facc15; }
        .card-cyan .table-header-soft { color: #38bdf8; }
        .card-purple .table-header-soft { color: #c084fc; }
        .card-pink .table-header-soft { color: #f472b6; }
        .card-orange .table-header-soft { color: #fb923c; }

        .h-name { color: #ffffff; text-align: left; }
        .h-thc { color: #4ade80; text-align: right; }
        .h-price { color: #facc15; text-align: right; }

        .p-row { display: grid; grid-template-columns: minmax(0, 1fr) 68px 74px; column-gap: 4px; align-items: center; padding: 3.5px 0; border-bottom: 1px solid rgba(255,255,255,0.08); }
        .p-row:last-child { border-bottom: none; }

        .p-name { min-width: 0; white-space: normal !important; word-break: break-word !important; overflow-wrap: break-word !important; overflow: visible !important; text-overflow: clip !important; font-size: 15px; font-weight: 700; padding-right: 4px; color: #ffffff; line-height: 1.25; }
        .p-thc { text-align: right; color: #4ade80; font-size: 15px; font-weight: 800; white-space: nowrap; font-family: 'JetBrains Mono', monospace; }

        .soft-row { display: grid; grid-template-columns: minmax(0, 1fr) 58px 46px 42px 70px; column-gap: 4px; align-items: center; padding: 4px 2px; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 14px; }
        .soft-row:last-child { border-bottom: none; }
        .soft-row:nth-child(even) { background: rgba(255,255,255,0.03); }

        .soft-name { min-width: 0; white-space: normal !important; word-break: break-word !important; overflow-wrap: break-word !important; overflow: visible !important; text-overflow: clip !important; color: #ffffff; font-weight: 700; font-size: 14.5px; line-height: 1.25; padding-right: 4px; }
        .soft-meta { text-align: center; font-size: 11.5px; font-weight: 800; white-space: nowrap; }
        .meta-indica { color: #4ade80 !important; }
        .meta-hybrid { color: #facc15 !important; }
        .meta-sativa { color: #f87171 !important; }

        .soft-thc { text-align: center; color: #4ade80; font-weight: 800; font-size: 14.5px; font-family: 'JetBrains Mono', monospace; white-space: nowrap; }
        .soft-cbd { text-align: center; color: #cbd5e1; font-size: 13px; font-weight: 700; font-family: 'JetBrains Mono', monospace; white-space: nowrap; }

        .p-price { display: flex; flex-direction: column; align-items: flex-end; justify-content: center; line-height: 1; white-space: nowrap; text-align: right; }
        .p-price .regular { color: #facc15; font-size: 16.5px; font-weight: 900; font-family: 'JetBrains Mono', monospace; }
        .p-price .sale { color: #ef4444; font-size: 17px; font-weight: 900; font-family: 'JetBrains Mono', monospace; }
        .p-price .old { color: #facc15; font-size: 11px; font-weight: 700; text-decoration: line-through; opacity: 0.8; font-family: 'JetBrains Mono', monospace; }

        .badge-strain { font-size: 9px; font-weight: 800; padding: 1px 4px; border-radius: 4px; margin-right: 4px; text-transform: uppercase; display: inline-block; }
        .b-indica { background: rgba(74, 222, 128, 0.2); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.5); }
        .b-hybrid { background: rgba(250, 204, 21, 0.2); color: #facc15; border: 1px solid rgba(250, 204, 21, 0.5); }
        .b-sativa { background: rgba(248, 113, 113, 0.2); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.5); }

        .tv-sync-status { position: fixed; top: 8px; right: 12px; font-size: 11px; font-family: 'JetBrains Mono', monospace; color: #888; display: flex; align-items: center; gap: 6px; pointer-events: none; z-index: 100; }
        .pulse-dot { width: 7px; height: 7px; border-radius: 50%; background: #4ade80; box-shadow: 0 0 8px #4ade80; }

        .tv-floating-nav { position: fixed; bottom: 12px; left: 50%; transform: translateX(-50%); background: rgba(18, 18, 18, 0.95); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 999px; padding: 5px 14px; display: flex; align-items: center; gap: 8px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.8); z-index: 9999; backdrop-filter: blur(10px); transition: opacity 0.3s ease, transform 0.3s ease; }
        .tv-floating-nav.hidden { opacity: 0; pointer-events: none; transform: translate(-50%, 20px); }
        .nav-link-btn { color: #cbd5e1; font-size: 12px; font-weight: 700; text-decoration: none; padding: 5px 14px; border-radius: 999px; background: #202020; border: 1px solid #383838; display: inline-flex; align-items: center; gap: 4px; transition: all 0.2s ease; cursor: pointer; }
        .nav-link-btn.active, .nav-link-btn:hover { background: #4ade80; color: #000000; border-color: #4ade80; font-weight: 900; box-shadow: 0 0 12px rgba(74, 222, 128, 0.4); }
    </style>
</head>
<body>

    <!-- TV Sync Status Indicator -->
    <div class="tv-sync-status">
        <span class="pulse-dot"></span>
        <span id="tv-sync-time">TENDY LIVE SYNC</span>
    </div>

    <!-- Main TV Screen Mount -->
    <main id="menuMount"></main>

    <!-- Floating Navigation Bar -->
    <nav id="floatingNav" class="tv-floating-nav">
        <span style="font-size: 10px; font-weight: 900; color: #777;">DEDICATED TV:</span>
        <a href="?screen=1" id="nav-btn-screen1" class="nav-link-btn <?= $screen === 1 ? 'active' : '' ?>"><i class="bi bi-fire"></i> TV 1: Pre-Rolls</a>
        <a href="?screen=2" id="nav-btn-screen2" class="nav-link-btn <?= $screen === 2 ? 'active' : '' ?>"><i class="bi bi-flower1"></i> TV 2: Vapes & Flower</a>
        <a href="?screen=3" id="nav-btn-screen3" class="nav-link-btn <?= $screen === 3 ? 'active' : '' ?>"><i class="bi bi-cup-straw"></i> TV 3: Edibles & Drinks</a>
        <button type="button" class="nav-link-btn" onclick="toggleFullscreen()" title="Toggle Fullscreen (F)"><i class="bi bi-fullscreen"></i></button>
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
                <div class="p-row">
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

            let priceHtml = (it.is_sale && it.old_price) 
                ? `<span class="sale">${formatCAD(it.price)}</span><span class="old">${formatCAD(it.old_price)}</span>`
                : `<span class="regular">${formatCAD(it.price)}</span>`;

            return `
                <div class="soft-row">
                    <div class="soft-name">${it.product_name}</div>
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
            const subHtml = sec.subtitle ? `<div class="card-head-sub">${sec.subtitle}</div>` : '';
            return `
                <div class="soft-card card-${sec.color || 'gold'}">
                    <div class="card-head-title">${sec.title} <span class="title-count">(${sec.items.length})</span></div>
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
    </script>
</body>
</html>
