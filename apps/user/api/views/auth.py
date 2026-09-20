from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.user.api.serializers.auth import (
    LoginMobileSerializer,
    VerifyCodeSerializer,
)

from ...models.service.login import (
    check_login_mobile,
)

from ...models.service.verify import (
    verify_user_code,
)


# ============================================================
# Login - Mobile Number
# ============================================================

class LoginMobileView(
    APIView,
):
    """
    Start login process using mobile number.
    """

    def post(
        self,
        request,
    ):
        serializer = LoginMobileSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        response = check_login_mobile(
            mobile_number=serializer.validated_data[
                "mobile_number"
            ],
        )

        return Response(
            response,
            status=status.HTTP_200_OK,
        )


# ============================================================
# Login - Verification Code
# ============================================================

class VerifyCodeView(
    APIView,
):
    """
    Verify the authentication code
    and complete the login process.
    """

    def post(
        self,
        request,
    ):
        serializer = VerifyCodeSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        response = verify_user_code(
            mobile_number=serializer.validated_data[
                "mobile_number"
            ],
            code=serializer.validated_data[
                "code"
            ],
        )

        return Response(
            response,
            status=(
                status.HTTP_200_OK
                if response.get("success")
                else status.HTTP_400_BAD_REQUEST
            ),
        )