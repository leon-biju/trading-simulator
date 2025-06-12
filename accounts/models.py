from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    cash_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("100000.00"))
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user.username}"