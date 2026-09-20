# apps/user/models/wallet.py

from django.conf import settings
from django.db import models


class UserWallet(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )

    balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "user_wallets"
        verbose_name = "User Wallet"
        verbose_name_plural = "User Wallets"

    def __str__(self):
        return f"{self.user} - {self.balance}"