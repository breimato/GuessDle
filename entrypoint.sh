#!/bin/sh
set -e

# Arranca cron
cron

# Lanza el bot de Discord en segundo plano
python bot_discord/bot.py &

echo "🔍 Verificando si hay migraciones pendientes..."
python manage.py migrate --noinput

python manage.py collectstatic --noinput

# Lanza el servidor Django
python manage.py runserver 0.0.0.0:8000
