#!/usr/bin/env python3
"""
Local Web Dashboard Server for Batch Watermarker.
Powered by Python standard library (http.server).
Provides real-time preview, folder scanning, file upload, and multi-core batch processing.
"""

import os
import sys
import re
import json
import time
import io
import uuid
import shutil
import zipfile
import urllib.parse
import threading
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image, ImageOps

from watermark_engine import (
    scan_images,
    run_batch_watermark,
    apply_text_watermark,
    apply_image_watermark,
    fit_image_to_canvas
)

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 7860))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Global batch processing state
batch_state = {
    "is_running": False,
    "total": 0,
    "processed": 0,
    "failed": 0,
    "current_file": "",
    "time_seconds": 0,
    "speed": 0,
    "output_folder": "",
    "errors": []
}
batch_lock = threading.Lock()

class WatermarkHandler(BaseHTTPRequestHandler):
    def end_headers_with_cors(self, content_type="application/json"):
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers_with_cors()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Static files
        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(WEB_DIR, "index.html"), "text/html; charset=utf-8")
        elif path == "/style.css":
            self.serve_file(os.path.join(WEB_DIR, "style.css"), "text/css; charset=utf-8")
        elif path == "/app.js":
            self.serve_file(os.path.join(WEB_DIR, "app.js"), "application/javascript; charset=utf-8")

        # API: Scan Folder
        elif path == "/api/scan":
            folder = query.get("folder", [""])[0]
            if not folder:
                folder = BASE_DIR
            folder = os.path.expanduser(folder)

            if os.path.exists(folder) and os.path.isdir(folder):
                images = scan_images(folder)
                self.send_response(200)
                self.end_headers_with_cors()
                self.wfile.write(json.dumps({
                    "success": True,
                    "folder": folder,
                    "count": len(images),
                    "samples": images[:10]
                }).encode("utf-8"))
            else:
                self.send_response(200)
                self.end_headers_with_cors()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Papka topilmadi"
                }).encode("utf-8"))

        # API: Live Preview
        elif path == "/api/preview":
            img_path = query.get("file", [""])[0]
            mode = query.get("mode", ["text"])[0]
            pos = query.get("position", ["bottom-right"])[0]
            opacity = float(query.get("opacity", [0.7])[0])
            scale = float(query.get("scale", [0.05])[0])
            color = query.get("color", ["#ffffff"])[0]
            text = query.get("text", ["@brend_nomi"])[0]
            angle = int(query.get("angle", [0])[0])
            logo_path = query.get("logo", [""])[0]

            density = float(query.get("density", [1.0])[0])
            stagger_raw = query.get("stagger", ["auto"])[0]
            stagger = None if stagger_raw == "auto" else (stagger_raw in ("1", "true", "True"))
            stroke_width = int(query.get("stroke_width", [0])[0])
            stroke_color = query.get("stroke_color", ["#000000"])[0]

            # Canvas Frame & Scaling parameters
            canvas_enabled = query.get("canvas_enabled", ["0"])[0] in ("1", "true", "True")
            canvas_w = int(query.get("canvas_w", [1570])[0])
            canvas_h = int(query.get("canvas_h", [1002])[0])
            canvas_zoom = float(query.get("canvas_zoom", [1.0])[0])
            canvas_mode = query.get("canvas_mode", ["fit"])[0]
            canvas_bg = query.get("canvas_bg", ["#000000"])[0]
            border_width = int(query.get("border_width", [1])[0])
            border_color = query.get("border_color", ["#ffffff"])[0]

            if not os.path.exists(img_path):
                self.send_error(404, "Preview image file not found")
                return

            try:
                with Image.open(img_path) as raw:
                    img = ImageOps.exif_transpose(raw)

                    # If canvas frame is enabled, fit/scale image onto 1570x1002 canvas first
                    if canvas_enabled:
                        img = fit_image_to_canvas(
                            img=img,
                            target_w=canvas_w,
                            target_h=canvas_h,
                            scale_mode=canvas_mode,
                            zoom=canvas_zoom,
                            bg_color=canvas_bg,
                            border_width=border_width,
                            border_color=border_color
                        )

                    # Downscale for super snappy web preview
                    max_preview_dim = 1600
                    if max(img.size) > max_preview_dim:
                        img.thumbnail((max_preview_dim, max_preview_dim), Image.Resampling.LANCZOS)

                    if mode == "image" and logo_path and os.path.exists(logo_path):
                        with Image.open(logo_path) as l_img:
                            res = apply_image_watermark(
                                img=img,
                                logo_img=l_img,
                                position=pos,
                                opacity=opacity,
                                scale=scale,
                                angle=angle,
                                density=density,
                                stagger=stagger
                            )
                    else:
                        res = apply_text_watermark(
                            img=img,
                            text=text,
                            position=pos,
                            opacity=opacity,
                            scale=scale,
                            color=color,
                            stroke_color=stroke_color,
                            stroke_width=stroke_width,
                            angle=angle,
                            density=density,
                            stagger=stagger
                        )

                    if res.mode != "RGB":
                        res = res.convert("RGB")

                    buf = io.BytesIO()
                    res.save(buf, format="JPEG", quality=85)
                    buf.seek(0)
                    img_bytes = buf.read()

                    self.send_response(200)
                    self.end_headers_with_cors("image/jpeg")
                    self.wfile.write(img_bytes)
            except Exception as e:
                self.send_error(500, f"Preview generation error: {str(e)}")

        # API: Batch Status
        elif path == "/api/batch-status":
            with batch_lock:
                data = dict(batch_state)
            self.send_response(200)
            self.end_headers_with_cors()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        # Health Check (Docker / Cloud Platforms)
        elif path == "/health" or path == "/api/health":
            self.send_response(200)
            self.end_headers_with_cors()
            self.wfile.write(json.dumps({
                "status": "healthy",
                "service": "batch-watermark-studio",
                "time": time.time()
            }).encode("utf-8"))

        # API: Download Output as ZIP
        elif path == "/api/download-zip":
            folder = query.get("folder", [""])[0]
            if not folder:
                with batch_lock:
                    folder = batch_state.get("output_folder", "")
            if not folder:
                folder = os.path.join(BASE_DIR, "watermarked_output")
            folder = os.path.expanduser(folder)

            if not os.path.exists(folder) or not os.path.isdir(folder):
                self.send_error(404, "Natijalar papkasi topilmadi")
                return

            images = scan_images(folder)
            if not images:
                self.send_error(404, "Papkada suv belgisi qo'yilgan rasmlar mavjud emas")
                return

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for img_path in images:
                    arcname = os.path.basename(img_path)
                    zip_file.write(img_path, arcname=arcname)

            zip_bytes = zip_buffer.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", 'attachment; filename="watermarked_images.zip"')
            self.send_header("Content-Length", str(len(zip_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(zip_bytes)

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # API: Upload Logo
        if path == "/api/upload-logo":
            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            # Simple file save for PNG/JPG logo
            logo_save_path = os.path.join(UPLOADS_DIR, f"watermark_logo_{int(time.time())}.png")
            
            # Check if multipart or raw bytes
            if "multipart/form-data" in content_type:
                # Find boundary
                boundary = content_type.split("boundary=")[-1].split(";")[0].strip('"\r\n ').encode()
                parts = body.split(b"--" + boundary)
                saved = False
                for p in parts:
                    if b"filename=" in p and b"\r\n\r\n" in p:
                        header, file_data = p.split(b"\r\n\r\n", 1)
                        file_data = file_data.rsplit(b"\r\n", 1)[0]
                        with open(logo_save_path, "wb") as f:
                            f.write(file_data)
                        saved = True
                        break
                if not saved:
                    with open(logo_save_path, "wb") as f:
                        f.write(body)
            else:
                with open(logo_save_path, "wb") as f:
                    f.write(body)

            self.send_response(200)
            self.end_headers_with_cors()
            self.wfile.write(json.dumps({
                "success": True,
                "logo_path": logo_save_path
            }).encode("utf-8"))

        # API: Start Batch Processing
        elif path == "/api/batch-start":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            input_folder = os.path.expanduser(data.get("input_folder", ""))
            output_folder = os.path.expanduser(data.get("output_folder", ""))
            if not output_folder:
                output_folder = os.path.join(input_folder, "watermarked_output")

            mode = data.get("mode", "text")
            params = data.get("params", {})
            logo_path = data.get("logo_path")

            with batch_lock:
                if batch_state["is_running"]:
                    self.send_response(400)
                    self.end_headers_with_cors()
                    self.wfile.write(json.dumps({"error": "Jarayon allaqachon bajarilmoqda"}).encode("utf-8"))
                    return

                batch_state["is_running"] = True
                batch_state["total"] = len(scan_images(input_folder))
                batch_state["processed"] = 0
                batch_state["failed"] = 0
                batch_state["output_folder"] = output_folder
                batch_state["errors"] = []
                batch_state["time_seconds"] = 0
                batch_state["speed"] = 0

            # Run in background thread
            def worker():
                def progress(done, total, cur_file):
                    with batch_lock:
                        batch_state["processed"] = done
                        batch_state["total"] = total
                        batch_state["current_file"] = os.path.basename(cur_file)

                res = run_batch_watermark(
                    input_folder=input_folder,
                    output_folder=output_folder,
                    mode=mode,
                    params=params,
                    logo_path=logo_path,
                    progress_callback=progress
                )
                with batch_lock:
                    batch_state["is_running"] = False
                    batch_state["processed"] = res["processed"]
                    batch_state["failed"] = res["failed"]
                    batch_state["time_seconds"] = res["time_seconds"]
                    batch_state["speed"] = res["speed_per_sec"]
                    batch_state["errors"] = res["errors"]

            threading.Thread(target=worker, daemon=True).start()

            self.send_response(200)
            self.end_headers_with_cors()
            self.wfile.write(json.dumps({
                "success": True,
                "message": "Batch jarayoni boshlandi"
            }).encode("utf-8"))

        # API: Upload Batch Images or ZIP Archive
        elif path == "/api/upload-batch":
            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            batch_id = f"batch_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            target_folder = os.path.join(UPLOADS_DIR, batch_id)
            os.makedirs(target_folder, exist_ok=True)

            if "multipart/form-data" in content_type:
                boundary = content_type.split("boundary=")[-1].split(";")[0].strip('"\r\n ').encode()
                parts = body.split(b"--" + boundary)
                for p in parts:
                    if b"filename=" in p and b"\r\n\r\n" in p:
                        header, file_data = p.split(b"\r\n\r\n", 1)
                        file_data = file_data.rsplit(b"\r\n", 1)[0]
                        header_str = header.decode("utf-8", errors="ignore")
                        match = re.search(r'filename="?([^"\r\n;]+)"?', header_str)
                        fname = match.group(1).strip() if match else "uploaded_file"
                        
                        fname = os.path.basename(fname)
                        if fname.lower().endswith(".zip"):
                            zip_tmp = os.path.join(target_folder, fname)
                            with open(zip_tmp, "wb") as f:
                                f.write(file_data)
                            try:
                                with zipfile.ZipFile(zip_tmp, "r") as zf:
                                    for member in zf.namelist():
                                        norm_member = os.path.normpath(member)
                                        if norm_member.startswith("..") or norm_member.startswith("/"):
                                            continue
                                        ext = os.path.splitext(norm_member)[1].lower()
                                        if ext in {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}:
                                            filename_only = os.path.basename(norm_member)
                                            if filename_only:
                                                source = zf.open(member)
                                                target_dest = open(os.path.join(target_folder, filename_only), "wb")
                                                with source, target_dest:
                                                    shutil.copyfileobj(source, target_dest)
                            except Exception as ze:
                                print(f"ZIP ochishda xatolik: {ze}")
                            finally:
                                if os.path.exists(zip_tmp):
                                    os.remove(zip_tmp)
                        else:
                            ext = os.path.splitext(fname)[1].lower()
                            if ext in {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}:
                                file_dest = os.path.join(target_folder, fname)
                                with open(file_dest, "wb") as f:
                                    f.write(file_data)

            images = scan_images(target_folder)
            self.send_response(200)
            self.end_headers_with_cors()
            self.wfile.write(json.dumps({
                "success": True,
                "folder": target_folder,
                "count": len(images),
                "samples": images[:10]
            }).encode("utf-8"))

        # API: Open Output Folder in Finder / File Manager (Safe for Headless Servers)
        elif path == "/api/open-folder":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            data = json.loads(body.decode("utf-8")) if body else {}
            target = data.get("folder") or batch_state.get("output_folder")
            if target and os.path.exists(target):
                opened = False
                try:
                    if sys.platform == "darwin":
                        res = subprocess.run(["open", target], capture_output=True, timeout=2)
                        opened = res.returncode == 0
                    elif sys.platform == "win32":
                        os.startfile(target)
                        opened = True
                    else:
                        res = subprocess.run(["xdg-open", target], capture_output=True, timeout=2)
                        opened = res.returncode == 0
                except Exception:
                    opened = False

                self.send_response(200)
                self.end_headers_with_cors()
                self.wfile.write(json.dumps({
                    "success": True,
                    "opened_in_gui": opened,
                    "message": "Papka ochildi" if opened else "Masofaviy serverda GUI yo'q, ZIP yuklab olishdan foydalaning"
                }).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers_with_cors()
                self.wfile.write(json.dumps({"error": "Papka mavjud emas"}).encode("utf-8"))

        else:
            self.send_error(404, "Not Found")

    def serve_file(self, file_path, content_type):
        if not os.path.exists(file_path):
            self.send_error(404, f"File not found: {file_path}")
            return
        with open(file_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.end_headers_with_cors(content_type)
        self.wfile.write(content)

    def log_message(self, format, *args):
        # Clean terminal output
        pass

def run_server(host=HOST, port=PORT):
    server = HTTPServer((host, port), WatermarkHandler)
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    print(f"\n" + "=" * 58)
    print(f" 🚀 WATERMARK WEB BOSHQARUV PANELI ISHGA TUSHDI")
    print(f" 🌐 Host: {host} | Port: {port}")
    print(f" 🔗 Havola: http://{display_host}:{port}")
    print(f"=" * 58 + "\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer to'xtatildi.")

if __name__ == "__main__":
    h = os.environ.get("HOST", "0.0.0.0")
    p = int(os.environ.get("PORT", PORT))
    if len(sys.argv) > 1:
        try:
            p = int(sys.argv[1])
        except ValueError:
            pass
    run_server(host=h, port=p)
