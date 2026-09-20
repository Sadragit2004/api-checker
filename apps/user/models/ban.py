# apps/user/models/ban.py

from django.conf import settings
from django.db import models


class UserBan(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bans",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    reason = models.TextField(
        blank=True,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "user_bans"
        verbose_name = "User Ban"
        verbose_name_plural = "User Bans"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - Ban"