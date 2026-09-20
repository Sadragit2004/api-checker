
# apps/user/models/user.py

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from .managers import UserManager
from .validation.user import check_mobile
from .validation.user import check_nationcode


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"


class User(
    AbstractBaseUser,
    PermissionsMixin,
):

    first_name = models.CharField(
        max_length=100,
        blank=True,
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
    )

    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    mobile_number = models.CharField(
        max_length=15,
        unique=True,
        db_index=True,
        validators=[
            check_mobile.validate_iranian_mobile_number,
        ],
    )

    national_code = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        validators=[
            check_nationcode.validate_iranian_national_code,
        ],
    )

    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_staff = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "mobile_number"

    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

        verbose_name = "User"

        verbose_name_plural = "Users"

        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return self.mobile_number

