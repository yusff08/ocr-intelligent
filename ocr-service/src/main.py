from dotenv import load_dotenv
load_dotenv()

import os
import sys
from pathlib import Path

# Add src directory to sys.path if not already present
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Environment variable configurations before importing PaddleOCR / PaddlePaddle
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

import json
import re
import time
import traceback
from typing import List, Optional, Any
import cv2
import numpy as np
import arabic_reshaper
from bidi.algorithm import get_display
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from paddleocr import PaddleOCR
from pydantic import BaseModel
from sqlalchemy.orm import Session
import openai

# Import Database, Models, and Auth helpers with flexible fallback mechanism
try:
    from .database import engine, get_db
    from .models import Base, User, DocumentHistory
    from .auth import (
        hash_password,
        verify_password,
        create_access_token,
        get_current_user,
        get_optional_current_user
    )
    from .ocr import (
        extract_images_from_pdf_bytes,
        extract_page_ocr_and_boxes,
        bgr_image_to_base64_jpeg
    )
except ImportError:
    from database import engine, get_db
    from models import Base, User, DocumentHistory
    from auth import (
        hash_password,
        verify_password,
        create_access_token,
        get_current_user,
        get_optional_current_user
    )
    from ocr import (
        extract_images_from_pdf_bytes,
        extract_page_ocr_and_boxes,
        bgr_image_to_base64_jpeg
    )


# Initialize Database tables
Base.metadata.create_all(bind=engine)
print("--> [DATABASE] SQLite initialized at ocr.db")

app = FastAPI(
    title="Intelligent OCR Microservice",
    description="REST API for optical character recognition, JWT authentication, and LLM-powered document analysis",
    version="1.0.0"
)

# Enable CORS for frontend integration (Registered immediately after FastAPI instantiation)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# HTTP Request Logging Middleware to capture incoming client IPs (Mobile, Desktop, API clients)
@app.middleware("http")
async def log_client_requests(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    print(f"--> [REQUEST] Received {request.method} {request.url.path} from client: {client_ip}")
    response = await call_next(request)
    return response


# Initialize PaddleOCR engine globally (Speed optimized with text_det_limit_side_len=960 and angle classification disabled)
ocr_engine = PaddleOCR(
    use_angle_cls=False,
    lang='ar',
    cpu_threads=4,
    text_det_limit_side_len=960
)


# Pydantic models for request/response payloads
class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class LineItem(BaseModel):
    description: str = "N/A"
    quantity: float = 1.0
    unit_price: float = 0.0
    total_price: float = 0.0


class DocumentMetadata(BaseModel):
    document_type: str = "generic"
    vendor_name: str = "Unknown Vendor"
    invoice_number: str = "N/A"
    issue_date: str = "N/A"
    due_date: str = "N/A"
    currency: str = "EUR"
    subtotal: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0
    items: List[LineItem] = []


SYSTEM_PROMPT = """You are an expert multilingual and bilingual invoice document analyzer AI. 
Extract details into valid JSON. Normalize Arabic text (RTL) and Arabic numbers (٠-٩ to 0-9). The invoice currency is often SAR or TND. Extract real line items, totals, and vendor names.

Extraction Guidelines:
1. Normalize Eastern Arabic numerals (٠, ١, ٢, ٣, ٤, ٥, ٦, ٧, ٨, ٩) to standard digits (0-9).
2. Vendor Name: Extract full vendor/company name, including bilingual text if present (e.g., "ElectroTel Ahmed A.Alsfoog / Electrical & Telecom Est").
3. Invoice Number: Look for Inv#, No, Code, ref, or codes like "5SD09460".
4. Dates: Standardize issue_date and due_date to YYYY-MM-DD format.
5. Currency: Determine 3-letter ISO code (e.g. SAR for Saudi Riyal / ريال / SR, TND for Tunisian Dinar, EUR, USD, MAD, EGP).
6. Amounts: Extract subtotal, tax_amount, and total_amount as numeric floats.
7. Line Items: Extract description (bilingual Arabic/English), quantity, unit_price, and total_price for each line item.

JSON Schema:
{
  "document_type": "invoice | receipt | generic",
  "vendor_name": "string",
  "invoice_number": "string",
  "issue_date": "string (YYYY-MM-DD or original date)",
  "due_date": "string (YYYY-MM-DD or original date)",
  "currency": "3-letter ISO code (e.g., SAR, TND, EUR, USD, GBP, MAD, DZD)",
  "subtotal": float,
  "tax_amount": float,
  "total_amount": float,
  "items": [
    {
      "description": "string",
      "quantity": float,
      "unit_price": float,
      "total_price": float
    }
  ]
}

Return ONLY raw valid JSON matching this schema without markdown codeblocks or extra conversational text.
"""


def normalize_arabic_digits(text: str) -> str:
    """Converts Eastern Arabic numerals (٠-٩) to standard digits (0-9)."""
    if not text:
        return text
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"
    translation_table = str.maketrans(arabic_digits, english_digits)
    return text.translate(translation_table)


def format_arabic_text(text: str) -> str:
    """Reshapes Arabic characters and applies bidirectional algorithm for proper RTL display."""
    if not text:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        return bidi_text
    except Exception:
        return text


def preprocess_image(contents: bytes) -> np.ndarray:
    """
    Decodes image bytes, applies downscaling (max side 1280px for high speed OCR),
    CLAHE contrast enhancement, and returns an RGB image numpy array.
    """
    nparr = np.frombuffer(contents, np.uint8)
    image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image_bgr is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Could not decode image. Please upload a valid image file (PNG, JPEG, etc.)."
        )

    # 1. Downscale image if max dimension exceeds 1280px to speed up PaddleOCR detection
    h, w = image_bgr.shape[:2]
    max_dim = 1280
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        image_bgr = cv2.resize(image_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    # 2. CLAHE Contrast Enhancement in LAB color space
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)
    limg = cv2.merge((cl, a_channel, b_channel))
    enhanced_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    # 3. Convert BGR to RGB for PaddleOCR
    image_rgb = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2RGB)
    return image_rgb


