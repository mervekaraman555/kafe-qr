#!/bin/bash
# ============================================================
# KAFE QR SİPARİŞ SİSTEMİ — macOS KURULUM YÜKLEYİCİSİ (.app)
# ============================================================

echo "============================================================"
echo "  ☕ KAFE QR SİPARİŞ — macOS KURULUM YÜKLEYİCİSİ"
# Proje kök dizinini otomatik algıla
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/app.py" ]; then
  APP_DIR="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/../../app.py" ]; then
  APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
  APP_DIR="$SCRIPT_DIR"
fi

echo "============================================================"
echo "📁 Proje Dizini: $APP_DIR"
echo ""

echo "[1/3] Masaüstüne ve Uygulamalar'a 'Kafe Giriş Ekranı.app' kuruluyor..."
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
  <string>1.0</string>
</dict>
</plist>
EOF

cat > "$MAC_APP_PATH/Contents/MacOS/KafeGiris" <<EOF
#!/bin/bash
APP_DIR="$APP_DIR"
if ! lsof -i :8091 > /dev/null 2>&1; then
  cd "\$APP_DIR" && nohup python3 app.py > /tmp/kafe_qr_server.log 2>&1 &
  sleep 1
fi
open "http://localhost:8091/giris"
EOF

chmod +x "$MAC_APP_PATH/Contents/MacOS/KafeGiris"

echo "[2/3] Sunucu kontrol ediliyor ve başlatılıyor..."
if ! lsof -i :8091 > /dev/null 2>&1; then
  cd "$APP_DIR" && nohup python3 app.py > /tmp/kafe_qr_server.log 2>&1 &
  sleep 1
fi

echo "[3/3] Giriş Ekranı açılıyor..."
open "http://localhost:8091/giris"

echo ""
echo "✅ macOS Kurulumu Tamamlandı!"
echo "   Masaüstünüzde 'Kafe Giriş Ekranı.app' uygulaması oluşturuldu."

