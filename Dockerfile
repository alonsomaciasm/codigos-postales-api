# Multi-stage Dockerfile Hardened (Non-root user)
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Imagen Final Producción
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Copiar dependencias compiladas
COPY --from=builder /install /usr/local

# Crear usuario sin privilegios para seguridad (OWASP Docker Hardening)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

# Copiar código de la aplicación y la base de datos procesada
COPY app /app/app
COPY scripts /app/scripts
COPY sepomex.db /app/sepomex.db

# Crear directorio de logs y asignar permisos completos al usuario sin privilegios
RUN mkdir -p /app/logs && chmod -R 777 /app/logs && chown -R appuser:appgroup /app

USER appuser:appgroup

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Servidor ASGI Granian (Rust) o Uvicorn con Workers configurables por variable de entorno
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-2}"]