def parse_text_with_llm(raw_text: str) -> dict:
    """
    Universal LLM parser that extracts structured business JSON from raw OCR text.
    Uses Groq or OpenAI client endpoints with structured prompts.
    Includes robust schema sanitization and a fallback heuristic parser.
    """
    api_key = os.getenv("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")
    model_name = os.getenv("LLM_MODEL_NAME", "llama-3.3-70b-versatile")

    if api_key and not api_key.startswith("your_"):
        try:
            print(f"--> Sending text to Groq model {model_name}...")
            client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Document Raw Text:\n\n{raw_text}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            if content:
                parsed_json = json.loads(content)
                # Robustly sanitize items list to prevent Pydantic validation errors
                if isinstance(parsed_json.get("items"), list):
                    cleaned_items = []
                    for item in parsed_json["items"]:
                        if isinstance(item, dict):
                            cleaned_items.append({
                                "description": str(item.get("description", item.get("name", "N/A"))),
                                "quantity": float(item.get("quantity", 1.0)) if str(item.get("quantity", "")).replace(".", "", 1).isdigit() else 1.0,
                                "unit_price": float(item.get("unit_price", item.get("price", 0.0))) if str(item.get("unit_price", item.get("price", ""))).replace(".", "", 1).isdigit() else 0.0,
                                "total_price": float(item.get("total_price", item.get("total", 0.0))) if str(item.get("total_price", item.get("total", ""))).replace(".", "", 1).isdigit() else 0.0
                            })
                        elif isinstance(item, str):
                            cleaned_items.append({"description": item, "quantity": 1.0, "unit_price": 0.0, "total_price": 0.0})
                    parsed_json["items"] = cleaned_items
                return DocumentMetadata(**parsed_json).model_dump()
        except Exception as e:
            print(f"LLM API Call Warning ({type(e).__name__}): {e}. Falling back to heuristic parser.")
            traceback.print_exc()
    else:
        print("--> No valid GROQ_API_KEY set in environment or .env. Using fallback heuristic parser.")

    # Fallback Heuristic Parser when LLM API is unavailable or fails
    normalized_text = normalize_arabic_digits(raw_text)
    text_lower = normalized_text.lower()

    # Detect currency ISO code
    currency = "EUR"
    if any(k in text_lower for k in ["sar", "riyal", "ريال", "سعودي", "sr"]):
        currency = "SAR"
    elif any(k in text_lower for k in ["tnd", "dinar", "dt", "دينار"]):
        currency = "TND"
    elif any(k in text_lower for k in ["usd", "$", "dollar"]):
        currency = "USD"
    elif any(k in text_lower for k in ["gbp", "£", "pound"]):
        currency = "GBP"
    elif any(k in text_lower for k in ["mad", "dirham"]):
        currency = "MAD"

    doc_type = "invoice" if any(k in text_lower for k in ["invoice", "facture", "فاتورة"]) else "generic"

    inv_match = re.search(r'(?:invoice|facture|inv|ref|no|num|5sd)[#\s:\-]*([A-Za-z0-9\-]+)', normalized_text, re.IGNORECASE)
    invoice_number = inv_match.group(1) if inv_match else "INV-001"

    dates = re.findall(r'\b(?:\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}|\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})\b', normalized_text)
    issue_date = dates[0] if dates else "N/A"
    due_date = dates[1] if len(dates) > 1 else "N/A"

    amount_matches = re.findall(r'\b\d+(?:[,\.]\d{2})?\b', normalized_text)
    float_amounts = []
    for a in amount_matches:
        try:
            val = float(a.replace(',', '.'))
            if val > 0:
                float_amounts.append(val)
        except ValueError:
            pass
    float_amounts.sort()

    total_amount = float_amounts[-1] if float_amounts else 0.0
    subtotal = float_amounts[-2] if len(float_amounts) >= 2 else (round(total_amount * 0.8, 2) if total_amount > 0 else 0.0)
    tax_amount = round(total_amount - subtotal, 2) if total_amount >= subtotal else 0.0

    lines = [line.strip() for line in normalized_text.split('\n') if line.strip()]
    vendor_name = lines[0] if lines else "Unknown Vendor"

    sample_items = [
        LineItem(description="Extracted Line Item 1", quantity=1.0, unit_price=subtotal, total_price=subtotal)
    ] if subtotal > 0 else []

    return DocumentMetadata(
        document_type=doc_type,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        issue_date=issue_date,
        due_date=due_date,
        currency=currency,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        items=sample_items
    ).model_dump()


