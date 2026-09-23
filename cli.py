#!/usr/bin/env python3
"""
CLI Tool for Batch Watermarking
1000 ta va undan ortiq rasmlarga bir necha soniyada watermark qo'yish terminal vositasi.
"""

import os
import sys
import argparse
import time
from pathlib import Path
from watermark_engine import (
    run_batch_watermark,
    scan_images,
    apply_text_watermark,
    apply_image_watermark
)
from PIL import Image

def draw_progress_bar(current: int, total: int, prefix: str = "", length: int = 30):
    percent = float(current) / max(1, total)
    filled = int(length * percent)
    bar = "█" * filled + "░" * (length - filled)
    sys.stdout.write(f"\r{prefix} |{bar}| {current}/{total} ({percent*100:.1f}%)")
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")

def interactive_wizard():
    print("\n" + "=" * 55)
    print(" 🌊 1000 TA RASMGA WATERMARK QO'YISH YORDAMCHISI")
    print("=" * 55)

    # 1. Input folder
    while True:
        inp = input("\n📂 Rasmlar turgan papka yo'lini kiriting (masalan: ./images yoki to'liq yo'l):\n> ").strip()
        # Remove quotes if user dragged and dropped folder in terminal
        inp = inp.strip("\"'")
        if not inp:
            inp = os.getcwd()
        if os.path.exists(inp) and os.path.isdir(inp):
            imgs = scan_images(inp)
            if not imgs:
                print(f"⚠️ Bu papkada qo'llab-quvvatlanadigan rasm fayllari topilmadi. Boshqa papka kiriting.")
                continue
            print(f"✅ Topildi: {len(imgs)} ta rasm")
            input_folder = inp
            break
        else:
            print(f"❌ Bunday papka topilmadi: {inp}")

    # 2. Watermark mode
    print("\n💧 Suv belgisi (Watermark) turini tanlang:")
    print("  [1] Matn (Text) — masalan brend nomi, @kanal_nomi yoki telefon raqam")
    print("  [2] Logo (PNG rasm) — tayyor shaffof logo tasviri")
    mode_choice = input("Tanlov (1 yoki 2) [default: 1]: ").strip() or "1"
    mode = "image" if mode_choice == "2" else "text"

    logo_path = None
    text_content = "WATERMARK"
    if mode == "image":
        while True:
            l_path = input("\n🖼 Logo faylining yo'lini kiriting (PNG/JPG):\n> ").strip().strip("\"'")
            if os.path.exists(l_path) and os.path.isfile(l_path):
                logo_path = l_path
                print(f"✅ Logo tanlandi: {logo_path}")
                break
            else:
                print(f"❌ Logo fayli topilmadi: {l_path}")
    else:
        text_content = input("\n✍️ Qanday matn yozilsin? [default: @brend_nomi]: ").strip() or "@brend_nomi"

    # 3. Position
    print("\n📍 Joylashuvni tanlang:")
    print("  [1] Butun rasm bo'ylab diagonal (Edu360 uslubi) — 🔥 Tavsiya etiladi")
    print("  [2] Pastki o'ng burchakda (bottom-right)")
    print("  [3] Markazda (center)")
    print("  [4] Pastki chap burchakda (bottom-left)")
    print("  [5] Yuqori o'ng burchakda (top-right)")
    print("  [6] Shaxmat takrorlanuvchi (Tiled)")
    pos_choice = input("Tanlov (1-6) [default: 1]: ").strip() or "1"
    pos_map = {
        "1": "diagonal-grid",
        "2": "bottom-right",
        "3": "center",
        "4": "bottom-left",
        "5": "top-right",
        "6": "tiled"
    }
    position = pos_map.get(pos_choice, "diagonal-grid")

    # 4. Opacity
    default_op = "38%" if position == "diagonal-grid" else "70%"
    opacity_input = input(f"\n👓 Shaffoflik darajasi (10% dan 100% gacha) [default: {default_op}]: ").strip()
    try:
        opacity_val = float(opacity_input.replace("%", "")) / 100.0 if opacity_input else (0.38 if position == "diagonal-grid" else 0.7)
        opacity_val = max(0.1, min(1.0, opacity_val))
    except Exception:
        opacity_val = 0.38 if position == "diagonal-grid" else 0.7

    # 5. Output folder
    default_out = os.path.join(input_folder, "watermarked_output")
    out_input = input(f"\n💾 Natijalar qaysi papkaga saqlansin? [default: {default_out}]:\n> ").strip().strip("\"'")
    output_folder = out_input if out_input else default_out

    # Confirmation
    print("\n" + "-" * 55)
    print(f"🚀 Boshlashga tayyormisiz?")
    print(f"  - Manba papka: {input_folder}")
    print(f"  - Rejim: {mode.upper()} ({text_content if mode=='text' else logo_path})")
    print(f"  - Joylashuv: {position} ({'Edu360 diagonal panjara' if position == 'diagonal-grid' else position})")
    print(f"  - Shaffoflik: {int(opacity_val * 100)}%")
    print(f"  - Natija papkasi: {output_folder}")
    print("-" * 55)
    
    confirm = input("Ishga tushirish uchun [Enter] bosing (yoki bekor qilish uchun 'n'): ").strip().lower()
    if confirm == 'n':
        print("Bekor qilindi.")
        sys.exit(0)

    # Run
    is_grid = position in ("diagonal-grid", "edu360")
    params = {
        "text": text_content,
        "position": position,
        "opacity": opacity_val,
        "scale": 0.040 if is_grid else (0.05 if mode == "text" else 0.20),
        "color": "#ffffff",
        "stroke_color": "#000000",
        "stroke_width": 0 if is_grid else 2,
        "angle": 12 if is_grid else (-30 if position == "tiled" else 0),
        "density": 1.0,
        "stagger": False if is_grid else (True if position == "tiled" else None)
    }

    start_batch_cli(input_folder, output_folder, mode, params, logo_path)


