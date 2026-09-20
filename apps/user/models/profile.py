# apps/user/models/profile.py

from django.conf import settings
from django.db import models


class UserProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    avatar = models.ImageField(
        upload_to="users/avatars/",
        null=True,
        blank=True,
    )

    bio = models.TextField(
        blank=True,
    )

    national_card_image = models.ImageField(
        upload_to="users/national_cards/",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "user_profiles"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user} Profile"