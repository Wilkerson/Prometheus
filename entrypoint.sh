#!/bin/sh
set -e

echo "[Prometheus] Aguardando banco de dados..."
until python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prometheus.settings.production')
django.setup()
from django.db import connection
connection.ensure_connection()
" 2>/dev/null; do
    echo "[Prometheus] DB nao disponivel, tentando em 2s..."
    sleep 2
done
echo "[Prometheus] Banco de dados disponivel."

echo "[Prometheus] Aplicando migracoes..."
python manage.py migrate --noinput

echo "[Prometheus] Configurando grupos e permissoes..."
python manage.py setup_groups

echo "[Prometheus] Coletando arquivos estaticos..."
python manage.py collectstatic --noinput

echo "[Prometheus] Iniciando aplicacao..."
exec "$@"
