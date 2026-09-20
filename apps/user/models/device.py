# apps/user/models/device.py

from django.conf import settings
from django.db import models


class UserDevice(models.Model):

    class DeviceType(models.TextChoices):
        MOBILE = "mobile", "Mobile"
        TABLET = "tablet", "Tablet"
        DESKTOP = "desktop", "Desktop"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="devices",
    )

    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "user_devices"
        verbose_name = "User Device"
        verbose_name_plural = "User Devices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.device_type}"