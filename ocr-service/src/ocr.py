import base64
import io
import json
import sys
import traceback
from typing import List, Tuple, Any, Dict
import cv2
import numpy as np
from PIL import Image

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


def extract_images_from_pdf_bytes(pdf_bytes: bytes) -> List[np.ndarray]:
    """
    Converts PDF byte stream into a list of BGR OpenCV images.
    Supports pdf2image (poppler), pypdf/PIL image extraction, and direct imdecode fallbacks.
    """
    images: List[np.ndarray] = []

    # Method 1: pdf2image (poppler)
    if PDF2IMAGE_AVAILABLE:
        try:
            print("--> [PDF Extraction] Attempting rendering via pdf2image (poppler)...")
            pil_images = convert_from_bytes(pdf_bytes)
            for pil_img in pil_images:
                rgb_array = np.array(pil_img.convert("RGB"))
                bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
                images.append(bgr_array)
            if images:
                print(f"--> [PDF Extraction] Rendered {len(images)} page(s) via pdf2image.")
                return images
        except Exception as e:
            print(f"--> [PDF Extraction Warning] pdf2image failed: {e}")

    # Method 2: pypdf page rendering / image object extraction
    if PYPDF_AVAILABLE:
        try:
            print("--> [PDF Extraction] Attempting fallback via pypdf image object extraction...")
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for page_idx, page in enumerate(reader.pages):
                for img_file in page.images:
                    try:
                        pil_img = Image.open(io.BytesIO(img_file.data)).convert("RGB")
                        bgr_array = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                        images.append(bgr_array)
                    except Exception as img_err:
                        print(f"--> [PDF Extraction Warning] Failed page {page_idx} image decode: {img_err}")
            if images:
                print(f"--> [PDF Extraction] Extracted {len(images)} embedded image(s) via pypdf.")
                return images
        except Exception as e:
            print(f"--> [PDF Extraction Warning] pypdf extraction failed: {e}")

    # Method 3: Direct OpenCV byte decode fallback (for single page image-PDFs)
    try:
        nparr = np.frombuffer(pdf_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            print("--> [PDF Extraction] Decoded byte stream directly via OpenCV imdecode.")
            images.append(img)
    except Exception:
        pass

    return images


def extract_page_ocr_and_boxes(result: Any) -> Tuple[List[str], List[float], List[Dict[str, Any]]]:
    """
    Extracts text lines, confidence scores, and line bounding boxes [x_min, y_min, x_max, y_max] from OCR result.
    """
    raw_lines: List[str] = []
    confidences: List[float] = []
    boxes: List[Dict[str, Any]] = []

    if not result:
        return raw_lines, confidences, boxes

    for page in result:
        if not page:
            continue

        if isinstance(page, list):
            for line in page:
                if not line or not isinstance(line, (list, tuple)) or len(line) < 2:
                    continue

                poly_coords = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                content = line[1]

                txt = ""
                conf = 0.0
                if isinstance(content, (list, tuple)) and len(content) >= 1:
                    txt = str(content[0])
                    if len(content) >= 2:
                        try:
                            conf = float(content[1])
                        except (ValueError, TypeError):
                            conf = 0.0
                elif isinstance(content, str):
                    txt = content

                if txt:
                    raw_lines.append(txt)
                    if conf > 0:
                        confidences.append(conf)

                    if isinstance(poly_coords, (list, tuple)) and len(poly_coords) >= 4:
                        xs = [pt[0] for pt in poly_coords if isinstance(pt, (list, tuple)) and len(pt) >= 2]
                        ys = [pt[1] for pt in poly_coords if isinstance(pt, (list, tuple)) and len(pt) >= 2]
                        if xs and ys:
                            boxes.append({
                                "x_min": round(float(min(xs)), 1),
                                "y_min": round(float(min(ys)), 1),
                                "x_max": round(float(max(xs)), 1),
                                "y_max": round(float(max(ys)), 1),
                                "text": txt,
                                "confidence": round(conf, 4)
                            })

    return raw_lines, confidences, boxes


def bgr_image_to_base64_jpeg(image_bgr: np.ndarray) -> str:
    """Encodes a BGR image array into a base64 JPEG data URL string."""
    try:
        success, buffer = cv2.imencode('.jpg', image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if success:
            encoded = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        print(f"--> [Image Base64 Encoding Warning]: {e}")
    return ""
