#!/usr/bin/env python3
"""
Kafe QR Sipariş Reklam Videosu (.mp4) Üretici
- 5 sahneyi 1920x1080 Full HD çözünürlükte çizer
- Her sahnenin Türkçe nöral seslendirmesini (sahne1..5.mp3) alır
- Her sahnenin sonuna tam 1.8 saniye sessizlik (boşluk) ekler
- Masaüstüne 'Kafe_QR_Siparis_Reklam.mp4' olarak kaydeder
"""

import os
import subprocess
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

PROJECT_DIR = "/Users/mervekaraman/Desktop/AI PROJELERİM/kafe-qr-siparis"
AUDIO_DIR = os.path.join(PROJECT_DIR, "audio")
FRAMES_DIR = os.path.join(PROJECT_DIR, "frames")
OUTPUT_MP4 = "/Users/mervekaraman/Desktop/Kafe_QR_Siparis_Reklam.mp4"
PAUSE_SEC = 1.8

os.makedirs(FRAMES_DIR, exist_ok=True)

W, H = 1920, 1080


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


FONT_TAG = load_font(26, bold=True)
FONT_H1 = load_font(60, bold=True)
FONT_BODY = load_font(33, bold=False)
FONT_SUB = load_font(32, bold=True)
FONT_CARD_TITLE = load_font(38, bold=True)
FONT_CARD = load_font(28, bold=False)
FONT_CARD_BOLD = load_font(30, bold=True)
FONT_BIG_PRICE = load_font(64, bold=True)


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


