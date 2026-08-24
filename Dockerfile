FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging configuration and readme
COPY pyproject.toml README.md /app/

# Create dummy src structure to allow caching of pip dependencies install
RUN mkdir -p /app/src/routers /app/src/services /app/src/models /app/src/schemas && \
    touch /app/src/__init__.py /app/src/main.py \
    /app/src/routers/__init__.py /app/src/services/__init__.py \
    /app/src/models/__init__.py /app/src/schemas/__init__.py

# Install dependencies in editable mode
RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Command to run uvicorn with hot-reload
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
