"""
Django settings for aisha project.

Generated by 'django-admin startproject' using Django 5.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""
from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-devb7q#%p=4y1#bt)6l6=#5fm4r+n*d7g-5n%i8tox9(nlx=vd'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["aisha-production-2f63.up.railway.app", ]
CSRF_TRUSTED_ORIGINS = ['https://aisha-production-2f63.up.railway.app']
CORS_ALLOWED_ORIGINS = [
    "https://aisha-production-2f63.up.railway.app",  
]


# Application definition

INSTALLED_APPS = [
    "jazzmin",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',
    'corsheaders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'corsheaders.middleware.CorsMiddleware',  
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'aisha.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR,'templates')],
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

WSGI_APPLICATION = 'aisha.wsgi.application'
#JAZZMIN SETTINGS
JAZZMIN_SETTINGS = {
    "topmenu_links": [
        {
            "name": "HOME PAGE",
            "url": "https://aisha-production-2f63.up.railway.app/",
            "new_window": False,
            "permissions": ["is_superuser"],
            "icon": "fas fa-home",
        },
    ],
    "site_url": "",  #removes default “View site” if you just want HOME PAGE
    "site_title": "IUIU Admin",
    "site_header": "IUIU Dashboard",
    "site_brand": "IUIU",
    "welcome_sign": "Welcome to the IUIU Admin Portal",
    "copyright": "IUIU",
    #"site_logo": "static/images/iuiu-logo.png",  # optional
   # "login_logo": "static/images/iuiu-logo.png",  # optional
   # "login_logo_dark": "static/images/iuiu-logo.png",  # optional

    "search_model": [
        "app.Student"
    ],

    "show_sidebar": True,
    "navigation_expanded": True,
    "order_with_respect_to": ["app"],

    "icons": {
        "auth": "fas fa-users-cog",
        "auth.User": "fas fa-user",
        "app.Student": "fas fa-user-graduate",
        "app.Faculty": "fas fa-university",
        "app.Course": "fas fa-book",
        "app.AcademicRecord": "fas fa-file-alt",
        "app.AttritionAnalysisResult": "fas fa-chart-line",
    },

    "changeform_format": "horizontal_tabs",  # Options: "single", "collapsible", "horizontal_tabs"
}


 
# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases


'''
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

'''

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        #ssl_require=True
    )
}





# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGOUT_REDIRECT_URL = 'home'  # or any other URL name




 
