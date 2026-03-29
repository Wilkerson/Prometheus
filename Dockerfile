# ============================================================
# Stage 1: Builder — instala dependencias e compila Tailwind
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY . .
RUN PYTHONPATH=/install/lib/python3.12/site-packages \
    /install/bin/pytailwindcss -i static/src/input.css -o static/css/output.css --minify || true

# ============================================================
# Stage 2: Runtime — imagem final enxuta
# ============================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-prometheus.settings.production}

WORKDIR /app

# Dependencias de sistema (runtime only)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copia dependencias Python do builder
COPY --from=builder /install /usr/local

# Copia codigo fonte
COPY . .

# Copia Tailwind compilado do builder
COPY --from=builder /build/static/css/output.css static/css/output.css

# Coleta arquivos estaticos
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Cria usuario nao-root
RUN groupadd -r prometheus && useradd -r -g prometheus prometheus \
    && chown -R prometheus:prometheus /app
USER prometheus

# Entrypoint
COPY --chown=prometheus:prometheus entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "prometheus.wsgi:application", "--config", "gunicorn.conf.py"]
