#!/usr/bin/env python3
"""
PythonAnywhere üzerinde kafe_1 projesini otomatik olarak WSGI'ya bağlar.
"""
import glob
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
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
            print(f"✅ WSGI ayar dosyası otomatik güncellendi: {wf}")
        except Exception as e:
            print(f"⚠️ {wf} güncellenemedi: {e}")
else:
    print("ℹ️ Henüz Web sekmesinden 'Add a new web app' oluşturmadınız.")
    print("   Lütfen PythonAnywhere üst menüden 'Web' -> 'Add a new web app' -> 'Next' -> 'Flask' -> 'Python 3.10' -> 'Next' adımlarını yapıp bu komutu tekrar çalıştırın.")

