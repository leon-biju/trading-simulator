from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Wallet
from django.conf import settings
from .models import Currency

# Create a wallet for a new instance of User 
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallets(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.bulk_create(
            [Wallet(user=instance, currency=cur.value, balance=0) for cur in Currency]
        )
        # Set gbp wallet balance to £100,000
        wallet = Wallet.objects.get(user=instance, currency='GBP')
        wallet.balance = 100000
        wallet.save()