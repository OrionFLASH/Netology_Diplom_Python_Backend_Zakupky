# Образ для локального запуска веб-приложения и воркера Celery (дипломный проект).
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# manage.py добавляет src в sys.path; воркер Celery стартует без manage.py — задаём PYTHONPATH явно.
ENV PYTHONPATH=/app/src:/app

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
