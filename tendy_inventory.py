import json
import re
import ssl
import time
import urllib.request
import urllib.parse
import urllib.error
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional

import config

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
            "date": datetime.now().strftime("%Y-%m-%d"),
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
                    if stock and float(stock) > 0:
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
            
            # Normalize species: user directive "hybrid and blend are hybrid only"
            ind_items = d.get("indica", {}).get("items", [])
            for it in ind_items: it["species"] = "INDICA"

            hyb_items = d.get("hybrid", {}).get("items", [])
            for it in hyb_items: it["species"] = "HYBRID"

            sat_items = d.get("sativa", {}).get("items", [])
            for it in sat_items: it["species"] = "SATIVA"

            inf_items = d.get("infused", {}).get("items", [])
            inf_ind = []
            inf_hyb = []
            inf_sat = []

            for it in inf_items:
                spec = (it.get("species") or "HYBRID").upper()
                if "INDICA" in spec:
                    it["species"] = "INDICA"
                    inf_ind.append(it)
                elif "SATIVA" in spec:
                    it["species"] = "SATIVA"
                    inf_sat.append(it)
                else:
                    it["species"] = "HYBRID"
                    inf_hyb.append(it)

            result = {
                "screen": 1,
                "title": "Pre-Rolls & Infused Menu",
                "store": config.STORE_NAME,
                "total_in_stock": len(ind_items) + len(hyb_items) + len(sat_items) + len(inf_items),
                "updated_at": datetime.now().strftime("%I:%M:%S %p EST"),
                "structured": {
                    "indica": {
                        "title": "INDICA",
                        "color": "indica",
                        "items": ind_items
                    },
                    "hybrid": {
                        "title": "HYBRID",
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

            # Clean and normalize species
            for it in f.get("indica_dried", {}).get("items", []): it["species"] = "INDICA"
            for it in f.get("indica_milled", {}).get("items", []): it["species"] = "INDICA"
            for it in f.get("hybrid_dried", {}).get("items", []): it["species"] = "HYBRID"
            for it in f.get("hybrid_milled", {}).get("items", []): it["species"] = "HYBRID"
            for it in f.get("sativa_dried", {}).get("items", []): it["species"] = "SATIVA"
            for it in f.get("sativa_milled", {}).get("items", []): it["species"] = "SATIVA"

            for it in v.get("vapes_510_indica", {}).get("items", []): it["species"] = "INDICA"
            for it in v.get("vapes_510_hybrid", {}).get("items", []): it["species"] = "HYBRID"
            for it in v.get("vapes_510_sativa", {}).get("items", []): it["species"] = "SATIVA"

            for it in v.get("disp_indica", {}).get("items", []): it["species"] = "INDICA"
            for it in v.get("disp_hybrid", {}).get("items", []): it["species"] = "HYBRID"
            for it in v.get("disp_sativa", {}).get("items", []): it["species"] = "SATIVA"

            total_items = (
                len(f.get("indica_dried", {}).get("items", [])) +
                len(f.get("indica_milled", {}).get("items", [])) +
                len(f.get("hybrid_dried", {}).get("items", [])) +
                len(f.get("hybrid_milled", {}).get("items", [])) +
                len(f.get("sativa_dried", {}).get("items", [])) +
                len(f.get("sativa_milled", {}).get("items", [])) +
                len(v.get("vapes_510_indica", {}).get("items", [])) +
                len(v.get("vapes_510_hybrid", {}).get("items", [])) +
                len(v.get("vapes_510_sativa", {}).get("items", [])) +
                len(v.get("disp_indica", {}).get("items", [])) +
                len(v.get("disp_hybrid", {}).get("items", [])) +
                len(v.get("disp_sativa", {}).get("items", []))
            )

            result = {
                "screen": 2,
                "title": "Flower & Vapes Menu",
                "store": config.STORE_NAME,
                "total_in_stock": total_items,
                "updated_at": datetime.now().strftime("%I:%M:%S %p EST"),
                "structured": {
                    "flower": f,
                    "vapes": v
                }
            }
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = now
            return result

        if cache_key in self._cache:
            return self._cache[cache_key]

        return {"screen": 2, "title": "Flower & Vapes Menu", "total_in_stock": 0, "structured": {"flower": {}, "vapes": {}}}

    # =========================================================================
    # SCREEN 3: SOFT CHEWS, DRINKS, CONCENTRATES & WELLNESS (3 COLUMN DECKS)
    # =========================================================================
    def get_screen_3_edibles_drinks(self, store_id: int = 1, location_id: Optional[str] = None) -> Dict[str, Any]:
        """Screen 3: Concentrates, Beverages, Soft Chews / Gummies, Chocolates, and Wellness."""
        cache_key = f"screen_3_store_{store_id}"
        now = time.time()
        
        if cache_key in self._cache and (now - self._cache_timestamps.get(cache_key, 0)) < config.INVENTORY_CACHE_TTL_SECONDS:
            return self._cache[cache_key]

        feed = self.fetch_teamhub_screen_feed(screen_id=3, store_id=store_id)
        if feed and feed.get("structured"):
            d = feed["structured"]
            
            # Split gummies into Indica/Hybrid (Col 2) & Sativa (Col 3)
            all_gummies = d.get("gummies", {}).get("items", [])
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

            for it in d.get("concentrates", {}).get("items", []):
                spec = (it.get("species") or "HYBRID").upper()
                it["species"] = "SATIVA" if "SATIVA" in spec else ("INDICA" if "INDICA" in spec else "HYBRID")

            for it in d.get("beverages", {}).get("items", []):
                spec = (it.get("species") or "HYBRID").upper()
                it["species"] = "SATIVA" if "SATIVA" in spec else ("INDICA" if "INDICA" in spec else "HYBRID")

            for it in d.get("chocolates", {}).get("items", []):
                spec = (it.get("species") or "HYBRID").upper()
                it["species"] = "SATIVA" if "SATIVA" in spec else ("INDICA" if "INDICA" in spec else "HYBRID")

            for it in d.get("wellness", {}).get("items", []):
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

            total_items = (
                len(d.get("concentrates", {}).get("items", [])) +
                len(d.get("beverages", {}).get("items", [])) +
                len(all_gummies) +
                len(d.get("chocolates", {}).get("items", [])) +
                len(d.get("wellness", {}).get("items", []))
            )

            result = {
                "screen": 3,
                "title": "Soft Chews & Edibles Menu",
                "store": config.STORE_NAME,
                "total_in_stock": total_items,
                "updated_at": datetime.now().strftime("%I:%M:%S %p EST"),
                "structured": {
                    "concentrates": d.get("concentrates", {"title": "Concentrates", "subtitle": "PREMIUM EXTRACTS", "color": "gold", "items": []}),
                    "beverages": d.get("beverages", {"title": "Beverages", "subtitle": "REFRESH • RELAX • ENJOY", "color": "cyan", "items": []}),
                    "gummies_ind_hyb": g_ind_hyb_card,
                    "chocolates": d.get("chocolates", {"title": "Chocolates", "subtitle": "ARTISAN SWEETS", "color": "orange", "items": []}),
                    "gummies_sativa": g_sat_card,
                    "wellness": d.get("wellness", {"title": "Wellness & Topicals", "subtitle": "HEALTH & BALANCE", "color": "purple", "items": []})
                }
            }
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = now
            return result

        if cache_key in self._cache:
            return self._cache[cache_key]

        return {"screen": 3, "title": "Soft Chews & Edibles Menu", "total_in_stock": 0, "structured": {}}

# Global singleton service
inventory_service = TendyInventoryService()
