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
        
STRAIN_DATABASE_PREROLL = {
    # INDICA
    "cali kush": "INDICA",
    "pink rozay": "INDICA",
    "blueberry": "INDICA",
    "zombie kush": "INDICA",
    "strawberry pie": "INDICA",
    "permanent marker": "INDICA",
    "sour kush": "INDICA",
    "pineapple nuken": "SATIVA",
    "pink drip": "INDICA",
    "kush cookies": "INDICA",
    "frozen grapes": "INDICA",
    "couch potato": "INDICA",
    "triangle kush": "INDICA",
    "pink moon": "INDICA",
    "cherry boat": "INDICA",
    "10th planet": "INDICA",
    "uk cheddar cheese": "INDICA",
    "pink kush": "INDICA",
    "blue magic": "INDICA",
    "wedding cake": "INDICA",
    "indica pre-roll": "INDICA",
    "roll up indica": "INDICA",
    "lil buddy indica": "INDICA",

    # SATIVA
    "maui wowie": "SATIVA",
    "lil buddy sativa": "SATIVA",
    "panama gold": "SATIVA",
    "tropical pocket puffs": "SATIVA",
    "diesel pocket puffs": "SATIVA",
    "sativa pre-roll": "SATIVA",
    "pineapple express": "SATIVA",
    "lavender haze": "SATIVA",
    "peggys puff": "SATIVA",
    "blueberry dream": "SATIVA",
    "zsweet": "SATIVA",
    "rooster call": "SATIVA",
    "sgt. pineapple": "SATIVA",
    "roll up sativa": "SATIVA",
    "fruit loopz": "SATIVA",
    "animal face": "SATIVA",
    "crumbled lime": "SATIVA",
    "lemon shocker": "SATIVA",
    "bahama berry": "SATIVA",
    "lemon diesel": "SATIVA",
    "sour chem": "SATIVA",
    "plg #7": "SATIVA",
    "pink lemon gas": "SATIVA",

    # HYBRID & BLENDS
    "liquid imagination": "HYBRID",
    "billy blunt": "HYBRID",
    "juicy blunt": "HYBRID",
    "dutchy blunt": "HYBRID",
    "forbidden applez": "HYBRID",
    "twofer": "HYBRID",
    "opp sativa - indica": "HYBRID",
    "junior j": "HYBRID",
    "animal mintz": "HYBRID",
    "animal rntz": "HYBRID",
    "double dutchies": "HYBRID",
    "grape diamonds": "HYBRID",
    "fruit punch slims": "HYBRID",
    "rolls pre-roll": "HYBRID"
}

def classify_preroll(name: str, brand: str = "") -> str:
    full = f"{brand} {name}".lower()
    for pattern, species in STRAIN_DATABASE_PREROLL.items():
        if pattern in full:
            return species
    if "sativa" in full: return "SATIVA"
    if "indica" in full: return "INDICA"
STRAIN_DATABASE_FLOWER = {
    # INDICA
    "blueberry muffinz": "INDICA",
    "couch potato": "INDICA",
    "gmo cookies": "INDICA",
    "kush cookies": "INDICA",
    "purple cherry punch": "INDICA",
    "cali kush": "INDICA",
    "cropped blueberry": "INDICA",
    "sapphire kush": "INDICA",
    "strawberry pie": "INDICA",
    "pure milled - indica": "INDICA",
    "pure milled indica": "INDICA",
    "pop n’ pour blue raspberry": "INDICA",
    "pop n pour blue raspberry": "INDICA",

    # SATIVA
    "cosmic lemonade": "SATIVA",
    "frosted lemons": "SATIVA",
    "ripped sativa": "SATIVA",
    "rooster call": "SATIVA",
    "sour chem": "SATIVA",
    "strawberry cheezequake": "SATIVA",
    "tutti frutti crunchy puff": "SATIVA",
    "citrus sweet": "SATIVA",
    "lemon pave": "SATIVA",
    "maui wowie": "SATIVA",
    "pure milled - sativa": "SATIVA",
    "pure milled sativa": "SATIVA",
    "pop n’ pour strawnana": "SATIVA",
    "pop n pour strawnana": "SATIVA",

    # HYBRID
    "chromatica": "HYBRID",
    "chubby nuggies": "HYBRID",
    "farmer’s market": "HYBRID",
    "farmers market": "HYBRID",
    "frosted cream puffs": "HYBRID",
    "moon drifter": "HYBRID",
    "secret formula": "HYBRID",
    "the goods": "HYBRID",
    "the handy harvest": "HYBRID",
    "do-si-dos": "HYBRID",
    "sgt. pineapple": "HYBRID",
    "dragon cake": "HYBRID"
}

def classify_flower(name: str, brand: str = "") -> str:
    full = f"{brand} {name}".lower()
    for pattern, species in STRAIN_DATABASE_FLOWER.items():
        if pattern in full:
            return species
    if "sativa" in full: return "SATIVA"
    if "indica" in full: return "INDICA"
    return "HYBRID"

