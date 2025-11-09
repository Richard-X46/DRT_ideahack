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

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app 
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "src.app.main:application"]