from rest_framework import serializers


class LoginMobileSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(
        max_length=15,
    )





class VerifyCodeSerializer(
    serializers.Serializer,
):
    mobile_number = serializers.CharField(
        max_length=15,
    )

    code = serializers.CharField(
        max_length=128,
    )