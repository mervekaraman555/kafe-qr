#!/bin/bash
# ============================================================
# KAFE QR SİPARİŞ — ANDROID (.APK) PAKETİ OLUŞTURUCU
# ============================================================
# Bu betik, sunucu adresinize bağlanan bağımsız bir Android .APK
# projesi (Capacitor) oluşturur.

SUNUCU_URL="${1:-http://192.168.1.100:8091/giris}"
echo "🤖 Android .APK yapılandırması hazırlanıyor (Sunucu: $SUNUCU_URL)..."

cat > capacitor.config.json <<EOF
{
  "appId": "com.artisankafe.qrsiparis",
  "appName": "Kafe Yönetim",
  "webDir": "www",
  "server": {
    "url": "$SUNUCU_URL",
    "cleartext": true
  }
}
EOF

echo "✅ capacitor.config.json oluşturuldu."
echo "Not: Doğrudan APK gerekmeksizin tüm Android cihazlara 'Android_Kurulum_Yukleyici.html' veya '/kurulum?os=android' adresinden tek tıkla WebAPK kurulumu yapılabilir."

