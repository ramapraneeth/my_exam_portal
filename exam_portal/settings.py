"""
Django settings for my_exam_portal project.
A mock test / online exam platform (AP EAPCET style), wired to use:
- Supabase Postgres as the database (instead of SQLite)
- Supabase Storage (S3-compatible) for candidate photo uploads
- All secrets/config read from environment variables (set in Render's
  dashboard in production, or a local .env file for local development)

See README.md for the full Supabase + Render setup walkthrough.
"""

from pathlib import Path
import os

import dj_database_url
from decouple import Config, RepositoryEnv, config as decouple_config

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------
# Locally: reads a .env file in the project root if one exists (for your own
#          machine only - never commit this file).
# On Render: .env is not used. Render injects environment variables directly
#          into the process, and decouple/os.environ read those exactly the
#          same way, so no code change is needed between the two.
_env_path = BASE_DIR / '.env'
if _env_path.exists():
    config = Config(RepositoryEnv(str(_env_path)))
else:
    config = decouple_config  # falls back to os.environ only

# ---------------------------------------------------------------------------
# Core security settings
# ---------------------------------------------------------------------------

# DEBUG controls whether Django shows full error pages (tracebacks, request
# info) or a generic error page. Set DEBUG=True in your environment variables
# while you're setting things up so you can SEE what's wrong when something
# breaks. Set DEBUG=False once everything works and real candidates use this,
# since debug pages can leak sensitive info (settings, secret key, etc.) to
# anyone who triggers an error.
DEBUG = config('DEBUG', default='True') == 'True'

# SECURITY WARNING: keep this secret in production. Set DJANGO_SECRET_KEY as
# an environment variable in Render's dashboard - never hardcode a real one
# here or commit it to git.
SECRET_KEY = config(
    'DJANGO_SECRET_KEY',
    default='django-insecure-local-dev-only-change-me'
)

# Comma-separated list, e.g. "my-exam-portal.onrender.com,localhost"
# "*" (the default) works everywhere but is not recommended once you have
# a real domain - see README.md's production checklist.
_allowed_hosts = config('ALLOWED_HOSTS', default='*')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(',') if h.strip()]

# Render provides this automatically for every web service - add it so the
# app accepts requests on its own *.onrender.com URL without you having to
# set ALLOWED_HOSTS by hand after every deploy.
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)

# Needed so Django trusts POST requests (login, answer-saving, submit)
# coming from your Render HTTPS domain - without this CSRF checks fail in
# production even though everything works fine locally.
CSRF_TRUSTED_ORIGINS = [f'https://{h}' for h in ALLOWED_HOSTS if h not in ('*', '')]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',  # django-storages: lets MEDIA files be saved to Supabase Storage
    'exams',     # our exam portal app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'exam_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'exam_portal.wsgi.application'

# ---------------------------------------------------------------------------
# Database - Supabase Postgres
# ---------------------------------------------------------------------------
# DATABASE_URL is a single connection string Supabase gives you, e.g.:
#   postgresql://postgres.xxxx:[email protected]:6543/postgres
# Set it as an environment variable (Render dashboard, or your local .env).
# See README.md for exactly where to copy this from in Supabase and why we
# use the *pooled* connection (port 6543) rather than the direct one (5432).
#
# If DATABASE_URL is not set at all (e.g. you haven't configured Supabase
# yet), this falls back to a local SQLite file purely so `manage.py check`
# and other commands don't crash with no DB configured - but the real,
# persistent database for this project is Supabase Postgres. Don't rely on
# this SQLite fallback for anything you want to keep.
DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files (CSS, JS) - served by WhiteNoise, NOT Supabase
# ---------------------------------------------------------------------------
# Static files (your style.css, exam.js) are part of the codebase itself,
# not user data, so they stay served by WhiteNoise from Render as before.
# Only MEDIA (user-uploaded candidate photos) moves to Supabase Storage below.
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# ---------------------------------------------------------------------------
# Media files (candidate photos) - Supabase Storage (S3-compatible)
# ---------------------------------------------------------------------------
# Why this matters: Render's free tier filesystem is *ephemeral* - anything
# saved to disk (like uploaded photos under MEDIA_ROOT) is WIPED on every
# restart/redeploy. Supabase Storage is a separate, persistent file bucket,
# so candidate photos survive restarts the same way your Postgres data does.
#
# These all come from environment variables - see README.md for exactly
# where to find each value in your Supabase project dashboard.
USE_SUPABASE_STORAGE = config('USE_SUPABASE_STORAGE', default='False') == 'True'

if USE_SUPABASE_STORAGE:
    AWS_ACCESS_KEY_ID = config('SUPABASE_S3_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = config('SUPABASE_S3_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = config('SUPABASE_S3_BUCKET_NAME', default='candidate-photos')
    AWS_S3_ENDPOINT_URL = config('SUPABASE_S3_ENDPOINT_URL', default='')
    AWS_S3_REGION_NAME = config('SUPABASE_S3_REGION', default='ap-south-1')
    AWS_S3_ADDRESSING_STYLE = 'path'
    AWS_DEFAULT_ACL = None  # bucket policy controls access; see README
    AWS_QUERYSTRING_AUTH = False  # plain public URLs, no expiring signature
    AWS_S3_FILE_OVERWRITE = False  # don't silently overwrite same-named uploads

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/object/public/{AWS_STORAGE_BUCKET_NAME}/"
else:
    # Local fallback: ordinary filesystem storage, same as the original
    # project. Used automatically until you set USE_SUPABASE_STORAGE=True.
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = 'media/'
    MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login redirect settings
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'test_list'
LOGOUT_REDIRECT_URL = 'login'
