from rest_framework_simplejwt.tokens import RefreshToken

from apps.user.models.user import User


def create_user_tokens(
    user: User,
) -> dict[str, str]:
    """
    Create JWT access and refresh tokens for a user.
    """

    refresh = RefreshToken.for_user(
        user,
    )

    return {
        "access_token": str(
            refresh.access_token,
        ),
        "refresh_token": str(
            refresh,
        ),
        "token_type": "Bearer",
    }