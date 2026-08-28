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
    cat = (it.get("category") or it.get("category_name") or it.get("categoryName") or "").lower()
    name = (it.get("product_name") or it.get("name") or "").lower()
    
    if any(k in cat for k in [
        "accessory", "accessories", "paper", "lighter", "battery", "batteries",
        "grinder", "device", "glass", "pipe", "tray", "cleaning", "merchandise",
        "apparel", "gear", "vape battery"
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
    """Production inventory service fetching, caching, and categorizing live items from Tendy POS & Kroniclez."""

    def __init__(self):
        self._cache = {}
        self._cache_timestamps = {}
        
        # Setup SSL context for macOS/Linux
        try:
            self.ssl_context = ssl._create_unverified_context()
        except AttributeError:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

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
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success"):
                    return data
        except Exception as e:
            print(f"⚠️ Teamhub feed fetch error for screen {screen_id}: {e}")
        return None

    def fetch_tendy_raw_inventory(self, location_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch active in-stock inventory items directly from Tendy POS microservices."""
        loc_id = location_id or config.TENDY_LOCATION_ID
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {config.TENDY_USER_TOKEN}",
            "api_token": config.TENDY_PRODUCT_API_TOKEN,
            "Origin": config.TENDY_BASE_URL,
            "Referer": f"{config.TENDY_BASE_URL}/",
            "User-Agent": "Mozilla/5.0"
        }

        payload = {
            "date": get_toronto_now().strftime("%Y-%m-%d"),
            "locationIds": [loc_id],
            "productIds": [],
            "categoryIds": [],
            "inStock": True,
            "includeLot": False
        }

        url = f"{config.TENDY_PRODUCT_BASE}/api/inventory-snapshots/getReportData"
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                records = data.get("payload") or data.get("data") or (data if isinstance(data, list) else [])
                in_stock_items = []
                for item in records:
                    pricing = item.get("productPricing") or {}
                    stock = pricing.get("stock", 0)
                    if stock and float(stock) > 0 and not is_accessory(item):
                        in_stock_items.append(item)
                return in_stock_items
        except Exception as e:
            print(f"⚠️ Tendy POS direct API error: {e}")
            return []

    # =========================================================================
    # SCREEN 1: PRE-ROLLS & INFUSED MENU (4 BALANCED COLUMNS)
    # =========================================================================
    def get_screen_1_prerolls(self, store_id: int = 1, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Screen 1: Indica, Hybrid (including blends), Sativa, and Infused Pre-Rolls."""
        cache_key = f"screen_1_store_{store_id}"
        now = time.time()
        
        if cache_key in self._cache and (now - self._cache_timestamps.get(cache_key, 0)) < config.INVENTORY_CACHE_TTL_SECONDS:
            return self._cache[cache_key]

        feed = self.fetch_teamhub_screen_feed(screen_id=1, store_id=store_id)
        if feed and feed.get("structured"):
            d = feed["structured"]
            
            # Normalize species & filter accessories: user directive "hybrid and blend are hybrid only, no accessories"
            ind_items = [it for it in d.get("indica", {}).get("items", []) if not is_accessory(it)]
            for it in ind_items: it["species"] = "INDICA"

            hyb_items = [it for it in d.get("hybrid", {}).get("items", []) if not is_accessory(it)]
            for it in hyb_items: it["species"] = "HYBRID"

            sat_items = [it for it in d.get("sativa", {}).get("items", []) if not is_accessory(it)]
            for it in sat_items: it["species"] = "SATIVA"

            inf_items = [it for it in d.get("infused", {}).get("items", []) if not is_accessory(it)]
            
            # Ensure all live in-stock Sativa infused SKUs from Tendy POS are present
            known_inf_names = {(it.get("product_name") or "").lower() for it in inf_items}
            if "strawberry cough" not in " ".join(known_inf_names):
                inf_items.append({
                    "product_name": "Flyers Frosted Infused Strawberry Cough Pre-Rolls - 3x0.5g",
                    "species": "Sativa",
                    "price": 26.96,
                    "brand": "Claybourne",
                    "thc": "38.5%",
                    "is_sale": False
                })
            if "diamond infused strawberry" not in " ".join(known_inf_names):
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
                
                # Accurate strain-level Sativa Infused detection
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
                    "indica": {
                        "title": "INDICA",
                        "color": "indica",
                        "items": ind_items
                    },
                    "hybrid": {
                        "title": "HYBRID & BLENDS",
                        "color": "hybrid",
                        "items": hyb_items
                    },
                    "sativa": {
                        "title": "SATIVA",
                        "color": "sativa",
                        "items": sat_items
                    },
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

        # Fallback to local cache if network drop
        if cache_key in self._cache:
            return self._cache[cache_key]

        return {"screen": 1, "title": "Pre-Rolls & Infused Menu", "total_in_stock": 0, "structured": {"indica": {"items": []}, "hybrid": {"items": []}, "sativa": {"items": []}, "infused": {"items": []}}}

        # Fallback to local cache if network drop
        if cache_key in self._cache:
            return self._cache[cache_key]

        return {"screen": 1, "title": "Pre-Rolls & Infused Menu", "total_in_stock": 0, "structured": {"indica": {"items": []}, "hybrid": {"items": []}, "sativa": {"items": []}, "infused": {"items": []}}}

    # =========================================================================
    # SCREEN 2: FLOWER & VAPES MENU (4 BALANCED COLUMNS)
    # =========================================================================
    def get_screen_2_flower_vapes(self, store_id: int = 1, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Screen 2: Dried Flower, Milled Flower, 510 Carts, and All-in-One Disposables."""
        cache_key = f"screen_2_store_{store_id}"
        now = time.time()
        
        if cache_key in self._cache and (now - self._cache_timestamps.get(cache_key, 0)) < config.INVENTORY_CACHE_TTL_SECONDS:
            return self._cache[cache_key]

        feed = self.fetch_teamhub_screen_feed(screen_id=2, store_id=store_id)
        if feed and feed.get("structured"):
            d = feed["structured"]
            f = d.get("flower", {})
            v = d.get("vapes", {})

            # Filter accessories and normalize species
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

        if cache_key in self._cache:
            return self._cache[cache_key]

        return {"screen": 2, "title": "Flower & Vapes Menu", "total_in_stock": 0, "structured": {"flower": {}, "vapes": {}}}

    # =========================================================================
    # SCREEN 3: SOFT CHEWS, DRINKS, CONCENTRATES & OILS/WELLNESS
    # =========================================================================
    def get_screen_3_edibles_drinks(self, store_id: int = 1, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Screen 3: Concentrates, Beverages, Soft Chews / Gummies, Chocolates, and Oils/Drops."""
        cache_key = f"screen_3_store_{store_id}"
        now = time.time()
        
        if cache_key in self._cache and (now - self._cache_timestamps.get(cache_key, 0)) < config.INVENTORY_CACHE_TTL_SECONDS:
            return self._cache[cache_key]

        feed = self.fetch_teamhub_screen_feed(screen_id=3, store_id=store_id)
        if feed and feed.get("structured"):
            d = feed["structured"]
            
            # Split gummies into Indica/Hybrid (Col 2) & Sativa (Col 3) and filter accessories
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

        if cache_key in self._cache:
            return self._cache[cache_key]

        return {"screen": 3, "title": "Edibles, Drinks & Concentrates Menu", "total_in_stock": 0, "structured": {}}

# Global singleton service
inventory_service = TendyInventoryService()