def extract_text_and_confidence_from_ocr_result(result: Any) -> tuple[List[str], List[float]]:
    """Ultra-resilient parser for all variations of PaddleOCR and PaddleX result structures."""
    extracted_lines: List[str] = []
    confidences: List[float] = []

    if not result:
        return extracted_lines, confidences

    for page in result:
        if not page:
            continue

        if isinstance(page, dict):
            raw_texts = page.get('rec_texts', []) or page.get('texts', [])
            raw_scores = page.get('rec_scores', []) or page.get('scores', [])
            for t in raw_texts:
                if t:
                    extracted_lines.append(str(t))
            for c in raw_scores:
                try:
                    confidences.append(float(c))
                except (ValueError, TypeError):
                    pass
        elif isinstance(page, list):
            for line in page:
                if not line:
                    continue
                if isinstance(line, (list, tuple)) and len(line) >= 2:
                    content = line[1]
                    if isinstance(content, (list, tuple)) and len(content) >= 1:
                        txt = str(content[0])
                        extracted_lines.append(txt)
                        if len(content) >= 2:
                            try:
                                confidences.append(float(content[1]))
                            except (ValueError, TypeError):
                                pass
                    elif isinstance(content, str):
                        extracted_lines.append(content)
                elif isinstance(line, str):
                    extracted_lines.append(line)

    return extracted_lines, confidences


