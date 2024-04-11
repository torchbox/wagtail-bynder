"""
Django settings for temp project.

For more information on this file, see
https://docs.djangoproject.com/en/stable/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/stable/ref/settings/
"""

import os

import dj_database_url


env = os.environ.copy()

# Build paths inside the project like this: os.path.join(PROJECT_DIR, ...)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "not-a-secret"  # noqa: S105

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "testserver"]


# Application definition

INSTALLED_APPS = [
    "wagtail_bynder",
    "testapp",
    "wagtail.users",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.admin",
    "wagtail.sites",
    "wagtail.snippets",
    "wagtail",
    "taggit",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "wagtail_bynder.middleware.PatchWagtailURLsMiddleware",
]

ROOT_URLCONF = "testapp.urls"

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


# Using DatabaseCache to make sure that the cache is cleared between tests.
# This prevents false-positives in some wagtail core tests where we are
# changing the 'wagtail_root_paths' key which may cause future tests to fail.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache",
    }
}


# don't use the intentionally slow default password hasher
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)


# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases

DATABASES = {
    "default": dj_database_url.config(default="sqlite:///test_wagtail_bynder.sqlite3"),
}


# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATICFILES_DIRS = [os.path.join(PROJECT_DIR, "static")]

STATIC_ROOT = os.path.join(PROJECT_DIR, "test-static")
STATIC_URL = "/static/"

MEDIA_ROOT = os.path.join(PROJECT_DIR, "test-media")


# Wagtail settings

WAGTAIL_SITE_NAME = "Wagtail Bynder test site"

WAGTAILIMAGES_IMAGE_MODEL = "testapp.CustomImage"
WAGTAILDOCS_DOCUMENT_MODEL = "testapp.CustomDocument"

# Bynder (DAMS)
# -----------------------------------------------------------------------------

BYNDER_DOMAIN = env.get("BYNDER_DOMAIN", "test-org.bynder.com")
BYNDER_API_TOKEN = env.get("BYNDER_API_TOKEN", None)
BYNDER_COMPACTVIEW_API_TOKEN = env.get("BYNDER_COMPACTVIEW_API_TOKEN", None)
BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME = env.get(
    "BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME", "WagtailSource"
)
BYNDER_DISABLE_WAGTAIL_EDITING_FOR_ASSETS = (
    env.get("BYNDER_DISABLE_WAGTAIL_EDITING_FOR_ASSETS", "false").lower() == "true"
)
BYNDER_SYNC_EXISTING_IMAGES_ON_CHOOSE = (
    env.get("BYNDER_SYNC_EXISTING_IMAGES_ON_CHOOSE", "false").lower() == "true"
)
BYNDER_SYNC_EXISTING_DOCUMENTS_ON_CHOOSE = (
    env.get("BYNDER_SYNC_EXISTING_DOCUMENTS_ON_CHOOSE", "false").lower() == "true"
)
# Video
BYNDER_VIDEO_MODEL = "testapp.Video"
BYNDER_VIDEO_PRIMARY_DERIVATIVE_NAME = env.get(
    "BYNDER_VIDEO_PRIMARY_DERIVATIVE_NAME", "WebPrimary"
)
BYNDER_VIDEO_FALLBACK_DERIVATIVE_NAME = env.get(
    "BYNDER_VIDEO_FALLBACK_DERIVATIVE_NAME", "WebFallback"
)
