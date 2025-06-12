# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements_mac.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements_mac.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash fusevault && \
    chown -R fusevault:fusevault /app
USER fusevault

# Expose port
EXPOSE 8000

# Health check - environment-appropriate for IPv4/IPv6
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sh -c 'if [ "$RAILWAY_ENVIRONMENT_NAME" ]; then python -c "import requests; requests.get(\"http://[::1]:8000/docs\")"; else python -c "import requests; requests.get(\"http://localhost:8000/docs\")"; fi' || exit 1

# Run the application with environment-appropriate binding
# Use IPv6 (::) on Railway for private networking, IPv4 (0.0.0.0) locally
CMD ["sh", "-c", "if [ \"$RAILWAY_ENVIRONMENT_NAME\" ]; then uvicorn app.main:app --host :: --port 8000; else uvicorn app.main:app --host 0.0.0.0 --port 8000; fi"]