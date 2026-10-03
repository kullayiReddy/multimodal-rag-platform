FROM python:3.10-slim

# System dependencies for PDF parsing, image processing, OCR, and PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Create data directories
RUN mkdir -p /app/data/uploads /app/data/processed /app/data/images /app/data/chroma /app/data/faiss /app/data/numpy_vectors

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
