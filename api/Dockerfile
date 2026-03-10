FROM python:3.11-slim

WORKDIR /app

# System deps for playwright + psycopg2
RUN apt-get update && apt-get install -y \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright chromium for LMS upload
RUN pip install playwright && playwright install chromium --with-deps

# Copy app
COPY . /app/api
COPY ../agents /app/agents

ENV PYTHONPATH=/app
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
