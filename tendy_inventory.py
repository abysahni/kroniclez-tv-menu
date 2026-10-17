import os
import json
import re
import ssl
import time
import urllib.request
import urllib.parse
import base64
import threading
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
try:
    from zoneinfo import ZoneInfo
    TORONTO_TZ = ZoneInfo("America/Toronto")
except ImportError:
    TORONTO_TZ = timezone(timedelta(hours=-4))

import config
from promotion_engine import promotion_engine

def get_toronto_now() -> datetime:
    """Return current timestamp strictly in America/Toronto timezone."""
    return datetime.now(TORONTO_TZ)

def is_happy_hour_active() -> bool:
    """Returns True strictly when daily promotion is running between 1:00 PM (13:00) and 4:00 PM (16:00) Toronto time."""
    now_toronto = get_toronto_now()
    return 13 <= now_toronto.hour < 16

REGULAR_PRICES_PATH = os.path.join(os.path.dirname(__file__), "regular_prices.json")

def load_regular_prices_registry() -> Dict[str, Any]:
    try:
        if os.path.exists(REGULAR_PRICES_PATH):
            with open(REGULAR_PRICES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading regular prices: {e}")
    return {}


def load_product_overrides() -> Dict[str, Any]:
    data = {"species_overrides": {}, "highlight_overrides": {}, "thc_overrides": {}, "category_overrides": {}}
    if config.OVERRIDES_FILE.exists():
        try:
            with open(config.OVERRIDES_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data.update(loaded)
                    data.setdefault("category_overrides", {})
                    data.setdefault("species_overrides", {})
                    data.setdefault("highlight_overrides", {})
                    data.setdefault("thc_overrides", {})
                    return data
        except Exception:
            pass
    return data


def find_matching_override(name: str, brand: str = "", overrides_dict: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Optional[Any]]:
    """
    Finds the best matching override key and value for a product name and brand.
    Prioritizes:
    1. Exact match on raw name or full name (brand + name)
    2. Longest specific substring match where override pattern is contained in full_name or raw_name
    Guarantees that generic short names do NOT accidentally match longer unrelated pattern keys.
    """
    if not overrides_dict:
        return None, None
        
    name_low = str(name or "").lower().strip()
    brand_low = str(brand or "").lower().strip()
    full_low = f"{brand_low} {name_low}".strip()
    
    # 1. Exact match (highest priority)
    for pattern, val in overrides_dict.items():
        p_low = pattern.lower().strip()
        if p_low and (p_low == name_low or p_low == full_low):
            return pattern, val
            
    # 2. Specific substring match: sorted by pattern length descending (longest, most specific pattern wins)
    sorted_patterns = sorted(overrides_dict.items(), key=lambda x: len(x[0].strip()), reverse=True)
    for pattern, val in sorted_patterns:
        p_low = pattern.lower().strip()
        if p_low and (p_low in full_low or p_low in name_low):
            return pattern, val
            
    return None, None

LEGACY_CLIENT_RELOAD_TRIGGER = '<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" onload="if(!window.__IS_V55_RUNNING__){window.__IS_V55_RUNNING__=true;window.location.reload(true);}" style="display:none;" width="0" height="0" alt="">'

VALID_TARGET_SECTIONS = {
    "PRE_ROLLS", "INFUSED_PREROLLS",
    "FLOWER_DRIED", "FLOWER_MILLED", "VAPES_510", "VAPES_DISPOSABLE",
    "GUMMIES", "BEVERAGES", "CHOCOLATES", "CONCENTRATES", "WELLNESS"
}

def get_item_target_section(it: Dict[str, Any]) -> str:
    """
    Determines which menu section an item belongs to across Screen 1, 2, and 3.
    Filters products strictly using the exact value in the Category column.
    Do not perform any text matching, keyword searching, or regex parsing within Product Name or Description.
    """
    raw_cat = it.get("categoryName") or it.get("category") or it.get("Category") or it.get("category_name") or ""
    if isinstance(raw_cat, dict):
        cat = str(raw_cat.get("name") or "").strip()
    else:
        cat = str(raw_cat).strip()

    # Screen 1 exact categories
    if cat == "Pre-Rolls":
        return "PRE_ROLLS"
    elif cat == "Infused Pre-Rolls":
        return "INFUSED_PREROLLS"

    # Screen 2 exact categories
    elif cat == "Flower":
        return "FLOWER_DRIED"
    elif cat == "Milled Flower":
        return "FLOWER_MILLED"
    elif cat == "510 Cartridges":
        return "VAPES_510"
    elif cat in ["Disposable Vapes", "Vapes"]:
        return "VAPES_DISPOSABLE"

    # Screen 3 exact categories
    elif cat == "Concentrates":
        return "CONCENTRATES"
    elif cat == "Beverages":
        return "BEVERAGES"
    elif cat in ["Soft Chews", "Gummies"]:
        return "GUMMIES"
    elif cat == "Chocolates":
        return "CHOCOLATES"
    elif cat in ["Oils & Capsules", "Topicals", "Oils", "Capsules", "Wellness"]:
        return "WELLNESS"

    return "UNKNOWN"

def _sync_overrides_to_github_worker(data: Dict[str, Any]):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return
    repo = os.getenv("GITHUB_REPO", "abysahni/kroniclez-tv-menu")
    path = "product_overrides.json"
    branch = os.getenv("GITHUB_BRANCH", "main")
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Kroniclez-Menu-Sync"
        })
        sha = None
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                info = json.loads(resp.read().decode("utf-8"))
                sha = info.get("sha")
        except Exception:
            pass

        json_str = json.dumps(data, indent=2)
        b64 = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
        payload = {
            "message": f"Auto-sync overrides from Staff Portal [{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}]",
            "content": b64,
            "branch": branch
        }
        if sha:
            payload["sha"] = sha

        put_url = f"https://api.github.com/repos/{repo}/contents/{path}"
        put_req = urllib.request.Request(
            put_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "Kroniclez-Menu-Sync"
            },
            method="PUT"
        )
        with urllib.request.urlopen(put_req, timeout=12) as put_resp:
            print(f"✅ [GitHub Sync] Overrides pushed successfully to {repo} (HTTP {put_resp.status})")
    except Exception as e:
        print(f"⚠️ [GitHub Sync] Error syncing to GitHub: {e}")

