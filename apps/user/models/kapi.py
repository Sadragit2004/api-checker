import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class ApiKeyPlan(models.TextChoices):
    LITE = "lite", "Lite"
    PRO = "pro", "Pro"


class ApiKey(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )

    name = models.CharField(
        max_length=100,
        blank=True,
    )

    key_prefix = models.CharField(
        max_length=20,
        db_index=True,
        editable=False,
    )

    key_hash = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
    )

    plan = models.CharField(
        max_length=10,
        choices=ApiKeyPlan.choices,
        default=ApiKeyPlan.LITE,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "api_keys"
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return f"{self.name or 'API Key'} - {self.plan}"

    # ---------------------------------------------------------
    # Key generation
    # ---------------------------------------------------------

    @staticmethod
    def generate_key():
        """
        Generate a new raw API key.

        Example:
      
        """

        return f"sk_live_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_key(raw_key: str):
        """
        Hash the raw API key before storing it in database.
        """

        return hashlib.sha256(
            raw_key.encode("utf-8")
        ).hexdigest()

    @classmethod
    def create_key(
        cls,
        *,
        user,
        name="",
        plan=ApiKeyPlan.LITE,
        expires_at=None,
    ):
        """
        Create a new API key.

        Returns:
            instance
            raw_key

        Important:
        raw_key is returned only once and is NOT stored in database.
        """

        raw_key = cls.generate_key()

        instance = cls(
            user=user,
            name=name,
            plan=plan,
            expires_at=expires_at,
            key_prefix=raw_key[:20],
            key_hash=cls.hash_key(raw_key),
        )

        instance.save()

        return instance, raw_key

    # ---------------------------------------------------------
    # Status
    # ---------------------------------------------------------

    @property
    def is_expired(self):
        if self.expires_at is None:
            return False

        return timezone.now() >= self.expires_at

    @property
    def usable(self):
        return (
            self.is_active
            and not self.is_expired
        )

    # ---------------------------------------------------------
    # Usage
    # ---------------------------------------------------------

    def mark_used(self):
        self.last_used_at = timezone.now()

        self.save(
            update_fields=[
                "last_used_at",
            ]
        )