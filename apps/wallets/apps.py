from django.apps import AppConfig


class WalletsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.wallets'
    
    def ready(self):
        import apps.wallets.signals
