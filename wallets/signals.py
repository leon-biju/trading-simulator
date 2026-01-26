from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Wallet
from django.conf import settings
from market.models import Currency


# Create a wallet for a new instance of User 
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallets(sender, instance, created, **kwargs): # type: ignore
    if created:
        Wallet.objects.bulk_create(
            [Wallet(user=instance, currency=currency, balance=0, pending_balance=0) for currency in Currency.objects.all()]
        )
        
        base_currency = Currency.objects.get(is_base=True)
        base_wallet = Wallet.objects.get(user=instance, currency=base_currency)
        base_wallet.balance = 100000
        base_wallet.save()