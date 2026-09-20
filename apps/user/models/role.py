# apps/user/models/role.py

from django.db import models


class Role(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    api_access = models.BooleanField(
        default=False,
    )

    url_access = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "roles"
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["name"]

    def __str__(self):
        return self.name