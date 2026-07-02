#!/bin/sh
set -e

# Прогоняем миграции до старта приложения. В compose сюда попадаем уже после
# healthcheck БД, так что Postgres готов принимать подключения.
echo "Applying database migrations..."
alembic upgrade head

# Через exec процесс из CMD становится PID 1 и получает сигналы напрямую,
# поэтому docker stop корректно гасит uvicorn.
exec "$@"
