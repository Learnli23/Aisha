from django.apps import AppConfig

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'  #  app's  name

    def ready(self):
        import app.signals  # This ensures signals.py is imported on app startup
