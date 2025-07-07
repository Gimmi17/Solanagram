FROM python:3.11-alpine

WORKDIR /app

# Install build dependencies for psycopg2
RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev

# Copy and install requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy extractor script
COPY extractor.py /app/extractor.py

ENV PYTHONUNBUFFERED=1

CMD ["python", "/app/extractor.py"] 