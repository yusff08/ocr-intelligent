FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV, C++, and PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    gcc \
    g++ \
    curl \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*



# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and test suite
COPY src/ ./src/
COPY tests/ ./tests/
COPY .env* ./

# Expose microservice port
EXPOSE 8080

# Run FastAPI application via uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
