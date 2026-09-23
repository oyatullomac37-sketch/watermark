#!/usr/bin/env python3
"""
Verification script for Deployment Endpoints of Batch Watermark Studio.
Tests /health, /api/scan, /api/upload-batch, and /api/download-zip.
"""

import os
import sys
import time
import json
import zipfile
import io
import urllib.request
import urllib.error
import subprocess

TEST_PORT = 7869
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

def run_tests():
    print(f"🚀 Starting server on port {TEST_PORT} for deployment verification...")
    env = dict(os.environ)
    env["HOST"] = "0.0.0.0"
    env["PORT"] = str(TEST_PORT)
    
    server_proc = subprocess.Popen(
        [sys.executable, "server.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    time.sleep(1.5)
    
    try:
        # 1. Test /health
        print("\n--- Test 1: GET /health ---")
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=5) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("status") == "healthy", f"Invalid response: {data}"
            print("✅ /health passed:", data)

        # 2. Test /api/scan
        print("\n--- Test 2: GET /api/scan ---")
        with urllib.request.urlopen(f"{BASE_URL}/api/scan?folder=test_images", timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("success") is True
            print(f"✅ /api/scan passed: found {data.get('count')} images")

        # 3. Test /api/download-zip
        print("\n--- Test 3: GET /api/download-zip ---")
        with urllib.request.urlopen(f"{BASE_URL}/api/download-zip?folder=test_images", timeout=5) as resp:
            assert resp.status == 200
            assert resp.headers.get("Content-Type") == "application/zip"
            zip_bytes = resp.read()
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                namelist = zf.namelist()
                assert len(namelist) > 0, "ZIP should contain files"
                print(f"✅ /api/download-zip passed: valid ZIP with {len(namelist)} files ({len(zip_bytes)} bytes)")

        # 4. Test /api/upload-batch (Multipart upload with a test image)
        print("\n--- Test 4: POST /api/upload-batch ---")
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        filename = "test_upload_sample.jpg"
        
        # Read a sample test image
        sample_img_path = os.path.join("test_images", os.listdir("test_images")[0])
        with open(sample_img_path, "rb") as f:
            file_content = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode("utf-8") + file_content + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            f"{BASE_URL}/api/upload-batch",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("success") is True
            assert data.get("count") >= 1
            print(f"✅ /api/upload-batch passed: uploaded to {data.get('folder')}, count={data.get('count')}")

        # 5. Test /api/upload-batch with a ZIP archive
        print("\n--- Test 5: POST /api/upload-batch (ZIP archive extraction) ---")
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("img1.jpg", file_content)
            zf.writestr("img2.jpg", file_content)
            zf.writestr("img3.jpg", file_content)
        zip_bytes = zip_buf.getvalue()

        zip_body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="batch_test.zip"\r\n'
            f"Content-Type: application/zip\r\n\r\n"
        ).encode("utf-8") + zip_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req_zip = urllib.request.Request(
            f"{BASE_URL}/api/upload-batch",
            data=zip_body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}"
            }
        )
        with urllib.request.urlopen(req_zip, timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("success") is True
            assert data.get("count") == 3, f"Expected 3 extracted images, got {data.get('count')}"
            print(f"✅ ZIP extraction passed: extracted {data.get('count')} images into {data.get('folder')}")

        print("\n" + "=" * 55)
        print(" 🎉 ALL 5 DEPLOYMENT ENDPOINT TESTS PASSED SUCCESSFULLY!")
        print("=" * 55 + "\n")

    finally:
        server_proc.terminate()
        server_proc.wait(timeout=3)
        print("Server stopped cleanly.")

if __name__ == "__main__":
    run_tests()
