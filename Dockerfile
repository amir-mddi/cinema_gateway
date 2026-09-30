FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements.txt

COPY . /app

RUN mkdir -p /app/staticfiles /app/db \
    && chown -R app:app /app

USER app

EXPOSE 8079

CMD ["gunicorn", "backend.project.wsgi:application", "--bind", "0.0.0.0:8079", "--workers", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
