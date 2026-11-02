#!/bin/bash
# Kafe QR Sipariş Sistemini Başlatır ve Giriş Ekranını Açar
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! lsof -i :8091 > /dev/null 2>&1; then
  echo "🚀 Kafe QR Sipariş sunucusu başlatılıyor..."
  cd "$APP_DIR" && nohup python3 app.py > /tmp/kafe_qr_server.log 2>&1 &
  sleep 1
fi

open "http://localhost:8091/giris"
