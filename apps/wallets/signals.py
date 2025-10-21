from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Wallet
from django.conf import settings

# Create a wallet for a new instance of User 
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance, balance=settings.STARTING_BALANCE)
        # Only new users get a wallet created loaded with 100,000 gbp