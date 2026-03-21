#!/bin/sh
set -e
if [ -n "$SSL_CERTFILE" ] && [ -n "$SSL_KEYFILE" ]; then
  exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${UVICORN_PORT:-8443}" \
    --ssl-certfile "$SSL_CERTFILE" \
    --ssl-keyfile "$SSL_KEYFILE"
else
  exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${UVICORN_PORT:-8000}"
fi
