from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Wallet
from django.conf import settings
from market.models import Currency

from market.services.fx import get_fx_conversion


from config.constants import STARTING_BALANCE


# Create a wallet for a new instance of User 
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallets(sender, instance, created, **kwargs): # type: ignore
    if created:
        Wallet.objects.bulk_create(
            [Wallet(user=instance, currency=currency, balance=0, pending_balance=0) for currency in Currency.objects.all()]
        )
        
        server_base_currency = Currency.objects.get(is_base=True)
        user_home_currency = getattr(instance, '_home_currency', None) or server_base_currency
        # convert to the user's home currency using the FX conversion service.
        _, converted_amount = get_fx_conversion(
            from_currency_code=server_base_currency.code,
            to_currency_code=user_home_currency.code,
            from_amount=STARTING_BALANCE,
            to_amount=None
        )
        home_wallet = Wallet.objects.get(user=instance, currency=user_home_currency)
        home_wallet.balance = converted_amount
        home_wallet.save()