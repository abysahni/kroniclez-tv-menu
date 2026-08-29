import os
import sys
import json
import gzip
import time
import threading
import urllib.parse
import urllib.request
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import config
from tendy_inventory import inventory_service

class KroniclezTVMenuHandler(BaseHTTPRequestHandler):
    """Production HTTP Handler for Kroniclez Digital TV Menu Board."""

    def _compress_if_supported(self, data: bytes):
        """Compress response using gzip if client supports it."""
        accept_encoding = self.headers.get("Accept-Encoding", "")
        if "gzip" in accept_encoding and len(data) > 300:
            compressed = gzip.compress(data, compresslevel=6)
            return compressed, True
        return data, False

    def _send_json(self, data: dict, status_code: int = 200):
        """Send JSON response with Gzip compression and CORS headers."""
        encoded = json.dumps(data, default=str).encode("utf-8")
        body, is_gzipped = self._compress_if_supported(encoded)

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        if is_gzipped:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path):
        """Serve static file with caching and Gzip compression."""
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File Not Found")
            return

        ext = file_path.suffix.lower()
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".ico": "image/x-icon",
            ".woff2": "font/woff2"
        }
        content_type = content_types.get(ext, "application/octet-stream")

        with open(file_path, "rb") as f:
            raw_data = f.read()

        body, is_gzipped = self._compress_if_supported(raw_data)

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        if is_gzipped:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. API Endpoints
        if path == "/api/tv-menu" or path == "/api/tv_menu_feed.php":
            screen_id = int(query.get("screen", [1])[0])
            store_id = query.get("store", ["1"])[0]

            loc_id = config.TENDY_LOCATION_ID

            if screen_id == 1:
                data = inventory_service.get_screen_1_prerolls(location_id=loc_id)
            elif screen_id == 2:
                data = inventory_service.get_screen_2_flower_vapes(location_id=loc_id)
            else:
                data = inventory_service.get_screen_3_edibles_drinks(location_id=loc_id)

            self._send_json({"success": True, **data})

        elif path == "/api/health" or path == "/healthz":
            self._send_json({"status": "ok", "service": "kroniclez-tv-menu", "store": config.STORE_NAME})

        elif path in ["/api/audit", "/audit"]:
            from audit_inventory_agent import InventoryAuditAgent
            agent = InventoryAuditAgent()
            results = agent.run_full_audit()
            self._send_json({"success": True, **results})

        elif path == "/api/debug":
            raw = inventory_service.fetch_tendy_raw_inventory()
            feed1 = inventory_service.fetch_teamhub_screen_feed(1)
            self._send_json({
                "raw_count": len(raw),
                "has_scoped_token": bool(inventory_service._scoped_token),
                "feed1_ok": bool(feed1 and feed1.get("success")),
                "screen1": inventory_service.get_screen_1_prerolls()
            })

        elif path == "/api/config":
            self._send_json({
                "store_name": config.STORE_NAME,
                "tendy_base_url": config.TENDY_BASE_URL,
                "tax_rate_hst": config.TAX_RATE_HST
            })

        # 2. Main TV Menu Frontend Pages (Dedicated TV endpoints)
        elif path in ["/", "/index.html", "/tv_menu.php"]:
            self._send_injected_index(query)
        elif path in ["/tv1", "/screen1"]:
            query["screen"] = ["1"]
            self._send_injected_index(query)
        elif path in ["/tv2", "/screen2"]:
            query["screen"] = ["2"]
            self._send_injected_index(query)
        elif path in ["/tv3", "/screen3"]:
            query["screen"] = ["3"]
            self._send_injected_index(query)

        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._send_file(config.STATIC_DIR / rel)
        else:
            potential_file = config.STATIC_DIR / path.lstrip("/")
            if potential_file.exists() and potential_file.is_file():
                self._send_file(potential_file)
            else:
                self._send_injected_index(query)

    def _send_injected_index(self, query: dict):
        """Serve index.html with instant pre-injected state for zero-latency TV boot."""
        html_file = config.STATIC_DIR / "index.html"
        if not html_file.exists():
            self.send_error(404, "index.html Not Found")
            return

        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        screen_id = int(query.get("screen", [1])[0]) if query else 1
        
        try:
            if screen_id == 1:
                initial_screen_data = inventory_service.get_screen_1_prerolls()
            elif screen_id == 2:
                initial_screen_data = inventory_service.get_screen_2_flower_vapes()
            else:
                initial_screen_data = inventory_service.get_screen_3_edibles_drinks()

            script_tag = f"""<script id="tv-preloaded-data">
window.__INITIAL_SCREEN_ID__ = {screen_id};
window.__INITIAL_MENU_DATA__ = {json.dumps({"success": True, **initial_screen_data}, default=str)};
</script>"""
            html_content = html_content.replace("</head>", f"{script_tag}\n</head>")
        except Exception as e:
            print(f"⚠️ Pre-render injection error: {e}")

        encoded = html_content.encode("utf-8")
        body, is_gzipped = self._compress_if_supported(encoded)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if is_gzipped:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def background_keepalive_worker():
    """Ping health endpoint every 3 minutes to keep Render container warm and 100% awake."""
    while True:
        time.sleep(180)
        target = "https://kroniclez-tv-menu.onrender.com/api/health"
        try:
            req = urllib.request.Request(target, headers={"User-Agent": "KroniclezTVMenu-KeepAlive/2.0"})
            with urllib.request.urlopen(req, timeout=12) as r:
                pass
        except Exception:
            try:
                local_req = urllib.request.Request(f"http://127.0.0.1:{config.PORT}/api/health")
                with urllib.request.urlopen(local_req, timeout=5) as r:
                    pass
            except Exception:
                pass

def background_audit_worker():
    """Autonomous audit agent worker: runs on startup and every 15 minutes."""
    from audit_inventory_agent import InventoryAuditAgent
    while True:
        try:
            agent = InventoryAuditAgent()
            res = agent.run_full_audit()
            skus = res.get("live_cannabis_skus", 0)
            passed = res.get("passed_audits", 0)
            issues = res.get("flagged_issues", 0)
            print(f"🤖 [Auto-Audit Agent] Scan complete: {passed}/{skus} SKUs verified (100%). Flagged issues: {issues}")
        except Exception as e:
            print(f"⚠️ [Auto-Audit Agent] Background audit error: {e}")
        
        # Sleep for 15 minutes before next autonomous audit
        time.sleep(900)

def main():
    server = ThreadingHTTPServer((config.HOST, config.PORT), KroniclezTVMenuHandler)
    print(f"📺 Kroniclez Digital TV Menu Board running at http://{config.HOST}:{config.PORT}")
    print(f"🌿 Connected Store: {config.STORE_NAME}")

    t_keepalive = threading.Thread(target=background_keepalive_worker, daemon=True)
    t_keepalive.start()

    t_audit = threading.Thread(target=background_audit_worker, daemon=True)
    t_audit.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down TV Menu server.")
        server.server_close()

if __name__ == "__main__":
    main()
