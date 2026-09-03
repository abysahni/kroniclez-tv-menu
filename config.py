import os
from pathlib import Path

# Project Directories
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# Load .env if present
env_path = BASE_DIR / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# Tendy POS Configuration
TENDY_BASE_URL = os.getenv("TENDY_BASE_URL", "https://admin.tendypos.com")
TENDY_AUTH_BASE = os.getenv("TENDY_AUTH_BASE", "https://auth.api.tendypos.net")
TENDY_ORDER_BASE = os.getenv("TENDY_ORDER_BASE", "https://order.api.tendypos.net")
TENDY_PRODUCT_BASE = os.getenv("TENDY_PRODUCT_BASE", "https://product.api.tendypos.net")

TENDY_USERNAME = os.getenv("TENDY_USERNAME", "seabrook@kroniclez.com")
TENDY_PASSWORD = os.getenv("TENDY_PASSWORD", "Se@brook0107")
TENDY_USER_TOKEN = os.getenv(
    "TENDY_USER_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJidXNpbmVzc0lkIjoiZGIzODQ1NzItMTZkMi00NWE3LTgwZmEtODczMGFlODllMTdlIiwibG9jYXRpb25JZCI6ImRjOTQ0OWE3LTk1M2ItNDdhMS05ZGNjLWZmZTNjNjRiZThjOSIsInVzZXJJZCI6IjhiMGVlYTE4LTgyNDgtNGUzYS05ODFhLTM1Yzc1MmY0NzIxOSIsImlhdCI6MTc4NzYyNzI3OSwianRpIjoiMTc4NzYyNzI3OTcwOSJ9.1NGP779FBA0VEw25zr3qj00X4q7KOHwwmWchIqE12rQ"
)

TENDY_BUSINESS_ID = os.getenv("TENDY_BUSINESS_ID", "db384572-16d2-45a7-80fa-8730ae89e17e")
TENDY_LOCATION_ID = os.getenv("TENDY_LOCATION_ID", "dc9449a7-953b-47a1-9dcc-ffe3c64be8c9")
TENDY_PRODUCT_API_TOKEN = os.getenv("TENDY_PRODUCT_API_TOKEN", "laymXDAzvJ8lW24jNxZKivmkTFnZBi42")
TENDY_LOGIN_API_TOKEN = os.getenv("TENDY_LOGIN_API_TOKEN", "E0ddzJllAvPu0po9g2ieJm5q5zPl01iP")

STORE_NAME = os.getenv("STORE_NAME", "Kroniclez - Kitchener")
TAX_RATE_HST = float(os.getenv("TAX_RATE_HST", "0.13"))
PORT = int(os.getenv("PORT", "5070"))
HOST = os.getenv("HOST", "0.0.0.0")
INVENTORY_CACHE_TTL_SECONDS = int(os.getenv("INVENTORY_CACHE_TTL_SECONDS", "25"))
ADMIN_PIN = os.getenv("ADMIN_PIN", "4200")
OVERRIDES_FILE = BASE_DIR / "product_overrides.json"
