FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=odoo_web.settings

WORKDIR /app

RUN groupadd --system django && useradd --system --gid django --home-dir /app django

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --requirement requirements.txt

COPY --chown=django:django . ./

RUN mkdir -p /app/staticfiles && chown django:django /app/staticfiles

USER django

RUN DJANGO_DEBUG=false DJANGO_SECRET_KEY=collectstatic-build-only python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "odoo_web.wsgi:application", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
