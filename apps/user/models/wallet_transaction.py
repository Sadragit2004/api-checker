# apps/user/models/wallet_transaction.py

from django.db import models


class WalletTransaction(models.Model):

    wallet = models.ForeignKey(
        "user.UserWallet",
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_banned = models.BooleanField(
        default=False,
    )

    class Meta:
        db_table = "wallet_transactions"
        verbose_name = "Wallet Transaction"
        verbose_name_plural = "Wallet Transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.wallet.user} - {self.amount}"