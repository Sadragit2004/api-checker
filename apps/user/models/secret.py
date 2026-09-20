# apps/user/models/secret.py

from django.conf import settings
from django.db import models


class UserSecret(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="secrets",
    )

    code = models.CharField(
        max_length=128,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    expires_at = models.DateTimeField()

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "user_secrets"
        verbose_name = "User Secret"
        verbose_name_plural = "User Secrets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.code}"