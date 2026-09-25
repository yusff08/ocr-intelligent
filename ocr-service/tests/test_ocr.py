from unittest.mock import patch
import numpy as np



def test_ocr_empty_file_upload(client):
    """Test POST /api/ocr with an empty file returns 400 Bad Request."""
    files = {"file": ("empty.png", b"", "image/png")}
    response = client.post("/api/ocr", files=files)
    assert response.status_code == 400
    assert "Empty file uploaded" in response.json().get("detail", "")


def test_ocr_invalid_mime_type(client):
    """Test POST /api/ocr with an invalid MIME type returns 415 Unsupported Media Type."""
    files = {"file": ("script.sh", b"echo Hello", "text/x-shellscript")}
    response = client.post("/api/ocr", files=files)
    assert response.status_code == 415
    assert "Unsupported media type" in response.json().get("detail", "")


@patch("main.perform_ocr")
def test_ocr_valid_image_upload(mock_ocr, client):
    """Test POST /api/ocr with a valid image returns 200 OK with schema keys."""
    mock_ocr.return_value = ("INVOICE #1024\nTotal: 150.00 EUR", 0.9850)

    # Valid PNG image bytes (1x1 PNG pixel)
    valid_png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00"
        b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    files = {"file": ("test_invoice.png", valid_png_bytes, "image/png")}
    response = client.post("/api/ocr", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert "text" in data
    assert "confidence" in data
    assert data.get("confidence") == 0.9850


@patch("main.perform_ocr")
@patch("main.parse_text_with_llm")
def test_ocr_analyze_valid_document(mock_llm, mock_ocr, client):
    """Test POST /api/ocr/analyze returns 200 OK with metadata and schema keys."""
    mock_ocr.return_value = ("FACTUR 999\nTotal 250 TND", 0.99)
    mock_llm.return_value = {
        "document_type": "invoice",
        "vendor_name": "Tech Corp",
        "invoice_number": "FACTUR-999",
        "currency": "TND",
        "total_amount": 250.0,
        "items": []
    }

    files = {"file": ("invoice.jpg", b"fake-jpg-content", "image/jpeg")}
    response = client.post("/api/ocr/analyze", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert data.get("document_type") == "invoice"
    assert "metadata" in data
    assert "raw_text" in data
    assert "processing_time" in data


@patch("main.preprocess_image")
@patch("main.ocr_engine.ocr")
@patch("main.parse_text_with_llm")
def test_upload_multi_page_documents(mock_llm, mock_ocr_engine, mock_preprocess, client):
    """Test POST /api/ocr/upload-multi with multiple page images."""
    mock_preprocess.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_ocr_engine.return_value = [
        [[[10, 10], [100, 10], [100, 30], [10, 30]], ["Multi-Page Item 1", 0.98]]
    ]
    mock_llm.return_value = {
        "document_type": "invoice",
        "vendor_name": "MultiVendor Ltd",
        "invoice_number": "INV-MULTI-100",
        "currency": "EUR",
        "total_amount": 500.0,
        "items": [
            {"description": "Multi-Page Item 1", "quantity": 1.0, "unit_price": 500.0, "total_price": 500.0}
        ]
    }

    files = [
        ("files", ("page1.png", b"fake-png-1", "image/png")),
        ("files", ("page2.png", b"fake-png-2", "image/png"))
    ]

    response = client.post("/api/ocr/upload-multi", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert data.get("page_count") == 2
    assert "pages_data" in data
    assert len(data["pages_data"]) == 2
    assert data["pages_data"][0]["page_number"] == 1
    assert data["pages_data"][1]["page_number"] == 2


