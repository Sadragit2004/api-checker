from rest_framework import serializers

from apps.user.models.user import User


class UserResponseSerializer(
    serializers.ModelSerializer,
):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "mobile_number",
        ]