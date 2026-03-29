#!/bin/sh
set -e

SETTINGS=${DJANGO_SETTINGS_MODULE:-prometheus.settings.production}
echo "[Prometheus] Ambiente: $SETTINGS"

echo "[Prometheus] Aguardando banco de dados..."
until python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$SETTINGS')
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

# Staging: carregar fixtures se banco estiver vazio
if echo "$SETTINGS" | grep -q "staging"; then
    USER_COUNT=$(python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$SETTINGS')
django.setup()
from apps.accounts.models import Usuario
print(Usuario.objects.count())
" 2>/dev/null)

    if [ "$USER_COUNT" = "0" ]; then
        echo "[Prometheus] Staging: banco vazio — carregando dados de teste..."
        python manage.py reset_dev --no-input
    else
        echo "[Prometheus] Staging: banco ja populado ($USER_COUNT usuarios)."
    fi
fi

echo "[Prometheus] Coletando arquivos estaticos..."
python manage.py collectstatic --noinput

echo "[Prometheus] Iniciando aplicacao..."
exec "$@"
