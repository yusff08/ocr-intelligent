# Intelligent OCR Microservice API Specification

## 1. Overview

This document specifies the RESTful API endpoints exposed by the **Intelligent OCR Microservice**. The service provides health monitoring, text extraction (OCR), and advanced intelligent document analysis (classification and field metadata extraction).

- **Base URL:** `http://localhost:8080` (or `https://<domain>`)
- **API Version:** `v1`
- **Default Format:** `JSON` (except multipart payload uploads)

---

## 2. Summary of Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Service health status check | No |
| `POST` | `/api/ocr` | Basic text extraction from an uploaded image file | No |
| `POST` | `/api/ocr/analyze` | Intelligent document analysis & metadata extraction | No |

---

## 3. Error Response Format

All failed API requests return a standard JSON error response payload:

```json
{
  "success": false,
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "Unsupported file format. Allowed formats: image/jpeg, image/png, image/tiff, application/pdf.",
    "timestamp": "2026-07-28T15:14:31Z"
  }
}
```

### Common HTTP Status Codes
- `200 OK` - Request succeeded.
- `400 Bad Request` - Missing or malformed parameters.
- `415 Unsupported Media Type` - File format not supported.
- `422 Unprocessable Entity` - Image unreadable or OCR processing failed.
- `500 Internal Server Error` - Server runtime failure.

---

## 4. Endpoint Specifications

---

### 4.1 `GET /api/health`

Checks the availability and operational status of the OCR microservice.

#### Request

- **HTTP Method:** `GET`
- **URL:** `/api/health`
- **Headers:** None required
- **Query Parameters:** None
- **Body:** None

#### Response

##### `200 OK`

```json
{
  "status": "UP"
}
```

##### Fields Description

| Field | Type | Description |
| :--- | :--- | :--- |
| `status` | `string` | System operational state. Returns `"UP"` when service is healthy. |

#### Example `cURL`

```bash
curl -X GET "http://localhost:8080/api/health" \
     -H "Accept: application/json"
```

---

### 4.2 `POST /api/ocr`

Performs optical character recognition (OCR) on an uploaded image file and returns the extracted raw text along with an overall confidence score.

#### Request

- **HTTP Method:** `POST`
- **URL:** `/api/ocr`
- **Headers:**
  - `Content-Type: multipart/form-data`
  - `Accept: application/json`
- **Form Data Parameters:**

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `file` | `file (binary)` | **Yes** | Image file to process (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.pdf`). Max size: 10 MB. |
| `language` | `string` | No | Language code for OCR engine (e.g., `eng`, `fra`, `deu`). Default: `eng`. |

#### Response

##### `200 OK`

```json
{
  "success": true,
  "text": "INVOICE #10243\nDate: 2026-07-15\nTotal Amount: $1,250.00\nThank you for your business!",
  "confidence": 0.95
}
```

##### Fields Description

| Field | Type | Description |
| :--- | :--- | :--- |
| `success` | `boolean` | Indicates whether OCR text extraction was successful (`true`/`false`). |
| `text` | `string` | The extracted raw plain text extracted from the document image. |
| `confidence` | `float` | Estimated accuracy confidence score of the OCR output (range `0.00` to `1.00`). |

#### Example `cURL`

```bash
curl -X POST "http://localhost:8080/api/ocr" \
     -H "Accept: application/json" \
     -F "file=@/path/to/sample_invoice.png" \
     -F "language=eng"
```

---

### 4.3 `POST /api/ocr/analyze`

Performs intelligent document analysis on an uploaded image. In addition to raw text extraction, this endpoint classifies the document type (e.g., invoice, receipt, ID card) and extracts structured key-value metadata entities.

#### Request

- **HTTP Method:** `POST`
- **URL:** `/api/ocr/analyze`
- **Headers:**
  - `Content-Type: multipart/form-data`
  - `Accept: application/json`
- **Form Data Parameters:**

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `file` | `file (binary)` | **Yes** | Document image to analyze (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.pdf`). Max size: 10 MB. |
| `extract_table` | `boolean` | No | Option to extract tabular structures if detected. Default: `false`. |

#### Response

##### `200 OK`

```json
{
  "success": true,
  "document_type": "invoice",
  "metadata": {
    "invoice_number": "INV-2026-001",
    "issue_date": "2026-07-28",
    "due_date": "2026-08-28",
    "vendor_name": "Acme Solutions Corp",
    "total_amount": 1250.00,
    "currency": "USD",
    "tax_amount": 125.00
  },
  "raw_text": "ACME SOLUTIONS CORP\nINVOICE #INV-2026-001\nIssue Date: 2026-07-28\nDue Date: 2026-08-28\nSubtotal: $1,125.00\nTax: $125.00\nTotal: $1,250.00",
  "processing_time": 2.5
}
```

##### Fields Description

| Field | Type | Description |
| :--- | :--- | :--- |
| `success` | `boolean` | Indicates whether document analysis succeeded (`true`/`false`). |
| `document_type` | `string` | Detected document category (e.g., `"invoice"`, `"receipt"`, `"identity_card"`, `"passport"`, `"generic"`). |
| `metadata` | `object` | Key-value pairs of extracted structured domain entities specific to the document type. |
| `raw_text` | `string` | Full unformatted text extracted from the document. |
| `processing_time` | `float` | Duration of the analysis operation in seconds. |

#### Example `cURL`

```bash
curl -X POST "http://localhost:8080/api/ocr/analyze" \
     -H "Accept: application/json" \
     -F "file=@/path/to/invoice_sample.pdf" \
     -F "extract_table=true"
```