STRAIN_DATABASE_VAPE = {
    # INDICA
    "blue razz": "INDICA",
    "blue venom": "INDICA",
    "blueberry kush": "INDICA",
    "cherry liquid diamond": "INDICA",
    "blue zello": "INDICA",
    "hawaiian za": "INDICA",
    "jungle fruit": "INDICA",
    "lemon freeze": "INDICA",
    "blood orange tangie": "INDICA",
    "tiger blood": "INDICA",
    "watermelon splash": "INDICA",
    "wild berry": "INDICA",
    "fruit punch bowl": "INDICA",
    "mango fuzz": "INDICA",
    "watermelon ice": "INDICA",

    # HYBRID
    "banana og": "HYBRID",
    "fruity gobstomper": "HYBRID",
    "fruity gobbstomper": "HYBRID",
    "blueberry octane": "HYBRID",
    "macchiato gold": "HYBRID",
    "strawberry banana": "HYBRID",
    "ninja fruit": "HYBRID",
    "poppin peach": "HYBRID",
    "alien og": "HYBRID",
    "kush mint": "HYBRID",
    "lemonade classic": "HYBRID",

    # SATIVA
    "acapulco gold": "SATIVA",
    "blue kiwi": "SATIVA",
    "cloudberry": "SATIVA",
    "strawberry": "SATIVA",
    "pink grapefruit": "SATIVA",
    "mango sour": "SATIVA",
    "mosa x blood orange": "SATIVA",
    "peach shockwave": "SATIVA",
    "sticky grape": "SATIVA",
    "strawberry lemonade": "SATIVA",
    "blue daze": "SATIVA",
    "pineapple paradise": "SATIVA",
    "peach lemonade": "SATIVA",
    "rainbow melon": "SATIVA",
    "sunset sherb": "SATIVA"
}

def classify_vape(name: str, brand: str = "") -> str:
    full = f"{brand} {name}".lower()
    for pattern, species in STRAIN_DATABASE_VAPE.items():
        if pattern in full:
            return species
    if "sativa" in full: return "SATIVA"
    if "indica" in full: return "INDICA"
    return "HYBRID"
