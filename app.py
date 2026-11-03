#!/usr/bin/env python3
"""
Kafe QR Sipariş ve Masa Takip Sistemi (Ayrılmış Mimari)
Sıfır dış bağımlılık (yalnızca Python standart kütüphanesi + SQLite).

- Müşteri QR Sipariş Sunucusu (Port 8090):
  http://localhost:8090/?no=1  -> Sadece müşteri menü, sipariş verme, kendi siparişlerini ve tutarını görme ekranı (musteri_ekrani.html).
  Bu portta çalışan ekranı (/personel) ve diğer masaların verileri tamamen kapalıdır.

- Çalışan / Personel Sunucusu (Port 8091):
  http://localhost:8091/personel -> Kafe çalışanları için canlı sipariş, garson zili & masa hesap ekranı (calisan_ekrani.html).
  http://localhost:8091/qr       -> Masalar için yazdırılabilir QR kod oluşturucu.
"""

import base64
import json
import os
import secrets
import socket
import sqlite3
import threading
import time
from datetime import datetime
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

CUSTOMER_PORT = int(os.environ.get("PORT", "8090"))
STAFF_PORT = int(os.environ.get("STAFF_PORT", "8091"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "kafe.db")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
MUSTERI_HTML_PATH = os.path.join(BASE_DIR, "musteri_ekrani.html")
CALISAN_HTML_PATH = os.path.join(BASE_DIR, "calisan_ekrani.html")
GIRIS_HTML_PATH = os.path.join(BASE_DIR, "giris_ekrani.html")
YETKILI_HTML_PATH = os.path.join(BASE_DIR, "yetkili_ekrani.html")
QR_HTML_PATH = os.path.join(BASE_DIR, "qr_kodlar.html")
ADISYON_HTML_PATH = os.path.join(BASE_DIR, "adisyon.html")

SESSIONS = {}  # {token: {"id": ..., "username": ..., "name": ..., "role": ...}}

DEFAULT_USERS = [
    ("Kafe Personeli", "personel", "1234", "personel"),
    ("Kafe Yetkilisi", "yetkili", "0000", "yetkili"),
]

DEFAULT_MENU = [
    # Kahveler
    ("Türk Kahvesi", "Sıcak İçecekler", 75, "☕", "Geleneksel köz tadında, lokum ile"),
    ("Americano", "Sıcak İçecekler", 95, "☕", "Çift shot espresso ve sıcak su"),
    ("Caffe Latte", "Sıcak İçecekler", 110, "🥛", "Kadifemsi süt köpüğü ve espresso"),
    ("Cappuccino", "Sıcak İçecekler", 110, "☕", "Yoğun köpüklü İtalyan klasiği"),
    ("Flat White", "Sıcak İçecekler", 120, "☕", "Çift ristretto ve ince mikro köpük"),
    ("Demleme Çay", "Sıcak İçecekler", 35, "🫖", "Taze demlenmiş Rize çayı"),
    ("Sahlep", "Sıcak İçecekler", 115, "🥣", "Tarçınlı sıcak kış klasiği"),
    # Soğuk İçecekler
    ("Iced Latte", "Soğuk İçecekler", 120, "🧊", "Buzlu süt ve taze espresso"),
    ("Iced Americano", "Soğuk İçecekler", 105, "🧊", "Ferahlatıcı soğuk espresso"),
    ("Ev Yapımı Limonata", "Soğuk İçecekler", 95, "🍋", "Taze nane yaprakları ile"),
    ("Taze Portakal Suyu", "Soğuk İçecekler", 110, "🍊", "Sipariş anında sıkılmış"),
    ("Soğuk Hibiskus Çayı", "Soğuk İçecekler", 100, "🌺", "Orman meyveli ferahlatıcı"),
    # Tatlılar
    ("San Sebastian Cheesecake", "Tatlılar", 165, "🍰", "Belçika çikolatası sosu ile"),
    ("Tiramisu", "Tatlılar", 155, "🍮", "Mascarpone peynirli ve espresso ıslatmalı"),
    ("Sıcak Brownie", "Tatlılar", 150, "🍫", "Vanilyalı dondurma topu ile"),
    ("Kruvasan", "Tatlılar", 95, "🥐", "Tereyağlı çıtır Fransız kruvasanı"),
    # Atıştırmalık & Kahvaltı
    ("Avokadolu Poşe Yumurta Tost", "Yiyecekler", 185, "🥑", "Ekşi mayalı ekmek üzerinde"),
    ("Kaşarlı & Sucuklu Bazlama Tost", "Yiyecekler", 145, "🥪", "Yanında kiraz domates ve yeşillik ile"),
    ("Mozzarella & Pesto Sandviç", "Yiyecekler", 160, "🥖", "Taze fesleğen soslu ciabatta"),
]


def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def merge_items_list(items_list: list) -> list:
    merged = {}
    for item in items_list:
        key = (str(item.get("name", "")), float(item.get("price", 0)))
        if key not in merged:
            merged[key] = {
                "id": item.get("id", 0),
                "name": item["name"],
                "price": float(item["price"]),
                "qty": int(item["qty"]),
            }
        else:
            merged[key]["qty"] += int(item["qty"])
    return list(merged.values())


def consolidate_table_orders(conn, table_no: int = None):
    cur = conn.cursor()
    if table_no is not None:
        tables = [table_no]
    else:
        rows = cur.execute(
            "SELECT DISTINCT table_no FROM orders WHERE status != 'odendi'"
        ).fetchall()
        tables = [r["table_no"] for r in rows]

    for t_no in tables:
        open_rows = cur.execute(
            "SELECT * FROM orders WHERE table_no = ? AND status != 'odendi' ORDER BY id ASC",
            (t_no,),
        ).fetchall()
        if len(open_rows) <= 1:
            continue
        keep_id = open_rows[0]["id"]
        all_items = []
        notes = []
        statuses = []
        for r in open_rows:
            all_items.extend(json.loads(r["items_json"]))
            if r["note"] and r["note"].strip() and r["note"].strip() not in notes:
                notes.append(r["note"].strip())
            statuses.append(r["status"])
        merged_items = merge_items_list(all_items)
        total = sum(float(i["price"]) * int(i["qty"]) for i in merged_items)
        combined_note = " | ".join(notes)
        if "bekliyor" in statuses:
            final_status = "bekliyor"
        elif "hazirlaniyor" in statuses:
            final_status = "hazirlaniyor"
        else:
            final_status = "tamamlandi"
        now = datetime.now().strftime("%H:%M:%S")
        cur.execute(
            """
            UPDATE orders
            SET items_json = ?, note = ?, total = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(merged_items, ensure_ascii=False), combined_note, total, final_status, now, keep_id),
        )
        other_ids = [r["id"] for r in open_rows[1:]]
        cur.execute(
            f"DELETE FROM orders WHERE id IN ({','.join('?' for _ in other_ids)})",
            other_ids,
        )
    conn.commit()


def save_uploaded_image(image_data: str) -> str:
    if not image_data:
        return ""
    image_data = image_data.strip()
    if image_data.startswith("data:image/"):
        try:
            header, b64_data = image_data.split(",", 1)
            ext = "jpg"
            if "image/png" in header:
                ext = "png"
            elif "image/webp" in header:
                ext = "webp"
            elif "image/gif" in header:
                ext = "gif"
            os.makedirs(UPLOADS_DIR, exist_ok=True)
            filename = f"urun_{int(time.time() * 1000)}_{secrets.token_hex(4)}.{ext}"
            filepath = os.path.join(UPLOADS_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(b64_data))
            return f"/uploads/{filename}"
        except Exception:
            return ""
    return image_data


def init_db():
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    conn = db_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            emoji TEXT NOT NULL,
            description TEXT DEFAULT '',
            image_url TEXT DEFAULT ''
        )
        """
    )
    try:
        cur.execute("ALTER TABLE menu ADD COLUMN image_url TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_no INTEGER NOT NULL,
            items_json TEXT NOT NULL,
            note TEXT DEFAULT '',
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'bekliyor',
            order_date TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    try:
        cur.execute("ALTER TABLE orders ADD COLUMN order_date TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    today_str = datetime.now().strftime("%Y-%m-%d")
    cur.execute("UPDATE orders SET order_date = ? WHERE order_date = '' OR order_date IS NULL", (today_str,))
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS waiter_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_no INTEGER NOT NULL,
            reason TEXT NOT NULL DEFAULT 'Garson Çağrısı',
            status TEXT NOT NULL DEFAULT 'bekliyor',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'personel'
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('table_count', '12')")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('fixed_table_count', '12')")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('qr_base_url', '')")
    count = cur.execute("SELECT COUNT(*) FROM menu").fetchone()[0]
    if count == 0:
        cur.executemany(
            "INSERT INTO menu (name, category, price, emoji, description) VALUES (?, ?, ?, ?, ?)",
            DEFAULT_MENU,
        )
    user_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        cur.executemany(
            "INSERT INTO users (name, username, password, role) VALUES (?, ?, ?, ?)",
            DEFAULT_USERS,
        )
    conn.commit()
    consolidate_table_orders(conn)
    conn.close()


def serialize_order(row) -> dict:
    order_date = ""
    if "order_date" in row.keys() and row["order_date"]:
        order_date = row["order_date"]
    else:
        order_date = datetime.now().strftime("%Y-%m-%d")
    return {
        "id": row["id"],
        "table_no": row["table_no"],
        "items": json.loads(row["items_json"]),
        "note": row["note"] or "",
        "total": row["total"],
        "status": row["status"],  # bekliyor | hazirlaniyor | tamamlandi | odendi
        "order_date": order_date,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def serialize_call(row) -> dict:
    return {
        "id": row["id"],
        "table_no": row["table_no"],
        "reason": row["reason"],
        "status": row["status"],  # bekliyor | ilgilenildi
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


HTML_QR = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kafe Masa QR Kodları — Yazdırılabilir</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; padding: 24px; }
  .toolbar {
    max-width: 1080px; margin: 0 auto 24px; background: #fff; padding: 18px 22px;
    border-radius: 14px; border: 1px solid #e2e8f0; display: flex; flex-wrap: wrap;
    justify-content: space-between; align-items: center; gap: 14px;
  }
  .toolbar h1 { font-size: 1.2rem; margin: 0 0 4px; }
  .toolbar p { font-size: 0.85rem; color: #475569; margin: 0; }
  .controls { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 0.9rem; }
  button {
    background: #b45309; color: #fff; border: none; padding: 9px 16px;
    border-radius: 8px; font-weight: 700; cursor: pointer;
  }
  button.print-btn { background: #0f172a; }
  .qr-grid {
    max-width: 1080px; margin: 0 auto;
    display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 18px;
  }
  .qr-card {
    background: #fff; border: 2px solid #1e293b; border-radius: 18px; padding: 18px;
    text-align: center; box-shadow: 0 4px 14px rgba(0,0,0,0.04); page-break-inside: avoid;
  }
  .qr-card h2 { font-size: 1.35rem; margin: 0 0 4px; color: #b45309; }
  .qr-card .sub { font-size: 0.78rem; color: #64748b; margin-bottom: 10px; }
  .qr-box {
    width: 170px; height: 170px; margin: 0 auto 10px;
    display: flex; align-items: center; justify-content: center;
  }
  .qr-box img { width: 170px; height: 170px; border-radius: 8px; }
  .qr-url { font-size: 0.72rem; color: #475569; word-break: break-all; margin-bottom: 8px; }
  .test-link {
    display: inline-block; font-size: 0.8rem; font-weight: 700; color: #15803d;
    text-decoration: none; border: 1px solid #86efac; background: #dcfce7;
    padding: 5px 10px; border-radius: 999px;
  }
  @media print {
    .toolbar, .test-link { display: none !important; }
    body { background: #fff; padding: 0; }
  }
</style>
</head>
<body>

<div class="toolbar">
  <div>
    <h1>🔳 Masa Sipariş Kare Kodları (QR)</h1>
    <p>Her masanın kendi QR kodu vardır. Müşteri okuttuğunda yalnızca o masanın sipariş ekranı açılır.</p>
  </div>
  <div class="controls">
    <label style="font-size:0.85rem;">Masa Sayısı:
      <input type="number" id="tableCount" value="12" min="1" max="100" style="width:70px;">
    </label>
    <label style="font-size:0.85rem;">Müşteri QR Adresi:
      <input type="text" id="baseUrl" style="width:230px;">
    </label>
    <button onclick="renderQRs()">Güncelle</button>
    <button class="print-btn" onclick="window.print()">🖨️ Yazdır / PDF Kaydet</button>
  </div>
</div>

<div class="qr-grid" id="qrGrid"></div>

<script>
  const defaultHost = "__LAN_ORIGIN__";
  document.getElementById("baseUrl").value = defaultHost;

  function renderQRs() {
    const count = parseInt(document.getElementById("tableCount").value || "12", 10);
    const base = document.getElementById("baseUrl").value.replace(/\\/$/, "");
    const grid = document.getElementById("qrGrid");
    const cards = [];
    for (let i = 1; i <= count; i++) {
      const targetUrl = `${base}/?no=${i}`;
      const qrApi = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=8&data=${encodeURIComponent(targetUrl)}`;
      cards.push(`
        <div class="qr-card">
          <h2>☕ MASA ${i}</h2>
          <div class="sub">Menüyü görmek ve sipariş vermek için kameranızla okutun</div>
          <div class="qr-box">
            <img src="${qrApi}" alt="Masa ${i} QR">
          </div>
          <div class="qr-url">${targetUrl}</div>
          <a class="test-link" href="${targetUrl}" target="_blank">Masa ${i} Müşteri Ekranı →</a>
        </div>
      `);
    }
    grid.innerHTML = cards.join("");
  }

  renderQRs();
</script>
</body>
</html>
"""


class BaseKafeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data: dict, status: int = 200, cookie_header: str = None):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        if cookie_header:
            self.send_header("Set-Cookie", cookie_header)
        self.end_headers()
        self.wfile.write(raw)

    def _send_html(self, html: str, status: int = 200):
        raw = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _get_session_user(self):
        raw_cookie = self.headers.get("Cookie", "")
        if not raw_cookie:
            return None
        cookie = SimpleCookie()
        cookie.load(raw_cookie)
        if "kafe_session" in cookie:
            token = cookie["kafe_session"].value
            return SESSIONS.get(token)
        return None

    def _read_json_body(self) -> dict:
        if hasattr(self, "_cached_json_body"):
            return self._cached_json_body
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            self._cached_json_body = json.loads(body or "{}")
        except json.JSONDecodeError:
            self._cached_json_body = {}
        return self._cached_json_body

    def _serve_upload(self, path: str) -> bool:
        if not path.startswith("/uploads/"):
            return False
        fname = os.path.basename(path)
        fpath = os.path.join(UPLOADS_DIR, fname)
        if not os.path.isfile(fpath):
            return False
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else "jpg"
        mime_map = {
            "png": "image/png",
            "webp": "image/webp",
            "gif": "image/gif",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }
        ctype = mime_map.get(ext, "image/jpeg")
        with open(fpath, "rb") as f:
            raw = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(raw)
        return True

    def _serve_pwa_and_installers(self, path: str) -> bool:
        if path in ("/manifest.json", "/sw.js", "/icon-192.png", "/icon-512.png"):
            fpath = os.path.join(BASE_DIR, path.lstrip("/"))
            if not os.path.isfile(fpath):
                return False
            ctype = "application/json; charset=utf-8"
            if path.endswith(".js"):
                ctype = "application/javascript; charset=utf-8"
            elif path.endswith(".png"):
                ctype = "image/png"
            with open(fpath, "rb") as f:
                raw = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return True

        if path == "/kurulum":
            kurulum_path = os.path.join(BASE_DIR, "kurulum_ekrani.html")
            if os.path.isfile(kurulum_path):
                lan_staff = f"http://{get_lan_ip()}:{STAFF_PORT}"
                with open(kurulum_path, "r", encoding="utf-8") as f:
                    html = f.read().replace("__LAN_STAFF_ORIGIN__", lan_staff)
                self._send_html(html)
                return True

        if path == "/kurulum/windows.bat":
            fpath = os.path.join(BASE_DIR, "Kurulum_Paketleri", "1_Windows_Kurulum", "Windows_Kurulum_Yukleyici.bat")
            if os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    raw = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", 'attachment; filename="Windows_Kurulum_Yukleyici.bat"')
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return True

        if path == "/kurulum/mac.command":
            fpath = os.path.join(BASE_DIR, "Kurulum_Paketleri", "2_Mac_Kurulum", "Mac_Kurulum_Yukleyici.command")
            if os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    raw = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", 'attachment; filename="Mac_Kurulum_Yukleyici.command"')
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return True

        if path == "/kurulum/android":
            fpath = os.path.join(BASE_DIR, "Kurulum_Paketleri", "3_Android_Kurulum", "Android_Kurulum_Yukleyici.html")
            if os.path.isfile(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    self._send_html(f.read())
                return True

        if path == "/kurulum/harmonyos":
            fpath = os.path.join(BASE_DIR, "Kurulum_Paketleri", "4_HarmonyOS_Kurulum", "HarmonyOS_Kurulum_Yukleyici.html")
            if os.path.isfile(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    self._send_html(f.read())
                return True

        if path == "/kurulum/ios":
            fpath = os.path.join(BASE_DIR, "Kurulum_Paketleri", "5_iOS_Kurulum", "iOS_Kurulum_Yukleyici.html")
            if os.path.isfile(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    self._send_html(f.read())
                return True

        if path == "/kurulum/ios.mobileconfig":
            icon_path = os.path.join(BASE_DIR, "icon-192.png")
            icon_b64 = ""
            if os.path.isfile(icon_path):
                with open(icon_path, "rb") as f:
                    icon_b64 = base64.b64encode(f.read()).decode("ascii")
            req_host = self.headers.get("Host", "").strip()
            req_proto = self.headers.get("X-Forwarded-Proto", "http").strip() or "http"
            if req_host and not req_host.startswith("localhost") and not req_host.startswith("127.0.0.1") and not req_host.startswith("192.168.") and not req_host.startswith("10."):
                scheme = "https" if ("pythonanywhere" in req_host or "onrender" in req_host or req_proto == "https") else req_proto
                target_url = f"{scheme}://{req_host}/giris"
            else:
                target_url = f"http://{get_lan_ip()}:{STAFF_PORT}/giris"
            mc = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>FullScreen</key>
            <true/>
            <key>Icon</key>
            <data>{icon_b64}</data>
            <key>IgnoreManifestScope</key>
            <true/>
            <key>IsRemovable</key>
            <true/>
            <key>Label</key>
            <string>Kafe Yönetim</string>
            <key>PayloadDescription</key>
            <string>Kafe QR Sipariş ve Yönetim Uygulaması</string>
            <key>PayloadDisplayName</key>
            <string>Kafe Yönetim WebClip</string>
            <key>PayloadIdentifier</key>
            <string>com.artisankafe.qrsiparis.webclip</string>
            <key>PayloadType</key>
            <string>com.apple.webClip.managed</string>
            <key>PayloadUUID</key>
            <string>A1B2C3D4-E5F6-4789-9012-3456789ABCDE</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>Precomposed</key>
            <true/>
            <key>URL</key>
            <string>{target_url}</string>
        </dict>
    </array>
    <key>PayloadDescription</key>
    <string>Artisan Kafe iOS ve iPadOS Tam Ekran Uygulama Kurulum Profili</string>
    <key>PayloadDisplayName</key>
    <string>Kafe Yönetim — iOS Uygulaması</string>
    <key>PayloadIdentifier</key>
            <string>com.artisankafe.qrsiparis.profile</string>
    <key>PayloadOrganization</key>
    <string>Artisan Kafe</string>
    <key>PayloadRemovalDisallowed</key>
    <false/>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>F1E2D3C4-B5A6-4987-8012-3456789EDCBA</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>"""
            raw = mc.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/x-apple-aspen-config")
            self.send_header("Content-Disposition", 'attachment; filename="Kafe_Yonetim_iOS.mobileconfig"')
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return True

        if path == "/guncelle":
            import subprocess, glob, urllib.request
            logs = []
            raw_base = "https://raw.githubusercontent.com/mervekaraman555/kafe-qr/main"
            update_files = [
                "app.py", "giris_ekrani.html", "musteri_ekrani.html", "calisan_ekrani.html",
                "yetkili_ekrani.html", "adisyon.html", "qr_kodlar.html", "kurulum_ekrani.html",
                "reklam_videosu.html", "manifest.json", "sw.js"
            ]
            downloaded = 0
            for fn in update_files:
                try:
                    urllib.request.urlretrieve(f"{raw_base}/{fn}", os.path.join(BASE_DIR, fn))
                    downloaded += 1
                except Exception:
                    pass
            if downloaded > 0:
                logs.append(f"{downloaded} dosya GitHub üzerinden güncellendi.")
            else:
                try:
                    out = subprocess.check_output(
                        ["git", "-C", BASE_DIR, "pull", "--rebase", "origin", "main"],
                        stderr=subprocess.STDOUT,
                        timeout=20,
                    ).decode("utf-8", errors="ignore")
                    logs.append(out.strip())
                except Exception as e:
                    logs.append(f"Git bilgi: {e}")
            for wsgi_file in glob.glob("/var/www/*_wsgi.py"):
                try:
                    os.utime(wsgi_file, None)
                    logs.append(f"WSGI yenilendi: {wsgi_file}")
                except Exception as e:
                    logs.append(f"WSGI hata: {e}")
            msg_html = "<br>".join(logs) or "Güncelleme tamamlandı."
            self._send_html(
                f"<!DOCTYPE html><html lang='tr'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>Sistem Güncellendi</title></head><body style='background:#0f0d0b;color:#f5f0eb;font-family:sans-serif;padding:30px;text-align:center;'>"
                f"<h2 style='color:#10b981;'>✅ Bulut Sunucu Güncellendi!</h2>"
                f"<p style='color:#c2b29f;font-size:14px;'>{msg_html}</p>"
                f"<a href='/giris' style='display:inline-block;margin-top:16px;padding:12px 24px;background:#d97706;color:#fff;text-decoration:none;border-radius:10px;font-weight:bold;'>Giriş Ekranına Dön</a>"
                f"</body></html>"
            )
            return True

        return False


class MusteriHandler(BaseKafeHandler):
    """
    Müşteri QR Sipariş Ekranına ve bulut ortamında tek port üzerinden tüm uç noktalara hizmet verir.
    """

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/masa" or (path == "/" and "no" in qs):
            with open(MUSTERI_HTML_PATH, "r", encoding="utf-8") as f:
                return self._send_html(f.read())

        if path in ("/", "/giris", "/login", "/giris_ekrani.html"):
            with open(GIRIS_HTML_PATH, "r", encoding="utf-8") as f:
                return self._send_html(f.read())

        if path == "/personel":
            with open(CALISAN_HTML_PATH, "r", encoding="utf-8") as f:
                return self._send_html(f.read())

        if path == "/yetkili":
            with open(YETKILI_HTML_PATH, "r", encoding="utf-8") as f:
                return self._send_html(f.read())

        if path == "/reklam":
            reklam_path = os.path.join(BASE_DIR, "reklam_videosu.html")
            if os.path.exists(reklam_path):
                with open(reklam_path, "r", encoding="utf-8") as f:
                    return self._send_html(f.read())

        if path in ("/Kafe_QR_Siparis_Tanitim_Videosu.mp4", "/tanitim.mp4"):
            mp4_path = os.path.join(BASE_DIR, "Kafe_QR_Siparis_Tanitim_Videosu.mp4")
            if os.path.isfile(mp4_path):
                with open(mp4_path, "rb") as f:
                    raw = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Disposition", 'attachment; filename="Kafe_QR_Siparis_Tanitim_Videosu.mp4"')
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return

        if path.startswith("/audio/"):
            fname = os.path.basename(path)
            audio_path = os.path.join(BASE_DIR, "audio", fname)
            if os.path.exists(audio_path) and fname.endswith(".mp3"):
                with open(audio_path, "rb") as f:
                    raw = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                self.wfile.write(raw)
                return

        if self._serve_upload(path) or self._serve_pwa_and_installers(path):
            return

        if path == "/adisyon":
            with open(ADISYON_HTML_PATH, "r", encoding="utf-8") as f:
                return self._send_html(f.read())

        if path == "/qr":
            lan_origin = f"http://{get_lan_ip()}:{CUSTOMER_PORT}"
            with open(QR_HTML_PATH, "r", encoding="utf-8") as f:
                return self._send_html(f.read().replace("__LAN_ORIGIN__", lan_origin))

        if path == "/api/me":
            user = self._get_session_user()
            return self._send_json({"user": user})

        if path == "/api/users":
            conn = db_conn()
            rows = conn.execute("SELECT id, name, username, role FROM users ORDER BY id ASC").fetchall()
            conn.close()
            return self._send_json({"users": [dict(r) for r in rows]})

        if path == "/api/menu":
            conn = db_conn()
            rows = conn.execute("SELECT * FROM menu ORDER BY id ASC").fetchall()
            conn.close()
            return self._send_json({"items": [dict(r) for r in rows]})

        if path == "/api/orders":
            conn = db_conn()
            table_no = qs.get("table_no", [None])[0]
            if table_no is not None:
                rows = conn.execute(
                    "SELECT * FROM orders WHERE table_no = ? ORDER BY id DESC",
                    (int(table_no),),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
            conn.close()
            return self._send_json({"orders": [serialize_order(r) for r in rows]})

        if path == "/api/calls":
            conn = db_conn()
            table_no = qs.get("table_no", [None])[0]
            if table_no is not None:
                rows = conn.execute(
                    "SELECT * FROM waiter_calls WHERE table_no = ? AND status = 'bekliyor' ORDER BY id DESC",
                    (int(table_no),),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM waiter_calls WHERE status = 'bekliyor' ORDER BY id DESC"
                ).fetchall()
            conn.close()
            return self._send_json({"calls": [serialize_call(r) for r in rows]})

        if path == "/api/settings":
            return PersonelHandler.do_GET(self)

        return self._send_json({"error": "Sayfa bulunamadı"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        payload = self._read_json_body()

        if path == "/api/login":
            return PersonelHandler.do_POST(self)
        if path in ("/api/logout", "/api/menu", "/api/users", "/api/settings") or path.startswith("/api/menu/") or path.startswith("/api/users/") or (path.startswith("/api/orders/") and path.endswith("/status")):
            return PersonelHandler.do_POST(self)

        if path == "/api/orders":
            table_no = int(payload.get("table_no", 1))
            items = payload.get("items", [])
            note = str(payload.get("note", "")).strip()
            if not items:
                return self._send_json({"error": "Sepet boş"}, status=400)

            now = datetime.now().strftime("%H:%M:%S")
            today_str = datetime.now().strftime("%Y-%m-%d")
            conn = db_conn()
            cur = conn.cursor()
            existing = cur.execute(
                "SELECT * FROM orders WHERE table_no = ? AND status != 'odendi' ORDER BY id ASC LIMIT 1",
                (table_no,),
            ).fetchone()

            if existing:
                order_id = existing["id"]
                combined_items = merge_items_list(json.loads(existing["items_json"]) + items)
                total = sum(float(i["price"]) * int(i["qty"]) for i in combined_items)
                existing_note = (existing["note"] or "").strip()
                if note and note not in existing_note:
                    combined_note = f"{existing_note} | {note}" if existing_note else note
                else:
                    combined_note = existing_note
                cur.execute(
                    """
                    UPDATE orders
                    SET items_json = ?, note = ?, total = ?, status = 'bekliyor', order_date = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (json.dumps(combined_items, ensure_ascii=False), combined_note, total, today_str, now, order_id),
                )
            else:
                merged_new = merge_items_list(items)
                total = sum(float(i["price"]) * int(i["qty"]) for i in merged_new)
                cur.execute(
                    """
                    INSERT INTO orders (table_no, items_json, note, total, status, order_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'bekliyor', ?, ?, ?)
                    """,
                    (table_no, json.dumps(merged_new, ensure_ascii=False), note, total, today_str, now, now),
                )
                order_id = cur.lastrowid

            conn.commit()
            row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            conn.close()
            return self._send_json({"order": serialize_order(row)}, status=201)

        if path == "/api/calls":
            table_no = int(payload.get("table_no", 1))
            reason = str(payload.get("reason", "🔔 Garson Çağrısı")).strip() or "🔔 Garson Çağrısı"
            now = datetime.now().strftime("%H:%M:%S")
            conn = db_conn()
            cur = conn.cursor()
            existing = cur.execute(
                "SELECT id FROM waiter_calls WHERE table_no = ? AND reason = ? AND status = 'bekliyor'",
                (table_no, reason),
            ).fetchone()
            if existing:
                call_id = existing["id"]
                cur.execute(
                    "UPDATE waiter_calls SET updated_at = ?, created_at = ? WHERE id = ?",
                    (now, now, call_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO waiter_calls (table_no, reason, status, created_at, updated_at)
                    VALUES (?, ?, 'bekliyor', ?, ?)
                    """,
                    (table_no, reason, now, now),
                )
                call_id = cur.lastrowid
            conn.commit()
            row = conn.execute("SELECT * FROM waiter_calls WHERE id = ?", (call_id,)).fetchone()
            conn.close()
            return self._send_json({"call": serialize_call(row)}, status=201)

        if path.startswith("/api/tables/") and path.endswith("/pay"):
            parts = path.strip("/").split("/")
            table_no = int(parts[2])
            now = datetime.now().strftime("%H:%M:%S")
            conn = db_conn()
            conn.execute(
                "UPDATE orders SET status = 'odendi', updated_at = ? WHERE table_no = ? AND status != 'odendi'",
                (now, table_no),
            )
            conn.execute(
                "UPDATE waiter_calls SET status = 'ilgilenildi', updated_at = ? WHERE table_no = ? AND status = 'bekliyor'",
                (now, table_no),
            )
            conn.commit()
            conn.close()
            return self._send_json({"ok": True})

        if path == "/api/orders/reset":
            target_date = str(payload.get("order_date", "")).strip()
            only_paid = bool(payload.get("only_paid", True))
            conn = db_conn()
            if target_date:
                if only_paid:
                    conn.execute(
                        "DELETE FROM orders WHERE status = 'odendi' AND (order_date = ? OR order_date = '' OR order_date IS NULL)",
                        (target_date,),
                    )
                else:
                    conn.execute(
                        "DELETE FROM orders WHERE order_date = ? OR order_date = '' OR order_date IS NULL",
                        (target_date,),
                    )
            else:
                if only_paid:
                    conn.execute("DELETE FROM orders WHERE status = 'odendi'")
                else:
                    conn.execute("DELETE FROM orders")
            conn.commit()
            conn.close()
            return self._send_json({"ok": True})

        if path.startswith("/api/calls/") and path.endswith("/resolve"):
            parts = path.strip("/").split("/")
            call_id = int(parts[2])
            now = datetime.now().strftime("%H:%M:%S")
            conn = db_conn()
            conn.execute(
                "UPDATE waiter_calls SET status = 'ilgilenildi', updated_at = ? WHERE id = ?",
                (now, call_id),
            )
            conn.commit()
            conn.close()
            return self._send_json({"ok": True})

        if path == "/api/settings":
            conn = db_conn()
            if "table_count" in payload:
                tc = max(1, min(200, int(payload["table_count"])))
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('table_count', ?)", (str(tc),))
            if "fixed_table_count" in payload:
                fc = max(1, min(200, int(payload["fixed_table_count"])))
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('fixed_table_count', ?)", (str(fc),))
            if "qr_base_url" in payload:
                bu = str(payload["qr_base_url"]).strip()
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('qr_base_url', ?)", (bu,))
            conn.commit()
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            conn.close()
            cfg = {r["key"]: r["value"] for r in rows}
            return self._send_json({
                "ok": True,
                "table_count": int(cfg.get("table_count", "12") or 12),
                "fixed_table_count": int(cfg.get("fixed_table_count", "12") or 12),
                "qr_base_url": cfg.get("qr_base_url", ""),
            })

        return self._send_json({"error": "Bulunamadı"}, status=404)


class PersonelHandler(BaseKafeHandler):
    """
    Sadece Yetkili ve Çalışan Personel Paneline hizmet verir (Port 8091).
    Müşteri QR portundan tamamen bağımsızdır.
    """

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path in ("/", "/giris", "/login", "/giris_ekrani.html"):
            with open(GIRIS_HTML_PATH, "r", encoding="utf-8") as f:
                return self._send_html(f.read())

        if self._serve_upload(path) or self._serve_pwa_and_installers(path):
            return

        if path == "/personel":
            with open(CALISAN_HTML_PATH, "r", encoding="utf-8") as f:
                return self._send_html(f.read())

        if path == "/yetkili":
            with open(YETKILI_HTML_PATH, "r", encoding="utf-8") as f:
                return self._send_html(f.read())

        if path == "/adisyon":
            with open(ADISYON_HTML_PATH, "r", encoding="utf-8") as f:
                return self._send_html(f.read())

        if path == "/qr":
            lan_origin = f"http://{get_lan_ip()}:{CUSTOMER_PORT}"
            with open(QR_HTML_PATH, "r", encoding="utf-8") as f:
                return self._send_html(f.read().replace("__LAN_ORIGIN__", lan_origin))

        if path == "/reklam":
            reklam_path = os.path.join(BASE_DIR, "reklam_videosu.html")
            if os.path.exists(reklam_path):
                with open(reklam_path, "r", encoding="utf-8") as f:
                    return self._send_html(f.read())

        if path in ("/Kafe_QR_Siparis_Tanitim_Videosu.mp4", "/tanitim.mp4"):
            mp4_path = os.path.join(BASE_DIR, "Kafe_QR_Siparis_Tanitim_Videosu.mp4")
            if os.path.isfile(mp4_path):
                with open(mp4_path, "rb") as f:
                    raw = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Disposition", 'attachment; filename="Kafe_QR_Siparis_Tanitim_Videosu.mp4"')
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return

        if path.startswith("/audio/"):
            fname = os.path.basename(path)
            audio_path = os.path.join(BASE_DIR, "audio", fname)
            if os.path.exists(audio_path) and fname.endswith(".mp3"):
                with open(audio_path, "rb") as f:
                    raw = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                self.wfile.write(raw)
                return

        if path == "/api/me":
            user = self._get_session_user()
            return self._send_json({"user": user})

        if path == "/api/users":
            conn = db_conn()
            rows = conn.execute("SELECT id, name, username, role FROM users ORDER BY id ASC").fetchall()
            conn.close()
            return self._send_json({"users": [dict(r) for r in rows]})

        if path == "/api/menu":
            conn = db_conn()
            rows = conn.execute("SELECT * FROM menu ORDER BY id ASC").fetchall()
            conn.close()
            return self._send_json({"items": [dict(r) for r in rows]})

        if path == "/api/orders":
            conn = db_conn()
            table_no = qs.get("table_no", [None])[0]
            if table_no is not None:
                rows = conn.execute(
                    "SELECT * FROM orders WHERE table_no = ? ORDER BY id DESC",
                    (int(table_no),),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
            conn.close()
            return self._send_json({"orders": [serialize_order(r) for r in rows]})

        if path == "/api/calls":
            conn = db_conn()
            rows = conn.execute(
                "SELECT * FROM waiter_calls WHERE status = 'bekliyor' ORDER BY id DESC"
            ).fetchall()
            conn.close()
            return self._send_json({"calls": [serialize_call(r) for r in rows]})

        if path == "/api/settings":
            conn = db_conn()
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            conn.close()
            cfg = {r["key"]: r["value"] for r in rows}
            table_count = int(cfg.get("table_count", "12") or 12)
            fixed_count = int(cfg.get("fixed_table_count", str(table_count)) or table_count)
            return self._send_json({
                "table_count": table_count,
                "fixed_table_count": fixed_count,
                "qr_base_url": cfg.get("qr_base_url", ""),
            })

        return self._send_json({"error": "Bulunamadı"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        payload = self._read_json_body()

        if path == "/api/login":
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", "")).strip()
            role = str(payload.get("role", "personel")).strip()

            conn = db_conn()
            row = conn.execute(
                "SELECT id, name, username, role FROM users WHERE username = ? AND password = ?",
                (username, password),
            ).fetchone()
            conn.close()

            if not row:
                return self._send_json({"ok": False, "error": "Kullanıcı adı veya şifre hatalı!"}, status=401)

            user_dict = dict(row)
            if role == "yetkili" and user_dict["role"] != "yetkili":
                return self._send_json({"ok": False, "error": "Bu hesabın Yetkili / Yönetici giriş yetkisi yok!"}, status=403)

            token = secrets.token_hex(16)
            SESSIONS[token] = user_dict
            redirect_url = "/yetkili" if role == "yetkili" and user_dict["role"] == "yetkili" else "/personel"
            cookie_hdr = f"kafe_session={token}; Path=/; HttpOnly; SameSite=Lax"
            return self._send_json({"ok": True, "user": user_dict, "redirect": redirect_url}, cookie_header=cookie_hdr)

        if path == "/api/logout":
            raw_cookie = self.headers.get("Cookie", "")
            if raw_cookie:
                cookie = SimpleCookie()
                cookie.load(raw_cookie)
                if "kafe_session" in cookie:
                    SESSIONS.pop(cookie["kafe_session"].value, None)
            cookie_hdr = "kafe_session=; Path=/; Max-Age=0"
            return self._send_json({"ok": True}, cookie_header=cookie_hdr)

        if path == "/api/menu":
            name = str(payload.get("name", "")).strip()
            category = str(payload.get("category", "Sıcak İçecekler")).strip()
            price = float(payload.get("price", 0))
            emoji = str(payload.get("emoji", "☕")).strip() or "☕"
            description = str(payload.get("description", "")).strip()
            raw_image = str(payload.get("image_url", "") or payload.get("image_data", "")).strip()
            image_url = save_uploaded_image(raw_image)
            if not name or price <= 0:
                return self._send_json({"error": "Geçersiz ürün bilgisi"}, status=400)
            conn = db_conn()
            conn.execute(
                "INSERT INTO menu (name, category, price, emoji, description, image_url) VALUES (?, ?, ?, ?, ?, ?)",
                (name, category, price, emoji, description, image_url),
            )
            conn.commit()
            conn.close()
            return self._send_json({"ok": True, "image_url": image_url}, status=201)

        if path.startswith("/api/menu/") and path.endswith("/image"):
            parts = path.strip("/").split("/")
            item_id = int(parts[2])
            raw_image = str(payload.get("image_url", "") or payload.get("image_data", "")).strip()
            image_url = save_uploaded_image(raw_image)
            conn = db_conn()
            conn.execute("UPDATE menu SET image_url = ? WHERE id = ?", (image_url, item_id))
            conn.commit()
            conn.close()
            return self._send_json({"ok": True, "image_url": image_url})

        if path.startswith("/api/menu/") and path.endswith("/delete"):
            parts = path.strip("/").split("/")
            item_id = int(parts[2])
            conn = db_conn()
            conn.execute("DELETE FROM menu WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            return self._send_json({"ok": True})

        if path == "/api/users":
            name = str(payload.get("name", "")).strip()
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", "")).strip()
            role = str(payload.get("role", "personel")).strip()
            if not name or not username or not password:
                return self._send_json({"error": "Tüm alanları doldurun"}, status=400)
            conn = db_conn()
            try:
                conn.execute(
                    "INSERT INTO users (name, username, password, role) VALUES (?, ?, ?, ?)",
                    (name, username, password, role),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                return self._send_json({"error": "Bu kullanıcı adı zaten kayıtlı"}, status=400)
            conn.close()
            return self._send_json({"ok": True}, status=201)

        if path.startswith("/api/users/") and path.endswith("/delete"):
            parts = path.strip("/").split("/")
            user_id = int(parts[2])
            conn = db_conn()
            conn.execute("DELETE FROM users WHERE id = ? AND username != 'yetkili'", (user_id,))
            conn.commit()
            conn.close()
            return self._send_json({"ok": True})

        if path.startswith("/api/orders/") and path.endswith("/status"):
            parts = path.strip("/").split("/")
            order_id = int(parts[2])
            new_status = payload.get("status", "tamamlandi")
            now = datetime.now().strftime("%H:%M:%S")
            conn = db_conn()
            row = conn.execute("SELECT table_no FROM orders WHERE id = ?", (order_id,)).fetchone()
            if new_status == "odendi":
                if row:
                    t_no = row["table_no"]
                    conn.execute(
                        "UPDATE orders SET status = 'odendi', updated_at = ? WHERE table_no = ? AND status != 'odendi'",
                        (now, t_no),
                    )
                    conn.execute(
                        "UPDATE waiter_calls SET status = 'ilgilenildi', updated_at = ? WHERE table_no = ? AND status = 'bekliyor'",
                        (now, t_no),
                    )
            else:
                if row:
                    t_no = row["table_no"]
                    conn.execute(
                        "UPDATE orders SET status = ?, updated_at = ? WHERE table_no = ? AND status != 'odendi'",
                        (new_status, now, t_no),
                    )
                else:
                    conn.execute(
                        "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
                        (new_status, now, order_id),
                    )
            conn.commit()
            conn.close()
            return self._send_json({"ok": True})

        if path.startswith("/api/tables/") and path.endswith("/pay"):
            parts = path.strip("/").split("/")
            table_no = int(parts[2])
            now = datetime.now().strftime("%H:%M:%S")
            conn = db_conn()
            conn.execute(
                "UPDATE orders SET status = 'odendi', updated_at = ? WHERE table_no = ? AND status != 'odendi'",
                (now, table_no),
            )
            conn.execute(
                "UPDATE waiter_calls SET status = 'ilgilenildi', updated_at = ? WHERE table_no = ? AND status = 'bekliyor'",
                (now, table_no),
            )
            conn.commit()
            conn.close()
            return self._send_json({"ok": True})

        if path == "/api/orders/reset":
            target_date = str(payload.get("order_date", "")).strip()
            only_paid = bool(payload.get("only_paid", True))
            conn = db_conn()
            if target_date:
                if only_paid:
                    conn.execute(
                        "DELETE FROM orders WHERE status = 'odendi' AND (order_date = ? OR order_date = '' OR order_date IS NULL)",
                        (target_date,),
                    )
                else:
                    conn.execute(
                        "DELETE FROM orders WHERE order_date = ? OR order_date = '' OR order_date IS NULL",
                        (target_date,),
                    )
            else:
                if only_paid:
                    conn.execute("DELETE FROM orders WHERE status = 'odendi'")
                else:
                    conn.execute("DELETE FROM orders")
            conn.commit()
            conn.close()
            return self._send_json({"ok": True})

        if path.startswith("/api/calls/") and path.endswith("/resolve"):
            parts = path.strip("/").split("/")
            call_id = int(parts[2])
            now = datetime.now().strftime("%H:%M:%S")
            conn = db_conn()
            conn.execute(
                "UPDATE waiter_calls SET status = 'ilgilenildi', updated_at = ? WHERE id = ?",
                (now, call_id),
            )
            conn.commit()
            conn.close()
            return self._send_json({"ok": True})

        if path == "/api/settings":
            conn = db_conn()
            if "table_count" in payload:
                tc = max(1, min(200, int(payload["table_count"])))
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('table_count', ?)", (str(tc),))
            if "fixed_table_count" in payload:
                fc = max(1, min(200, int(payload["fixed_table_count"])))
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('fixed_table_count', ?)", (str(fc),))
            if "qr_base_url" in payload:
                bu = str(payload["qr_base_url"]).strip()
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('qr_base_url', ?)", (bu,))
            conn.commit()
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            conn.close()
            cfg = {r["key"]: r["value"] for r in rows}
            return self._send_json({
                "ok": True,
                "table_count": int(cfg.get("table_count", "12") or 12),
                "fixed_table_count": int(cfg.get("fixed_table_count", "12") or 12),
                "qr_base_url": cfg.get("qr_base_url", ""),
            })

        return self._send_json({"error": "Bulunamadı"}, status=404)


class _WSGIAdapter(MusteriHandler):
    def __init__(self, environ):
        import io
        path_info = environ.get("PATH_INFO", "/") or "/"
        query_string = environ.get("QUERY_STRING", "")
        self.path = f"{path_info}?{query_string}" if query_string else path_info
        self.headers = {
            "Host": environ.get("HTTP_HOST", ""),
            "X-Forwarded-Proto": environ.get("HTTP_X_FORWARDED_PROTO", environ.get("wsgi.url_scheme", "https")),
            "Cookie": environ.get("HTTP_COOKIE", ""),
            "Content-Length": environ.get("CONTENT_LENGTH") or "0",
            "Content-Type": environ.get("CONTENT_TYPE", ""),
        }
        self.rfile = environ.get("wsgi.input") or io.BytesIO(b"")
        self.wfile = io.BytesIO()
        self._status_code = 200
        self._resp_headers = []

    def send_response(self, code, message=None):
        self._status_code = int(code)

    def send_header(self, keyword, value):
        self._resp_headers.append((str(keyword), str(value)))

    def end_headers(self):
        pass


_WSGI_DB_INITIALIZED = False


def application(environ, start_response):
    global _WSGI_DB_INITIALIZED
    if not _WSGI_DB_INITIALIZED:
        init_db()
        _WSGI_DB_INITIALIZED = True
    adapter = _WSGIAdapter(environ)
    method = (environ.get("REQUEST_METHOD") or "GET").upper()
    if method == "POST":
        adapter.do_POST()
    else:
        adapter.do_GET()
    status_map = {
        200: "200 OK",
        201: "201 Created",
        400: "400 Bad Request",
        401: "401 Unauthorized",
        403: "403 Forbidden",
        404: "404 Not Found",
        500: "500 Internal Server Error",
    }
    status_str = status_map.get(adapter._status_code, f"{adapter._status_code} OK")
    start_response(status_str, adapter._resp_headers)
    return [adapter.wfile.getvalue()]


def main():
    init_db()
    lan_ip = get_lan_ip()
    customer_server = ThreadingHTTPServer(("0.0.0.0", CUSTOMER_PORT), MusteriHandler)
    staff_server = ThreadingHTTPServer(("0.0.0.0", STAFF_PORT), PersonelHandler)

    t_staff = threading.Thread(target=staff_server.serve_forever, daemon=True)
    t_staff.start()

    print(f"✅ Kafe QR Sipariş Sistemi (Ayrılmış Mimari) çalışıyor:")
    print(f"   📱 MÜŞTERİ QR SİPARİŞ EKRANI (Port {CUSTOMER_PORT}):")
    print(f"      • Masa 1 Müşteri Ekranı : http://localhost:{CUSTOMER_PORT}/?no=1")
    print(f"      • Telefon QR Erişimi    : http://{lan_ip}:{CUSTOMER_PORT}/?no=1")
    print(f"   🔐 YETKİLİ & ÇALIŞAN GİRİŞ EKRANI (Port {STAFF_PORT} - Müşteriye Kapalı):")
    print(f"      • Giriş Ekranı          : http://localhost:{STAFF_PORT}/giris")
    print(f"      • Çalışan Paneli        : http://localhost:{STAFF_PORT}/personel (personel / 1234)")
    print(f"      • Yetkili Paneli        : http://localhost:{STAFF_PORT}/yetkili  (yetkili / 0000)")
    print(f"      • Masa QR Kodları       : http://localhost:{STAFF_PORT}/qr")
    customer_server.serve_forever()


if __name__ == "__main__":
    main()
