from apps.core.api.response import (
    error_response,
    success_response,
)

from apps.user.api.serializers.user import (
    UserResponseSerializer,
)

from .secret import (
    deactivate_secret,
    get_active_user_secret,
    is_secret_expired,
)
from .token import create_user_tokens
from .user import get_user_by_mobile


def verify_user_code(
    *,
    mobile_number: str,
    code: str,
) -> dict:

    user = get_user_by_mobile(
        mobile_number,
    )

    if user is None:
        return error_response(
            code="USER_NOT_FOUND",
            message="کاربری با این شماره موبایل یافت نشد.",
        )

    if not user.is_active:
        return error_response(
            code="USER_INACTIVE",
            message="حساب کاربری غیرفعال است.",
        )

    secret = get_active_user_secret(
        user,
    )

    if secret is None:
        return error_response(
            code="VERIFICATION_CODE_NOT_FOUND",
            message="کد تایید فعالی برای این شماره وجود ندارد.",
        )

    if is_secret_expired(
        secret,
    ):
        deactivate_secret(
            secret,
        )

        return error_response(
            code="VERIFICATION_CODE_EXPIRED",
            message="کد تایید منقضی شده است.",
        )

    if secret.code != code:
        return error_response(
            code="INVALID_VERIFICATION_CODE",
            message="کد تایید وارد شده صحیح نیست.",
        )

    deactivate_secret(
        secret,
    )

    tokens = create_user_tokens(
        user,
    )

    return success_response(
        data={
            "authenticated": True,
            **tokens,
            "user": UserResponseSerializer(
                user,
            ).data,
        },
    )