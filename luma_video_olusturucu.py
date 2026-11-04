#!/usr/bin/env python3
"""
Luma AI (Dream Machine) Video Oluşturucu
Bu araç ile ürün fotoğraflarınızı videodaki gibi hareketli sinematik videolara dönüştürebilirsiniz.
"""

import os
import sys
import time

def check_luma():
    try:
        from lumaai import LumaAI
        return LumaAI
    except ImportError:
        print("❌ 'lumaai' kütüphanesi bulunamadı. Lütfen 'pip install lumaai' çalıştırın.")
        sys.exit(1)

def main():
    print("=" * 60)
    print("🎬 LUMA AI (DREAM MACHINE) — ÜRÜN VİDEO OLUŞTURUCU")
    print("=" * 60)
    
    api_key = os.environ.get("LUMAAI_API_KEY")
    if not api_key:
        print("\nℹ️ Luma AI API Anahtarı Gerekli!")
        print("1. https://lumalabs.ai/dream-machine/api adresine gidin.")
        print("2. Ücretsiz hesap açıp 'Create API Key' butonuna basarak bir anahtar alın.")
        print("-" * 60)
        api_key = input("👉 Luma API Key'inizi buraya yapıştırın (veya çıkmak için Enter): ").strip()
        if not api_key:
            print("\n💡 İpucu: Kod kullanmadan doğrudan web üzerinden ücretsiz video oluşturmak için:")
            print("   Masaüstünüzdeki 'Luma_AI_Dream_Machine' kısayoluna çift tıklayabilirsiniz!")
            return

    LumaAI = check_luma()
    client = LumaAI(auth_token=api_key)

    print("\nNe yapmak istersiniz?")
    print("1. Ürün Fotoğrafını Videoya Dönüştür (Image-to-Video)")
    print("2. Metin / Tarif Yazarak Sıfırdan Video Üret (Text-to-Video)")
    secim = input("Seçiminiz (1 veya 2): ").strip()

    prompt = ""
    image_url = None

    if secim == "1":
        print("\n📸 Ürün Görseli:")
        print("Örnek: https://faruk8503.pythonanywhere.com/uploads/urun_artisan_burger.jpg")
        image_url = input("Ürün görseli internet linki (URL): ").strip()
        prompt = input("Hareket / Efekt açıklaması (Örn: cinematic slow motion dripping cheese sauce and smoke): ").strip()
        if not prompt:
            prompt = "cinematic slow motion commercial food shot, mouthwatering dripping sauce, gentle camera zoom, 4k"
    else:
        prompt = input("\nVideo Tarifi (Prompt): ").strip()
        if not prompt:
            prompt = "delicious gourmet burger with melted dripping cheddar cheese and flying bacon slices, 4k commercial"

    print("\n⏳ Luma Dream Machine ile video üretimi başlatılıyor...")
    try:
        if image_url:
            generation = client.generations.create(
                prompt=prompt,
                keyframes={
                    "frame0": {
                        "type": "image",
                        "url": image_url
                    }
                }
            )
        else:
            generation = client.generations.create(
                prompt=prompt
            )

        print(f"✅ Video işlemi oluşturuldu! (ID: {generation.id})")
        print("⏳ Video yapay zeka tarafından işleniyor (yaklaşık 1-2 dakika sürer)...")

        while generation.state not in ["completed", "failed"]:
            time.sleep(5)
            generation = client.generations.get(id=generation.id)
            print(f"   Durum: {generation.state}...")

        if generation.state == "completed":
            video_url = generation.assets.video
            print("\n🎉 VİDEONUZ HAZIR!")
            print(f"👉 Video İndirme Linki: {video_url}")
        else:
            print(f"\n❌ Video oluşturulamadı: {generation.failure_reason}")

    except Exception as e:
        print(f"\n❌ Bir hata oluştu: {e}")

if __name__ == "__main__":
    main()

