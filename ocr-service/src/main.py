import os
# Disable PIR API to prevent PaddlePaddle OneDNN ConvertPirAttribute2RuntimeAttribute errors
os.environ['FLAGS_enable_pir_api'] = '0'

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

# Initialize PaddleOCR engine globally with MKLDNN disabled
ocr_engine = PaddleOCR(use_angle_cls=True, lang='fr', use_mkldnn=False)


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

        # Perform OCR using PaddleOCR
        result = ocr_engine.ocr(image)

        extracted_lines = []
        confidences = []

        # Parse PaddleOCR output structure: list of pages/results
        if result and len(result) > 0 and result[0] is not None:
            for line in result[0]:
                if len(line) >= 2 and isinstance(line[1], (tuple, list)):
                    text_str = line[1][0]
                    confidence_score = float(line[1][1])
                    extracted_lines.append(text_str)
                    confidences.append(confidence_score)

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
