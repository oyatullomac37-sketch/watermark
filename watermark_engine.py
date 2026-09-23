"""
Batch Watermark Engine
High-performance, multi-core image watermarking engine using Pillow.
Supports both Text and Image/Logo watermarks, multiple positions,
alpha transparency, tiling, rotation, and EXIF orientation preservation.
"""

import os
import math
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional, Tuple, Dict, Any, Callable
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}

# Common system font paths for macOS / Linux / Windows fallback
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\arial.ttf"
]

def get_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    """Load a truetype font or fallback to default."""
    for font_path in FONT_CANDIDATES:
        if not bold and "Bold" in font_path:
            continue
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def calculate_position(
    base_w: int,
    base_h: int,
    overlay_w: int,
    overlay_h: int,
    position: str = "bottom-right",
    padding: int = 24
) -> Tuple[int, int]:
    """Calculate (x, y) coordinates for an overlay given a position name."""
    pos = position.lower()
    if pos == "center":
        x = (base_w - overlay_w) // 2
        y = (base_h - overlay_h) // 2
    elif pos == "top-left":
        x = padding
        y = padding
    elif pos == "top-right":
        x = base_w - overlay_w - padding
        y = padding
    elif pos == "bottom-left":
        x = padding
        y = base_h - overlay_h - padding
    elif pos == "top-center":
        x = (base_w - overlay_w) // 2
        y = padding
    elif pos == "bottom-center":
        x = (base_w - overlay_w) // 2
        y = base_h - overlay_h - padding
    else:  # default "bottom-right"
        x = base_w - overlay_w - padding
        y = base_h - overlay_h - padding

    # Keep within boundaries
    return max(0, x), max(0, y)


