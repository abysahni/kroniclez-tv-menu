import json
import re
import ssl
import time
import urllib.request
import urllib.parse
import urllib.error
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
try:
    from zoneinfo import ZoneInfo
    TORONTO_TZ = ZoneInfo("America/Toronto")
except ImportError:
    TORONTO_TZ = timezone(timedelta(hours=-4))

import config

def get_toronto_now() -> datetime:
    """Return current timestamp strictly in America/Toronto timezone."""
    return datetime.now(TORONTO_TZ)

def is_accessory(it: Dict[str, Any]) -> bool:
    """Filter out non-cannabis accessories (batteries, papers, lighters, grinders)."""
    raw_cat = it.get("category") or it.get("category_name") or it.get("categoryName") or ""
    if isinstance(raw_cat, dict):
        cat = str(raw_cat.get("name") or "").lower()
    else:
        cat = str(raw_cat).lower()
        
    raw_name = it.get("product_name") or it.get("name") or ""
    name = str(raw_name).lower()
    
    if any(k in cat for k in [
        "accessory", "accessories", "paper", "lighter", "lighers", "battery", "batteries",
        "grinder", "device", "glass", "pipe", "tray", "cleaning", "merchandise",
        "apparel", "gear", "vape battery", "bongs", "scale", "cone"
    ]):
        return True
        
    if any(k in name for k in [
        "raw classic", "raw organic", "rolling paper", "filter tips", "cone 6 pack",
        "cone 3 pack", "bic lighter", "clipper", "510 battery", "uni pro",
        "grinder", "rolling tray", "bong", "pipe", "cleaning swab", "iso-shine"
    ]):
        return True
        
    return False

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

    def _authenticate_tendy(self) -> Optional[str]:
        """Authenticate with Tendy POS auth API and return scoped JWT token."""
        try:
            login_payload = json.dumps({
                "username": config.TENDY_USERNAME or "seabrook@kroniclez.com",
                "password": config.TENDY_PASSWORD or "Se@brook0107"
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
        inv_payload = json.dumps({
            "date": get_toronto_now().strftime("%Y-%m-%d"),
            "locationIds": [loc_id],
            "productIds": [],
            "categoryIds": [],
            "inStock": True,
            "includeLot": False
        }).encode("utf-8")

        inv_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "api_token": "laymXDAzvJ8lW24jNxZKivmkTFnZBi42",
            "Origin": "https://admin.tendypos.com",
            "Referer": "https://admin.tendypos.com/",
            "User-Agent": "Mozilla/5.0"
        }

        try:
            req = urllib.request.Request(
                "https://product.api.tendypos.net/api/inventory-snapshots/getReportData",
                data=inv_payload,
                headers=inv_headers,
                method="POST"
            )
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as resp:
                inv_data = json.loads(resp.read().decode("utf-8"))
                records = inv_data.get("payload") or []
                in_stock_items = []
                for item in records:
                    pricing = item.get("productPricing") or {}
                    stock = pricing.get("stock", 0)
                    if stock and float(stock) > 0 and not is_accessory(item):
                        in_stock_items.append(item)
                
                if in_stock_items:
                    self._raw_inventory_cache = in_stock_items
                    self._raw_cache_time = now
                return self._raw_inventory_cache
        except Exception as e:
            print(f"⚠️ Tendy POS inventory fetch error: {e}")
            token = self._authenticate_tendy()
            if token and not force_refresh:
                return self.fetch_tendy_raw_inventory(force_refresh=True)
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

        feed = self.fetch_teamhub_screen_feed(screen_id=1, store_id=store_id)
        if feed and feed.get("structured") and feed.get("structured", {}).get("indica", {}).get("items"):
            d = feed["structured"]
            ind_items = [it for it in d.get("indica", {}).get("items", []) if not is_accessory(it)]
            for it in ind_items: it["species"] = "INDICA"

            hyb_items = [it for it in d.get("hybrid", {}).get("items", []) if not is_accessory(it)]
            for it in hyb_items: it["species"] = "HYBRID"

            sat_items = [it for it in d.get("sativa", {}).get("items", []) if not is_accessory(it)]
            for it in sat_items: it["species"] = "SATIVA"

            inf_items = [it for it in d.get("infused", {}).get("items", []) if not is_accessory(it)]
            
            known_inf = " ".join([(it.get("product_name") or "").lower() for it in inf_items])
            if "strawberry cough" not in known_inf:
                inf_items.append({
                    "product_name": "Flyers Frosted Infused Strawberry Cough Pre-Rolls - 3x0.5g",
                    "species": "Sativa",
                    "price": 26.96,
                    "brand": "Claybourne",
                    "thc": "38.5%",
                    "is_sale": False
                })
            if "diamond infused strawberry" not in known_inf:
                inf_items.append({
                    "product_name": "High Potency 50+ Diamond Infused Strawberry Pre-Rolls - 3x0.5g",
                    "species": "Sativa",
                    "price": 24.43,
                    "brand": "Jays",
                    "thc": "52.0%",
                    "is_sale": False
                })

            inf_ind = []
            inf_hyb = []
            inf_sat = []

            for it in inf_items:
                name_low = (it.get("product_name") or "").lower()
                spec_low = (it.get("species") or "").lower()
                if any(k in name_low for k in ["strawberry cough", "blue dream", "berry sunshine", "diamond infused strawberry"]):
                    it["species"] = "SATIVA"
                    inf_sat.append(it)
                elif any(k in name_low for k in ["watermelon z", "berry white", "grapey grape", "northern lights", "pink gas", "purple punch", "titanimal"]) or "indica" in spec_low:
                    it["species"] = "INDICA"
                    inf_ind.append(it)
                else:
                    it["species"] = "HYBRID"
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
            cat = (it.get("category") or {}).get("name", "")
            name = it.get("name", "")
            pricing = it.get("productPricing") or {}
            price = pricing.get("sale_price", 0)
            stock = pricing.get("stock", 0)
            brand = (it.get("brand") or {}).get("name", "")
            var = it.get("variantName", "")
            
            p_title = f"{brand.upper()} - {name} ({var})" if brand else f"{name} ({var})"
            entry = {"product_name": p_title, "price": price, "stock": stock, "brand": brand, "thc": "30%", "is_sale": False}

            if "Infused Pre-Rolls" in cat or "infused" in name.lower():
                name_low = name.lower()
                if any(k in name_low for k in ["strawberry cough", "blue dream", "berry sunshine", "diamond infused strawberry"]):
                    entry["species"] = "SATIVA"
                    inf_sat.append(entry)
                elif any(k in name_low for k in ["watermelon z", "berry white", "grapey grape", "northern lights", "pink gas", "purple punch", "titanimal"]):
                    entry["species"] = "INDICA"
                    inf_ind.append(entry)
                else:
                    entry["species"] = "HYBRID"
                    inf_hyb.append(entry)
                inf_items.append(entry)

            elif "Pre-Rolls" in cat:
                name_low = name.lower()
                if any(k in name_low for k in ["sativa", "lemon", "haze", "sour diesel", "jack", "tropic", "sunshine", "carmel", "animal face"]):
                    entry["species"] = "SATIVA"
                    sat_items.append(entry)
                elif any(k in name_low for k in ["indica", "kush", "pink", "purple", "gmo", "black mountain", "gas", "comatose", "grape"]):
                    entry["species"] = "INDICA"
                    ind_items.append(entry)
                else:
                    entry["species"] = "HYBRID"
                    hyb_items.append(entry)

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

    # =========================================================================
    # SCREEN 2: FLOWER & VAPES MENU (4 BALANCED COLUMNS)
    # =========================================================================
    def get_screen_2_flower_vapes(self, store_id: int = 1, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Screen 2: Dried Flower, Milled Flower, 510 Carts, and All-in-One Disposables."""
        cache_key = f"screen_2_store_{store_id}"
        now = time.time()
        
        if cache_key in self._cache and (now - self._cache_timestamps.get(cache_key, 0)) < 25:
            return self._cache[cache_key]

        feed = self.fetch_teamhub_screen_feed(screen_id=2, store_id=store_id)
        if feed and feed.get("structured") and feed.get("structured", {}).get("flower", {}).get("indica_dried", {}).get("items"):
            d = feed["structured"]
            f = d.get("flower", {})
            v = d.get("vapes", {})

            ind_dr = [it for it in f.get("indica_dried", {}).get("items", []) if not is_accessory(it)]
            for it in ind_dr: it["species"] = "INDICA"
            ind_mil = [it for it in f.get("indica_milled", {}).get("items", []) if not is_accessory(it)]
            for it in ind_mil: it["species"] = "INDICA"

            hyb_dr = [it for it in f.get("hybrid_dried", {}).get("items", []) if not is_accessory(it)]
            for it in hyb_dr: it["species"] = "HYBRID"
            hyb_mil = [it for it in f.get("hybrid_milled", {}).get("items", []) if not is_accessory(it)]
            for it in hyb_mil: it["species"] = "HYBRID"

            sat_dr = [it for it in f.get("sativa_dried", {}).get("items", []) if not is_accessory(it)]
            for it in sat_dr: it["species"] = "SATIVA"
            sat_mil = [it for it in f.get("sativa_milled", {}).get("items", []) if not is_accessory(it)]
            for it in sat_mil: it["species"] = "SATIVA"

            v510_ind = [it for it in v.get("vapes_510_indica", {}).get("items", []) if not is_accessory(it)]
            for it in v510_ind: it["species"] = "INDICA"
            v510_hyb = [it for it in v.get("vapes_510_hybrid", {}).get("items", []) if not is_accessory(it)]
            for it in v510_hyb: it["species"] = "HYBRID"
            v510_sat = [it for it in v.get("vapes_510_sativa", {}).get("items", []) if not is_accessory(it)]
            for it in v510_sat: it["species"] = "SATIVA"

            disp_ind = [it for it in v.get("disp_indica", {}).get("items", []) if not is_accessory(it)]
            for it in disp_ind: it["species"] = "INDICA"
            disp_hyb = [it for it in v.get("disp_hybrid", {}).get("items", []) if not is_accessory(it)]
            for it in disp_hyb: it["species"] = "HYBRID"
            disp_sat = [it for it in v.get("disp_sativa", {}).get("items", []) if not is_accessory(it)]
            for it in disp_sat: it["species"] = "SATIVA"

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
            cat = (it.get("category") or {}).get("name", "")
            name = it.get("name", "")
            pricing = it.get("productPricing") or {}
            price = pricing.get("sale_price", 0)
            stock = pricing.get("stock", 0)
            brand = (it.get("brand") or {}).get("name", "")
            var = it.get("variantName", "")
            
            p_title = f"{brand.upper()} - {name} ({var})" if brand else f"{name} ({var})"
            entry = {"product_name": p_title, "price": price, "stock": stock, "brand": brand, "thc": "28%", "is_sale": False}

            if "Flower" in cat or "Dried" in cat or "Milled" in cat:
                n_low = name.lower()
                is_mil = "milled" in cat.lower() or "milled" in n_low
                if any(k in n_low for k in ["sativa", "lemon", "haze", "sour", "rooster", "cosmic", "cheezequake", "citrus"]):
                    entry["species"] = "SATIVA"
                    (sat_mil if is_mil else sat_dr).append(entry)
                elif any(k in n_low for k in ["indica", "couch", "cookies", "gmo", "muffinz", "blueberry", "kush", "cali"]):
                    entry["species"] = "INDICA"
                    (ind_mil if is_mil else ind_dr).append(entry)
                else:
                    entry["species"] = "HYBRID"
                    (hyb_mil if is_mil else hyb_dr).append(entry)

            elif "510 Cartridges" in cat:
                n_low = name.lower()
                if any(k in n_low for k in ["sativa", "acapulco", "lemonade", "mango", "strawberry", "grapefruit", "shockwave"]):
                    entry["species"] = "SATIVA"
                    v510_sat.append(entry)
                elif any(k in n_low for k in ["indica", "kush", "berry", "cherry", "tiger", "watermelon", "blood orange", "freeze"]):
                    entry["species"] = "INDICA"
                    v510_ind.append(entry)
                else:
                    entry["species"] = "HYBRID"
                    v510_hyb.append(entry)

            elif "Disposable Vapes" in cat:
                n_low = name.lower()
                if any(k in n_low for k in ["sativa", "daze", "pineapple", "peach", "rainbow", "sunset"]):
                    entry["species"] = "SATIVA"
                    disp_sat.append(entry)
                elif any(k in n_low for k in ["indica", "punch", "mango", "watermelon"]):
                    entry["species"] = "INDICA"
                    disp_ind.append(entry)
                else:
                    entry["species"] = "HYBRID"
                    disp_hyb.append(entry)

        total_items = len(ind_dr) + len(ind_mil) + len(hyb_dr) + len(hyb_mil) + len(sat_dr) + len(sat_mil) + len(v510_ind) + len(v510_hyb) + len(v510_sat) + len(disp_ind) + len(disp_hyb) + len(disp_sat)
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

    # =========================================================================
    # SCREEN 3: SOFT CHEWS, DRINKS, CONCENTRATES & OILS/WELLNESS
    # =========================================================================
    def get_screen_3_edibles_drinks(self, store_id: int = 1, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Screen 3: Concentrates, Beverages, Soft Chews / Gummies, Chocolates, and Oils/Drops."""
        cache_key = f"screen_3_store_{store_id}"
        now = time.time()
        
        if cache_key in self._cache and (now - self._cache_timestamps.get(cache_key, 0)) < 25:
            return self._cache[cache_key]

        feed = self.fetch_teamhub_screen_feed(screen_id=3, store_id=store_id)
        if feed and feed.get("structured") and feed.get("structured", {}).get("gummies", {}).get("items"):
            d = feed["structured"]
            all_gummies = [it for it in d.get("gummies", {}).get("items", []) if not is_accessory(it)]
            g_ind_hyb = []
            g_sat = []

            for it in all_gummies:
                spec = (it.get("species") or "HYBRID").upper()
                if "SATIVA" in spec:
                    it["species"] = "SATIVA"
                    g_sat.append(it)
                elif "INDICA" in spec:
                    it["species"] = "INDICA"
                    g_ind_hyb.append(it)
                else:
                    it["species"] = "HYBRID"
                    g_ind_hyb.append(it)

            concentrates = [it for it in d.get("concentrates", {}).get("items", []) if not is_accessory(it)]
            for it in concentrates:
                spec = (it.get("species") or "HYBRID").upper()
                it["species"] = "SATIVA" if "SATIVA" in spec else ("INDICA" if "INDICA" in spec else "HYBRID")

            beverages = [it for it in d.get("beverages", {}).get("items", []) if not is_accessory(it)]
            for it in beverages:
                spec = (it.get("species") or "HYBRID").upper()
                it["species"] = "SATIVA" if "SATIVA" in spec else ("INDICA" if "INDICA" in spec else "HYBRID")

            chocolates = [it for it in d.get("chocolates", {}).get("items", []) if not is_accessory(it)]
            for it in chocolates:
                spec = (it.get("species") or "HYBRID").upper()
                it["species"] = "SATIVA" if "SATIVA" in spec else ("INDICA" if "INDICA" in spec else "HYBRID")

            wellness = [it for it in d.get("wellness", {}).get("items", []) if not is_accessory(it)]
            for it in wellness:
                spec = (it.get("species") or "HYBRID").upper()
                it["species"] = "SATIVA" if "SATIVA" in spec else ("INDICA" if "INDICA" in spec else "HYBRID")

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
            cat = (it.get("category") or {}).get("name", "")
            name = it.get("name", "")
            pricing = it.get("productPricing") or {}
            price = pricing.get("sale_price", 0)
            stock = pricing.get("stock", 0)
            brand = (it.get("brand") or {}).get("name", "")
            var = it.get("variantName", "")
            
            p_title = f"{brand.upper()} - {name} ({var})" if brand else f"{name} ({var})"
            entry = {"product_name": p_title, "price": price, "stock": stock, "brand": brand, "thc": "10mg", "is_sale": False}

            if "Soft Chews" in cat or "gummy" in name.lower() or "chew" in name.lower():
                n_low = name.lower()
                if "sativa" in n_low:
                    entry["species"] = "SATIVA"
                    g_sat.append(entry)
                elif "indica" in n_low:
                    entry["species"] = "INDICA"
                    g_ind_hyb.append(entry)
                else:
                    entry["species"] = "HYBRID"
                    g_ind_hyb.append(entry)
                all_gummies.append(entry)

            elif "Beverages" in cat or "drink" in name.lower() or "tea" in name.lower():
                entry["species"] = "HYBRID"
                beverages.append(entry)

            elif "Chocolates" in cat or "chocolate" in name.lower():
                entry["species"] = "HYBRID"
                chocolates.append(entry)

            elif "Concentrates" in cat or "hash" in name.lower() or "resin" in name.lower() or "rosin" in name.lower() or "shatter" in name.lower():
                entry["species"] = "HYBRID"
                concentrates.append(entry)

            elif "Oils" in cat or "Drops" in cat or "Topicals" in cat:
                entry["species"] = "HYBRID"
                wellness.append(entry)

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
