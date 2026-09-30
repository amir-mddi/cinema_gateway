import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=False)


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "yes", "true", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-development-only")
DEBUG = env_bool("DEBUG", False)
if not DEBUG and len(SECRET_KEY) < 32:
    raise RuntimeError("DJANGO_SECRET_KEY must be set to a long secret in production")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8079").rstrip("/")
_public_scheme = urlparse(PUBLIC_BASE_URL).scheme.lower()

ALLOWED_HOSTS = [
    item.strip()
    for item in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if item.strip()
]
CSRF_TRUSTED_ORIGINS = [
    item.strip()
    for item in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if item.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "backend.apps.cinema.apps.CinemaConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.project.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "backend.project.wsgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "fa"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

if os.getenv("DATABASE_ENGINE", "sqlite").strip().lower() == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "cinema"),
            "USER": os.getenv("DB_USER", "cinema"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "db"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / os.getenv("SQLITE_PATH", "db/cinema.sqlite3"),
            "OPTIONS": {"timeout": 20},
        }
    }

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
ADMIN_TELEGRAM_IDS = frozenset(
    int(item.strip())
    for item in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",")
    if item.strip()
)
PROXY_URL = os.getenv("PROXY_URL", "").strip() or None

DELIVERY_MODE = os.getenv("DELIVERY_MODE", "forward").strip().lower()
if DELIVERY_MODE not in {"forward", "copy"}:
    raise RuntimeError("DELIVERY_MODE must be forward or copy")

MEDIA_TTL_SECONDS = int(os.getenv("MEDIA_TTL_SECONDS", "30"))
POST_CLICK_LIMIT = int(os.getenv("POST_CLICK_LIMIT", "5"))
BOT_REQUEST_TIMEOUT = float(os.getenv("BOT_REQUEST_TIMEOUT", "45"))
STORAGE_CHAT_ID = int(os.getenv("STORAGE_CHAT_ID", "0"))

# Reverse-proxy / cookie settings. For the current IP-only HTTP deployment,
# set SECURE_COOKIES=0 and SECURE_SSL_REDIRECT=0. Switch both to 1 behind HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_COOKIES = env_bool("SECURE_COOKIES", _public_scheme == "https")
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "backend.apps.cinema": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        }
    },
}
