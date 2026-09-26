FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
COPY streamlit_app/requirements.txt streamlit_app/requirements.txt
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY streamlit_app/ streamlit_app/

ENV BACKEND_URL=http://127.0.0.1:8000 \
    PYTHONUNBUFFERED=1

EXPOSE 10000

CMD ["sh", "-c", "uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 & exec streamlit run streamlit_app/app.py --server.address 0.0.0.0 --server.port ${PORT:-10000} --server.headless true"]
