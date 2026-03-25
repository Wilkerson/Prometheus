#!/bin/sh
set -e

echo "Aguardando banco de dados..."
while ! python -c "
import psycopg
conn = psycopg.connect(
    dbname='${DB_NAME}',
    user='${DB_USER}',
    password='${DB_PASSWORD}',
    host='${DB_HOST}',
    port='${DB_PORT}'
)
conn.close()
" 2>/dev/null; do
    sleep 1
done
echo "Banco de dados disponível."

echo "Aplicando migrações..."
python manage.py migrate --noinput

echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

exec "$@"
