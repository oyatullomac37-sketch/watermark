"""
Test and Verification Suite for Batch Watermark Engine
Generates test images, runs text and logo watermark pipelines,
and benchmarks multiprocessing speed.
"""

import os
import time
import shutil
from PIL import Image, ImageDraw
from watermark_engine import (
    run_batch_watermark,
    apply_text_watermark,
    apply_image_watermark,
    scan_images
)

TEST_DIR = os.path.join(os.path.dirname(__file__), "test_images")
TEST_OUTPUT = os.path.join(os.path.dirname(__file__), "test_output")
TEST_LOGO = os.path.join(os.path.dirname(__file__), "test_logo.png")

def create_synthetic_data(count: int = 50):
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR, exist_ok=True)

    print(f"Creating {count} synthetic test images...")
    resolutions = [
        (1280, 720),
        (1920, 1080),
        (800, 1200),
        (1024, 1024),
        (640, 480)
    ]

    for i in range(count):
        w, h = resolutions[i % len(resolutions)]
        # Create gradient or patterned image
        img = Image.new("RGB", (w, h), color=(30 + (i * 4) % 180, 50 + (i * 3) % 150, 80 + (i * 5) % 150))
        draw = ImageDraw.Draw(img)
        # Draw some geometric shapes
        draw.rectangle([w // 4, h // 4, 3 * w // 4, 3 * h // 4], outline=(255, 255, 255), width=4)
        draw.text((w // 3, h // 2), f"Test Photo #{i+1}", fill=(240, 240, 240))
        
        filename = f"sample_{i+1:03d}.jpg"
        img.save(os.path.join(TEST_DIR, filename), quality=90)

    # Create transparent PNG logo
    logo = Image.new("RGBA", (400, 120), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(logo)
    ldraw.rounded_rectangle([0, 0, 399, 119], radius=20, fill=(30, 41, 59, 230), outline=(59, 130, 246, 255), width=3)
    ldraw.text((40, 45), "⚡ WATERMARK LOGO", fill=(255, 255, 255, 255))
    logo.save(TEST_LOGO)
    print("Test logo created.")

def run_tests():
    create_synthetic_data(50)

    print("\n--- Test 1: Text Watermark Batch (50 images) ---")
    if os.path.exists(TEST_OUTPUT):
        shutil.rmtree(TEST_OUTPUT)

    res1 = run_batch_watermark(
        input_folder=TEST_DIR,
        output_folder=TEST_OUTPUT,
        mode="text",
        params={
            "text": "@brend_nomi",
            "position": "bottom-right",
            "opacity": 0.75,
            "scale": 0.05,
            "color": "#ffffff",
            "stroke_color": "#000000"
        }
    )
    print(f"Results: Total={res1['total']}, Processed={res1['processed']}, Failed={res1['failed']}")
    print(f"Elapsed: {res1['time_seconds']}s | Speed: {res1['speed_per_sec']} images/sec")
    assert res1['processed'] == 50, f"Expected 50 processed, got {res1['processed']}"
    assert res1['failed'] == 0, f"Expected 0 failed, got {res1['failed']}"

    print("\n--- Test 2: Logo Watermark Batch (50 images) ---")
    logo_out = os.path.join(TEST_OUTPUT, "logo_run")
    res2 = run_batch_watermark(
        input_folder=TEST_DIR,
        output_folder=logo_out,
        mode="image",
        logo_path=TEST_LOGO,
        params={
            "position": "bottom-right",
            "opacity": 0.8,
            "scale": 0.22
        }
    )
    print(f"Results: Total={res2['total']}, Processed={res2['processed']}, Failed={res2['failed']}")
    print(f"Elapsed: {res2['time_seconds']}s | Speed: {res2['speed_per_sec']} images/sec")
    assert res2['processed'] == 50
    assert res2['failed'] == 0

    print("\n--- Test 3: Tiled (Pattern) Watermark Test ---")
    tiled_out = os.path.join(TEST_OUTPUT, "tiled_run")
    res3 = run_batch_watermark(
        input_folder=TEST_DIR,
        output_folder=tiled_out,
        mode="text",
        params={
            "text": "MAXFIY / CONFIDENTIAL",
            "position": "tiled",
            "opacity": 0.25,
            "scale": 0.04,
            "angle": -30
        }
    )
    print(f"Tiled Results: Processed={res3['processed']}, Speed={res3['speed_per_sec']} images/sec")
    assert res3['processed'] == 50

    print("\n--- Test 4: Edu360 Diagonal Grid Batch Test ---")
    edu360_out = os.path.join(TEST_OUTPUT, "edu360_run")
    res4 = run_batch_watermark(
        input_folder=TEST_DIR,
        output_folder=edu360_out,
        mode="text",
        params={
            "text": "www.edu360.uz",
            "position": "diagonal-grid",
            "opacity": 0.38,
            "scale": 0.040,
            "angle": 12,
            "density": 1.0,
            "stagger": False,
            "color": "#ffffff",
            "stroke_width": 0
        }
    )
    print(f"Edu360 Results: Processed={res4['processed']}, Speed={res4['speed_per_sec']} images/sec")
    assert res4['processed'] == 50
    assert res4['failed'] == 0

    print("\n--- Test 5: 1570x1002 Canvas Frame + Zoom Batch Test ---")
    canvas_out = os.path.join(TEST_OUTPUT, "canvas_run")
    res5 = run_batch_watermark(
        input_folder=TEST_DIR,
        output_folder=canvas_out,
        mode="text",
        params={
            "text": "www.edu360.uz",
            "position": "diagonal-grid",
            "opacity": 0.38,
            "scale": 0.040,
            "angle": 12,
            "density": 1.0,
            "stagger": False,
            "color": "#ffffff",
            "stroke_width": 0,
            "canvas_enabled": True,
            "canvas_w": 1570,
            "canvas_h": 1002,
            "canvas_mode": "fit",
            "canvas_zoom": 1.15,
            "canvas_bg": "#000000",
            "border_width": 1,
            "border_color": "#ffffff"
        }
    )
    print(f"Canvas Results: Processed={res5['processed']}, Speed={res5['speed_per_sec']} images/sec")
    assert res5['processed'] == 50
    assert res5['failed'] == 0

    # Verify first output image dimensions
    out_sample = os.path.join(canvas_out, "sample_001.jpg")
    with Image.open(out_sample) as check_img:
        assert check_img.size == (1570, 1002), f"Expected (1570, 1002), got {check_img.size}"
        print(f"Verified output image dimensions: {check_img.size}")

    print("\n" + "=" * 50)
    print(" ALL 5 TESTS PASSED PERFECTLY! MULTI-CORE ENGINE IS WORKING.")
    print("=" * 50)

if __name__ == "__main__":
    run_tests()
