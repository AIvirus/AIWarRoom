# AI WarRoom as a container image: the same box runs on a laptop and on a server.
#   docker build -t warroom .
#   docker compose up --build        (with a local PostgreSQL, see compose.yaml)

FROM python:3.12-slim

# Print logs straight away, don't write .pyc files, keep pip quiet and the image small,
# and be patient with slow networks (a classroom's Wi-Fi, say).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Dependencies first: this layer is reused until requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Then the code (.dockerignore keeps out .env, the virtual environment, the database...).
COPY . .

# Gather every static file into /app/staticfiles for WhiteNoise. Production settings
# insist on a secret key and a database URL, so give throwaway ones for this one command;
# collectstatic never connects to the database, and these values don't stay in the image.
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_SECRET_KEY=build-only-not-secret \
    DATABASE_URL=postgres://build:build@localhost:5432/build \
    python manage.py collectstatic --noinput

# Don't run as root: if the app were ever broken into, the intruder gets little.
RUN useradd --create-home --uid 10001 warroom
USER warroom

ENV DJANGO_SETTINGS_MODULE=config.settings.production \
    PORT=8000
EXPOSE 8000

# Bring the database up to date, then serve. Hosts like Render set PORT themselves.
# A long timeout because a website scan or an AI call can take 20 seconds or more.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi --bind 0.0.0.0:${PORT} --workers 2 --timeout 120 --access-logfile -"]
