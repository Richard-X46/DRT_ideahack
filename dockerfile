FROM python:3.11-slim

WORKDIR /app

# Copy dependency files first (for caching)
COPY pyproject.toml ./
COPY uv.lock* ./

# Install UV and dependencies
RUN pip install --no-cache-dir uv

# Install dependencies from pyproject.toml
RUN uv pip install --system -e .

# Copy the rest of the application code
COPY src/ ./src/


# Ensure static and templates folders are present
COPY src/app/static/ ./src/app/static/
COPY src/app/templates/ ./src/app/templates/

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app 
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Use Uvicorn for FastAPI instead of Gunicorn
CMD ["uvicorn", "src.app.main_fastapi:app", "--host", "0.0.0.0", "--port", "5000", "--timeout-keep-alive", "120"]