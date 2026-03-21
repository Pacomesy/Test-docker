FROM python:3.12-slim

WORKDIR /app

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /data \
    && chown appuser:appuser /data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY docker-entrypoint.sh /docker-entrypoint.sh
# Windows CRLF dans le script → "no such file or directory" sous Linux
RUN sed -i 's/\r$//' /docker-entrypoint.sh \
    && chmod +x /docker-entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser

ENV DATA_DIR=/data
EXPOSE 8000 8443

ENTRYPOINT ["/bin/sh", "/docker-entrypoint.sh"]
