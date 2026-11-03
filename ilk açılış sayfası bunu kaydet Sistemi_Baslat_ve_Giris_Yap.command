#!/bin/bash
# Kafe QR Sipariş Sistemini Başlatır, İnternet Tünelini Açar ve Giriş Ekranını Açar
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! lsof -i :8091 > /dev/null 2>&1; then
  echo "🚀 Kafe QR Sipariş sunucusu başlatılıyor..."
  cd "$APP_DIR" && nohup python3 app.py > /tmp/kafe_qr_server.log 2>&1 &
  sleep 1
fi

if [ -x "$HOME/.local/bin/cloudflared" ] && ! pgrep -f "cloudflared tunnel" > /dev/null 2>&1; then
  echo "🌐 Ücretsiz internet tüneli başlatılıyor..."
  nohup "$HOME/.local/bin/cloudflared" tunnel --url http://localhost:8090 > /tmp/kafe_tunnel.log 2>&1 &
  sleep 5
fi

TUNNEL_URL=$(grep -o "https://[a-zA-Z0-9-]*\.trycloudflare\.com" /tmp/kafe_tunnel.log 2>/dev/null | tail -n 1)
if [ -n "$TUNNEL_URL" ]; then
  echo "✅ Canlı İnternet Adresiniz: $TUNNEL_URL"
  open "$TUNNEL_URL/giris"
else
  open "http://localhost:8091/giris"
fi
