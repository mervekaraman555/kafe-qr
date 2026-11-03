#!/bin/bash
# ============================================================
# KAFE QR SİPARİŞ SİSTEMİ — macOS KURULUM YÜKLEYİCİSİ (.app)
# ============================================================

echo "============================================================"
echo "  ☕ KAFE QR SİPARİŞ — macOS KURULUM YÜKLEYİCİSİ"
CLOUD_URL="https://faruk8503.pythonanywhere.com/giris"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR=""
if [ -f "$SCRIPT_DIR/app.py" ]; then
  APP_DIR="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/../../app.py" ]; then
  APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

echo "============================================================"
echo "[1/3] Masaüstüne 'Kafe Giriş Ekranı.app' kuruluyor..."
MAC_APP_PATH="$HOME/Desktop/Kafe Giriş Ekranı.app"
mkdir -p "$MAC_APP_PATH/Contents/MacOS"
mkdir -p "$MAC_APP_PATH/Contents/Resources"

cat > "$MAC_APP_PATH/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>KafeGiris</string>
  <key>CFBundleIdentifier</key>
  <string>com.artisankafe.qrsiparis</string>
  <key>CFBundleName</key>
  <string>Kafe Giriş Ekranı</string>
  <key>CFBundleDisplayName</key>
  <string>Kafe Giriş Ekranı</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>2.0</string>
</dict>
</plist>
EOF

if [ -n "$APP_DIR" ]; then
cat > "$MAC_APP_PATH/Contents/MacOS/KafeGiris" <<EOF
#!/bin/bash
APP_DIR="$APP_DIR"
if ! lsof -i :8091 > /dev/null 2>&1; then
  cd "\$APP_DIR" && nohup python3 app.py > /tmp/kafe_qr_server.log 2>&1 &
  sleep 1
fi
open "http://localhost:8091/giris"
EOF
else
cat > "$MAC_APP_PATH/Contents/MacOS/KafeGiris" <<EOF
#!/bin/bash
open "$CLOUD_URL"
EOF
fi

chmod +x "$MAC_APP_PATH/Contents/MacOS/KafeGiris"

if [ -n "$APP_DIR" ]; then
  echo "[2/3] Yerel sunucu kontrol ediliyor ve başlatılıyor..."
  if ! lsof -i :8091 > /dev/null 2>&1; then
    cd "$APP_DIR" && nohup python3 app.py > /tmp/kafe_qr_server.log 2>&1 &
    sleep 1
  fi
  echo "[3/3] Giriş Ekranı açılıyor..."
  open "http://localhost:8091/giris"
else
  echo "[2/3] Bulut Giriş Ekranı açılıyor..."
  open "$CLOUD_URL"
fi

echo ""
echo "✅ macOS Kurulumu Tamamlandı!"
echo "   Masaüstünüzde 'Kafe Giriş Ekranı.app' uygulaması oluşturuldu."
