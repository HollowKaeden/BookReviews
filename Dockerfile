FROM python:3.12-slim

# Не пишем .pyc и не буферизуем вывод, чтобы логи шли сразу.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Ставим проект из pyproject: pip тянет зависимости и кладёт сам пакет app.
COPY pyproject.toml ./
COPY app ./app
RUN pip install .

# Дальше то, что нужно в рантайме помимо кода.
COPY alembic ./alembic
COPY alembic.ini ./
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Работаем не от root, заодно готовим каталог под обложки.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
