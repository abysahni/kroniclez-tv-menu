# 📺 Kroniclez Digital TV Menu Board (Live Tendy POS Sync)

High-definition, real-time digital cannabis menu board system for Kroniclez retail store TV screens (Kitchener & Waterloo).

Connects directly to **Tendy POS Inventory Microservices** to pull live in-stock products, automatically filter out sold-out items, classify cannabis strains into accurate categories, and display prices & potencies on store screens.

---

## 🌟 Menu Screens Overview

### **Screen 1: Pre-Rolls & Infused Menu**
* URL: `http://localhost:5060/?screen=1`
* **Column 1**: Indica Pre-Rolls
* **Column 2**: Hybrid Pre-Rolls (includes all Blends)
* **Column 3**: Sativa Pre-Rolls
* **Column 4**: Infused Pre-Rolls (Indica, Hybrid, and Sativa Diamond/Terpene Infused)

### **Screen 2: Flower & Vapes Menu**
* URL: `http://localhost:5060/?screen=2`
* **Column 1**: Indica & Hybrid Dried Flower (+ Milled Flower below)
* **Column 2**: Sativa Dried Flower (+ Milled Flower below)
* **Column 3**: 510 Thread Cartridges (Indica & Hybrid)
* **Column 4**: 510 Sativa Cartridges & All-in-One Disposables

### **Screen 3: Soft Chews, Beverages & Concentrates Menu**
* URL: `http://localhost:5060/?screen=3`
* **Column Deck 1 (Left)**: Concentrates (Live Rosin, Diamonds, Shatter) & Ready-to-Drink THC/CBD Beverages
* **Column Deck 2 (Center)**: Indica & Hybrid Soft Chews / Gummies + Chocolates & Sweets
* **Column Deck 3 (Right)**: Sativa Soft Chews / Gummies + Wellness, Oils & Capsules

---

## 🎮 TV Remote & Keyboard Hotkeys

| Hotkey | Action |
| :--- | :--- |
| **`1`** | Jump to **Screen 1: Pre-Rolls & Infused** |
| **`2`** | Jump to **Screen 2: Flower & Vapes** |
| **`3`** | Jump to **Screen 3: Soft Chews & Drinks** |
| **`F`** | Toggle **Full Screen** mode |
| **`A`** | Toggle **Auto-Cycle Rotation Mode** (switches screen every 30 seconds) |
| **`R`** | Force refresh live inventory from Tendy POS |

---

## 🚀 Running the Server Locally

```bash
cd kroniclez_tv_menu
python3 server.py
```

The menu will be accessible at:
* **All Screens (with floating nav)**: `http://localhost:5060`
* **Direct TV 1**: `http://localhost:5060/?screen=1`
* **Direct TV 2**: `http://localhost:5060/?screen=2`
* **Direct TV 3**: `http://localhost:5060/?screen=3`
* **Auto-Rotating Screen**: `http://localhost:5060/?screen=1&auto=1`
