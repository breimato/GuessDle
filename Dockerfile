FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# ─── 2. Instala dependencias del sistema (cron + tzdata) ──────────────────────
RUN apt-get update \
 && apt-get install -y --no-install-recommends cron tzdata \
 && ln -fs /usr/share/zoneinfo/Europe/Madrid /etc/localtime \
 && dpkg-reconfigure -f noninteractive tzdata \
 && rm -rf /var/lib/apt/lists/*

# ─── 3. Copia requirements y las instala ──────────────────────────────────────
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# ─── 4. Copia el código fuente ────────────────────────────────────────────────
COPY . /app/

# ─── 5. Añade la tarea cron ───────────────────────────────────────────────────
#  - 0 23 * * * → a las 23:00 todos los días
#  - redireccionamos stdout/err al log /var/log/cron.log
RUN echo '0 23 * * * cd /app && /usr/local/bin/python manage.py generate_daily_targets >> /var/log/cron.log 2>&1' \
    > /etc/cron.d/daily_targets \
 && chmod 0644 /etc/cron.d/daily_targets \
 && crontab /etc/cron.d/daily_targets

# ─── 6. Copia el entrypoint y dale permisos ───────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
