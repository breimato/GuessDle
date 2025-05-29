#!/bin/sh
set -e

# Arranca cron
cron

# Lanza el servidor Django
python manage.py runserver 0.0.0.0:8000
