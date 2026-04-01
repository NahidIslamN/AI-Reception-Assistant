
from decouple import config

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")


DEBUG = config("DEBUG")

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'auths.apps.AuthsConfig',
    'rest_framework',
    'rest_framework_simplejwt',    
    'chats',
    'django_celery_beat',
    'ai_striming',
    'admin_dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'chats.middleware.UpdateLastActivityMiddleware',
    'auths.middleware.last_activity.UpdateLastActivityMiddleware',
]

ROOT_URLCONF = 'AI_Strming.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI_APPLICATION = 'DjangoApp.wsgi.application'


ASGI_APPLICATION = 'AI_Strming.asgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': config("ENGINE"),
        'NAME': BASE_DIR / config("NAME"),
    }
}


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'postgres',
#         'USER': 'postgres',
#         'PASSWORD': 'your-password',
#         'HOST': 'db.xxxx.supabase.co',
#         'PORT': '5432',
#     }
# }





###### Must be add db credrintilal to env when it go to production


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]




REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],

    'DEFAULT_THROTTLE_RATES': {
        'user': '30/min',   # logged-in users: max 30 requests per minute
        'anon': '5/min',    # anonymous users: max 5 requests per minute
    }

}


from datetime import timedelta


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=3600),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}


# 03. Define CustomUser Model in settings

AUTH_USER_MODEL = 'auths.CustomUser'



# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

import os
STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "public/static"),
    os.path.join(BASE_DIR, "static")
]

MEDIA_ROOT = os.path.join(BASE_DIR, 'public/static')
MEDIA_URL = 'api/v1/media/'




EMAIL_BACKEND=config("EMAIL_BACKEND")
EMAIL_HOST=config("EMAIL_HOST")
EMAIL_PORT=config("EMAIL_PORT")
EMAIL_USE_TLS=config("EMAIL_USE_TLS")
EMAIL_HOST_USER=config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD=config("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL=config("DEFAULT_FROM_EMAIL")


# STRIPE_TEST_SECRET_KEY = config('STRIPE_TEST_SECRET_KEY')
# STRIPE_TEST_PUBLIC_KEY = config('STRIPE_TEST_SECRET_KEY')




CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
