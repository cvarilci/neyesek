"""
config projesi için Django ayarları.

Sırlar ve ortama özgü değerler `.env` dosyasından okunur (bkz. `.env.example`).
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _env_list(name):
    value = os.environ.get(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ["SECRET_KEY"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS")

CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "recipes",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# Vercel sunucusuz olduğu için Supabase'e bağlanırken connection pooler
# (transaction mode, port 6543) kullanılır. CONN_MAX_AGE=0 ve
# DISABLE_SERVER_SIDE_CURSORS=True bu mod ile uyum için zorunludur.

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=0)
    }
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
else:
    # DATABASE_URL tanımlı değilse yerel geliştirme için SQLite kullanılır.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "tr"

TIME_ZONE = "Europe/Istanbul"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Tıklama kaçırma (clickjacking) koruması
X_FRAME_OPTIONS = "DENY"


# Kimlik doğrulama (django-allauth) — Faz 4
# https://docs.allauth.org/en/latest/account/configuration.html

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_SIGNUP_FORM_CLASS = "accounts.forms.NameSignupForm"
# Prototip: e-posta doğrulaması zorunlu değil ama gönderilir (konsola yazılır).
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_UNIQUE_EMAIL = True

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "recipes:home"
ACCOUNT_LOGOUT_REDIRECT_URL = "recipes:home"

# allauth'un hız sınırlama sayaçları Django'nun cache framework'ünü kullanır.
# CACHES tanımlanmazsa varsayılan LocMemCache devreye girer; bu, tek bir Python
# sürecine özeldir ve Vercel'in sunucusuz (serverless) ortamındaki birden fazla
# fonksiyon örneği arasında PAYLAŞILMAZ — yani ACCOUNT_RATE_LIMITS sessizce
# etkisiz kalabilir. Yeni bir bağımlılık eklemeden paylaşılan bir önbellek için
# veritabanı tabanlı cache kullanılıyor (Supabase Postgres, yerelde SQLite).
# Tabloyu oluşturmak için: python manage.py createcachetable
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache_table",
    }
}

# Giriş denemelerinde ve hassas allauth uç noktalarında hız sınırı.
# Ayarlanmazsa ACCOUNT_RATE_LIMITS varsayılanı boş sözlüktür, yani sınırsız
# deneme yapılabilir — Faz 5 güvenlik gözden geçirmesiyle bilinçli olarak eklendi.
ACCOUNT_RATE_LIMITS = {
    "login": "30/m/ip",
    "login_failed": "10/m/ip,5/5m/key",
    "signup": "20/m/ip",
    "reset_password": "20/m/ip,5/m/key",
    "reset_password_from_key": "20/m/ip",
    "change_password": "5/m/user",
    "manage_email": "10/m/user",
    "confirm_email": "1/3m/key",
}

# Geliştirmede gerçek e-posta servisi yok; e-postalar konsola yazılır.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# Üretim güvenlik başlıkları — yalnızca DEBUG=False iken etkin.
# Vercel (ve çoğu ters proxy) isteği HTTPS olarak karşılayıp uygulamaya HTTP
# olarak iletir; SECURE_PROXY_SSL_HEADER olmadan SECURE_SSL_REDIRECT sonsuz
# yönlendirme döngüsüne girer.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7  # 1 hafta; sorun çıkmazsa artırılabilir
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
