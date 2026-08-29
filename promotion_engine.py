import os
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

try:
    from zoneinfo import ZoneInfo
    TORONTO_TZ = ZoneInfo("America/Toronto")
except ImportError:
    TORONTO_TZ = timezone(timedelta(hours=-4))

def get_toronto_now() -> datetime:
    """Return current timestamp in America/Toronto timezone."""
    return datetime.now(TORONTO_TZ)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "promotions_config.json")
REGULAR_PRICES_PATH = os.path.join(os.path.dirname(__file__), "regular_prices.json")

class PromotionEngine:
    """
    Autonomous Promotion Engine supporting:
    1. Direct Regular Price Comparison (any price lowered below regular price triggers sale mode).
    2. Scheduled Multi-Promotions (Happy Hour 1PM-4PM, Munchie Monday, Flower Friday, etc.).
    """

    def __init__(self, config_path: str = CONFIG_PATH, reg_prices_path: str = REGULAR_PRICES_PATH):
        self.config_path = config_path
        self.reg_prices_path = reg_prices_path
        self._last_loaded_config = 0
        self._last_loaded_reg = 0
        self._promotions = []
        self._regular_prices = {}
        self._load_all()

    def _load_all(self):
        # 1. Load Promotions Config
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._promotions = data.get("promotions", [])
                    self._last_loaded_config = os.path.getmtime(self.config_path)
            else:
                self._promotions = []
        except Exception as e:
            print(f"[PromotionEngine] Error loading {self.config_path}: {e}")

        # 2. Load Regular Prices Database
        try:
            if os.path.exists(self.reg_prices_path):
                with open(self.reg_prices_path, "r", encoding="utf-8") as f:
                    self._regular_prices = json.load(f)
                    self._last_loaded_reg = os.path.getmtime(self.reg_prices_path)
            else:
                self._regular_prices = {}
        except Exception as e:
            print(f"[PromotionEngine] Error loading {self.reg_prices_path}: {e}")

    def get_all_promotions(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.config_path) and os.path.getmtime(self.config_path) > self._last_loaded_config:
            self._load_all()
        return self._promotions

    def get_regular_price(self, name: str, sku_id: str = "") -> Optional[float]:
        """Lookup regular baseline price for an item by SKU ID or normalized name."""
        if os.path.exists(self.reg_prices_path) and os.path.getmtime(self.reg_prices_path) > self._last_loaded_reg:
            self._load_all()

        # Try SKU match
        if sku_id and str(sku_id) in self._regular_prices:
            return float(self._regular_prices[str(sku_id)].get("regular_price", 0))

        # Try Name match
        name_clean = (name or "").strip().lower()
        for k, v in self._regular_prices.items():
            if v.get("name", "").strip().lower() == name_clean:
                return float(v.get("regular_price", 0))

        return None

    def evaluate_item(self, name: str, category: str, brand: str = "", price: float = 0.0, sku_id: str = "") -> Dict[str, Any]:
        """
        Evaluate if a product qualifies for sale display.
        Rule 1: If current POS price < regular baseline price -> Auto Sale!
        Rule 2: If active scheduled promotion rule applies -> Scheduled Sale!
        """
        if os.path.exists(self.config_path) and os.path.getmtime(self.config_path) > self._last_loaded_config:
            self._load_all()
        if os.path.exists(self.reg_prices_path) and os.path.getmtime(self.reg_prices_path) > self._last_loaded_reg:
            self._load_all()

        sale_p = float(price or 0.0)
        name_low = (name or "").lower()
        cat_low = (category or "").lower()
        brand_low = (brand or "").lower()

        # --- RULE 1: DIRECT REGULAR PRICE COMPARISON ---
        reg_p = self.get_regular_price(name, sku_id)
        if reg_p and reg_p > 0:
            # If current price is at least $0.10 lower than regular price, it is a SALE!
            if sale_p < (reg_p - 0.05):
                disc_pct = round(((reg_p - sale_p) / reg_p) * 100)
                return {
                    "is_sale": True,
                    "price": sale_p,
                    "old_price": reg_p,
                    "discount_percent": disc_pct,
                    "promo_name": "Special Sale Price"
                }

        # --- RULE 2: SCHEDULED MULTI-PROMOTION RULES ---
        now = get_toronto_now()
        current_day = now.strftime("%A")
        current_time_str = now.strftime("%H:%M")

        for promo in self._promotions:
            if not promo.get("enabled", True):
                continue

            days = [d.capitalize() for d in promo.get("days", [])]
            if days and current_day not in days:
                continue

            schedule_type = promo.get("schedule_type", "all_day")
            if schedule_type == "time_window":
                start_t = promo.get("start_time", "00:00")
                end_t = promo.get("end_time", "23:59")
                if not (start_t <= current_time_str < end_t):
                    continue

            excluded = promo.get("excluded_keywords", [])
            if any(k.lower() in name_low for k in excluded):
                continue

            promo_cats = [c.lower() for c in promo.get("categories", [])]
            promo_brands = [b.lower() for b in promo.get("brands", [])]

            cat_match = False
            if not promo_cats:
                cat_match = True
            else:
                for c in promo_cats:
                    if c in cat_low or c in name_low:
                        cat_match = True
                        break
                    if "flower" in c and ("flower" in cat_low or "milled" in cat_low):
                        cat_match = True
                        break
                    if "vape" in c and ("vape" in cat_low or "cartridge" in cat_low):
                        cat_match = True
                        break
                    if "concentrate" in c and ("concentrate" in cat_low or "extract" in cat_low or "hash" in name_low or "rosin" in name_low or "shatter" in name_low or "diamond" in name_low):
                        cat_match = True
                        break
                    if "edible" in c and ("edible" in cat_low or "soft chew" in cat_low or "gummy" in name_low or "chocolate" in cat_low):
                        cat_match = True
                        break

            brand_match = False
            if not promo_brands:
                brand_match = True
            else:
                for b in promo_brands:
                    if b in brand_low or b in name_low:
                        brand_match = True
                        break

            if cat_match and brand_match:
                discount_pct = int(promo.get("discount_percent", 10))
                factor = 1.0 - (discount_pct / 100.0)
                old_p = round(sale_p / factor, 2) if (sale_p > 0 and factor > 0) else None
                return {
                    "is_sale": True,
                    "price": sale_p,
                    "old_price": old_p,
                    "discount_percent": discount_pct,
                    "promo_name": promo.get("name", "Special Promotion")
                }

        # Regular Price / No Promo
        return {
            "is_sale": False,
            "price": sale_p,
            "old_price": None,
            "discount_percent": 0,
            "promo_name": None
        }

# Global Singleton Instance
promotion_engine = PromotionEngine()
