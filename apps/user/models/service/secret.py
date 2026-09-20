import secrets

from datetime import timedelta

from django.utils import timezone

from apps.user.models.secret import UserSecret
from apps.user.models.user import User


# ============================================================
# Constants
# ============================================================

VERIFICATION_CODE_LENGTH = 6
VERIFICATION_CODE_EXPIRE_MINUTES = 2


# ============================================================
# Create Verification Code
# ============================================================

def create_user_secret(
    *,
    user: User,
    expiry_minutes: int = VERIFICATION_CODE_EXPIRE_MINUTES,
) -> UserSecret:
    """
    Create a new verification code for a user.

    Any previous active verification codes are
    deactivated before creating the new code.
    """

    UserSecret.objects.filter(
        user=user,
        is_active=True,
    ).update(
        is_active=False,
    )

    code = (
        f"{secrets.randbelow(10 ** VERIFICATION_CODE_LENGTH):0{VERIFICATION_CODE_LENGTH}d}"
    )

    # ========================================================
    # Development Debug
    # ========================================================

    print("=" * 60)
    print("OTP CODE GENERATED")
    print(f"User ID : {user.pk}")
    print(f"Mobile  : {user.mobile_number}")
    print(f"Code    : {code}")
    print(f"Expires : {expiry_minutes} minute(s)")
    print("=" * 60)

    # ========================================================
    # Create Secret
    # ========================================================

    return UserSecret.objects.create(
        user=user,
        code=code,
        expires_at=timezone.now()
        + timedelta(
            minutes=expiry_minutes,
        ),
        is_active=True,
    )


# ============================================================
# Get Active Verification Code
# ============================================================

def get_active_user_secret(
    user: User,
) -> UserSecret | None:
    """
    Return the latest active verification code
    belonging to the given user.
    """

    return (
        UserSecret.objects
        .filter(
            user=user,
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )


# ============================================================
# Check Expiration
# ============================================================

def is_secret_expired(
    secret: UserSecret,
) -> bool:
    """
    Return True if the verification code has expired.
    """

    return timezone.now() >= secret.expires_at


# ============================================================
# Deactivate Verification Code
# ============================================================

def deactivate_secret(
    secret: UserSecret,
) -> None:
    """
    Deactivate verification code.
    """

    if secret.is_active:
        secret.is_active = False

        secret.save(
            update_fields=[
                "is_active",
            ],
        )