def start_batch_cli(input_folder, output_folder, mode, params, logo_path=None):
    images = scan_images(input_folder)
    total = len(images)
    print(f"\n⚡ Jarayon boshlandi: {total} ta rasm 8 ta parallel oqimda qayta ishlanmoqda...\n")

    start_time = time.time()
    last_update = [0]

    def on_progress(done, tot, current_file):
        # Update progress bar smoothly
        draw_progress_bar(done, tot, prefix="⏳ Ishlanmoqda")

    res = run_batch_watermark(
        input_folder=input_folder,
        output_folder=output_folder,
        mode=mode,
        params=params,
        logo_path=logo_path,
        progress_callback=on_progress
    )

    print("\n" + "=" * 55)
    print(f"🎉 MUVAFFAQIYATLI YAKUNLANDI!")
    print(f"  - Jami rasmlar: {res['total']} ta")
    print(f"  - Muvaffaqiyatli: {res['processed']} ta")
    print(f"  - Xatolar: {res['failed']} ta")
    print(f"  - Sarflangan vaqt: {res['time_seconds']} soniya")
    print(f"  - Tezlik: {res['speed_per_sec']} rasm/sekund")
    print(f"  - Natijalar papkasi: {output_folder}")
    print("=" * 55)

    if sys.platform == "darwin":
        print(f"\n💡 Papkani ochish uchun buyruq: open \"{output_folder}\"")


def main():
    parser = argparse.ArgumentParser(description="1000 ta rasmga tezkor watermark qo'yuvchi vosita")
    parser.add_argument("-i", "--input", help="Rasmlar joylashgan papka yo'li")
    parser.add_argument("-o", "--output", help="Natijaviy rasmlar saqlanadigan papka")
    parser.add_argument("-m", "--mode", choices=["text", "image"], default="text", help="Watermark turi (text yoki image)")
    parser.add_argument("-t", "--text", default="@brend_nomi", help="Matnli watermark uchun matn")
    parser.add_argument("-l", "--logo", help="Logo rasm fayli yo'li (PNG/JPG)")
    parser.add_argument("-p", "--position", default="bottom-right",
                        choices=["bottom-right", "bottom-left", "top-right", "top-left", "center", "tiled"],
                        help="Watermark joylashuvi")
    parser.add_argument("--opacity", type=float, default=0.7, help="Shaffoflik (0.1 dan 1.0 gacha)")
    parser.add_argument("--scale", type=float, default=None, help="Masshtab (0.02 - 0.50)")
    parser.add_argument("--color", default="#ffffff", help="Matn rangi (masalan #ffffff)")
    parser.add_argument("--angle", type=int, default=0, help="Aylanish burchagi")

    args = parser.parse_args()

    # If no input directory passed, start interactive wizard
    if not args.input:
        interactive_wizard()
        return

    # Direct CLI execution
    input_folder = os.path.abspath(args.input)
    if not os.path.exists(input_folder):
        print(f"❌ Xato: Bunday papka topilmadi: {input_folder}")
        sys.exit(1)

    output_folder = os.path.abspath(args.output) if args.output else os.path.join(input_folder, "watermarked_output")

    scale = args.scale
    if scale is None:
        scale = 0.20 if args.mode == "image" else 0.05

    params = {
        "text": args.text,
        "position": args.position,
        "opacity": max(0.05, min(1.0, args.opacity)),
        "scale": scale,
        "color": args.color,
        "stroke_color": "#000000",
        "stroke_width": 2,
        "angle": args.angle if args.angle != 0 else (-30 if args.position == "tiled" else 0)
    }

    start_batch_cli(input_folder, output_folder, args.mode, params, args.logo)

if __name__ == "__main__":
    main()
