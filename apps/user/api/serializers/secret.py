# apps/user/api/serializers/secret.py

from rest_framework import serializers

from apps.user.models.secret import UserSecret


class UserSecretSerializer(
    serializers.ModelSerializer,
):
    class Meta:
        model = UserSecret

        fields = (
            "code",
            "created_at",
            "expires_at",
            "is_active",
        )