def perform_ocr(contents: bytes) -> tuple[str, float]:
    """Helper function to preprocess image bytes and run PaddleOCR with Arabic RTL reshaping."""
    image = preprocess_image(contents)

    # Perform OCR
    result = ocr_engine.ocr(image)

    raw_lines, raw_confidences = extract_text_and_confidence_from_ocr_result(result)

    formatted_lines = []
    for line in raw_lines:
        normalized = normalize_arabic_digits(line)
        formatted = format_arabic_text(normalized)
        formatted_lines.append(formatted)

    combined_text = "\n".join(formatted_lines)
    avg_confidence = round(float(np.mean(raw_confidences)), 4) if raw_confidences else 0.0
    return combined_text, avg_confidence


# --- AUTHENTICATION & USER MANAGEMENT ENDPOINTS ---

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user account with email and hashed password."""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )

    hashed_pw = hash_password(user_data.password)
    new_user = User(email=user_data.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "success": True,
        "message": "User registered successfully",
        "user_id": new_user.id,
        "email": new_user.email
    }


@app.post("/api/auth/login")
async def login_user(
    request: Request,
    user_data: Optional[UserLogin] = None,
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    grant_type: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Authenticates user credentials and returns a JWT Bearer access token.
    Supports Swagger Authorize modal, JSON payload body, and form data.
    """
    email_input = None
    pass_input = None

    if user_data and user_data.email:
        email_input = user_data.email
        pass_input = user_data.password

    if not email_input and username:
        email_input = username
        pass_input = password

    if not email_input or not pass_input:
        try:
            body = await request.json()
            if isinstance(body, dict):
                email_input = body.get("email") or body.get("username")
                pass_input = body.get("password")
        except Exception:
            pass

    if not email_input or not pass_input:
        try:
            form = await request.form()
            email_input = form.get("username") or form.get("email")
            pass_input = form.get("password")
        except Exception:
            pass

    if not email_input or not pass_input:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required."
        )

    user = db.query(User).filter(User.email == email_input).first()
    if not user or not verify_password(pass_input, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email
        }
    }


