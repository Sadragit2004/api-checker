# apps/user/models/login.py

from django.conf import settings
from django.db import models


class UserLogin(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="login_history",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "user_logins"
        verbose_name = "User Login"
        verbose_name_plural = "User Logins"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.created_at}"