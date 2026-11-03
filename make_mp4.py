#!/usr/bin/env python3
"""
Kafe QR Sipariş & Yönetim Sistemi — Son Şekliyle Sesli Tanıtım Videosu (.mp4) Üretici
- Eski reklam videosunu ve eski sahne dosyalarını temizler
- 6 sahneyi 1920x1080 Full HD çözünürlükte son özelliklerle çizer:
  1. QR Okutma & Sabit QR / İlave Masa Sistemi
  2. Tam Ekran Ürün Görseli (Zoom) & Garson Zili ile Sipariş
  3. Çalışan Ekranı: Sesli Sipariş ve Garson Çağrı Bildirimi
  4. Canlı Birleştirilmiş Hesap & Termal Adisyon Fişi
  5. Yetkili Yönetici Paneli: Fotoğraflı Menü & Günlük Ciro Takibi
  6. 5 İşletim Sistemi Kurulumu (Windows, Mac, Android, HarmonyOS, iOS)
- Her sahnenin Türkçe nöral seslendirmesini (edge-tts) üretir
- Her sahnenin sonuna 1.5 saniye nefes boşluğu ekler ve MP4 oluşturur
"""

import asyncio
import glob
import os
import subprocess
import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

PROJECT_DIR = "/Users/mervekaraman/Desktop/AI PROJELERİM/kafe-qr-siparis"
AUDIO_DIR = os.path.join(PROJECT_DIR, "audio")
FRAMES_DIR = os.path.join(PROJECT_DIR, "frames")
OLD_MP4 = os.path.join(PROJECT_DIR, "Kafe_QR_Siparis_Reklam.mp4")
OLD_DESKTOP_MP4 = "/Users/mervekaraman/Desktop/Kafe_QR_Siparis_Reklam.mp4"
OUTPUT_MP4 = os.path.join(PROJECT_DIR, "Kafe_QR_Siparis_Tanitim_Videosu.mp4")
PAUSE_SEC = 1.5
VOICE = "tr-TR-AhmetNeural"

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)

W, H = 1920, 1080