@app.get("/api/auth/me")
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns profile details of the authenticated user."""
    return {
        "success": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None
        }
    }


# --- GENERAL & PROTECTED DOCUMENT PROCESSING ENDPOINTS ---

@app.get("/api")
async def api_base(request: Request):
    """Root API route for base API availability checks."""
    client_ip = request.client.host if request.client else "unknown"
    print(f"--> [REQUEST] Base API check GET /api from client: {client_ip}")
    return {"message": "OCR API Service", "status": "ok"}


@app.get("/api/health")
async def health_check(request: Request):
    """Health check endpoint to verify microservice operational status."""
    client_ip = request.client.host if request.client else "unknown"
    print(f"--> [REQUEST] Health check GET /api/health from client: {client_ip}")
    return {"status": "UP"}



@app.post("/api/ocr")
async def extract_text(
    request: Request,
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    OCR Endpoint: Extracts raw text and saves user document history if authenticated.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_label = current_user.email if current_user else "guest"
    print(f"--> [REQUEST] POST /api/ocr from {user_label} (IP: {client_ip}, File: {file.filename})")
    try:
        if file.content_type and not (file.content_type.startswith("image/") or file.content_type in ["application/pdf", "application/octet-stream"]):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported media type: {file.content_type}"
            )
        contents = await file.read()
        if not contents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded."
            )

        combined_text, avg_confidence = perform_ocr(contents)

        doc_id = None
        if current_user:
            doc_record = DocumentHistory(
                user_id=current_user.id,
                filename=file.filename or "uploaded_file",
                document_type="generic",
                raw_text=combined_text,
                metadata_json=json.dumps({"confidence": avg_confidence})
            )
            db.add(doc_record)
            db.commit()
            db.refresh(doc_record)
            doc_id = doc_record.id

        return {
            "success": True,
            "text": combined_text,
            "confidence": avg_confidence,
            "document_id": doc_id
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"--> [ERROR 500] OCR extraction failed: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}"
        )


@app.post("/api/ocr/analyze")
async def analyze_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Intelligent Document Analysis Endpoint:
    Executes OCR + LLM structuring and saves user document history if authenticated.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_label = current_user.email if current_user else "guest"
    print(f"--> [REQUEST] POST /api/ocr/analyze from {user_label} (IP: {client_ip}, File: {file.filename})")
    start_time = time.time()
    try:
        if file.content_type and not (file.content_type.startswith("image/") or file.content_type in ["application/pdf", "application/octet-stream"]):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported media type: {file.content_type}"
            )
        contents = await file.read()
        if not contents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded."
            )

        # 1. Perform PaddleOCR extraction
        raw_text, _ = perform_ocr(contents)

        # 2. Run LLM Structuring logic
        metadata = parse_text_with_llm(raw_text)

        # 3. Calculate processing time
        processing_time = round(time.time() - start_time, 2)

        # 4. Save document execution history if user is authenticated
        doc_id = None
        if current_user:
            doc_record = DocumentHistory(
                user_id=current_user.id,
                filename=file.filename or "uploaded_file",
                document_type=metadata.get("document_type", "generic"),
                raw_text=raw_text,
                metadata_json=json.dumps(metadata)
            )
            db.add(doc_record)
            db.commit()
            db.refresh(doc_record)
            doc_id = doc_record.id

        return {
            "success": True,
            "document_id": doc_id,
            "document_type": metadata.get("document_type", "generic"),
            "metadata": metadata,
            "raw_text": raw_text,
            "processing_time": processing_time
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"--> [ERROR 500] Document analysis failed: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document analysis failed: {str(e)}"
        )


@app.post("/api/ocr/upload-multi")
async def process_multi_page_upload(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Multi-Page Document Processing Endpoint:
    Accepts multiple image files or multi-page PDFs, runs per-page OCR, extracts bounding boxes,
    stitches raw text across pages, merges line items, and persists page_count and pages_data.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_label = current_user.email if current_user else "guest"
    print(f"--> [REQUEST] POST /api/ocr/upload-multi from {user_label} (IP: {client_ip}, Files count: {len(files)})")

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded."
        )

    try:
        start_time = time.time()
        page_records = []
        combined_lines = []

        for idx, uploaded_file in enumerate(files):
            if uploaded_file.content_type and not (uploaded_file.content_type.startswith("image/") or uploaded_file.content_type in ["application/pdf", "application/octet-stream"]):
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Unsupported media type: {uploaded_file.content_type}"
                )
            contents = await uploaded_file.read()
            if not contents:
                continue

            filename = uploaded_file.filename or f"page_{idx + 1}"
            is_pdf = filename.lower().endswith(".pdf") or uploaded_file.content_type == "application/pdf"

            page_images = []
            if is_pdf:
                page_images = extract_images_from_pdf_bytes(contents)

            if not page_images:
                try:
                    preprocessed = preprocess_image(contents)
                    page_images = [preprocessed]
                except Exception as prep_err:
                    print(f"--> [Preprocess Warning] Page {idx + 1} ({filename}) decode failed: {prep_err}")

            for page_idx, img_bgr in enumerate(page_images):
                res = ocr_engine.ocr(img_bgr)
                lines, confs, boxes = extract_page_ocr_and_boxes(res)
                combined_lines.extend(lines)

                preview_url = bgr_image_to_base64_jpeg(img_bgr)
                avg_conf = round(float(np.mean(confs)), 4) if confs else 0.95

                page_records.append({
                    "page_number": len(page_records) + 1,
                    "raw_text": "\n".join(lines),
                    "boxes": boxes,
                    "confidence": avg_conf,
                    "preview_url": preview_url
                })

        if not page_records:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid image or PDF content could be extracted."
            )

        raw_text = "\n".join(combined_lines)
        metadata = parse_text_with_llm(raw_text)
        processing_time = round(time.time() - start_time, 2)

        doc_id = None
        if current_user:
            doc_record = DocumentHistory(
                user_id=current_user.id,
                filename=files[0].filename if len(files) == 1 else f"Batch ({len(files)} files)",
                document_type=metadata.get("document_type", "generic"),
                raw_text=raw_text,
                metadata_json=json.dumps(metadata),
                page_count=len(page_records),
                pages_data=json.dumps(page_records)
            )
            db.add(doc_record)
            db.commit()
            db.refresh(doc_record)
            doc_id = doc_record.id

        return {
            "success": True,
            "document_id": doc_id,
            "page_count": len(page_records),
            "document_type": metadata.get("document_type", "generic"),
            "metadata": metadata,
            "raw_text": raw_text,
            "pages_data": page_records,
            "processing_time": processing_time
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"--> [ERROR 500] Multi-page processing failed: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-page document processing failed: {str(e)}"
        )



@app.get("/api/documents/history")
async def get_document_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected Document History Endpoint:
    Returns all historical document extractions for the logged-in user ordered by created_at descending.
    """
    records = db.query(DocumentHistory).filter(
        DocumentHistory.user_id == current_user.id
    ).order_by(DocumentHistory.created_at.desc()).all()

    history_list = []
    for doc in records:
        parsed_metadata = None
        if doc.metadata_json:
            try:
                parsed_metadata = json.loads(doc.metadata_json)
            except Exception:
                parsed_metadata = doc.metadata_json

        parsed_pages_data = None
        if doc.pages_data:
            try:
                parsed_pages_data = json.loads(doc.pages_data)
            except Exception:
                parsed_pages_data = doc.pages_data

        history_list.append({
            "id": doc.id,
            "user_id": doc.user_id,
            "filename": doc.filename,
            "document_type": doc.document_type,
            "raw_text": doc.raw_text,
            "metadata": parsed_metadata,
            "page_count": doc.page_count or 1,
            "pages_data": parsed_pages_data,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        })

    return {
        "success": True,
        "count": len(history_list),
        "documents": history_list
    }