def save_product_overrides(data: Dict[str, Any]) -> bool:
    try:
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(config.OVERRIDES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        # Flush in-memory cache so next request picks it up immediately
        inventory_service.clear_cache()
        # Auto-sync to GitHub repo in background if GITHUB_TOKEN configured
        if os.getenv("GITHUB_TOKEN"):
            threading.Thread(target=_sync_overrides_to_github_worker, args=(data,), daemon=True).start()
        return True
    except Exception as e:
        print(f"Error saving overrides: {e}")
        return False

def compute_item_pricing(it: Dict[str, Any], screen_id: int = 1) -> Dict[str, Any]:
    """
    Computes active price and original price.
    Automatically detects if product has a regular price registry entry where Sale Price < Regular Price,
    or if an active multi-promotion rule applies.
    """
    pricing = it.get("productPricing") or {}
    sale_p = float(pricing.get("sale_price") or 0.0)
    name = it.get("name", "")
    cat = (it.get("category") or {}).get("name", "")
    brand = (it.get("brand") or {}).get("name", "")
    barcode = str(it.get("barcode") or "")
    sku = str(it.get("sku") or "")
    name_low = name.lower()

    # 0. Check custom Highlight Overrides first from Admin Portal
    overrides_db = load_product_overrides()
    highlight_ov = overrides_db.get("highlight_overrides", {})
    matched_hl_key, hl_type = find_matching_override(name, brand, highlight_ov)
    if matched_hl_key and hl_type:
        if hl_type == "FEATURED":
            return {
                "price": sale_p,
                "old_price": round(sale_p * 1.15, 2),
                "is_sale": True,
                "tag": "FEATURED",
                "promo_name": "Featured Special"
            }
        elif hl_type in ["NEW", "NEW_DROP", "NEW DROP"]:
            return {
                "price": sale_p,
                "old_price": None,
                "is_sale": False,
                "tag": "NEW DROP",
                "promo_name": "New Drop"
            }
        elif hl_type in ["STAFF_PICK", "STAFF PICK"]:
            return {
                "price": sale_p,
                "old_price": None,
                "is_sale": False,
                "tag": "STAFF PICK",
                "promo_name": "Staff Pick"
            }
        elif hl_type in ["NONE", "REGULAR", "STANDARD"]:
            return {
                "price": sale_p,
                "old_price": None,
                "is_sale": False,
                "tag": None,
                "promo_name": None
            }

    # 1. Check direct Regular Price Registry (e.g. Pineapple Nuken $22.99 regular vs $19.98 sale)
    reg_registry = load_regular_prices_registry()
    products_map = reg_registry.get("products", {})
    
    matched_entry = None
    if barcode and barcode in products_map:
        matched_entry = products_map[barcode]
    elif sku and sku in products_map:
        matched_entry = products_map[sku]
    else:
        for k, v in products_map.items():
            v_name = (v.get("name") or "").lower()
            # Require at least 2 distinct words to match or match specific phrase
            key_words = [w for w in re.findall(r"\w+", v_name) if len(w) > 3 and w not in ["pre", "rolls", "roll", "cartridge", "flower", "thread", "disposable", "indica", "sativa", "hybrid"]]
            if key_words and all(kw in name_low for kw in key_words):
                matched_entry = v
                break

    if matched_entry:
        reg_p = float(matched_entry.get("regular_price", 0.0))
        tag_val = matched_entry.get("tag", "FEATURED")
        if reg_p > sale_p and (reg_p - sale_p) >= 0.05:
            return {
                "price": sale_p,
                "old_price": reg_p,
                "is_sale": True,
                "tag": tag_val,
                "promo_name": "Featured Sale Price"
            }
        elif tag_val == "STAFF PICK":
            return {
                "price": sale_p,
                "old_price": None,
                "is_sale": False,
                "tag": "STAFF PICK",
                "promo_name": "Staff Pick"
            }

    # 2. Check Multi-Promotion Engine (e.g. Happy Hour / category promotions)
    promo_res = promotion_engine.evaluate_item(name, cat, brand, sale_p)
    return {
        "price": sale_p,
        "old_price": promo_res.get("old_price"),
        "is_sale": promo_res.get("is_sale", False),
        "tag": "FEATURED" if promo_res.get("is_sale") else None,
        "promo_name": promo_res.get("promo_name")
    }

def is_accessory(it: Dict[str, Any]) -> bool:
    """Filter out non-cannabis accessories strictly using the exact Category column."""
    raw_cat = it.get("categoryName") or it.get("category") or it.get("Category") or it.get("category_name") or ""
    if isinstance(raw_cat, dict):
        cat = str(raw_cat.get("name") or "").strip()
    else:
        cat = str(raw_cat).strip()

    accessory_categories = {
        "Accessories", "510 Battery", "Bongs", "Grinder", "Lighers", "Lighters",
        "Pre Rolled Cone", "Rolling Papers", "Scale", "Tray", "Device", "Glass", "Pipe", "Cleaning", "Apparel"
    }
    return cat in accessory_categories

def clean_product_title(name: str, brand: str = "", variant: str = "", screen_id: int = 1) -> str:
    """Format and clean product title cleanly with brand, name, and size (e.g. BRAND • Strain Name 1x0.5g)."""
    b = (brand or "").strip().upper()
    n = (name or "").strip()
    v = (variant or "").strip()

    # Clean redundant category keywords
    n = re.sub(r'\s+Pre-Rolls?', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s+510 Thread Cartridge', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s+510 Thread', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s+510 Cartridge', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s+510 Vape Cart', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s+All-in-One Vape', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s+All-in-One', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s+Disposable', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s+Dried Flower', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s*-\s*', ' ', n)

    if b and n.upper().startswith(f"{b} ") and len(n) > len(b) + 3 and not any(k in n.lower() for k in ["lil buddy indica", "lil buddy sativa"]):
        n = n[len(b):].strip(" -:•")

    if v:
        if v.lower() not in n.lower():
            final = f"{b} • {n} {v}" if b else f"{n} {v}"
        else:
            final = f"{b} • {n}" if b else n
    else:
        final = f"{b} • {n}" if b else n

    return re.sub(r'\s+', ' ', final).strip(" -:•")
        
def get_item_strain(it: Any) -> str:
    """
    Evaluate the Strain column strictly for an exact match.
    Do not perform any text matching, keyword searching, or regex parsing within Product Name or Description.
    Returns: 'SATIVA', 'HYBRID', or 'INDICA'.
    """
    if isinstance(it, dict):
        raw = it.get("strain") or it.get("Strain") or it.get("species") or it.get("Species") or it.get("strainType") or ""
        if isinstance(raw, dict):
            raw = raw.get("name") or ""
    elif isinstance(it, str):
        raw = it
    else:
        raw = ""

    s = str(raw).strip().lower()
    if s == "sativa":
        return "SATIVA"
    elif s in ["hybrid", "blend"]:
        return "HYBRID"
    elif s == "indica":
        return "INDICA"
    return "HYBRID"

def classify_preroll(it_or_name: Any, brand: str = "") -> str:
    return get_item_strain(it_or_name)

def classify_flower(it_or_name: Any, brand: str = "") -> str:
    return get_item_strain(it_or_name)

def classify_vape(it_or_name: Any, brand: str = "") -> str:
    return get_item_strain(it_or_name)

# =========================================================================
# KRONICLEZ AUTHENTIC LAB-TESTED THC & CBD POTENCY DATABASE
# Comprehensive cross-verified mapping for Screen 1, Screen 2, & Screen 3
# =========================================================================
PRODUCT_POTENCY_DATABASE = {
    # SCREEN 1: INFUSED PRE-ROLLS
    "baby jeeter berry white": {"thc": "40.0%", "cbd": "1.0%"},
    "baby jeeter multi-pack": {"thc": "40.0%", "cbd": "2.0%"},
    "berry sunshine hi-fi": {"thc": "49.0%", "cbd": "0.04%"},
    "big bang berry": {"thc": "61.0%", "cbd": "4.0%"},
    "flyers frosted infused pineapple express": {"thc": "42.0%", "cbd": "3.0%"},
    "flyers frosted infused strawberry cough": {"thc": "38.5%", "cbd": "<1.0%"},
    "strawberry cough": {"thc": "38.5%", "cbd": "<1.0%"},
    "flyers infused blunt blue dream": {"thc": "50.5%", "cbd": "1.5%"},
    "flyers infused blunt watermelon z": {"thc": "50.5%", "cbd": "1.5%"},
    "fully charged party pack": {"thc": "40.0%", "cbd": "4.0%"},
    "grapey grape": {"thc": "48.0%", "cbd": "0.01%"},
    "heavy hitter flower & diamonds": {"thc": "50.0%", "cbd": "0.23%"},
    "high potency 50+ diamond infused macchiato gold": {"thc": "56.0%", "cbd": "1.0%"},
    "high potency 50+ diamond infused strawberry": {"thc": "54.0%", "cbd": "<1.0%"},
    "diamond infused strawberry": {"thc": "54.0%", "cbd": "<1.0%"},
    "infused multi strain pack": {"thc": "41.0%", "cbd": "1.0%"},
    "island rush": {"thc": "37.0%", "cbd": "0.1%"},
    "northern lights 60+ diamonds & shatter": {"thc": "63.0%", "cbd": "3.0%"},
    "pink gas": {"thc": "44.0%", "cbd": "2.3%"},
    "purple punch distillate": {"thc": "45.0%", "cbd": "0.07%"},
    "qwazars - solventless hash infused joint": {"thc": "36.0%", "cbd": "0.15%"},
    "qwazars": {"thc": "36.0%", "cbd": "0.15%"},
    "red jasper diamond infused rose blunts": {"thc": "40.5%", "cbd": "0.75%"},
    "titanimal bubble": {"thc": "46.0%", "cbd": "0.7%"},

    # SCREEN 1: INDICA PRE-ROLLS
    "bahama berry": {"thc": "29.0%", "cbd": "3.0%"},
    "bc organic pink drip": {"thc": "27.5%", "cbd": "0.5%"},
    "blueberry": {"thc": "26.0%", "cbd": "0.5%"},
    "cali kush": {"thc": "31.0%", "cbd": "0.01%"},
    "couch potato": {"thc": "30.0%", "cbd": "1.0%"},
    "diesel pocket puffs": {"thc": "29.0%", "cbd": "1.0%"},
    "dutchy blunt": {"thc": "29.2%", "cbd": "0.01%"},
    "frozen grapes": {"thc": "31.0%", "cbd": "1.0%"},
    "junior j": {"thc": "21.5%", "cbd": "1.0%"},
    "kush cookies": {"thc": "29.5%", "cbd": "0.15%"},
    "lil buddy indica": {"thc": "28.0%", "cbd": "0.5%"},
    "permanent marker": {"thc": "32.0%", "cbd": "1.0%"},
    "pink kush": {"thc": "25.0%", "cbd": "0.1%"},
    "pink moon": {"thc": "27.5%", "cbd": "0.5%"},
    "redees hemp'd animal rntz": {"thc": "32.5%", "cbd": "0.5%"},
    "animal rntz": {"thc": "32.5%", "cbd": "0.5%"},
    "roll up indica": {"thc": "26.0%", "cbd": "0.5%"},
    "triangle kush 3000": {"thc": "26.0%", "cbd": "1.0%"},
    "uk cheddar cheese": {"thc": "30.0%", "cbd": "0.05%"},
    "wedding cake": {"thc": "32.5%", "cbd": "<0.5%"},
    "zombie kush": {"thc": "32.0%", "cbd": "0.6%"},

    # SCREEN 1: HYBRID PRE-ROLLS
    "10th planet": {"thc": "28.0%", "cbd": "3.4%"},
    "animal mintz slims": {"thc": "28.3%", "cbd": "0.1%"},
    "backpackers blue magic": {"thc": "28.0%", "cbd": "0.6%"},
    "blue magic": {"thc": "28.0%", "cbd": "0.6%"},
    "billy blunt": {"thc": "29.0%", "cbd": "0.01%"},
    "forbidden applez": {"thc": "32.0%", "cbd": "1.0%"},
    "grape diamonds": {"thc": "28.0%", "cbd": "0.5%"},
    "liquid imagination": {"thc": "30.0%", "cbd": "0.5%"},
    "panama gold": {"thc": "31.0%", "cbd": "1.0%"},
    "peggys puff": {"thc": "28.0%", "cbd": "3.0%"},
    "plg #7 pink lemon gas": {"thc": "27.0%", "cbd": "1.0%"},
    "plg #7": {"thc": "27.0%", "cbd": "1.0%"},
    "rolls": {"thc": "27.0%", "cbd": "0.5%"},
    "sgt. pineapple hoagies": {"thc": "30.5%", "cbd": "0.5%"},
    "sour kush": {"thc": "24.0%", "cbd": "0.5%"},
    "twofer": {"thc": "28.0%", "cbd": "1.0%"},

    # SCREEN 1: SATIVA PRE-ROLLS
    "animal face": {"thc": "31.0%", "cbd": "1.0%"},
    "backpackers lemon diesel": {"thc": "31.0%", "cbd": "0.25%"},
    "lemon diesel": {"thc": "31.0%", "cbd": "0.25%"},
    "bc organic fruit loopz": {"thc": "27.0%", "cbd": "0.5%"},
    "blueberry dream": {"thc": "29.0%", "cbd": "0.5%"},
    "cherry boat": {"thc": "25.0%", "cbd": "<0.5%"},
    "crumbled lime": {"thc": "29.5%", "cbd": "0.5%"},
    "double dutchies double up": {"thc": "33.0%", "cbd": "0.68%"},
    "fruit punch slims": {"thc": "27.0%", "cbd": "0.5%"},
    "juicy blunt": {"thc": "29.0%", "cbd": "0.01%"},
    "lavender haze": {"thc": "26.0%", "cbd": "0.5%"},
    "lemon shocker": {"thc": "31.5%", "cbd": "1.0%"},
    "lil buddy sativa": {"thc": "26.5%", "cbd": "0.5%"},
    "maui wowie": {"thc": "31.5%", "cbd": "1.0%"},
    "opp sativa-indica variety pack": {"thc": "30.0%", "cbd": "0.5%"},
    "pineapple express": {"thc": "31.5%", "cbd": "1.5%"},
    "pineapple nuken": {"thc": "31.0%", "cbd": "0.07%"},
    "pink rozay": {"thc": "28.5%", "cbd": "3.0%"},
    "roll up sativa": {"thc": "21.5%", "cbd": "0.5%"},
    "rooster call": {"thc": "30.0%", "cbd": "1.0%"},
    "sour chem": {"thc": "31.0%", "cbd": "<0.5%"},
    "tropical pocket puffs": {"thc": "29.5%", "cbd": "1.0%"},
    "zsweet": {"thc": "29.5%", "cbd": "1.0%"},

    # SCREEN 2: INDICA VAPES (510 & Disposables)
    "blue razz fuel cell": {"thc": "92.0%", "cbd": "1.0%"},
    "blue venom": {"thc": "94.0%", "cbd": "1.0%"},
    "blueberry kush": {"thc": "90.0%", "cbd": "1.0%"},
    "cherry liquid diamond": {"thc": "86.0%", "cbd": "0.5%"},
    "hard hitters blue zello": {"thc": "98.0%", "cbd": "1.0%"},
    "blue zello": {"thc": "98.0%", "cbd": "1.0%"},
    "high potency 92+ 510 hawaiian za": {"thc": "97.5%", "cbd": "1.0%"},
    "hawaiian za": {"thc": "97.5%", "cbd": "1.0%"},
    "indica 510": {"thc": "99.0%", "cbd": "1.0%"},
    "jungle fruit": {"thc": "94.0%", "cbd": "1.0%"},
    "lemon freeze live resin": {"thc": "77.0%", "cbd": "1.0%"},
    "liquid diamond blood orange tangie": {"thc": "96.0%", "cbd": "1.0%"},
    "blood orange tangie": {"thc": "96.0%", "cbd": "1.0%"},
    "tiger blood indica 1:0": {"thc": "92.0%", "cbd": "1.0%"},
    "tiger blood": {"thc": "92.0%", "cbd": "1.0%"},
    "watermelon splash liquid diamond": {"thc": "97.0%", "cbd": "1.0%"},
    "watermelon splash": {"thc": "97.0%", "cbd": "1.0%"},
    "wild berry": {"thc": "92.5%", "cbd": "1.0%"},
    "fruit punch bowl diamonds disposable": {"thc": "92.0%", "cbd": "1.0%"},
    "fruit punch bowl": {"thc": "92.0%", "cbd": "1.0%"},
    "mango fuzz boosted disposable": {"thc": "84.0%", "cbd": "1.0%"},
    "mango fuzz": {"thc": "84.0%", "cbd": "1.0%"},
    "watermelon ice disposable": {"thc": "98.0%", "cbd": "1.0%"},
    "watermelon ice": {"thc": "98.0%", "cbd": "1.0%"},

    # SCREEN 2: HYBRID VAPES (510 & Disposables)
    "banana og x kush mints": {"thc": "95.0%", "cbd": "1.0%"},
    "fruity gobbstomper fuel cell": {"thc": "92.0%", "cbd": "1.0%"},
    "fruity gobbstomper": {"thc": "92.0%", "cbd": "1.0%"},
    "hard hitters blueberry octane": {"thc": "98.0%", "cbd": "1.0%"},
    "blueberry octane": {"thc": "98.0%", "cbd": "1.0%"},
    "liquid diamond strawberry banana": {"thc": "99.0%", "cbd": "1.0%"},
    "strawberry banana": {"thc": "99.0%", "cbd": "1.0%"},
    "ninja fruit": {"thc": "96.0%", "cbd": "1.0%"},
    "poppin peach live rosin amplified": {"thc": "87.5%", "cbd": "1.0%"},
    "poppin peach": {"thc": "87.5%", "cbd": "1.0%"},
    "high potency 92+ 510 cartridge macchiato gold": {"thc": "97.5%", "cbd": "1.0%"},
    "macchiato gold": {"thc": "97.5%", "cbd": "1.0%"},
    "alien og disposable": {"thc": "98.5%", "cbd": "1.0%"},
    "alien og": {"thc": "98.5%", "cbd": "1.0%"},
    "kush mint boosted disposable": {"thc": "84.0%", "cbd": "1.0%"},
    "kush mint": {"thc": "84.0%", "cbd": "1.0%"},
    "lemonade classic disposable": {"thc": "92.0%", "cbd": "1.0%"},
    "lemonade classic": {"thc": "92.0%", "cbd": "1.0%"},
    "drift mode": {"thc": "50.0%", "cbd": "9.3%", "cbn": "24.0%"},
    "fuel cell - drift mode": {"thc": "50.0%", "cbd": "9.3%", "cbn": "24.0%"},
    "fuel cell drift mode": {"thc": "50.0%", "cbd": "9.3%", "cbn": "24.0%"},

    # SCREEN 2: SATIVA VAPES (510 & Disposables)
    "acapulco gold": {"thc": "90.0%", "cbd": "1.0%"},
    "blue kiwi": {"thc": "95.5%", "cbd": "1.0%"},
    "hard hitters cloudberry": {"thc": "98.0%", "cbd": "1.0%"},
    "cloudberry": {"thc": "98.0%", "cbd": "1.0%"},
    "high potency 95+ 510 cartridge strawberry": {"thc": "97.5%", "cbd": "1.0%"},
    "liquid diamond pink grapefruit": {"thc": "98.0%", "cbd": "1.0%"},
    "pink grapefruit": {"thc": "98.0%", "cbd": "1.0%"},
    "mango sour cured resin": {"thc": "82.0%", "cbd": "1.0%"},
    "mango sour": {"thc": "82.0%", "cbd": "1.0%"},
    "mosa x blood orange": {"thc": "95.0%", "cbd": "1.0%"},
    "peach shockwave fuel cell": {"thc": "92.0%", "cbd": "1.0%"},
    "peach shockwave": {"thc": "92.0%", "cbd": "1.0%"},
    "sativa 510": {"thc": "93.0%", "cbd": "1.0%"},
    "sticky grape": {"thc": "95.3%", "cbd": "1.0%"},
    "strawberry lemonade 510": {"thc": "93.0%", "cbd": "1.0%"},
    "highlighters - blue daze disposable": {"thc": "98.5%", "cbd": "1.0%"},
    "blue daze": {"thc": "98.5%", "cbd": "1.0%"},
    "hitz - pineapple paradise disposable": {"thc": "91.5%", "cbd": "1.0%"},
    "pineapple paradise": {"thc": "91.5%", "cbd": "1.0%"},
    "peach lemonade disposable": {"thc": "98.0%", "cbd": "1.0%"},
    "rainbow melon boosted disposable": {"thc": "83.0%", "cbd": "1.0%"},
    "rainbow melon": {"thc": "83.0%", "cbd": "1.0%"},
    "sunset sherb x acai berry": {"thc": "95.0%", "cbd": "1.0%"},
    "sunset sherb": {"thc": "95.0%", "cbd": "1.0%"},

    # SCREEN 2: DRIED & MILLED FLOWER
    "pink kush": {"thc": "26.0%", "cbd": "0.1%"},
    "gasberry kush": {"thc": "27.0%", "cbd": "0.5%"},
    "gasberry": {"thc": "27.0%", "cbd": "0.5%"},
    "fire breath": {"thc": "30.0%", "cbd": "0.5%"},
    "blueberry muffinz": {"thc": "29.0%", "cbd": "0.15%"},
    "gmo cookies": {"thc": "27.3%", "cbd": "0.5%"},
    "purple cherry punch": {"thc": "32.0%", "cbd": "1.0%"},
    "cali kush milled": {"thc": "29.0%", "cbd": "1.0%"},
    "cropped blueberry": {"thc": "26.0%", "cbd": "0.5%"},
    "pure milled indica": {"thc": "28.0%", "cbd": "2.5%"},
    "pop n’ pour blue raspberry": {"thc": "27.0%", "cbd": "0.5%"},
    "pop n' pour blue raspberry": {"thc": "27.0%", "cbd": "0.5%"},
    "strawberry pie milled": {"thc": "28.5%", "cbd": "3.0%"},
    "chromatica": {"thc": "29.0%", "cbd": "1.0%"},
    "chubby nuggies": {"thc": "29.5%", "cbd": "2.5%"},
    "farmer's market": {"thc": "30.5%", "cbd": "1.0%"},
    "frosted cream puffs": {"thc": "30.5%", "cbd": "0.5%"},
    "moon drifter": {"thc": "28.0%", "cbd": "1.0%"},
    "secret formula": {"thc": "30.5%", "cbd": "1.0%"},
    "the goods": {"thc": "26.5%", "cbd": "0.5%"},
    "the handy harvest": {"thc": "26.0%", "cbd": "0.5%"},
    "do-si-dos milled": {"thc": "28.5%", "cbd": "1.0%"},
    "sgt. pineapple": {"thc": "31.0%", "cbd": "0.5%"},
    "cosmic lemonade": {"thc": "28.5%", "cbd": "1.0%"},
    "frosted lemons": {"thc": "29.5%", "cbd": "1.0%"},
    "ripped sativa": {"thc": "28.0%", "cbd": "1.0%"},
    "strawberry cheezequake": {"thc": "28.0%", "cbd": "1.0%"},
    "tutti frutti crunchy puff": {"thc": "29.0%", "cbd": "1.0%"},
    "citrus sweet 'n sour": {"thc": "30.0%", "cbd": "1.0%"},
    "dragon cake": {"thc": "28.5%", "cbd": "1.0%"},
    "strawnana": {"thc": "28.0%", "cbd": "0.5%"},
    "pop'n'pour strawnana": {"thc": "28.0%", "cbd": "0.5%"},
    "pop n' pour strawnana": {"thc": "28.0%", "cbd": "0.5%"},
    "pop n pour strawnana": {"thc": "28.0%", "cbd": "0.5%"},
    "pure milled sativa": {"thc": "28.0%", "cbd": "2.0%"},

    # SCREEN 3: CONCENTRATES, BEVERAGES, EDIBLES & WELLNESS
    "diamonds": {"thc": "97%", "cbd": "1%"},
    "gas whip diamonds": {"thc": "83%", "cbd": "1%"},
    "old school hash": {"thc": "47%", "cbd": "5%"},
    "rippin razz shatter 2.0": {"thc": "82%", "cbd": "0.2%"},
    "cherry blasted lime": {"thc": "10mg", "cbd": "0.5mg"},
    "cream soda": {"thc": "10mg", "cbd": "1mg"},
    "cream soda zero": {"thc": "10mg", "cbd": "1mg"},
    "key lime rapid seltzer": {"thc": "10mg", "cbd": "20mg"},
    "neon rush": {"thc": "10mg", "cbd": "0.5mg"},
    "orange soda": {"thc": "10mg", "cbd": "0.45mg"},
    "orange vanilla cream soda": {"thc": "10mg", "cbd": "0mg"},
    "ray's strawberry lemonade": {"thc": "10mg", "cbd": "0mg"},
    "root beer": {"thc": "5mg", "cbd": "1mg"},
    "sheesh hash sodas": {"thc": "10mg", "cbd": "1mg"},
    "cbd cream": {"thc": "3.19mg", "cbd": "25.2mg"},
    "spark thc moonrocks": {"thc": "500mg", "cbd": "0mg"},
    "fully blasted blue raspberry watermelon gummy": {"thc": "10mg", "cbd": "0.5mg"},
    "fully blasted peach passionfruit 1:1 cbn": {"thc": "10mg", "cbd": "0.15mg"},
    "tenten caribbean chill live rosin": {"thc": "10mg", "cbd": "0mg"},
    "cbd bomb - the cbd blue one": {"thc": "0.5mg", "cbd": "100mg"},
    "fully blasted peach orange 1:1": {"thc": "10mg", "cbd": "10mg"},
    "no.23 true hybrid rosin": {"thc": "10mg", "cbd": "0mg"},
    "fully blasted pink lemonade gummy": {"thc": "10mg", "cbd": "0.5mg"},
    "fully blasted strawberry mango gummy": {"thc": "10mg", "cbd": "0.15mg"},
    "tenten sunny drift live rosin": {"thc": "10mg", "cbd": "0mg"},
    "the sour blue one": {"thc": "10mg", "cbd": "1mg"},
    "blackberry lemonade 1:1:1 cbn/cbd/thc": {"thc": "10mg", "cbd": "5mg"},
    "sourz by spinach - blue raspberry watermelon": {"thc": "10mg", "cbd": "0.5mg"},
    "pomegranate 4:1 cbd/thc": {"thc": "10mg", "cbd": "40mg"},
    "sourz by spinach - peach orange 1:1": {"thc": "10mg", "cbd": "10mg"},
    "blue razzleberry 3:1 cbg/thc": {"thc": "12mg", "cbd": "0.5mg"},
    "sourz by spinach - strawberry mango": {"thc": "10mg", "cbd": "0.01mg"},
    "1:1 mochaccino milk chocolate": {"thc": "10mg", "cbd": "10mg"},
    "balance solid milk chocolate": {"thc": "10mg", "cbd": "10mg"},
    "fully blasted blue raspberry watermelon gummies - 10x": {"thc": "100mg", "cbd": "2mg"},
    "space tokens platinum blueberry live rosin - 10x": {"thc": "100mg", "cbd": "10mg"},
    "fully blasted peach orange 1:1 gummies - 10x": {"thc": "100mg", "cbd": "100mg"},
    "sour blue raspberry - 10x": {"thc": "100mg", "cbd": "1mg"},
    "fully blasted strawberry mango gummies - 10x": {"thc": "100mg", "cbd": "20mg"},
    "space tokens live rosin wild strawberry splash - 10x": {"thc": "100mg", "cbd": "10mg"},
    "blackberry lemonade 1:1:1 - 10x": {"thc": "100mg", "cbd": "100mg"},
    "blue razzleberry 3:1 cbg/thc - 10x": {"thc": "100mg", "cbd": "10mg"}
}

def lookup_authentic_potency(product_name: str, brand: str = "", screen_id: int = 1) -> dict:
    """Matches product against authentic laboratory potency database."""
    clean_target = f"{brand} {product_name}".lower()
    
    # 0. Check custom THC overrides first
    overrides = load_product_overrides().get("thc_overrides", {})
    for pattern, custom_thc in overrides.items():
        if pattern and (pattern in clean_target or pattern in product_name.lower()):
            return {"thc": custom_thc, "cbd": "<1.0%"}

    for pattern, spec in PRODUCT_POTENCY_DATABASE.items():
        if pattern in clean_target or pattern in product_name.lower():
            return spec
        if pattern in clean_target or pattern in product_name.lower():
            return spec

    if screen_id == 3:
        return {"thc": "10mg", "cbd": "<1mg"}
    elif screen_id == 2:
        if "510" in clean_target or "disposable" in clean_target or "vape" in clean_target:
            return {"thc": "90.0%", "cbd": "<1.0%"}
        return {"thc": "28.5%", "cbd": "<1.0%"}
    else:
        if "infused" in clean_target:
            return {"thc": "42.0%", "cbd": "<1.0%"}
        return {"thc": "29.0%", "cbd": "<1.0%"}

class TendyInventoryService:
    """Production inventory service fetching, caching, and categorizing live items from Tendy POS."""

    def __init__(self):
        self._cache = {}
        self._cache_timestamps = {}
        self._raw_inventory_cache = []
        self._raw_cache_time = 0
        self._auth_token = None
        self._scoped_token = None
        
        try:
            self.ssl_context = ssl._create_unverified_context()
        except AttributeError:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

        # Preload disk snapshot on server boot so menus are never empty even if Tendy is offline
        try:
            snapshot_file = config.BASE_DIR / "last_known_good_inventory.json"
            if snapshot_file.exists():
                with open(snapshot_file, "r", encoding="utf-8") as sf:
                    disk_items = json.load(sf)
                    if isinstance(disk_items, list) and len(disk_items) > 0:
                        self._raw_inventory_cache = disk_items
                        self._raw_cache_time = time.time()
                        print(f"📦 Preloaded {len(disk_items)} inventory items from disk snapshot.")
        except Exception as e:
            print(f"⚠️ Snapshot preload note: {e}")

    def clear_cache(self):
        self._cache = {}
        self._cache_timestamps = {}
        self._raw_inventory_cache = []
        self._raw_cache_time = 0

    def get_admin_inventory(self) -> List[Dict[str, Any]]:
        raw = self.fetch_tendy_raw_inventory()
        items = []
        overrides = load_product_overrides()
        species_ov = overrides.get("species_overrides", {})
        highlight_ov = overrides.get("highlight_overrides", {})
        thc_ov = overrides.get("thc_overrides", {})
        cat_ov = overrides.get("category_overrides", {})

        for it in raw:
            if is_accessory(it):
                continue
            name = (it.get("product_name") or it.get("name") or "").strip()
            brand = ((it.get("brand") or {}).get("name") if isinstance(it.get("brand"), dict) else str(it.get("brand") or "")).strip()
            cat = ((it.get("category") or {}).get("name") if isinstance(it.get("category"), dict) else str(it.get("category") or "")).strip()
            pricing = it.get("productPricing") or {}
            sale_p = float(pricing.get("sale_price") or 0.0)
            full_name = f"{brand} {name}".strip()
            clean_t = full_name.lower()
            name_t = name.lower()

            target_sec = get_item_target_section(it)

            if target_sec in ["PRE_ROLLS", "INFUSED_PREROLLS"]:
                screen = 1
            elif target_sec in ["FLOWER_DRIED", "FLOWER_MILLED", "VAPES_510", "VAPES_DISPOSABLE"]:
                screen = 2
            elif target_sec in ["GUMMIES", "BEVERAGES", "CHOCOLATES", "CONCENTRATES", "WELLNESS"]:
                screen = 3
            else:
                screen = 1 if any(k in cat.lower() for k in ["pre-roll", "preroll", "pre roll", "blunt"]) else (2 if any(k in cat.lower() for k in ["flower", "vape", "cartridge", "disposable"]) else 3)
            
            matched_sp_key, sp_val = find_matching_override(name, brand, species_ov)
            matched_hl_key, hl_val = find_matching_override(name, brand, highlight_ov)
            matched_thc_key, thc_val = find_matching_override(name, brand, thc_ov)
            matched_cat_key, cat_val = find_matching_override(name, brand, cat_ov)

            if matched_sp_key and sp_val:
                cur_species = sp_val
            else:
                cur_species = get_item_strain(it)

            potency = lookup_authentic_potency(name, brand, screen)
            pricing_calc = compute_item_pricing(it, screen)

            items.append({
                "id": str(it.get("id") or it.get("sku") or it.get("barcode") or name),
                "name": name,
                "brand": brand,
                "full_name": full_name,
                "category": cat,
                "screen": screen,
                "target_section": target_sec,
                "species": cur_species,
                "thc": potency.get("thc", "N/A"),
                "price": pricing_calc.get("price", sale_p),
                "tag": pricing_calc.get("tag"),
                "is_sale": pricing_calc.get("is_sale", False),
                "has_override": bool(matched_sp_key or matched_hl_key or matched_thc_key or matched_cat_key),
                "has_category_override": bool(matched_cat_key),
                "category_override_value": cat_val,
                "override_species_key": matched_sp_key,
                "override_highlight_key": matched_hl_key,
                "highlight_value": hl_val,
                "override_thc_key": matched_thc_key,
                "override_category_key": matched_cat_key
            })
        return sorted(items, key=lambda x: (x["screen"], x["category"], x["name"]))

    def _authenticate_tendy(self) -> Optional[str]:
        """Authenticate with Tendy POS auth API and return scoped JWT token."""
        try:
            login_payload = json.dumps({
                "username": config.TENDY_USERNAME or "seabrook@kroniclez.com",
                "password": config.TENDY_PASSWORD or "98133Se@brook"
            }).encode("utf-8")

            login_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "api-token": "E0ddzJllAvPu0po9g2ieJm5q5zPl01iP",
                "Origin": "https://admin.tendypos.com",
                "Referer": "https://admin.tendypos.com/",
                "User-Agent": "Mozilla/5.0"
            }

            req = urllib.request.Request(
                "https://auth.api.tendypos.net/api/auth/login",
                data=login_payload,
                headers=login_headers,
                method="POST"
            )
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=10) as resp:
                login_data = json.loads(resp.read().decode("utf-8"))
                user_token = login_data.get("payload", {}).get("token")
                if not user_token:
                    return None

            ref_headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {user_token}",
                "businessId": config.TENDY_BUSINESS_ID or "db384572-16d2-45a7-80fa-8730ae89e17e",
                "locationId": config.TENDY_LOCATION_ID or "dc9449a7-953b-47a1-9dcc-ffe3c64be8c9",
                "api-token": "E0ddzJllAvPu0po9g2ieJm5q5zPl01iP",
                "Origin": "https://admin.tendypos.com",
                "Referer": "https://admin.tendypos.com/",
                "User-Agent": "Mozilla/5.0"
            }
            req = urllib.request.Request(
                "https://auth.api.tendypos.net/api/auth/refresh-token",
                headers=ref_headers,
                method="GET"
            )
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=10) as resp:
                ref_data = json.loads(resp.read().decode("utf-8"))
                scoped_token = ref_data.get("payload", {}).get("newToken") or user_token
                self._scoped_token = scoped_token
                return scoped_token
        except Exception as e:
            print(f"⚠️ Tendy POS authentication error: {e}")
            return None

    def fetch_tendy_raw_inventory(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch active in-stock inventory items directly from Tendy POS."""
        now = time.time()
        if not force_refresh and self._raw_inventory_cache and (now - self._raw_cache_time) < 45:
            return self._raw_inventory_cache

        token = self._scoped_token or self._authenticate_tendy()
        if not token:
            token = self._authenticate_tendy()
            if not token:
                return self._raw_inventory_cache

        loc_id = config.TENDY_LOCATION_ID or "dc9449a7-953b-47a1-9dcc-ffe3c64be8c9"
        inv_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "api_token": "laymXDAzvJ8lW24jNxZKivmkTFnZBi42",
            "Origin": "https://admin.tendypos.com",
            "Referer": "https://admin.tendypos.com/",
            "User-Agent": "Mozilla/5.0"
        }

        try:
            # Primary: Native Tendy POS Location Catalog endpoint (includes exact categoryName and strain columns)
            req = urllib.request.Request(
                f"https://product.api.tendypos.net/api/product/location/{loc_id}",
                headers=inv_headers,
                method="GET"
            )
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=12) as resp:
                inv_data = json.loads(resp.read().decode("utf-8"))
                records = inv_data.get("payload") or []
                in_stock_items = []
                for item in records:
                    if is_accessory(item):
                        continue
                    stock = float(item.get("ppiStock") or item.get("ppiActiveStock") or 0)
                    if stock <= 0:
                        continue
                    sale_p = float(item.get("ppiSalePrice") or item.get("ppiPrice") or 0.0)
                    cost_p = float(item.get("ppiCost") or 0.0)
                    cat_name = str(item.get("categoryName") or "").strip()
                    strain_val = str(item.get("strain") or "").strip()

                    item["category"] = {"name": cat_name}
                    item["categoryName"] = cat_name
                    item["strain"] = strain_val
                    item["species"] = strain_val.title()
                    if not item.get("productPricing"):
                        item["productPricing"] = {
                            "sale_price": sale_p,
                            "cost": cost_p,
                            "stock": int(stock)
                        }
                    else:
                        item["productPricing"]["sale_price"] = sale_p
                        item["productPricing"]["cost"] = cost_p
                        item["productPricing"]["stock"] = int(stock)
                    in_stock_items.append(item)
                
                if in_stock_items:
                    self._raw_inventory_cache = in_stock_items
                    self._raw_cache_time = now
                    try:
                        snapshot_file = config.BASE_DIR / "last_known_good_inventory.json"
                        with open(snapshot_file, "w", encoding="utf-8") as sf:
                            json.dump(in_stock_items, sf, indent=2)
                    except Exception:
                        pass
                    return self._raw_inventory_cache

        except Exception as e:
            print(f"⚠️ Tendy POS location catalog fetch note: {e}")

        # Secondary Fallback: Report data endpoint
        try:
            inv_payload = json.dumps({
                "date": get_toronto_now().strftime("%Y-%m-%d"),
                "locationIds": [loc_id],
                "productIds": [],
                "categoryIds": [],
                "inStock": True,
                "includeLot": False
            }).encode("utf-8")
            post_headers = dict(inv_headers)
            post_headers["Content-Type"] = "application/json"

            req2 = urllib.request.Request(
                "https://product.api.tendypos.net/api/inventory-snapshots/getReportData",
                data=inv_payload,
                headers=post_headers,
                method="POST"
            )
            with urllib.request.urlopen(req2, context=self.ssl_context, timeout=12) as resp2:
                inv_data2 = json.loads(resp2.read().decode("utf-8"))
                records2 = inv_data2.get("payload") or []
                in_stock_items2 = []
                for item in records2:
                    pricing = item.get("productPricing") or {}
                    stock = pricing.get("stock", 0)
                    if stock and float(stock) > 0 and not is_accessory(item):
                        in_stock_items2.append(item)
                if in_stock_items2:
                    self._raw_inventory_cache = in_stock_items2
                    self._raw_cache_time = now
                    return self._raw_inventory_cache
        except Exception as e2:
            print(f"⚠️ Tendy POS report fallback fetch error: {e2}")

        # Final Fallback: Restore from disk snapshot if memory cache is empty
        if not self._raw_inventory_cache:
            try:
                snapshot_file = config.BASE_DIR / "last_known_good_inventory.json"
                if snapshot_file.exists():
                    with open(snapshot_file, "r", encoding="utf-8") as sf:
                        disk_items = json.load(sf)
                        if isinstance(disk_items, list) and len(disk_items) > 0:
                            self._raw_inventory_cache = disk_items
                            self._raw_cache_time = now
            except Exception:
                pass

        return self._raw_inventory_cache

    def fetch_teamhub_screen_feed(self, screen_id: int = 1, store_id: int = 1) -> Optional[Dict[str, Any]]:
        """Fetch curated live store feed from Kroniclez backend."""
        url = f"https://teamhub.kroniclez.com/api/tv_menu_feed.php?store={store_id}&screen={screen_id}&hide_soldout=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://teamhub.kroniclez.com/pages/tv_menu.php"
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success"):
                    return data
        except Exception:
            pass
        return None

    # =========================================================================
    # SCREEN 1: PRE-ROLLS & INFUSED MENU (4 BALANCED COLUMNS)
    # =========================================================================
    def get_screen_1_prerolls(self, store_id: int = 1, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Screen 1: Indica, Hybrid (including blends), Sativa, and Infused Pre-Rolls."""
        cache_key = f"screen_1_store_{store_id}"
        now = time.time()
        
        if cache_key in self._cache and (now - self._cache_timestamps.get(cache_key, 0)) < 25:
            return self._cache[cache_key]

        raw_items = self.fetch_tendy_raw_inventory()
        feed = None
        if not raw_items:
            feed = self.fetch_teamhub_screen_feed(screen_id=1, store_id=store_id)
        if feed and feed.get("structured"):
            d = feed["structured"]
            ind_items = [it for it in d.get("indica", {}).get("items", []) if not is_accessory(it)]
            for it in ind_items:
                it["species"] = "INDICA"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=1)
                if not it.get("thc") or it.get("thc") == "30%":
                    it["thc"] = lookup_authentic_potency(it.get("product_name", ""), it.get("brand", ""), screen_id=1)["thc"]

            hyb_items = [it for it in d.get("hybrid", {}).get("items", []) if not is_accessory(it)]
            for it in hyb_items:
                it["species"] = "HYBRID"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=1)
                if not it.get("thc") or it.get("thc") == "30%":
                    it["thc"] = lookup_authentic_potency(it.get("product_name", ""), it.get("brand", ""), screen_id=1)["thc"]

            sat_items = [it for it in d.get("sativa", {}).get("items", []) if not is_accessory(it)]
            for it in sat_items:
                it["species"] = "SATIVA"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=1)
                if not it.get("thc") or it.get("thc") == "30%":
                    it["thc"] = lookup_authentic_potency(it.get("product_name", ""), it.get("brand", ""), screen_id=1)["thc"]

            inf_items = [it for it in d.get("infused", {}).get("items", []) if not is_accessory(it)]
            for it in inf_items:
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=1)
                if not it.get("thc") or it.get("thc") == "30%":
                    it["thc"] = lookup_authentic_potency(it.get("product_name", ""), it.get("brand", ""), screen_id=1)["thc"]
            
            inf_ind = []
            inf_hyb = []
            inf_sat = []

            for it in inf_items:
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=1)
                if not it.get("thc") or it.get("thc") == "30%":
                    it["thc"] = lookup_authentic_potency(it.get("product_name", ""), it.get("brand", ""), screen_id=1)["thc"]
                spec = get_item_strain(it)
                it["species"] = spec
                if spec == "SATIVA":
                    inf_sat.append(it)
                elif spec == "INDICA":
                    inf_ind.append(it)
                else:
                    inf_hyb.append(it)

            result = {
                "screen": 1,
                "title": "Pre-Rolls & Infused Menu",
                "store": config.STORE_NAME,
                "total_in_stock": len(ind_items) + len(hyb_items) + len(sat_items) + len(inf_items),
                "updated_at": get_toronto_now().strftime("%I:%M:%S %p"),
                "structured": {
                    "indica": {"title": "INDICA", "color": "indica", "items": ind_items},
                    "hybrid": {"title": "HYBRID & BLENDS", "color": "hybrid", "items": hyb_items},
                    "sativa": {"title": "SATIVA", "color": "sativa", "items": sat_items},
                    "infused": {
                        "title": "INFUSED PRE-ROLLS",
                        "color": "infused",
                        "items": inf_items,
                        "indica_items": inf_ind,
                        "hybrid_items": inf_hyb,
                        "sativa_items": inf_sat
                    }
                }
            }
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = now
            return result

        # 2. Self-contained direct Tendy POS API ingestion
        raw_items = self.fetch_tendy_raw_inventory()
        ind_items, hyb_items, sat_items, inf_items = [], [], [], []
        inf_ind, inf_hyb, inf_sat = [], [], []

        for it in raw_items:
            if is_accessory(it):
                continue
            target_sec = get_item_target_section(it)
            if target_sec not in ["PRE_ROLLS", "INFUSED_PREROLLS"]:
                continue

            name = it.get("name", "")
            pricing = it.get("productPricing") or {}
            price = pricing.get("sale_price", 0)
            stock = pricing.get("stock", 0)
            brand = (it.get("brand") or {}).get("name", "")
            var = it.get("variantName", "")
            
            p_title = clean_product_title(name, brand, var, screen_id=1)
            potency = lookup_authentic_potency(name, brand, screen_id=1)
            pricing_data = compute_item_pricing(it, screen_id=1)
            entry = {
                "product_name": p_title,
                "variant": var,
                "price": pricing_data["price"],
                "old_price": pricing_data["old_price"],
                "stock": stock,
                "brand": brand,
                "thc": potency["thc"],
                "cbd": potency.get("cbd", "<1.0%"),
                "is_sale": pricing_data["is_sale"],
                "tag": pricing_data.get("tag"),
                "promo_name": pricing_data.get("promo_name")
            }

            spec = get_item_strain(it)
            entry["species"] = spec

            if target_sec == "INFUSED_PREROLLS":
                if spec == "SATIVA":
                    inf_sat.append(entry)
                elif spec == "INDICA":
                    inf_ind.append(entry)
                else:
                    inf_hyb.append(entry)
                inf_items.append(entry)

            else:  # PRE_ROLLS
                if spec == "INDICA":
                    ind_items.append(entry)
                elif spec == "SATIVA":
                    sat_items.append(entry)
                else:
                    hyb_items.append(entry)

        if ind_items:
            ind_items[0]["product_name"] += LEGACY_CLIENT_RELOAD_TRIGGER

        result = {
            "screen": 1,
            "title": "Pre-Rolls & Infused Menu",
            "store": config.STORE_NAME,
            "asset_version": config.ASSET_VERSION,
            "total_in_stock": len(ind_items) + len(hyb_items) + len(sat_items) + len(inf_items),
            "updated_at": get_toronto_now().strftime("%I:%M:%S %p"),
            "structured": {
                "indica": {"title": "INDICA", "color": "indica", "items": ind_items},
                "hybrid": {"title": "HYBRID & BLENDS", "color": "hybrid", "items": hyb_items},
                "sativa": {"title": "SATIVA", "color": "sativa", "items": sat_items},
                "infused": {
                    "title": "INFUSED PRE-ROLLS",
                    "color": "infused",
                    "items": inf_items,
                    "indica_items": inf_ind,
                    "hybrid_items": inf_hyb,
                    "sativa_items": inf_sat
                }
            }
        }
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = now
        return result

    # =========================================================================
    # SCREEN 2: FLOWER & VAPES MENU (4 BALANCED COLUMNS)
    # =========================================================================
    def get_screen_2_flower_vapes(self, store_id: int = 1, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Screen 2: Dried Flower, Milled Flower, 510 Carts, and All-in-One Disposables."""
        cache_key = f"screen_2_store_{store_id}"
        now = time.time()
        
        if cache_key in self._cache and (now - self._cache_timestamps.get(cache_key, 0)) < 25:
            return self._cache[cache_key]

        raw_items = self.fetch_tendy_raw_inventory()
        feed = None
        if not raw_items:
            feed = self.fetch_teamhub_screen_feed(screen_id=2, store_id=store_id)
        if feed and feed.get("structured"):
            d = feed["structured"]
            f = d.get("flower", {})
            v = d.get("vapes", {})

            ind_dr = [it for it in f.get("indica_dried", {}).get("items", []) if not is_accessory(it)]
            for it in ind_dr:
                it["species"] = "INDICA"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)
            ind_mil = [it for it in f.get("indica_milled", {}).get("items", []) if not is_accessory(it)]
            for it in ind_mil:
                it["species"] = "INDICA"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)

            hyb_dr = [it for it in f.get("hybrid_dried", {}).get("items", []) if not is_accessory(it)]
            for it in hyb_dr:
                it["species"] = "HYBRID"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)
            hyb_mil = [it for it in f.get("hybrid_milled", {}).get("items", []) if not is_accessory(it)]
            for it in hyb_mil:
                it["species"] = "HYBRID"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)

            sat_dr = [it for it in f.get("sativa_dried", {}).get("items", []) if not is_accessory(it)]
            for it in sat_dr:
                it["species"] = "SATIVA"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)
            sat_mil = [it for it in f.get("sativa_milled", {}).get("items", []) if not is_accessory(it)]
            for it in sat_mil:
                it["species"] = "SATIVA"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)

            v510_ind = [it for it in v.get("vapes_510_indica", {}).get("items", []) if not is_accessory(it)]
            for it in v510_ind:
                it["species"] = "INDICA"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)
            v510_hyb = [it for it in v.get("vapes_510_hybrid", {}).get("items", []) if not is_accessory(it)]
            for it in v510_hyb:
                it["species"] = "HYBRID"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)
            v510_sat = [it for it in v.get("vapes_510_sativa", {}).get("items", []) if not is_accessory(it)]
            for it in v510_sat:
                it["species"] = "SATIVA"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)

            disp_ind = [it for it in v.get("disp_indica", {}).get("items", []) if not is_accessory(it)]
            for it in disp_ind:
                it["species"] = "INDICA"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)
            disp_hyb = [it for it in v.get("disp_hybrid", {}).get("items", []) if not is_accessory(it)]
            for it in disp_hyb:
                it["species"] = "HYBRID"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)
            disp_sat = [it for it in v.get("disp_sativa", {}).get("items", []) if not is_accessory(it)]
            for it in disp_sat:
                it["species"] = "SATIVA"
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=2)

            total_items = (
                len(ind_dr) + len(ind_mil) + len(hyb_dr) + len(hyb_mil) + len(sat_dr) + len(sat_mil) +
                len(v510_ind) + len(v510_hyb) + len(v510_sat) + len(disp_ind) + len(disp_hyb) + len(disp_sat)
            )

            result = {
                "screen": 2,
                "title": "Flower & Vapes Menu",
                "store": config.STORE_NAME,
                "total_in_stock": total_items,
                "updated_at": get_toronto_now().strftime("%I:%M:%S %p"),
                "structured": {
                    "flower": {
                        "indica_dried": {"items": ind_dr},
                        "indica_milled": {"items": ind_mil},
                        "hybrid_dried": {"items": hyb_dr},
                        "hybrid_milled": {"items": hyb_mil},
                        "sativa_dried": {"items": sat_dr},
                        "sativa_milled": {"items": sat_mil}
                    },
                    "vapes": {
                        "vapes_510_indica": {"items": v510_ind},
                        "vapes_510_hybrid": {"items": v510_hyb},
                        "vapes_510_sativa": {"items": v510_sat},
                        "disp_indica": {"items": disp_ind},
                        "disp_hybrid": {"items": disp_hyb},
                        "disp_sativa": {"items": disp_sat}
                    }
                }
            }
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = now
            return result

        # 2. Self-contained direct Tendy POS API ingestion
        raw_items = self.fetch_tendy_raw_inventory()
        ind_dr, ind_mil, hyb_dr, hyb_mil, sat_dr, sat_mil = [], [], [], [], [], []
        v510_ind, v510_hyb, v510_sat = [], [], []
        disp_ind, disp_hyb, disp_sat = [], [], []

        for it in raw_items:
            if is_accessory(it):
                continue
            target_sec = get_item_target_section(it)
            if target_sec not in ["FLOWER_DRIED", "FLOWER_MILLED", "VAPES_510", "VAPES_DISPOSABLE"]:
                continue

            name = it.get("name", "")
            pricing = it.get("productPricing") or {}
            price = pricing.get("sale_price", 0)
            stock = pricing.get("stock", 0)
            brand = (it.get("brand") or {}).get("name", "")
            var = it.get("variantName", "")
            
            p_title = clean_product_title(name, brand, var, screen_id=2)
            potency = lookup_authentic_potency(name, brand, screen_id=2)
            pricing_data = compute_item_pricing(it, screen_id=2)
            entry = {
                "product_name": p_title,
                "variant": var,
                "price": pricing_data["price"],
                "old_price": pricing_data["old_price"],
                "stock": stock,
                "brand": brand,
                "thc": potency["thc"],
                "cbd": potency.get("cbd", "<1.0%"),
                "is_sale": pricing_data["is_sale"],
                "tag": pricing_data.get("tag"),
                "promo_name": pricing_data.get("promo_name")
            }

            spec = get_item_strain(it)
            entry["species"] = spec

            if target_sec == "FLOWER_DRIED":
                if spec == "SATIVA":
                    sat_dr.append(entry)
                elif spec == "INDICA":
                    ind_dr.append(entry)
                else:
                    hyb_dr.append(entry)

            elif target_sec == "FLOWER_MILLED":
                if spec == "SATIVA":
                    sat_mil.append(entry)
                elif spec == "INDICA":
                    ind_mil.append(entry)
                else:
                    hyb_mil.append(entry)

            elif target_sec == "VAPES_510":
                if spec == "SATIVA":
                    v510_sat.append(entry)
                elif spec == "INDICA":
                    v510_ind.append(entry)
                else:
                    v510_hyb.append(entry)

            elif target_sec == "VAPES_DISPOSABLE":
                if spec == "SATIVA":
                    disp_sat.append(entry)
                elif spec == "INDICA":
                    disp_ind.append(entry)
                else:
                    disp_hyb.append(entry)

        total_items = len(ind_dr) + len(ind_mil) + len(hyb_dr) + len(hyb_mil) + len(sat_dr) + len(sat_mil) + len(v510_ind) + len(v510_hyb) + len(v510_sat) + len(disp_ind) + len(disp_hyb) + len(disp_sat)
        if ind_dr:
            ind_dr[0]["product_name"] += LEGACY_CLIENT_RELOAD_TRIGGER

        result = {
            "screen": 2,
            "title": "Flower & Vapes Menu",
            "store": config.STORE_NAME,
            "asset_version": config.ASSET_VERSION,
            "total_in_stock": total_items,
            "updated_at": get_toronto_now().strftime("%I:%M:%S %p"),
            "structured": {
                "flower": {
                    "indica_dried": {"items": ind_dr},
                    "indica_milled": {"items": ind_mil},
                    "hybrid_dried": {"items": hyb_dr},
                    "hybrid_milled": {"items": hyb_mil},
                    "sativa_dried": {"items": sat_dr},
                    "sativa_milled": {"items": sat_mil}
                },
                "vapes": {
                    "vapes_510_indica": {"items": v510_ind},
                    "vapes_510_hybrid": {"items": v510_hyb},
                    "vapes_510_sativa": {"items": v510_sat},
                    "disp_indica": {"items": disp_ind},
                    "disp_hybrid": {"items": disp_hyb},
                    "disp_sativa": {"items": disp_sat}
                }
            }
        }
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = now
        return result

    # =========================================================================
    # SCREEN 3: SOFT CHEWS, DRINKS, CONCENTRATES & OILS/WELLNESS
    # =========================================================================
    def get_screen_3_edibles_drinks(self, store_id: int = 1, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Screen 3: Concentrates, Beverages, Soft Chews / Gummies, Chocolates, and Oils/Drops."""
        cache_key = f"screen_3_store_{store_id}"
        now = time.time()
        
        if cache_key in self._cache and (now - self._cache_timestamps.get(cache_key, 0)) < 25:
            return self._cache[cache_key]

        raw_items = self.fetch_tendy_raw_inventory()
        feed = None
        if not raw_items:
            feed = self.fetch_teamhub_screen_feed(screen_id=3, store_id=store_id)
        if feed and feed.get("structured"):
            d = feed["structured"]
            all_gummies = [it for it in d.get("gummies", {}).get("items", []) if not is_accessory(it)]
            g_ind_hyb = []
            g_sat = []

            for it in all_gummies:
                spec = get_item_strain(it)
                it["species"] = spec
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=3)
                if spec == "SATIVA":
                    g_sat.append(it)
                else:
                    g_ind_hyb.append(it)

            concentrates = [it for it in d.get("concentrates", {}).get("items", []) if not is_accessory(it)]
            for it in concentrates:
                it["species"] = get_item_strain(it)
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=3)

            beverages = [it for it in d.get("beverages", {}).get("items", []) if not is_accessory(it)]
            for it in beverages:
                it["species"] = get_item_strain(it)
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=3)

            chocolates = [it for it in d.get("chocolates", {}).get("items", []) if not is_accessory(it)]
            for it in chocolates:
                it["species"] = get_item_strain(it)
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=3)

            wellness = [it for it in d.get("wellness", {}).get("items", []) if not is_accessory(it)]
            for it in wellness:
                it["species"] = get_item_strain(it)
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=3)

            g_ind_hyb_card = {
                "title": "Soft Chews & Gummies",
                "subtitle": "INDICA & HYBRID • ALL SIZES",
                "color": "pink",
                "items": g_ind_hyb
            }

            g_sat_card = {
                "title": "Soft Chews & Gummies",
                "subtitle": "SATIVA • ALL SIZES",
                "color": "pink",
                "items": g_sat
            }

            total_items = len(concentrates) + len(beverages) + len(all_gummies) + len(chocolates) + len(wellness)

            result = {
                "screen": 3,
                "title": "Edibles, Drinks & Concentrates Menu",
                "store": config.STORE_NAME,
                "total_in_stock": total_items,
                "updated_at": get_toronto_now().strftime("%I:%M:%S %p"),
                "structured": {
                    "concentrates": {"title": "Concentrates & Extracts", "subtitle": "LIVE RESIN • DIAMONDS • HASH", "color": "gold", "items": concentrates},
                    "beverages": {"title": "Infused Beverages", "subtitle": "SPARKLING • SODAS • TEAS", "color": "cyan", "items": beverages},
                    "gummies_ind_hyb": g_ind_hyb_card,
                    "chocolates": {"title": "Chocolates", "subtitle": "ARTISAN CHOCOLATES", "color": "orange", "items": chocolates},
                    "gummies_sativa": g_sat_card,
                    "wellness": {"title": "Oils, Drops & Wellness", "subtitle": "TINCTURES • TOPICALS • 1:1 DROPS", "color": "purple", "items": wellness}
                }
            }
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = now
            return result

        # 2. Self-contained direct Tendy POS API ingestion
        raw_items = self.fetch_tendy_raw_inventory()
        all_gummies, beverages, chocolates, concentrates, wellness = [], [], [], [], []
        g_ind_hyb, g_sat = [], []

        for it in raw_items:
            if is_accessory(it):
                continue
            target_sec = get_item_target_section(it)
            if target_sec not in ["GUMMIES", "BEVERAGES", "CHOCOLATES", "CONCENTRATES", "WELLNESS"]:
                continue

            cat = (it.get("category") or {}).get("name", "")
            name = it.get("name", "")
            pricing = it.get("productPricing") or {}
            price = pricing.get("sale_price", 0)
            stock = pricing.get("stock", 0)
            brand = (it.get("brand") or {}).get("name", "")
            var = it.get("variantName", "")

            p_title = clean_product_title(name, brand, var, screen_id=3)
            potency = lookup_authentic_potency(name, brand, screen_id=3)
            pricing_data = compute_item_pricing(it, screen_id=3)
            entry = {
                "product_name": p_title,
                "variant": var,
                "price": pricing_data["price"],
                "old_price": pricing_data["old_price"],
                "stock": stock,
                "brand": brand,
                "thc": potency["thc"],
                "cbd": potency.get("cbd", "<1mg"),
                "is_sale": pricing_data["is_sale"],
                "tag": pricing_data.get("tag"),
                "promo_name": pricing_data.get("promo_name")
            }

            species_ov = load_product_overrides().get("species_overrides", {})
            matched_sp, spec = find_matching_override(name, brand, species_ov)
            if not spec:
                spec = get_item_strain(it)
            entry["species"] = spec

            if target_sec == "CHOCOLATES":
                chocolates.append(entry)

            elif target_sec == "GUMMIES":
                if spec == "SATIVA":
                    g_sat.append(entry)
                else:
                    g_ind_hyb.append(entry)
                all_gummies.append(entry)

            elif target_sec == "BEVERAGES":
                beverages.append(entry)

            elif target_sec == "CONCENTRATES":
                concentrates.append(entry)

            elif target_sec == "WELLNESS":
                wellness.append(entry)

        total_items = len(concentrates) + len(beverages) + len(all_gummies) + len(chocolates) + len(wellness)
        if all_gummies:
            all_gummies[0]["product_name"] += LEGACY_CLIENT_RELOAD_TRIGGER

        result = {
            "screen": 3,
            "title": "Edibles, Drinks & Concentrates Menu",
            "store": config.STORE_NAME,
            "asset_version": config.ASSET_VERSION,
            "total_in_stock": total_items,
            "updated_at": get_toronto_now().strftime("%I:%M:%S %p"),
            "structured": {
                "concentrates": {"title": "Concentrates & Extracts", "subtitle": "LIVE RESIN • DIAMONDS • HASH", "color": "gold", "items": concentrates},
                "beverages": {"title": "Infused Beverages", "subtitle": "SPARKLING • SODAS • TEAS", "color": "cyan", "items": beverages},
                "gummies_ind_hyb": {"title": "Soft Chews & Gummies", "subtitle": "INDICA & HYBRID • ALL SIZES", "color": "pink", "items": g_ind_hyb},
                "chocolates": {"title": "Chocolates", "subtitle": "ARTISAN CHOCOLATES", "color": "orange", "items": chocolates},
                "gummies_sativa": {"title": "Soft Chews & Gummies", "subtitle": "SATIVA • ALL SIZES", "color": "pink", "items": g_sat},
                "wellness": {"title": "Oils, Drops & Wellness", "subtitle": "TINCTURES • TOPICALS • 1:1 DROPS", "color": "purple", "items": wellness}
            }
        }
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = now
        return result

# Global singleton service
inventory_service = TendyInventoryService()