SCENES_DATA = [
    {
        "step_short": "1. QR & Sabit Masa",
        "step_badge": "1. Adım • Akıllı QR & Sabit Masa Sistemi",
        "title_l1": "Garson Beklemeye Son,",
        "title_gold": "İlave Masada Sabit QR Garantisi!",
        "desc": "Müşteri masadaki kare kodu okutarak uygulama indirmeden menüye bağlanır. İşletme yeni ilave masa açtığında mevcut masaların QR kodları kesinlikle değişmez, sabit kalır.",
        "voice": "Kafenizde garson beklemeye son! Müşteriniz masadaki kare kodu okutarak anında menüye bağlanır. Üstelik işletmeniz yeni ilave masa açtığında mevcut masaların kare kodları sabit kalır, sadece yeni masalar eklenir.",
    },
    {
        "step_short": "2. Tam Ekran Menü",
        "step_badge": "2. Adım • Tam Ekran Ürün Resmi & Garson Zili",
        "title_l1": "Ürüne Tıkla Tam Ekran Gör,",
        "title_gold": "Tek Tuşla Sipariş Ver & Zil Çal!",
        "desc": "Müşteri menüdeki ürün fotoğrafına dokunduğunda ürün tam ekran açılır. Detayları inceleyip sepete ekler, özel notunu yazar veya tek dokunuşla garson zilini çalar.",
        "voice": "Müşteriniz menüdeki ürünlerin resmine tıkladığında ürünü tam ekran yüksek kalitede inceler, sepetine ekler ve tek tuşla mutfağa gönderir. İhtiyaç halinde ekrandaki garson ziliyle anında garson çağırabilir.",
    },
    {
        "step_short": "3. Çalışan Ekranı",
        "step_badge": "3. Adım • Anında Sesli Bildirim & Mutfak",
        "title_l1": "Çalışan Ekranında Sesli Uyarı,",
        "title_gold": "Hangi Masa Ne İstedi Anında Gör!",
        "desc": "Sipariş veya garson çağrısı geldiği anda çalışan ekranında sesli zil çalar. Masa numarası, ürünler ve müşteri notu saniyesinde ekrana düşer.",
        "voice": "Sipariş verildiği veya garson zili çalındığı anda çalışan ekranında sesli uyarı duyulur. Personel hangi masanın ne istediğini ve özel sipariş notunu saniyesinde görerek hazırlığa başlar.",
    },
    {
        "step_short": "4. Canlı Adisyon",
        "step_badge": "4. Adım • Canlı Hesap & Termal Adisyon Fişi",
        "title_l1": "Birleştirilmiş Canlı Hesap ve",
        "title_gold": "Yazdırılabilir Termal Adisyon!",
        "desc": "Masadan verilen tüm ek siparişler tek adisyonda otomatik birleşir. Müşteri kendi telefonundan güncel hesabını canlı takip eder, kasadan tek tıkla adisyon fişi yazdırılır.",
        "voice": "Masadan verilen tüm siparişler tek adisyonda otomatik birleştirilir. Müşteriniz kendi telefonundan güncel hesabını şeffafça takip ederken, kasadan tek tıkla adisyon fişi yazdırılır.",
    },
    {
        "step_short": "5. Yetkili Paneli",
        "step_badge": "5. Adım • Yönetici Paneli & Ciro Raporu",
        "title_l1": "Fotoğraflı Menü Yönetimi ve",
        "title_gold": "Günlük / Geçmiş Ciro Takibi!",
        "desc": "Kafe yetkilisi özel şifreli panelinden yeni ürün fotoğrafı yükler, fiyatları günceller, personel hesaplarını yönetir ve günlük cirosunu tarih seçerek inceler.",
        "voice": "Yetkili yönetici paneli sayesinde menüye fotoğraflı yeni ürünler ekleyebilir, fiyatları anında güncelleyebilir ve kafenizin günlük cirosunu geçmiş tarihlerle birlikte detaylıca takip edebilirsiniz.",
    },
    {
        "step_short": "6. Tüm Cihazlar",
        "step_badge": "6. Adım • 5 İşletim Sistemine Tek Tıkla Kurulum",
        "title_l1": "Windows, Mac, Android,",
        "title_gold": "HarmonyOS ve iOS Kurulumu!",
        "desc": "Mağaza komisyonu olmadan kasa bilgisayarınıza, Mac cihazınıza, Android, Huawei HarmonyOS ve iPhone-iPad telefon ve tabletlere tek tıkla uygulama olarak kurulur.",
        "voice": "Gelişmiş kurulum merkezi ile Windows, Mac, Android, Huawei HarmonyOS ve iOS cihazların tamamına tek tıkla kurulur. Kafenizi modern teknolojiye taşımak için hemen kullanmaya başlayın!",
    },
]


def cleanup_old_files():
    for p in [OLD_MP4, OLD_DESKTOP_MP4, OUTPUT_MP4]:
        if os.path.exists(p):
            os.remove(p)
            print(f"🗑️ Eski video silindi: {p}")
    for p in glob.glob(os.path.join(FRAMES_DIR, "*")):
        os.remove(p)
    for p in glob.glob(os.path.join(AUDIO_DIR, "sahne*.mp3")):
        os.remove(p)


def load_font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