def fit_image_to_canvas(
    img: Image.Image,
    target_w: int = 1570,
    target_h: int = 1002,
    scale_mode: str = "fit",
    zoom: float = 1.0,
    bg_color: str = "#000000",
    border_width: int = 1,
    border_color: str = "#ffffff"
) -> Image.Image:
    """
    Fits, scales (zoom in / zoom out), and centers an input image onto a fixed canvas
    (e.g., 1570x1002) with optional background color and an elegant thin border.
    """
    orig_w, orig_h = img.size

    # Calculate base scale according to mode
    if scale_mode == "cover":
        base_scale = max(target_w / orig_w, target_h / orig_h)
    elif scale_mode == "original":
        base_scale = 1.0
    else:  # default "fit"
        base_scale = min(target_w / orig_w, target_h / orig_h)

    # Apply user zoom multiplier
    effective_scale = max(0.05, base_scale * max(0.1, zoom))

    new_w = max(10, int(orig_w * effective_scale))
    new_h = max(10, int(orig_h * effective_scale))

    # High-quality Lanczos resampling
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Parse background color
    try:
        if bg_color.startswith('#'):
            bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        else:
            bg_rgb = (0, 0, 0)
    except Exception:
        bg_rgb = (0, 0, 0)

    canvas = Image.new("RGBA", (target_w, target_h), (*bg_rgb, 255))

    # Center placement
    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2

    if resized.mode in ("RGBA", "LA") or (resized.mode == "P" and "transparency" in resized.info):
        resized_rgba = resized.convert("RGBA")
        canvas.paste(resized_rgba, (paste_x, paste_y), resized_rgba)
    else:
        canvas.paste(resized.convert("RGB"), (paste_x, paste_y))

    # Draw thin border around the canvas frame if enabled
    if border_width > 0:
        try:
            if border_color and border_color.startswith('#'):
                b_rgb = tuple(int(border_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            else:
                b_rgb = (255, 255, 255)
        except Exception:
            b_rgb = (255, 255, 255)

        draw = ImageDraw.Draw(canvas)
        for offset in range(border_width):
            draw.rectangle(
                [offset, offset, target_w - 1 - offset, target_h - 1 - offset],
                outline=(*b_rgb, 255)
            )

    if img.mode == "RGB":
        return canvas.convert("RGB")
    return canvas


def render_diagonal_grid(
    w: int,
    h: int,
    stamp: Image.Image,
    angle: float = 12.0,
    density: float = 1.0,
    gap_x_mult: float = 0.55,
    gap_y_mult: float = 4.2,
    stagger: bool = False
) -> Image.Image:
    """
    Renders a fast vector-based rotated grid across (w, h)
    matching the professional Edu360 watermark pattern.
    Supports both parallel aligned grid (Edu360) and staggered checkerboard.
    """
    rotated_stamp = stamp.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    rw, rh = rotated_stamp.size
    sw, sh = stamp.size

    # Spacing in the rotated grid frame (scaled by density)
    effective_density = max(0.2, min(3.0, density))
    gap_x = max(10, int(sw * gap_x_mult / effective_density))
    gap_y = max(10, int(sh * gap_y_mult / effective_density))
    step_u = sw + gap_x
    step_v = sh + gap_y

    rad = math.radians(angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    # u direction vector (along line of text, sloping upwards to the right)
    ux = cos_a
    uy = -sin_a
    # v direction vector (perpendicular line, pointing downwards)
    vx = sin_a
    vy = cos_a

    diag = math.hypot(w, h)
    max_u_count = int(diag / max(20, step_u)) + 3
    max_v_count = int(diag / max(20, step_v)) + 3

    cx, cy = w / 2, h / 2
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    for r in range(-max_v_count, max_v_count + 1):
        shift = (step_u / 2) if (stagger and r % 2 != 0) else 0
        v_offset_x = r * step_v * vx
        v_offset_y = r * step_v * vy

        for c in range(-max_u_count, max_u_count + 1):
            u_dist = c * step_u + shift
            px = cx + u_dist * ux + v_offset_x - rw / 2
            py = cy + u_dist * uy + v_offset_y - rh / 2

            if px + rw >= 0 and px <= w and py + rh >= 0 and py <= h:
                layer.paste(rotated_stamp, (int(px), int(py)), rotated_stamp)

    return layer


def apply_text_watermark(
    img: Image.Image,
    text: str,
    position: str = "bottom-right",
    opacity: float = 0.7,
    scale: float = 0.05,
    color: str = "#ffffff",
    stroke_color: str = "#000000",
    stroke_width: int = 0,
    angle: int = 0,
    density: float = 1.0,
    stagger: Optional[bool] = None,
    padding_ratio: float = 0.03
) -> Image.Image:
    """
    Apply a text watermark onto an image.
    Supports single positions, tiled, and diagonal-grid (Edu360 pattern).
    """
    base = img.convert("RGBA")
    w, h = base.size
    min_dim = min(w, h)

    pos_lower = position.lower()
    is_grid = pos_lower in ("diagonal-grid", "edu360", "diagonal")

    # In diagonal-grid, default scale is slightly smaller (cleaner) if not customized
    if is_grid and scale == 0.05:
        scale = 0.040

    font_size = max(12, int(min_dim * scale))
    font = get_font(font_size, bold=True)
    padding = max(10, int(min_dim * padding_ratio))

    # Parse hex color or fallback
    try:
        if color.startswith('#'):
            c_rgb = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        else:
            c_rgb = (255, 255, 255)
    except Exception:
        c_rgb = (255, 255, 255)

    alpha_val = int(255 * max(0.0, min(1.0, opacity)))
    text_rgba = (*c_rgb, alpha_val)

    # Stroke setup (in diagonal-grid, stroke is off by default for clean look)
    actual_stroke_width = stroke_width if stroke_width is not None else (0 if is_grid else 2)
    try:
        if stroke_color and stroke_color.startswith('#'):
            s_rgb = tuple(int(stroke_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        else:
            s_rgb = (0, 0, 0)
    except Exception:
        s_rgb = (0, 0, 0)
    stroke_rgba = (*s_rgb, int(alpha_val * 0.8)) if actual_stroke_width > 0 else None

    # 1. Edu360 Diagonal Grid Pattern
    if is_grid:
        effective_angle = 12 if angle == 0 else angle
        use_stagger = stagger if stagger is not None else False

        dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bbox = dummy_draw.textbbox((0, 0), text, font=font, stroke_width=actual_stroke_width)
        txt_w = bbox[2] - bbox[0]
        txt_h = bbox[3] - bbox[1]

        pad = 4
        stamp = Image.new("RGBA", (txt_w + pad * 2, txt_h + pad * 2), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(stamp)
        sdraw.text(
            (pad - bbox[0], pad - bbox[1]),
            text,
            font=font,
            fill=text_rgba,
            stroke_width=actual_stroke_width,
            stroke_fill=stroke_rgba
        )
        watermark_layer = render_diagonal_grid(
            w=w,
            h=h,
            stamp=stamp,
            angle=effective_angle,
            density=density,
            gap_x_mult=0.55,
            gap_y_mult=4.2,
            stagger=use_stagger
        )

    # 2. Classic Tiled Pattern
    elif pos_lower == "tiled":
        dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bbox = dummy_draw.textbbox((0, 0), text, font=font, stroke_width=actual_stroke_width)
        txt_w = bbox[2] - bbox[0] + 4
        txt_h = bbox[3] - bbox[1] + 4

        stamp = Image.new("RGBA", (txt_w + 30, txt_h + 30), (0, 0, 0, 0))
        stamp_draw = ImageDraw.Draw(stamp)
        stamp_draw.text(
            (15, 15),
            text,
            font=font,
            fill=text_rgba,
            stroke_width=actual_stroke_width,
            stroke_fill=stroke_rgba
        )
        effective_angle = -30 if angle == 0 else angle
        use_stagger = stagger if stagger is not None else True
        watermark_layer = render_diagonal_grid(
            w=w,
            h=h,
            stamp=stamp,
            angle=effective_angle,
            density=density,
            gap_x_mult=1.0,
            gap_y_mult=2.8,
            stagger=use_stagger
        )

    # 3. Single Position
    else:
        watermark_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dummy_draw = ImageDraw.Draw(watermark_layer)
        bbox = dummy_draw.textbbox((0, 0), text, font=font, stroke_width=actual_stroke_width)
        txt_w = bbox[2] - bbox[0]
        txt_h = bbox[3] - bbox[1]

        if angle != 0:
            stamp = Image.new("RGBA", (txt_w + 30, txt_h + 30), (0, 0, 0, 0))
            stamp_draw = ImageDraw.Draw(stamp)
            stamp_draw.text(
                (15, 15),
                text,
                font=font,
                fill=text_rgba,
                stroke_width=actual_stroke_width,
                stroke_fill=stroke_rgba
            )
            rotated = stamp.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
            rw, rh = rotated.size
            x, y = calculate_position(w, h, rw, rh, position, padding)
            watermark_layer.paste(rotated, (x, y), rotated)
        else:
            x, y = calculate_position(w, h, txt_w, txt_h, position, padding)
            draw = ImageDraw.Draw(watermark_layer)
            draw.text(
                (x - bbox[0], y - bbox[1]),
                text,
                font=font,
                fill=text_rgba,
                stroke_width=actual_stroke_width,
                stroke_fill=stroke_rgba
            )

    combined = Image.alpha_composite(base, watermark_layer)

    if img.mode == "RGB":
        return combined.convert("RGB")
    return combined


def apply_image_watermark(
    img: Image.Image,
    logo_img: Image.Image,
    position: str = "bottom-right",
    opacity: float = 0.8,
    scale: float = 0.20,
    angle: int = 0,
    density: float = 1.0,
    stagger: Optional[bool] = None,
    padding_ratio: float = 0.03
) -> Image.Image:
    """
    Apply an image/logo watermark onto a base image.
    Supports single positions, tiled, and diagonal-grid (Edu360 pattern).
    """
    base = img.convert("RGBA")
    w, h = base.size
    min_dim = min(w, h)
    padding = max(10, int(min_dim * padding_ratio))

    pos_lower = position.lower()
    is_grid = pos_lower in ("diagonal-grid", "edu360", "diagonal")

    logo = logo_img.convert("RGBA")

    # In diagonal-grid, logo size is more compact
    if is_grid and scale == 0.20:
        scale = 0.10

    # Resize logo proportionally
    target_w = max(20, int(w * scale))
    aspect = logo.height / logo.width
    target_h = max(20, int(target_w * aspect))
    logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Apply opacity to alpha channel
    if opacity < 1.0:
        r, g, b, a = logo.split()
        a = a.point(lambda p: int(p * max(0.0, min(1.0, opacity))))
        logo = Image.merge("RGBA", (r, g, b, a))

    if is_grid:
        effective_angle = 12 if angle == 0 else angle
        use_stagger = stagger if stagger is not None else False
        watermark_layer = render_diagonal_grid(
            w=w,
            h=h,
            stamp=logo,
            angle=effective_angle,
            density=density,
            gap_x_mult=0.6,
            gap_y_mult=3.5,
            stagger=use_stagger
        )
    elif pos_lower == "tiled":
        effective_angle = -30 if angle == 0 else angle
        use_stagger = stagger if stagger is not None else True
        watermark_layer = render_diagonal_grid(
            w=w,
            h=h,
            stamp=logo,
            angle=effective_angle,
            density=density,
            gap_x_mult=1.2,
            gap_y_mult=2.5,
            stagger=use_stagger
        )
    else:
        if angle != 0:
            logo = logo.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        watermark_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        lw, lh = logo.size

        x, y = calculate_position(w, h, lw, lh, position, padding)
        watermark_layer.paste(logo, (x, y), logo)

    combined = Image.alpha_composite(base, watermark_layer)

    if img.mode == "RGB":
        return combined.convert("RGB")
    return combined


def process_single_file(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker function for ProcessPoolExecutor.
    Processes one image file and saves the output.
    """
    input_path = task_data["input_path"]
    output_path = task_data["output_path"]
    mode = task_data["mode"]  # 'text' or 'image'
    params = task_data["params"]
    logo_path = task_data.get("logo_path")

    try:
        with Image.open(input_path) as raw_img:
            # Correct orientation from EXIF
            img = ImageOps.exif_transpose(raw_img)

            # Optional 1570x1002 canvas frame & image zoom scaling
            if params.get("canvas_enabled", False):
                img = fit_image_to_canvas(
                    img=img,
                    target_w=int(params.get("canvas_w", 1570)),
                    target_h=int(params.get("canvas_h", 1002)),
                    scale_mode=params.get("canvas_mode", "fit"),
                    zoom=float(params.get("canvas_zoom", 1.0)),
                    bg_color=params.get("canvas_bg", "#000000"),
                    border_width=int(params.get("border_width", 1)),
                    border_color=params.get("border_color", "#ffffff")
                )

            if mode == "text":
                result = apply_text_watermark(
                    img=img,
                    text=params.get("text", "Watermark"),
                    position=params.get("position", "bottom-right"),
                    opacity=float(params.get("opacity", 0.7)),
                    scale=float(params.get("scale", 0.05)),
                    color=params.get("color", "#ffffff"),
                    stroke_color=params.get("stroke_color", "#000000"),
                    stroke_width=int(params.get("stroke_width", 0)),
                    angle=int(params.get("angle", 0)),
                    density=float(params.get("density", 1.0)),
                    stagger=params.get("stagger", None)
                )
            elif mode == "image":
                if not logo_path or not os.path.exists(logo_path):
                    return {"success": False, "file": input_path, "error": "Logo file not found"}
                with Image.open(logo_path) as logo_img:
                    result = apply_image_watermark(
                        img=img,
                        logo_img=logo_img,
                        position=params.get("position", "bottom-right"),
                        opacity=float(params.get("opacity", 0.8)),
                        scale=float(params.get("scale", 0.20)),
                        angle=int(params.get("angle", 0)),
                        density=float(params.get("density", 1.0)),
                        stagger=params.get("stagger", None)
                    )
            else:
                return {"success": False, "file": input_path, "error": f"Unknown mode: {mode}"}

            # Prepare output directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Determine save parameters
            ext = Path(output_path).suffix.lower()
            if ext in {'.jpg', '.jpeg'}:
                if result.mode in ("RGBA", "P"):
                    result = result.convert("RGB")
                result.save(output_path, format="JPEG", quality=95, optimize=True)
            elif ext == '.png':
                result.save(output_path, format="PNG", optimize=True)
            elif ext == '.webp':
                result.save(output_path, format="WEBP", quality=95)
            else:
                result.save(output_path)

        return {"success": True, "file": input_path, "output": output_path}
    except Exception as e:
        return {"success": False, "file": input_path, "error": str(e)}


def scan_images(folder_path: str) -> list[str]:
    """Scan folder for supported image files."""
    if not os.path.exists(folder_path):
        return []
    
    image_files = []
    for root, _, files in os.walk(folder_path):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTENSIONS and not f.startswith('.'):
                image_files.append(os.path.join(root, f))
                
    # Sort for deterministic processing
    image_files.sort()
    return image_files


def run_batch_watermark(
    input_folder: str,
    output_folder: str,
    mode: str,
    params: Dict[str, Any],
    logo_path: Optional[str] = None,
    max_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Any]:
    """
    Run multi-core parallel watermark processing across all images in input_folder.
    """
    files = scan_images(input_folder)
    total = len(files)
    if total == 0:
        return {"total": 0, "processed": 0, "failed": 0, "time_seconds": 0, "files": []}

    os.makedirs(output_folder, exist_ok=True)

    tasks = []
    for fpath in files:
        rel_path = os.path.relpath(fpath, input_folder)
        out_fpath = os.path.join(output_folder, rel_path)
        tasks.append({
            "input_path": fpath,
            "output_path": out_fpath,
            "mode": mode,
            "params": params,
            "logo_path": logo_path
        })

    workers = max_workers or min(os.cpu_count() or 4, 8)
    processed = 0
    failed = 0
    errors = []

    start_time = time.time()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_single_file, task): task for task in tasks}
        for future in as_completed(futures):
            res = future.result()
            if res["success"]:
                processed += 1
            else:
                failed += 1
                errors.append(f"{os.path.basename(res['file'])}: {res['error']}")

            if progress_callback:
                progress_callback(processed + failed, total, res.get("file", ""))

    elapsed = round(time.time() - start_time, 2)

    return {
        "total": total,
        "processed": processed,
        "failed": failed,
        "errors": errors[:20],  # sample errors
        "time_seconds": elapsed,
        "speed_per_sec": round(total / elapsed, 1) if elapsed > 0 else total
    }
