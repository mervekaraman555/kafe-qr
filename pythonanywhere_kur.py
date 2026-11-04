#!/usr/bin/env python3
"""
PythonAnywhere üzerinde Kafe QR Sipariş projesini en son GitHub sürümüne günceller
ve WSGI ayar dosyasını otomatik olarak bağlayıp yeniler (Reload).
"""
import glob
import os
import urllib.request

RAW_BASE = "https://raw.githubusercontent.com/mervekaraman555/kafe-qr/main"
FILES = [
    "app.py",
    "giris_ekrani.html",
    "musteri_ekrani.html",
    "calisan_ekrani.html",
    "yetkili_ekrani.html",
    "adisyon.html",
    "qr_kodlar.html",
    "kurulum_ekrani.html",
    "reklam_videosu.html",
    "manifest.json",
    "sw.js",
    "icon-192.png",
    "icon-512.png",
    "uploads/urun_artisan_burger.jpg",
    "uploads/urun_matcha_latte.jpg",
    "uploads/urun_limonlu_cheesecake.jpg",
    "uploads/urun_oreolu_pasta.jpg",
    "luma_video_olusturucu.py",
    "kafe.db",
]

home_dir = os.path.expanduser("~")
project_dir = os.path.join(home_dir, "kafe_1")
target_dirs = {home_dir, project_dir, os.path.join(home_dir, "kafe-qr")}

for tdir in sorted(target_dirs):
    os.makedirs(tdir, exist_ok=True)
    print(f"⏳ Güncel dosyalar indiriliyor: {tdir}")
    for fname in FILES:
        try:
            target_file = os.path.join(tdir, fname)
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            urllib.request.urlretrieve(f"{RAW_BASE}/{fname}", target_file)
            print(f"  ✅ Güncellendi: {fname}")
        except Exception as e:
            print(f"  ⚠️ {fname} indirilemedi: {e}")

wsgi_content = f"""import os
import sys

path = {project_dir!r}
if path not in sys.path:
    sys.path.insert(0, path)

os.chdir(path)
from app import application
"""

wsgi_files = glob.glob("/var/www/*_wsgi.py")
if wsgi_files:
    for wf in wsgi_files:
        try:
            with open(wf, "w", encoding="utf-8") as f:
                f.write(wsgi_content)
            os.utime(wf, None)
            print(f"✅ WSGI ayar dosyası güncellendi ve sunucu otomatik yenilendi (Reload): {wf}")
        except Exception as e:
            print(f"⚠️ {wf} güncellenemedi: {e}")
else:
    print("ℹ️ Henüz Web sekmesinden 'Add a new web app' oluşturmadınız.")
    print("   Lütfen PythonAnywhere üst menüden 'Web' -> 'Add a new web app' -> 'Next' -> 'Flask' -> 'Python 3.10' -> 'Next' adımlarını yapıp bu komutu tekrar çalıştırın.")


