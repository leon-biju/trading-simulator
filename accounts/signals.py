# mypy: disable-error-code=no-untyped-def

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile
from django.conf import settings
    
from market.models import Currency


# Create a profile for a new instance of User 
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        home_currency = getattr(instance, '_home_currency', None)
        if home_currency is None:
            home_currency = Currency.objects.get(code='USD')
        Profile.objects.create(user=instance, home_currency=home_currency)