@app.get("/api/documents/history/{doc_id}")
async def get_document_history_by_id(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns details for a specific historical document owned by the authenticated user."""
    doc = db.query(DocumentHistory).filter(
        DocumentHistory.id == doc_id,
        DocumentHistory.user_id == current_user.id
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document record not found."
        )

    parsed_metadata = None
    if doc.metadata_json:
        try:
            parsed_metadata = json.loads(doc.metadata_json)
        except Exception:
            parsed_metadata = doc.metadata_json

    parsed_pages_data = None
    if doc.pages_data:
        try:
            parsed_pages_data = json.loads(doc.pages_data)
        except Exception:
            parsed_pages_data = doc.pages_data

    return {
        "success": True,
        "document": {
            "id": doc.id,
            "user_id": doc.user_id,
            "filename": doc.filename,
            "document_type": doc.document_type,
            "raw_text": doc.raw_text,
            "metadata": parsed_metadata,
            "page_count": doc.page_count or 1,
            "pages_data": parsed_pages_data,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        }
    }



@app.delete("/api/documents/history/{doc_id}")
async def delete_document_history_by_id(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a historical document record owned by the authenticated user."""
    doc = db.query(DocumentHistory).filter(
        DocumentHistory.id == doc_id,
        DocumentHistory.user_id == current_user.id
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document record not found."
        )

    db.delete(doc)
    db.commit()

    return {
        "success": True,
        "message": f"Document record {doc_id} deleted successfully."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
