from apps.core.api.response import (
    error_response,
    success_response,
)

from apps.user.api.serializers.secret import (
    UserSecretSerializer,
)

from .secret import (
    create_user_secret,
    deactivate_secret,
    get_active_user_secret,
    is_secret_expired,
)

from .user import (
    create_user_if_mobile_available,
    get_user_by_mobile,
)


def _build_login_data(
    *,
    user,
    secret,
) -> dict:
    """
    Build login response data from User
    and UserSecret models.
    """

    return {
        "mobile_number": user.mobile_number,
        **UserSecretSerializer(secret).data,
    }


def check_login_mobile(
    mobile_number: str,
) -> dict:
    """
    Check login status for a mobile number.

    Creates the user if the mobile number
    is not already registered.

    Creates a new verification code if:
        - No active code exists.
        - The previous code has expired.
    """

    # ========================================================
    # Get or Create User
    # ========================================================

    user = get_user_by_mobile(
        mobile_number,
    )

    if user is None:
        user = create_user_if_mobile_available(
            mobile_number=mobile_number,
        )

    if user is None:
        return error_response(
            code="USER_CREATION_FAILED",
            message="ایجاد کاربر انجام نشد.",
        )

    # ========================================================
    # Check User Status
    # ========================================================

    if not user.is_active:
        return error_response(
            code="USER_INACTIVE",
            message="حساب کاربری غیرفعال است.",
        )

    # ========================================================
    # Get Active Secret
    # ========================================================

    secret = get_active_user_secret(
        user,
    )

    # ========================================================
    # Create Secret
    # ========================================================

    if secret is None:
        secret = create_user_secret(
            user=user,
        )

    # ========================================================
    # Expired Secret
    # ========================================================

    elif is_secret_expired(secret):
        deactivate_secret(
            secret,
        )

        secret = create_user_secret(
            user=user,
        )

    # ========================================================
    # Response
    # ========================================================

    return success_response(
        data=_build_login_data(
            user=user,
            secret=secret,
        ),
    )