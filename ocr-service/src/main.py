import os

# Environment variable configurations before importing PaddleOCR / PaddlePaddle
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT'] = '0'

import time
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from paddleocr import PaddleOCR

app = FastAPI(
    title="Intelligent OCR Microservice",
    description="REST API for optical character recognition and intelligent document analysis",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize PaddleOCR engine globally (English/French support)
ocr_engine = PaddleOCR(use_textline_orientation=True, lang='en')


@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify microservice operational status."""
    return {"status": "UP"}


@app.post("/api/ocr")
async def extract_text(file: UploadFile = File(...)):
    """
    Extract raw OCR text from an uploaded image file using PaddleOCR.
    Accepts multipart/form-data with a file parameter.
    """
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded."
            )

        # Convert byte data to numpy array and decode into OpenCV image
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Could not decode image. Please upload a valid image file (PNG, JPEG, etc.)."
            )

        # Convert BGR (OpenCV default) to RGB for PaddleOCR
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Perform OCR using PaddleOCR
        result = ocr_engine.ocr(image)
        print("Raw PaddleOCR output:", result)

        extracted_lines = []
        confidences = []

        if result and len(result) > 0:
            res = result[0]
            # Check if PaddleOCR returned the PaddleX dictionary structure
            if isinstance(res, dict):
                extracted_lines = res.get('rec_texts', [])
                confidences = res.get('rec_scores', [])
            # Legacy tuple/list fallback
            elif isinstance(res, list):
                for line in res:
                    if line and len(line) >= 2 and isinstance(line[1], (tuple, list)):
                        extracted_lines.append(line[1][0])
                        confidences.append(float(line[1][1]))

        combined_text = "\n".join(extracted_lines)
        avg_confidence = round(float(np.mean(confidences)), 4) if confidences else 0.0

        return {
            "success": True,
            "text": combined_text,
            "confidence": avg_confidence
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}"
        )


@app.post("/api/ocr/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """
    Intelligent document analysis endpoint (dummy placeholder for analysis workflow).
    Classifies document type and extracts structured domain metadata.
    """
    filename = file.filename or "uploaded_file"
    return {
        "success": True,
        "document_type": "invoice",
        "metadata": {
            "invoice_number": "INV-2026-001",
            "issue_date": "2026-07-28",
            "vendor_name": "Acme Solutions Corp",
            "total_amount": 1250.00,
            "currency": "USD"
        },
        "raw_text": f"ACME SOLUTIONS CORP\nINVOICE #INV-2026-001\nTotal: $1,250.00\nFile: {filename}",
        "processing_time": 0.5
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