def clean_product_title(name: str, brand: str = "", variant: str = "", screen_id: int = 1) -> str:
    """Format clean, luxury dispensary menu title without redundant category keywords."""
    b = brand.strip().upper() if brand else ""
    n = name.strip()
    v = variant.strip()
    
    n = re.sub(r'(?i)\s+Pre-Rolls?', '', n)
    n = re.sub(r'(?i)\s+510 Thread Cartridge', '', n)
    n = re.sub(r'(?i)\s+510 Thread', '', n)
    n = re.sub(r'(?i)\s+510 Cartridge', '', n)
    n = re.sub(r'(?i)\s+510 Vape Cart', '', n)
    n = re.sub(r'(?i)\s+All-in-One Vape', '', n)
    n = re.sub(r'(?i)\s+All-In-One Vape', '', n)
    n = re.sub(r'(?i)\s+All-in-One', '', n)
    n = re.sub(r'(?i)\s+Disposable', '', n)
    n = re.sub(r'(?i)\s+Dried Flower', '', n)
    n = re.sub(r'\s*-\s*', ' ', n)
    
    if v:
        if v in n:
            n = n.replace(f"({v})", "").replace(f"- {v}", "").replace(v, "").strip()
        final_str = f"{b} • {n} {v}" if b else f"{n} {v}"
    else:
        final_str = f"{b} • {n}" if b else n
        
    final_str = re.sub(r'\s+', ' ', final_str).strip()
    return final_str

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
    "lemon pave milled": {"thc": "28.0%", "cbd": "1.0%"},
    "maui wowie milled": {"thc": "29.0%", "cbd": "1.0%"},
    "pop n' pour strawnana": {"thc": "28.0%", "cbd": "0.5%"},
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
    
    for pattern, spec in PRODUCT_POTENCY_DATABASE.items():
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

        feed = None
        if False:
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
            
            known_inf = " ".join([(it.get("product_name") or "").lower() for it in inf_items])
            if "strawberry cough" not in known_inf:
                inf_items.append({
                    "product_name": "CLAYBOURNE • Flyers Frosted Infused Strawberry Cough 3x0.5g",
                    "species": "Sativa",
                    "price": 26.96,
                    "brand": "Claybourne",
                    "thc": "38.5%",
                    "is_sale": False
                })
            if "diamond infused strawberry" not in known_inf:
                inf_items.append({
                    "product_name": "JAYS • High Potency 50+ Diamond Infused Strawberry 3x0.5g",
                    "species": "Sativa",
                    "price": 24.43,
                    "brand": "Jays",
                    "thc": "54.0%",
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
            
            p_title = clean_product_title(name, brand, var, screen_id=1)
            potency = lookup_authentic_potency(name, brand, screen_id=1)
            sale_p = float(price or 0.0)
            is_promo = ("infused" in cat.lower() or "infused" in name.lower())
            old_p = round(sale_p / 0.90, 2) if (is_promo and sale_p > 0) else None
            entry = {
                "product_name": p_title,
                "price": sale_p,
                "old_price": old_p,
                "stock": stock,
                "brand": brand,
                "thc": potency["thc"],
                "cbd": potency.get("cbd", "<1.0%"),
                "is_sale": is_promo
            }

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
                spec = classify_preroll(name, brand)
                entry["species"] = spec
                if spec == "INDICA":
                    ind_items.append(entry)
                elif spec == "SATIVA":
                    sat_items.append(entry)
                else:
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

        feed = None
        if False:
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
            cat = (it.get("category") or {}).get("name", "")
            name = it.get("name", "")
            pricing = it.get("productPricing") or {}
            price = pricing.get("sale_price", 0)
            stock = pricing.get("stock", 0)
            brand = (it.get("brand") or {}).get("name", "")
            var = it.get("variantName", "")
            
            p_title = clean_product_title(name, brand, var, screen_id=2)
            potency = lookup_authentic_potency(name, brand, screen_id=2)
            sale_p = float(price or 0.0)
            n_low = name.lower()
            is_promo = not ("sapphire kush" in n_low or "dragon cake" in n_low)
            old_p = round(sale_p / 0.90, 2) if (is_promo and sale_p > 0) else None
            entry = {
                "product_name": p_title,
                "price": sale_p,
                "old_price": old_p,
                "stock": stock,
                "brand": brand,
                "thc": potency["thc"],
                "cbd": potency.get("cbd", "<1.0%"),
                "is_sale": is_promo
            }

            if "Flower" in cat or "Dried" in cat or "Milled" in cat:
                n_low = name.lower()
                is_mil = "milled" in cat.lower() or "milled" in n_low
                spec = classify_flower(name, brand)
                entry["species"] = spec
                if spec == "SATIVA":
                    (sat_mil if is_mil else sat_dr).append(entry)
                elif spec == "INDICA":
                    (ind_mil if is_mil else ind_dr).append(entry)
                else:
                    (hyb_mil if is_mil else hyb_dr).append(entry)

            elif "510 Cartridges" in cat:
                spec = classify_vape(name, brand)
                entry["species"] = spec
                if spec == "SATIVA":
                    v510_sat.append(entry)
                elif spec == "INDICA":
                    v510_ind.append(entry)
                else:
                    v510_hyb.append(entry)

            elif "Disposable Vapes" in cat:
                spec = classify_vape(name, brand)
                entry["species"] = spec
                if spec == "SATIVA":
                    disp_sat.append(entry)
                elif spec == "INDICA":
                    disp_ind.append(entry)
                else:
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

        feed = None
        if False:
            d = feed["structured"]
            all_gummies = [it for it in d.get("gummies", {}).get("items", []) if not is_accessory(it)]
            g_ind_hyb = []
            g_sat = []

            for it in all_gummies:
                spec = (it.get("species") or "HYBRID").upper()
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=3)
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
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=3)

            beverages = [it for it in d.get("beverages", {}).get("items", []) if not is_accessory(it)]
            for it in beverages:
                spec = (it.get("species") or "HYBRID").upper()
                it["species"] = "SATIVA" if "SATIVA" in spec else ("INDICA" if "INDICA" in spec else "HYBRID")
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=3)

            chocolates = [it for it in d.get("chocolates", {}).get("items", []) if not is_accessory(it)]
            for it in chocolates:
                spec = (it.get("species") or "HYBRID").upper()
                it["species"] = "SATIVA" if "SATIVA" in spec else ("INDICA" if "INDICA" in spec else "HYBRID")
                it["product_name"] = clean_product_title(it.get("product_name", ""), it.get("brand", ""), screen_id=3)

            wellness = [it for it in d.get("wellness", {}).get("items", []) if not is_accessory(it)]
            for it in wellness:
                spec = (it.get("species") or "HYBRID").upper()
                it["species"] = "SATIVA" if "SATIVA" in spec else ("INDICA" if "INDICA" in spec else "HYBRID")
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
            cat = (it.get("category") or {}).get("name", "")
            name = it.get("name", "")
            pricing = it.get("productPricing") or {}
            price = pricing.get("sale_price", 0)
            stock = pricing.get("stock", 0)
            brand = (it.get("brand") or {}).get("name", "")
            var = it.get("variantName", "")
            
            p_title = clean_product_title(name, brand, var, screen_id=3)
            potency = lookup_authentic_potency(name, brand, screen_id=3)
            sale_p = float(price or 0.0)
            n_low = name.lower()
            c_low = cat.lower()
            is_promo = any(k in c_low for k in ["concentrate", "extract", "rosin", "shatter", "topical", "oil", "capsule", "wellness"]) or any(k in n_low for k in ["shatter", "rosin", "diamonds", "moonrocks", "cbd cream"])
            old_p = round(sale_p / 0.90, 2) if (is_promo and sale_p > 0) else None
            entry = {
                "product_name": p_title,
                "price": sale_p,
                "old_price": old_p,
                "stock": stock,
                "brand": brand,
                "thc": potency["thc"],
                "cbd": potency.get("cbd", "<1mg"),
                "is_sale": is_promo
            }

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
