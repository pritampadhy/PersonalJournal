## Docker Deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /app

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["gunicorn", \
     "--workers=4", \
     "--worker-class=gevent", \
     "--bind=0.0.0.0:5000", \
     "--timeout=120", \
     "--access-logfile=-", \
     "--error-logfile=-", \
     "app:create_app()"]
```