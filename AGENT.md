# Repository Guidelines & Agent Context

This repository contains the source code, tests, configuration, and documentation for the **Intelligent OCR Microservice System**.

---

## 1. Project Overview

The system is designed to perform optical character recognition (OCR) and intelligent document processing. It extracts raw text from document images using **PaddleOCR** and structures extracted content into domain-specific business JSON schemas via an **AI LLM engine**.

### Core Stack
- **Backend (`ocr-service/`):** Python 3.10+, FastAPI, Uvicorn, PaddleOCR v3+, OpenCV (Headless), NumPy.
- **Frontend (`ocr-frontend/`):** Angular 17+ Web UI.
- **Documentation (`documentation/`):** API specifications ([api-specs.md](file:///c:/Users/yusff/Desktop/stage/ocr-intelligent/documentation/api-specs.md)) and System Architecture ([architecture.md](file:///c:/Users/yusff/Desktop/stage/ocr-intelligent/documentation/architecture.md)).
- **Infrastructure:** Docker, Docker Compose, GitLab CI/CD (`.gitlab-ci.yml`).

---

## 2. Directory Structure

```
ocr-intelligent/
├── .gitlab-ci.yml
├── .gitignore
├── AGENT.md
├── docker-compose.yml
├── documentation/
│   ├── api-specs.md
│   └── architecture.md
├── ocr-frontend/
│   ├── angular.json
│   ├── README.md
│   └── src/
└── ocr-service/
    ├── Dockerfile
    ├── README.md
    ├── requirements.txt
    ├── tests/
    └── src/
        └── main.py
```

---

## 3. Backend Rules & Gotchas (`ocr-service`)

### Environment Variable Flags
PaddlePaddle v3 requires environment flags set **before** importing `PaddleOCR` or `cv2` to prevent OneDNN C++ runtime exceptions:

```python
import os
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT'] = '0'

import cv2
import numpy as np
from paddleocr import PaddleOCR
```

### PaddleOCR Engine Initialization
Use `use_textline_orientation=True` instead of deprecated `use_angle_cls`:

```python
ocr_engine = PaddleOCR(use_textline_orientation=True, lang='en')
```

### Image Color Conversion
OpenCV decodes image streams as BGR (`cv2.IMREAD_COLOR`). Always convert to **RGB** before passing the numpy image array to PaddleOCR:

```python
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
result = ocr_engine.ocr(image)
```

### Response Parsing
PaddleOCR v3 returns a dictionary structure containing `rec_texts` and `rec_scores` under `result[0]`. Fallback to list/tuple structures for backward compatibility.

---

## 4. REST API Endpoints

- **`GET /api/health`** -> Returns `{"status": "UP"}`
- **`POST /api/ocr`** -> Accepts `multipart/form-data` image file -> Returns `{"success": true, "text": "...", "confidence": 0.95}`
- **`POST /api/ocr/analyze`** -> Accepts `multipart/form-data` image file -> Returns `{"success": true, "document_type": "...", "metadata": {}, "raw_text": "...", "processing_time": 2.5}`

---

## 5. Branching & Commit Conventions

- Primary active branches: `main` and `develop`.
- Write clear, concise Git commit messages documenting functional changes and bug fixes.