FONT_TAG = load_font(23, bold=True)
FONT_STEP = load_font(21, bold=True)
FONT_H1 = load_font(54, bold=True)
FONT_BODY = load_font(31, bold=False)
FONT_SUB = load_font(29, bold=True)
FONT_CARD_TITLE = load_font(34, bold=True)
FONT_CARD = load_font(25, bold=False)
FONT_CARD_BOLD = load_font(27, bold=True)
FONT_SMALL_BOLD = load_font(22, bold=True)
FONT_BIG_PRICE = load_font(56, bold=True)


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_base(idx: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    sc = SCENES_DATA[idx]
    img = Image.new("RGB", (W, H), (15, 12, 10))
    draw = ImageDraw.Draw(img)

    # Arka plan koyu gradyan
    for y in range(H):
        r = int(24 + (11 - 24) * (y / H))
        g = int(18 + (17 - 18) * (y / H))
        b = int(14 + (32 - 14) * (y / H))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Üst ilerleme çubuğu
    total_scenes = len(SCENES_DATA)
    bar_w = int((W - 120) * ((idx + 1) / float(total_scenes)))
    draw.rounded_rectangle([60, 28, W - 60, 40], radius=6, fill=(45, 55, 72))
    draw.rounded_rectangle([60, 28, 60 + bar_w, 40], radius=6, fill=(245, 158, 11))

    # Üst sol marka rozeti
    draw.rounded_rectangle([60, 62, 540, 116], radius=26, fill=(30, 41, 59), outline=(245, 158, 11), width=2)
    draw.text((84, 76), "ARTISAN KAFE • QR SİPARİŞ SİSTEMİ", font=FONT_TAG, fill=(253, 230, 138))

    # Sağ üst 6 adımlı sahne göstergesi
    sx = W - 60
    for s_i in range(total_scenes - 1, -1, -1):
        label = SCENES_DATA[s_i]["step_short"]
        tb = draw.textbbox((0, 0), label, font=FONT_STEP)
        tw = (tb[2] - tb[0]) + 28
        sx -= tw
        active = s_i == idx
        draw.rounded_rectangle(
            [sx, 64, sx + tw, 114],
            radius=22,
            fill=(245, 158, 11) if active else (30, 41, 59),
            outline=(253, 230, 138) if active else (71, 85, 105),
            width=2,
        )
        draw.text(
            (sx + 14, 77),
            label,
            font=FONT_STEP,
            fill=(20, 15, 12) if active else (203, 213, 225),
        )
        sx -= 10

    # Sol metin alanı
    tb_badge = draw.textbbox((0, 0), sc["step_badge"].upper(), font=FONT_TAG)
    bw = (tb_badge[2] - tb_badge[0]) + 48
    draw.rounded_rectangle([80, 215, 80 + bw, 268], radius=24, fill=(68, 44, 14), outline=(245, 158, 11), width=2)
    draw.text((104, 229), sc["step_badge"].upper(), font=FONT_TAG, fill=(252, 211, 77))

    draw.text((80, 300), sc["title_l1"], font=FONT_H1, fill=(255, 255, 255))
    draw.text((80, 372), sc["title_gold"], font=FONT_H1, fill=(245, 158, 11))

    desc_lines = wrap_text(draw, sc["desc"], FONT_BODY, 820)
    dy = 470
    for line in desc_lines:
        draw.text((80, dy), line, font=FONT_BODY, fill=(203, 213, 225))
        dy += 45

    # Alt seslendirme (altyazı) kutusu
    draw.rounded_rectangle([60, H - 142, W - 60, H - 38], radius=22, fill=(9, 13, 26), outline=(245, 158, 11), width=2)
    sub_lines = wrap_text(draw, sc["voice"], FONT_SUB, W - 200)
    sy = H - 124 if len(sub_lines) > 1 else H - 104
    for line in sub_lines:
        tb = draw.textbbox((0, 0), line, font=FONT_SUB)
        lw = tb[2] - tb[0]
        draw.text(((W - lw) // 2, sy), line, font=FONT_SUB, fill=(254, 243, 199))
        sy += 36

    return img, draw


def make_scene_1():
    img, draw = draw_base(0)
    # Sol QR Kart (Sabit Masa)
    x0, y0 = 1030, 200
    draw.rounded_rectangle([x0, y0, x0 + 360, y0 + 540], radius=28, fill=(255, 255, 255), outline=(245, 158, 11), width=5)
    draw.rounded_rectangle([x0 + 45, y0 + 22, x0 + 315, y0 + 62], radius=16, fill=(241, 245, 249), outline=(148, 163, 184), width=2)
    draw.text((x0 + 68, y0 + 30), "Sabit Masa (Değişmez)", font=FONT_SMALL_BOLD, fill=(51, 65, 85))
    draw.text((x0 + 95, y0 + 82), "MASA 1", font=FONT_H1, fill=(180, 83, 9))

    qx, qy, qs = x0 + 65, y0 + 160, 230
    draw.rounded_rectangle([qx, qy, qx + qs, qy + qs], radius=14, fill=(248, 250, 252), outline=(15, 23, 42), width=5)
    pattern = ["111110111", "100010101", "101110011", "100010110", "111110101", "000000110", "111110011", "101010100", "111110111"]
    for r_i, row in enumerate(pattern):
        for c_i, ch in enumerate(row):
            if ch == "1":
                draw.rectangle([qx + 16 + c_i * 22, qy + 16 + r_i * 22, qx + 33 + c_i * 22, qy + 33 + r_i * 22], fill=(15, 23, 42))
    draw.rectangle([qx + 8, qy + 115, qx + qs - 8, qy + 123], fill=(34, 197, 94))
    draw.rounded_rectangle([x0 + 30, y0 + 425, x0 + 330, y0 + 490], radius=14, fill=(220, 252, 231), outline=(34, 197, 94), width=2)
    draw.text((x0 + 55, y0 + 444), "✓ QR Kod Sabit Korunur", font=FONT_SMALL_BOLD, fill=(21, 128, 61))

    # Sağ QR Kart (+ İlave Masa)
    x1, y1 = 1435, 200
    draw.rounded_rectangle([x1, y1, x1 + 360, y1 + 540], radius=28, fill=(255, 255, 255), outline=(5, 150, 105), width=5)
    draw.rounded_rectangle([x1 + 45, y1 + 22, x1 + 315, y1 + 62], radius=16, fill=(220, 252, 231), outline=(34, 197, 94), width=2)
    draw.text((x1 + 68, y1 + 30), "+ Yeni İlave Masa", font=FONT_SMALL_BOLD, fill=(21, 128, 61))
    draw.text((x1 + 78, y1 + 82), "MASA 13", font=FONT_H1, fill=(5, 150, 105))

    qx2, qy2 = x1 + 65, y1 + 160
    draw.rounded_rectangle([qx2, qy2, qx2 + qs, qy2 + qs], radius=14, fill=(248, 250, 252), outline=(5, 150, 105), width=5)
    for r_i, row in enumerate(reversed(pattern)):
        for c_i, ch in enumerate(row):
            if ch == "1":
                draw.rectangle([qx2 + 16 + c_i * 22, qy2 + 16 + r_i * 22, qx2 + 33 + c_i * 22, qy2 + 33 + r_i * 22], fill=(15, 23, 42))
    draw.rounded_rectangle([x1 + 30, y1 + 425, x1 + 330, y1 + 490], radius=14, fill=(5, 150, 105))
    draw.text((x1 + 42, y1 + 444), "Sadece İlaveyi Yazdır →", font=FONT_SMALL_BOLD, fill=(255, 255, 255))

    path = os.path.join(FRAMES_DIR, "scene1.png")
    img.save(path)
    return path


def make_scene_2():
    img, draw = draw_base(1)
    # Telefon + Tam Ekran Ürün Lightbox Görünümü
    x0, y0, x1, y1 = 1040, 175, 1810, 815
    draw.rounded_rectangle([x0, y0, x1, y1], radius=36, fill=(28, 22, 19), outline=(245, 158, 11), width=5)

    # Üst bar: Masa 4 + Garson Zili
    draw.rounded_rectangle([x0 + 20, y0 + 20, x1 - 20, y0 + 92], radius=20, fill=(45, 35, 29))
    draw.text((x0 + 42, y0 + 42), "Artisan Kafe • Masa 4", font=FONT_CARD_BOLD, fill=(255, 255, 255))
    draw.rounded_rectangle([x1 - 265, y0 + 32, x1 - 40, y0 + 80], radius=22, fill=(239, 68, 68), outline=(252, 165, 165), width=2)
    draw.text((x1 - 240, y0 + 43), "Garson Zili Çal", font=FONT_SMALL_BOLD, fill=(255, 255, 255))

    # Tam Ekran Ürün Görseli (Lightbox Kartı)
    lx0, ly0, lx1, ly1 = x0 + 45, y0 + 115, x1 - 45, y1 - 30
    draw.rounded_rectangle([lx0, ly0, lx1, ly1], radius=26, fill=(18, 14, 12), outline=(251, 191, 36), width=3)

    # Ürün fotoğraf alanı
    draw.rounded_rectangle([lx0 + 20, ly0 + 20, lx1 - 20, ly0 + 285], radius=18, fill=(68, 44, 24))
    # Kahve fincanı ve cheesecake illüstrasyonu
    draw.ellipse([lx0 + 230, ly0 + 55, lx0 + 440, ly0 + 245], fill=(217, 119, 6), outline=(254, 243, 199), width=6)
    draw.ellipse([lx0 + 260, ly0 + 82, lx0 + 410, ly0 + 218], fill=(120, 53, 15))
    draw.rounded_rectangle([lx0 + 35, ly0 + 32, lx0 + 310, ly0 + 74], radius=14, fill=(0, 0, 0))
    draw.text((lx0 + 50, ly0 + 42), "🔍 Tam Ekran Ürün Görünümü", font=FONT_SMALL_BOLD, fill=(253, 230, 138))
    draw.rounded_rectangle([lx1 - 76, ly0 + 32, lx1 - 32, ly0 + 76], radius=22, fill=(0, 0, 0), outline=(255, 255, 255), width=2)
    draw.text((lx1 - 63, ly0 + 40), "X", font=FONT_CARD_BOLD, fill=(255, 255, 255))

    # Ürün bilgileri ve sepete ekle
    draw.text((lx0 + 30, ly0 + 302), "SICAK İÇECEKLER • ÖZEL HARMAN", font=FONT_STEP, fill=(251, 191, 36))
    draw.text((lx0 + 30, ly0 + 334), "Caffe Latte & San Sebastian", font=FONT_CARD_TITLE, fill=(255, 255, 255))
    draw.text((lx0 + 30, ly0 + 382), "Çift shot espresso, kadifemsi sıcak süt ve taze krema", font=FONT_CARD, fill=(214, 199, 184))

    draw.text((lx0 + 30, ly0 + 438), "275 TL", font=FONT_H1, fill=(251, 191, 36))
    draw.rounded_rectangle([lx1 - 300, ly0 + 432, lx1 - 30, ly0 + 496], radius=16, fill=(34, 197, 94))
    draw.text((lx1 - 268, ly0 + 450), "+ Sepete Ekle & Gönder", font=FONT_CARD_BOLD, fill=(5, 46, 22))

    path = os.path.join(FRAMES_DIR, "scene2.png")
    img.save(path)
    return path


def make_scene_3():
    img, draw = draw_base(2)
    x0, y0, x1, y1 = 1030, 185, 1810, 805
    draw.rounded_rectangle([x0, y0, x1, y1], radius=30, fill=(15, 23, 42), outline=(245, 158, 11), width=5)

    # Üst kırmızı garson çağrı alarm barı
    draw.rounded_rectangle([x0 + 28, y0 + 26, x1 - 28, y0 + 112], radius=18, fill=(127, 29, 29), outline=(239, 68, 68), width=3)
    draw.text((x0 + 50, y0 + 42), "🔔 GARSON ÇAĞRISI: MASA 4", font=FONT_CARD_BOLD, fill=(254, 240, 138))
    draw.text((x0 + 50, y0 + 76), "Müşteri Talebi: Peçete & Servis İsteği (Sesli Uyarı Aktif)", font=FONT_SMALL_BOLD, fill=(254, 202, 202))
    draw.rounded_rectangle([x1 - 210, y0 + 44, x1 - 46, y0 + 94], radius=12, fill=(34, 197, 94))
    draw.text((x1 - 190, y0 + 57), "✓ İlgilenildi", font=FONT_SMALL_BOLD, fill=(5, 46, 22))

    # Sipariş kartı
    draw.rounded_rectangle([x0 + 28, y0 + 135, x0 + 230, y0 + 195], radius=14, fill=(245, 158, 11))
    draw.text((x0 + 54, y0 + 148), "MASA 4", font=FONT_CARD_TITLE, fill=(15, 23, 42))
    draw.text((x1 - 310, y0 + 152), "• Yeni Sipariş Geldi!", font=FONT_CARD_BOLD, fill=(252, 211, 77))

    draw.line([(x0 + 28, y0 + 215), (x1 - 28, y0 + 215)], fill=(51, 65, 85), width=2)
    draw.text((x0 + 40, y0 + 235), "2x  Caffe Latte", font=FONT_CARD_BOLD, fill=(248, 250, 252))
    draw.text((x1 - 160, y0 + 235), "220 TL", font=FONT_CARD_BOLD, fill=(248, 250, 252))

    draw.text((x0 + 40, y0 + 290), "1x  San Sebastian Cheesecake", font=FONT_CARD_BOLD, fill=(248, 250, 252))
    draw.text((x1 - 160, y0 + 290), "165 TL", font=FONT_CARD_BOLD, fill=(248, 250, 252))
    draw.line([(x0 + 28, y0 + 345), (x1 - 28, y0 + 345)], fill=(51, 65, 85), width=2)

    draw.rounded_rectangle([x0 + 28, y0 + 365, x1 - 28, y0 + 435], radius=14, fill=(68, 44, 14), outline=(245, 158, 11), width=2)
    draw.text((x0 + 48, y0 + 388), "Müşteri Notu: Bir latte yulaf sütlü olsun", font=FONT_CARD, fill=(253, 230, 138))

    draw.rounded_rectangle([x0 + 28, y0 + 465, x0 + 390, y0 + 555], radius=16, fill=(56, 189, 248))
    draw.text((x0 + 68, y0 + 496), "Hazırlanıyor İşaretle", font=FONT_CARD_BOLD, fill=(15, 23, 42))
    draw.rounded_rectangle([x0 + 410, y0 + 465, x1 - 28, y0 + 555], radius=16, fill=(34, 197, 94))
    draw.text((x0 + 448, y0 + 496), "✓ Servis Tamamla", font=FONT_CARD_BOLD, fill=(5, 46, 22))

    path = os.path.join(FRAMES_DIR, "scene3.png")
    img.save(path)
    return path


def make_scene_4():
    img, draw = draw_base(3)
    # Termal Adisyon Fişi & Canlı Hesap
    x0, y0, x1, y1 = 1060, 175, 1790, 815
    draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(255, 253, 249), outline=(203, 213, 225), width=5)

    draw.text((x0 + 205, y0 + 30), "ARTİSAN KAFE", font=FONT_CARD_TITLE, fill=(15, 23, 42))
    draw.text((x0 + 225, y0 + 74), "HESAP ADİSYON FİŞİ", font=FONT_SMALL_BOLD, fill=(100, 116, 139))

    draw.rounded_rectangle([x0 + 40, y0 + 115, x1 - 40, y0 + 172], radius=12, fill=(30, 41, 59))
    draw.text((x0 + 235, y0 + 127), "MASA 4 • AÇIK HESAP", font=FONT_CARD_BOLD, fill=(255, 255, 255))

    draw.text((x0 + 45, y0 + 198), "ÜRÜN", font=FONT_SMALL_BOLD, fill=(71, 85, 105))
    draw.text((x0 + 430, y0 + 198), "ADET", font=FONT_SMALL_BOLD, fill=(71, 85, 105))
    draw.text((x1 - 140, y0 + 198), "TUTAR", font=FONT_SMALL_BOLD, fill=(71, 85, 105))
    draw.line([(x0 + 40, y0 + 230), (x1 - 40, y0 + 230)], fill=(148, 163, 184), width=2)

    items = [
        ("Caffe Latte", "2x", "220 TL"),
        ("San Sebastian Cheesecake", "1x", "165 TL"),
        ("Taze Portakal Suyu (Ek Sipariş)", "1x", "95 TL"),
    ]
    iy = y0 + 250
    for name, qty, total in items:
        draw.text((x0 + 45, iy), name, font=FONT_CARD_BOLD, fill=(30, 41, 59))
        draw.text((x0 + 440, iy), qty, font=FONT_CARD_BOLD, fill=(180, 83, 9))
        draw.text((x1 - 145, iy), total, font=FONT_CARD_BOLD, fill=(30, 41, 59))
        iy += 54

    draw.line([(x0 + 40, y0 + 425), (x1 - 40, y0 + 425)], fill=(148, 163, 184), width=2)

    draw.rounded_rectangle([x0 + 40, y0 + 445, x1 - 40, y0 + 530], radius=16, fill=(254, 243, 199), outline=(245, 158, 11), width=3)
    draw.text((x0 + 65, y0 + 472), "GENEL TOPLAM", font=FONT_CARD_TITLE, fill=(120, 53, 15))
    draw.text((x1 - 220, y0 + 462), "480 TL", font=FONT_H1, fill=(120, 53, 15))

    draw.rounded_rectangle([x0 + 40, y0 + 550, x0 + 380, y0 + 615], radius=14, fill=(15, 23, 42))
    draw.text((x0 + 75, y0 + 570), "🖨️ Adisyonu Yazdır", font=FONT_CARD_BOLD, fill=(255, 255, 255))
    draw.rounded_rectangle([x0 + 400, y0 + 550, x1 - 40, y0 + 615], radius=14, fill=(21, 128, 61))
    draw.text((x0 + 445, y0 + 570), "💳 Hesabı Kapat", font=FONT_CARD_BOLD, fill=(255, 255, 255))

    path = os.path.join(FRAMES_DIR, "scene4.png")
    img.save(path)
    return path


def make_scene_5():
    img, draw = draw_base(4)
    # Yetkili Yönetici Paneli: Ciro & Fotoğraflı Menü Yönetimi
    x0, y0, x1, y1 = 1020, 180, 1820, 810
    draw.rounded_rectangle([x0, y0, x1, y1], radius=28, fill=(17, 24, 39), outline=(245, 158, 11), width=4)

    draw.text((x0 + 34, y0 + 28), "👔 Kafe Yetkili / Yönetici Paneli", font=FONT_CARD_TITLE, fill=(253, 230, 138))

    # Ciro Kartları
    draw.rounded_rectangle([x0 + 34, y0 + 85, x0 + 395, y0 + 220], radius=18, fill=(6, 78, 59), outline=(34, 197, 94), width=2)
    draw.text((x0 + 54, y0 + 105), "Tahsil Edilen Günlük Ciro", font=FONT_SMALL_BOLD, fill=(167, 243, 208))
    draw.text((x0 + 54, y0 + 142), "18.450 TL", font=FONT_H1, fill=(74, 222, 128))

    draw.rounded_rectangle([x0 + 415, y0 + 85, x1 - 34, y0 + 220], radius=18, fill=(68, 44, 14), outline=(245, 158, 11), width=2)
    draw.text((x0 + 435, y0 + 105), "Açık Masalardaki Tutar", font=FONT_SMALL_BOLD, fill=(253, 230, 138))
    draw.text((x0 + 435, y0 + 142), "2.340 TL", font=FONT_H1, fill=(251, 191, 36))

    # Fotoğraflı Ürün Ekleme Bölümü
    draw.rounded_rectangle([x0 + 34, y0 + 245, x1 - 34, y0 + 455], radius=18, fill=(30, 41, 59), outline=(71, 85, 105), width=2)
    draw.text((x0 + 54, y0 + 265), "📸 Fotoğraflı Menü & Fiyat Yönetimi", font=FONT_CARD_BOLD, fill=(255, 255, 255))

    draw.rounded_rectangle([x0 + 54, y0 + 312, x1 - 54, y0 + 372], radius=12, fill=(15, 23, 42))
    draw.text((x0 + 74, y0 + 328), "☕ Iced Caramel Macchiato  •  135 TL", font=FONT_CARD_BOLD, fill=(248, 250, 252))
    draw.rounded_rectangle([x1 - 245, y0 + 320, x1 - 70, y0 + 364], radius=10, fill=(245, 158, 11))
    draw.text((x1 - 225, y0 + 331), "📷 Resim Yükle", font=FONT_SMALL_BOLD, fill=(15, 23, 42))

    draw.rounded_rectangle([x0 + 54, y0 + 384, x1 - 54, y0 + 440], radius=12, fill=(15, 23, 42))
    draw.text((x0 + 74, y0 + 398), "🍰 Belçika Çikolatalı Sufle  •  170 TL", font=FONT_CARD_BOLD, fill=(248, 250, 252))
    draw.rounded_rectangle([x1 - 245, y0 + 392, x1 - 70, y0 + 432], radius=10, fill=(34, 197, 94))
    draw.text((x1 - 225, y0 + 401), "✓ Resim Aktif", font=FONT_SMALL_BOLD, fill=(5, 46, 22))

    # Alt Tarih Seçici & Personel Yönetimi
    draw.rounded_rectangle([x0 + 34, y0 + 480, x1 - 34, y0 + 595], radius=18, fill=(15, 23, 42), outline=(56, 189, 248), width=2)
    draw.text((x0 + 54, y0 + 502), "📅 Geçmiş Gün Sonu Raporları & Personel Şifre Yönetimi", font=FONT_CARD_BOLD, fill=(125, 211, 252))
    draw.text((x0 + 54, y0 + 545), "Yetkili ve Çalışan girişleri ayrı şifrelerle tam güvende!", font=FONT_CARD, fill=(203, 213, 225))

    path = os.path.join(FRAMES_DIR, "scene5.png")
    img.save(path)
    return path


def make_scene_6():
    img, draw = draw_base(5)
    # 5 İşletim Sistemi Kurulum Merkezi
    x0, y0, x1, y1 = 1020, 180, 1820, 810
    draw.rounded_rectangle([x0, y0, x1, y1], radius=28, fill=(17, 24, 39), outline=(245, 158, 11), width=4)
    draw.text((x0 + 40, y0 + 32), "📲 Çoklu İşletim Sistemi Kurulum Merkezi", font=FONT_CARD_TITLE, fill=(255, 255, 255))

    platforms = [
        ("1. Windows 10 / 11", "Kasa & POS Bilgisayarı (.bat Otomatik Kurulum)", (59, 130, 246)),
        ("2. Apple macOS", "Masaüstü .app Uygulaması (.command Yükleyici)", (168, 85, 247)),
        ("3. Android Cihazlar", "Telefon & Garson Tabletleri (Tek Tıkla Tam Ekran)", (34, 197, 94)),
        ("4. Huawei HarmonyOS", "Huawei Telefon & MatePad Tablet Paketi", (239, 68, 68)),
        ("5. Apple iOS / iPadOS", "iPhone & iPad (.mobileconfig Profil Kurulumu)", (56, 189, 248)),
    ]

    py = y0 + 95
    for title, sub, color in platforms:
        draw.rounded_rectangle([x0 + 36, py, x1 - 36, py + 92], radius=16, fill=(30, 41, 59), outline=color, width=3)
        draw.text((x0 + 60, py + 14), title, font=FONT_CARD_BOLD, fill=(255, 255, 255))
        draw.text((x0 + 60, py + 50), sub, font=FONT_SMALL_BOLD, fill=(203, 213, 225))
        draw.rounded_rectangle([x1 - 210, py + 24, x1 - 56, py + 68], radius=12, fill=color)
        draw.text((x1 - 185, py + 34), "⬇️ Hemen Kur", font=FONT_SMALL_BOLD, fill=(15, 23, 42) if color != (239, 68, 68) else (255, 255, 255))
        py += 104

    path = os.path.join(FRAMES_DIR, "scene6.png")
    img.save(path)
    return path


async def generate_all_voiceovers():
    for idx, sc in enumerate(SCENES_DATA, start=1):
        mp3_path = os.path.join(AUDIO_DIR, f"sahne{idx}.mp3")
        communicate = edge_tts.Communicate(sc["voice"], VOICE, rate="+4%")
        await communicate.save(mp3_path)
        print(f"🎙️ Seslendirme oluşturuldu: sahne{idx}.mp3")


def get_audio_duration(path: str) -> float:
    out = subprocess.check_output(["afinfo", path], text=True)
    for line in out.splitlines():
        if "estimated duration:" in line:
            return float(line.split("estimated duration:")[1].split()[0])
    return 7.0


def build_video():
    cleanup_old_files()
    asyncio.run(generate_all_voiceovers())

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    scenes = [
        (make_scene_1(), os.path.join(AUDIO_DIR, "sahne1.mp3")),
        (make_scene_2(), os.path.join(AUDIO_DIR, "sahne2.mp3")),
        (make_scene_3(), os.path.join(AUDIO_DIR, "sahne3.mp3")),
        (make_scene_4(), os.path.join(AUDIO_DIR, "sahne4.mp3")),
        (make_scene_5(), os.path.join(AUDIO_DIR, "sahne5.mp3")),
        (make_scene_6(), os.path.join(AUDIO_DIR, "sahne6.mp3")),
    ]

    seg_paths = []
    for i, (img_path, mp3_path) in enumerate(scenes, start=1):
        voice_dur = get_audio_duration(mp3_path)
        total_dur = round(voice_dur + PAUSE_SEC, 2)
        seg_out = os.path.join(FRAMES_DIR, f"seg_{i}.mp4")
        cmd = [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-i",
            img_path,
            "-i",
            mp3_path,
            "-filter_complex",
            f"[1:a]apad=pad_dur={PAUSE_SEC}[aout]",
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "25",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-t",
            str(total_dur),
            seg_out,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"🎬 Sahne {i} hazır: konuşma={voice_dur:.2f}s + boşluk={PAUSE_SEC}s -> toplam={total_dur:.2f}s")
        seg_paths.append(seg_out)

    concat_txt = os.path.join(FRAMES_DIR, "concat.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for p in seg_paths:
            f.write(f"file '{p}'\n")

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_txt,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            OUTPUT_MP4,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"\n✅ Yeni Sesli Tanıtım Videosu Oluşturuldu: {OUTPUT_MP4} ({os.path.getsize(OUTPUT_MP4) // 1024} KB)")
    desktop_copy = "/Users/mervekaraman/Desktop/Kafe_QR_Siparis_Tanitim_Videosu.mp4"
    import shutil
    shutil.copy2(OUTPUT_MP4, desktop_copy)
    print(f"✅ Masaüstüne de kaydedildi: {desktop_copy}")


if __name__ == "__main__":
    build_video()