def draw_base(idx: int, step_label: str, title_l1: str, title_gold: str, desc: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), (17, 13, 11))
    draw = ImageDraw.Draw(img)

    # Yumuşak arka plan gradyan kuşakları
    for y in range(H):
        r = int(26 + (15 - 26) * (y / H))
        g = int(19 + (23 - 19) * (y / H))
        b = int(15 + (42 - 15) * (y / H))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Üst ilerleme çubuğu
    bar_w = int((W - 120) * ((idx + 1) / 5.0))
    draw.rounded_rectangle([60, 32, W - 60, 44], radius=6, fill=(45, 55, 72))
    draw.rounded_rectangle([60, 32, 60 + bar_w, 44], radius=6, fill=(245, 158, 11))

    # Üst marka rozeti
    draw.rounded_rectangle([60, 68, 590, 126], radius=28, fill=(30, 41, 59), outline=(245, 158, 11), width=2)
    draw.text((88, 82), "ARTISAN KAFE  •  QR SİPARİŞ SİSTEMİ", font=FONT_TAG, fill=(253, 230, 138))

    # Sağ üst sahne göstergesi
    steps = ["1. QR Okut", "2. Sipariş Ver", "3. Çalışan Ekranı", "4. Tamamla", "5. Canlı Hesap"]
    sx = W - 60
    for s_i in range(4, -1, -1):
        label = steps[s_i]
        tb = draw.textbbox((0, 0), label, font=FONT_TAG)
        tw = (tb[2] - tb[0]) + 36
        sx -= tw
        active = s_i == idx
        draw.rounded_rectangle(
            [sx, 68, sx + tw, 124],
            radius=26,
            fill=(245, 158, 11) if active else (30, 41, 59),
            outline=(253, 230, 138) if active else (71, 85, 105),
            width=2,
        )
        draw.text(
            (sx + 18, 82),
            label,
            font=FONT_TAG,
            fill=(20, 15, 12) if active else (203, 213, 225),
        )
        sx -= 12

    # Sol metin alanı
    draw.rounded_rectangle([80, 230, 430, 286], radius=26, fill=(68, 44, 14), outline=(245, 158, 11), width=2)
    draw.text((104, 244), step_label.upper(), font=FONT_TAG, fill=(252, 211, 77))

    draw.text((80, 318), title_l1, font=FONT_H1, fill=(255, 255, 255))
    draw.text((80, 395), title_gold, font=FONT_H1, fill=(245, 158, 11))

    desc_lines = wrap_text(draw, desc, FONT_BODY, 820)
    dy = 495
    for line in desc_lines:
        draw.text((80, dy), line, font=FONT_BODY, fill=(203, 213, 225))
        dy += 48

    # Alt seslendirme (altyazı) kutusu
    draw.rounded_rectangle([80, H - 140, W - 80, H - 46], radius=22, fill=(9, 13, 26), outline=(245, 158, 11), width=2)
    sub_lines = wrap_text(draw, subtitle, FONT_SUB, W - 240)
    sy = H - 122 if len(sub_lines) > 1 else H - 108
    for line in sub_lines:
        tb = draw.textbbox((0, 0), line, font=FONT_SUB)
        lw = tb[2] - tb[0]
        draw.text(((W - lw) // 2, sy), line, font=FONT_SUB, fill=(254, 243, 199))
        sy += 38

    return img, draw


def make_scene_1():
    img, draw = draw_base(
        0,
        "1. Adım • Sıfır Bekleme",
        "Garson Beklemeye Son.",
        "Kare Kodu Okut, Menü Açılsın!",
        "Her masaya özel üretilen kare kodu müşteri telefon kamerasıyla okutur; uygulama indirmeden doğrudan kendi masasının menüsüne bağlanır.",
        "Kafenizde garson beklemeye son! Müşteriniz masadaki kare kodu okutur ve anında kendi masasının menüsüne bağlanır.",
    )
    # Sağ görsel: Masa QR kartı
    cx, cy = 1400, 480
    draw.rounded_rectangle([cx - 250, cy - 270, cx + 250, cy + 270], radius=36, fill=(255, 255, 255), outline=(245, 158, 11), width=6)
    draw.text((cx - 115, cy - 235), "MASA 4", font=FONT_H1, fill=(180, 83, 9))
    draw.text((cx - 190, cy - 160), "Sipariş için kameranızla okutun", font=FONT_CARD, fill=(100, 116, 139))

    # Sahte QR deseni
    qx, qy, qs = cx - 130, cy - 110, 260
    draw.rounded_rectangle([qx, qy, qx + qs, qy + qs], radius=16, fill=(248, 250, 252), outline=(15, 23, 42), width=6)
    cell = 26
    pattern = [
        "1111101011",
        "1000100101",
        "1010101110",
        "1000100011",
        "1111101010",
        "0000001101",
        "1111100110",
        "1000101001",
        "1010101100",
        "1111100111",
    ]
    for r_i, row in enumerate(pattern):
        for c_i, ch in enumerate(row):
            if ch == "1":
                x0 = qx + 15 + c_i * 23
                y0 = qy + 15 + r_i * 23
                draw.rectangle([x0, y0, x0 + 19, y0 + 19], fill=(15, 23, 42))

    # Yeşil tarama lazeri
    draw.rectangle([qx + 8, qy + 130, qx + qs - 8, qy + 138], fill=(34, 197, 94))
    draw.rounded_rectangle([cx - 195, cy + 175, cx + 195, cy + 235], radius=18, fill=(220, 252, 231), outline=(34, 197, 94), width=3)
    draw.text((cx - 165, cy + 190), "✓ Masa 4 Otomatik Seçildi", font=FONT_CARD_BOLD, fill=(21, 128, 61))

    path = os.path.join(FRAMES_DIR, "scene1.png")
    img.save(path)
    return path


def make_scene_2():
    img, draw = draw_base(
        1,
        "2. Adım • Kolay Sipariş",
        "Müşteri Seçimini Yapar,",
        "Tek Tuşla Mutfağa Gönderir.",
        "Sıcak-soğuk içecekler ve tatlılar arasından adet seçer, özel sipariş notunu yazar ve anında siparişi onaylar.",
        "Menüden dilediği ürünleri seçer, sipariş notunu ekler ve tek dokunuşla siparişini mutfağa gönderir.",
    )
    x0, y0, x1, y1 = 1090, 195, 1760, 795
    draw.rounded_rectangle([x0, y0, x1, y1], radius=40, fill=(250, 247, 242), outline=(30, 41, 59), width=8)
    draw.rounded_rectangle([x0 + 8, y0 + 8, x1 - 8, y0 + 92], radius=32, fill=(41, 32, 27))
    draw.text((x0 + 34, y0 + 32), "Artisan Kafe Menü", font=FONT_CARD_BOLD, fill=(255, 255, 255))
    draw.rounded_rectangle([x1 - 190, y0 + 24, x1 - 28, y0 + 76], radius=24, fill=(245, 158, 11))
    draw.text((x1 - 165, y0 + 34), "Masa 4", font=FONT_CARD_BOLD, fill=(28, 19, 14))

    # Ürün 1
    draw.rounded_rectangle([x0 + 30, y0 + 120, x1 - 30, y0 + 215], radius=18, fill=(255, 255, 255), outline=(231, 224, 214), width=2)
    draw.text((x0 + 52, y0 + 150), "Caffe Latte  (110 TL)", font=FONT_CARD_BOLD, fill=(31, 26, 23))
    draw.rounded_rectangle([x1 - 180, y0 + 142, x1 - 52, y0 + 194], radius=14, fill=(180, 83, 9))
    draw.text((x1 - 158, y0 + 152), "2 Adet", font=FONT_CARD_BOLD, fill=(255, 255, 255))

    # Ürün 2
    draw.rounded_rectangle([x0 + 30, y0 + 235, x1 - 30, y0 + 330], radius=18, fill=(255, 255, 255), outline=(231, 224, 214), width=2)
    draw.text((x0 + 52, y0 + 265), "San Sebastian  (165 TL)", font=FONT_CARD_BOLD, fill=(31, 26, 23))
    draw.rounded_rectangle([x1 - 180, y0 + 257, x1 - 52, y0 + 309], radius=14, fill=(180, 83, 9))
    draw.text((x1 - 158, y0 + 267), "1 Adet", font=FONT_CARD_BOLD, fill=(255, 255, 255))

    # Sipariş Notu
    draw.rounded_rectangle([x0 + 30, y0 + 355, x1 - 30, y0 + 440], radius=16, fill=(254, 243, 199), outline=(245, 158, 11), width=2)
    draw.text((x0 + 52, y0 + 382), "Not: Bir latte yulaf sütlü olsun", font=FONT_CARD, fill=(120, 53, 15))

    # Gönder Butonu
    draw.rounded_rectangle([x0 + 30, y0 + 470, x1 - 30, y0 + 560], radius=20, fill=(21, 128, 61))
    draw.text((x0 + 135, y0 + 498), "Siparişi Gönder (385 TL) →", font=FONT_CARD_TITLE, fill=(255, 255, 255))

    path = os.path.join(FRAMES_DIR, "scene2.png")
    img.save(path)
    return path


def make_scene_3():
    img, draw = draw_base(
        2,
        "3. Adım • Anında Bildirim",
        "Çalışanlar Hangi Masanın",
        "Ne İstediğini Anında Görür!",
        "Sipariş verildiği anda çalışan ekranında sesli uyarı çalar. Hangi masanın sipariş verdiği, ürünler ve not ekrana düşer.",
        "Kafe çalışanları, sesli bildirimle hangi masanın ne sipariş ettiğini ve özel notunu saniyesinde ekranda görür.",
    )
    x0, y0, x1, y1 = 1040, 210, 1800, 780
    draw.rounded_rectangle([x0, y0, x1, y1], radius=30, fill=(15, 23, 42), outline=(245, 158, 11), width=5)
    draw.rounded_rectangle([x0 + 34, y0 + 32, x0 + 260, y0 + 100], radius=16, fill=(245, 158, 11))
    draw.text((x0 + 62, y0 + 48), "MASA 4", font=FONT_CARD_TITLE, fill=(15, 23, 42))
    draw.text((x1 - 310, y0 + 52), "• Yeni Sipariş Geldi!", font=FONT_CARD_BOLD, fill=(252, 211, 77))

    draw.line([(x0 + 34, y0 + 128), (x1 - 34, y0 + 128)], fill=(51, 65, 85), width=2)
    draw.text((x0 + 40, y0 + 155), "2x  Caffe Latte", font=FONT_CARD_BOLD, fill=(248, 250, 252))
    draw.text((x1 - 160, y0 + 155), "220 TL", font=FONT_CARD_BOLD, fill=(248, 250, 252))

    draw.text((x0 + 40, y0 + 215), "1x  San Sebastian Cheesecake", font=FONT_CARD_BOLD, fill=(248, 250, 252))
    draw.text((x1 - 160, y0 + 215), "165 TL", font=FONT_CARD_BOLD, fill=(248, 250, 252))
    draw.line([(x0 + 34, y0 + 275), (x1 - 34, y0 + 275)], fill=(51, 65, 85), width=2)

    draw.rounded_rectangle([x0 + 34, y0 + 300, x1 - 34, y0 + 375], radius=14, fill=(68, 44, 14), outline=(245, 158, 11), width=2)
    draw.text((x0 + 54, y0 + 322), "Müşteri Notu: Bir latte yulaf sütlü olsun", font=FONT_CARD, fill=(253, 230, 138))

    draw.rounded_rectangle([x0 + 34, y0 + 415, x1 - 34, y0 + 515], radius=18, fill=(56, 189, 248))
    draw.text((x0 + 190, y0 + 448), "Hazırlanıyor Olarak İşaretle", font=FONT_CARD_BOLD, fill=(15, 23, 42))

    path = os.path.join(FRAMES_DIR, "scene3.png")
    img.save(path)
    return path


def make_scene_4():
    img, draw = draw_base(
        3,
        "4. Adım • Tek Tıkla Servis",
        "Sipariş Hazır Olduğunda",
        "'Tamamla' Tuşuna Basılır.",
        "Barista veya garson ürünleri masaya servis ettiğinde çalışan ekranından Tamamla (Hesabı Göster) butonuna dokunur.",
        "Ürünler hazırlandığında çalışan tek tuşla siparişi tamamlandı olarak işaretler.",
    )
    x0, y0, x1, y1 = 1040, 210, 1800, 780
    draw.rounded_rectangle([x0, y0, x1, y1], radius=30, fill=(15, 23, 42), outline=(34, 197, 94), width=5)
    draw.rounded_rectangle([x0 + 34, y0 + 32, x0 + 280, y0 + 100], radius=16, fill=(34, 197, 94))
    draw.text((x0 + 56, y0 + 48), "✓ MASA 4", font=FONT_CARD_TITLE, fill=(5, 46, 22))
    draw.text((x1 - 310, y0 + 52), "Servis Tamamlandı", font=FONT_CARD_BOLD, fill=(74, 222, 128))

    draw.line([(x0 + 34, y0 + 128), (x1 - 34, y0 + 128)], fill=(51, 65, 85), width=2)
    draw.text((x0 + 40, y0 + 155), "2x  Caffe Latte", font=FONT_CARD_BOLD, fill=(248, 250, 252))
    draw.text((x1 - 160, y0 + 155), "220 TL", font=FONT_CARD_BOLD, fill=(248, 250, 252))

    draw.text((x0 + 40, y0 + 215), "1x  San Sebastian Cheesecake", font=FONT_CARD_BOLD, fill=(248, 250, 252))
    draw.text((x1 - 160, y0 + 215), "165 TL", font=FONT_CARD_BOLD, fill=(248, 250, 252))
    draw.line([(x0 + 34, y0 + 275), (x1 - 34, y0 + 275)], fill=(51, 65, 85), width=2)

    draw.text((x0 + 40, y0 + 315), "Masa Toplam Hesabı:", font=FONT_CARD_TITLE, fill=(255, 255, 255))
    draw.text((x1 - 210, y0 + 308), "385 TL", font=FONT_H1, fill=(74, 222, 128))

    draw.rounded_rectangle([x0 + 34, y0 + 415, x1 - 34, y0 + 515], radius=18, fill=(34, 197, 94))
    draw.text((x0 + 115, y0 + 448), "✓ Tamamlandı • Hesap Müşteride Açık", font=FONT_CARD_BOLD, fill=(5, 46, 22))

    path = os.path.join(FRAMES_DIR, "scene4.png")
    img.save(path)
    return path


def make_scene_5():
    img, draw = draw_base(
        4,
        "5. Adım • Şeffaf Hesap",
        "Müşteri Kendi Ekranında",
        "Ödeyeceği Hesabı Anında Görür!",
        "Sipariş tamamlandığı anda müşterinin telefonunda yeşil onay kutusu açılır ve masanın toplam ödenecek hesap tutarı gösterilir.",
        "Ve sipariş tamamlandığı anda müşteriniz, kendi telefonunda ödeyeceği toplam hesap tutarını şeffafça görür!",
    )
    x0, y0, x1, y1 = 1090, 195, 1760, 795
    draw.rounded_rectangle([x0, y0, x1, y1], radius=40, fill=(250, 247, 242), outline=(30, 41, 59), width=8)
    draw.rounded_rectangle([x0 + 8, y0 + 8, x1 - 8, y0 + 92], radius=32, fill=(41, 32, 27))
    draw.text((x0 + 34, y0 + 32), "Artisan Kafe Canlı Hesap", font=FONT_CARD_BOLD, fill=(255, 255, 255))
    draw.rounded_rectangle([x1 - 190, y0 + 24, x1 - 28, y0 + 76], radius=24, fill=(245, 158, 11))
    draw.text((x1 - 165, y0 + 34), "Masa 4", font=FONT_CARD_BOLD, fill=(28, 19, 14))

    # Yeşil Toplam Hesap Kutusu
    draw.rounded_rectangle([x0 + 30, y0 + 120, x1 - 30, y0 + 330], radius=22, fill=(220, 252, 231), outline=(34, 197, 94), width=4)
    draw.text((x0 + 54, y0 + 142), "✓ TÜM SİPARİŞLERİNİZ TAMAMLANDI", font=FONT_CARD_BOLD, fill=(20, 83, 45))
    draw.text((x0 + 54, y0 + 186), "Masada ödenecek toplam hesap tutarınız:", font=FONT_CARD, fill=(21, 128, 61))
    draw.text((x0 + 54, y0 + 232), "385 TL", font=FONT_BIG_PRICE, fill=(20, 83, 45))

    # Kalemler
    draw.rounded_rectangle([x0 + 30, y0 + 355, x1 - 30, y0 + 440], radius=16, fill=(255, 255, 255), outline=(231, 224, 214), width=2)
    draw.text((x0 + 52, y0 + 382), "2x Caffe Latte", font=FONT_CARD_BOLD, fill=(31, 26, 23))
    draw.text((x1 - 165, y0 + 382), "220 TL", font=FONT_CARD_BOLD, fill=(31, 26, 23))

    draw.rounded_rectangle([x0 + 30, y0 + 455, x1 - 30, y0 + 540], radius=16, fill=(255, 255, 255), outline=(231, 224, 214), width=2)
    draw.text((x0 + 52, y0 + 482), "1x San Sebastian Cheesecake", font=FONT_CARD_BOLD, fill=(31, 26, 23))
    draw.text((x1 - 165, y0 + 482), "165 TL", font=FONT_CARD_BOLD, fill=(31, 26, 23))

    path = os.path.join(FRAMES_DIR, "scene5.png")
    img.save(path)
    return path


def get_audio_duration(path: str) -> float:
    out = subprocess.check_output(["afinfo", path], text=True)
    for line in out.splitlines():
        if "estimated duration:" in line:
            return float(line.split("estimated duration:")[1].split()[0])
    return 7.0


def build_video():
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    scenes = [
        (make_scene_1(), os.path.join(AUDIO_DIR, "sahne1.mp3")),
        (make_scene_2(), os.path.join(AUDIO_DIR, "sahne2.mp3")),
        (make_scene_3(), os.path.join(AUDIO_DIR, "sahne3.mp3")),
        (make_scene_4(), os.path.join(AUDIO_DIR, "sahne4.mp3")),
        (make_scene_5(), os.path.join(AUDIO_DIR, "sahne5.mp3")),
    ]

    seg_paths = []
    for i, (img_path, mp3_path) in enumerate(scenes, start=1):
        voice_dur = get_audio_duration(mp3_path)
        total_dur = round(voice_dur + PAUSE_SEC, 2)
        seg_out = os.path.join(FRAMES_DIR, f"seg_{i}.mp4")
        # apad filtresiyle sesin sonuna 1.8 sn gerçek sessizlik eklenir
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
        print(f"Sahne {i} hazır: konuşma={voice_dur:.2f}s + boşluk={PAUSE_SEC}s -> toplam={total_dur:.2f}s")
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
    print(f"\n✅ MP4 oluşturuldu: {OUTPUT_MP4} ({os.path.getsize(OUTPUT_MP4) // 1024} KB)")


if __name__ == "__main__":
    build_video()

