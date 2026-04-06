FROM python:3.12-slim

ARG SERVICE_NAME
WORKDIR /app

COPY ${SERVICE_NAME}/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY ${SERVICE_NAME}/main.py .

ENV SERVICE_NAME=${SERVICE_NAME}

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
