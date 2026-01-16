FROM python:3.11-slim

WORKDIR /app

COPY production-center/core-application /app/core-application

WORKDIR /app/core-application/apis/dv360_service

ENV PYTHONPATH=/app/core-application:/app/core-application/apis

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
