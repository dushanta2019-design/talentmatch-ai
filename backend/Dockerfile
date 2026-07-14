FROM python:3.12-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
# Shell form so $PORT from the platform (e.g. Render) is honored
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
