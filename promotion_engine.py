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

class PromotionEngine:
    """Autonomous Promotion Engine supporting multiple time-based, day-based, category-based, and brand-based promotions."""

    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path = config_path
        self._last_loaded = 0
        self._promotions = []
        self._load_config()

    def _load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._promotions = data.get("promotions", [])
                    self._last_loaded = os.path.getmtime(self.config_path)
            else:
                self._promotions = []
        except Exception as e:
            print(f"[PromotionEngine] Error loading {self.config_path}: {e}")

    def get_all_promotions(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.config_path) and os.path.getmtime(self.config_path) > self._last_loaded:
            self._load_config()
        return self._promotions

    def evaluate_item(self, name: str, category: str, brand: str = "", price: float = 0.0) -> Dict[str, Any]:
        """
        Evaluate if a product qualifies for any active promotion right now.
        Returns:
            {
                "is_sale": bool,
                "price": float,
                "old_price": Optional[float],
                "discount_percent": int,
                "promo_name": Optional[str]
            }
        """
        if os.path.exists(self.config_path) and os.path.getmtime(self.config_path) > self._last_loaded:
            self._load_config()

        now = get_toronto_now()
        current_day = now.strftime("%A")  # e.g. "Monday", "Saturday"
        current_time_str = now.strftime("%H:%M")  # e.g. "13:45", "18:05"

        name_low = (name or "").lower()
        cat_low = (category or "").lower()
        brand_low = (brand or "").lower()
        sale_p = float(price or 0.0)

        for promo in self._promotions:
            if not promo.get("enabled", True):
                continue

            # 1. Day of week filter
            days = [d.capitalize() for d in promo.get("days", [])]
            if days and current_day not in days:
                continue

            # 2. Time window filter
            schedule_type = promo.get("schedule_type", "all_day")
            if schedule_type == "time_window":
                start_t = promo.get("start_time", "00:00")
                end_t = promo.get("end_time", "23:59")
                if not (start_t <= current_time_str < end_t):
                    continue

            # 3. Excluded keywords filter
            excluded = promo.get("excluded_keywords", [])
            if any(k.lower() in name_low for k in excluded):
                continue

            # 4. Category & Brand Matching
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
                    # Alias match for flower/vapes/edibles
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

        # No promo active
        return {
            "is_sale": False,
            "price": sale_p,
            "old_price": None,
            "discount_percent": 0,
            "promo_name": None
        }

# Global Singleton Instance
promotion_engine = PromotionEngine()
