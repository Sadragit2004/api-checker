from apps.user.models.user import User


def get_user_by_mobile(
    mobile_number: str,
) -> User | None:
    """
    Return the user associated with the given mobile number.

    Returns:
        User: Existing user.
        None: User does not exist.
    """

    return (
        User.objects
        .filter(
            mobile_number=mobile_number,
        )
        .first()
    )


def create_user_if_mobile_available(
    *,
    mobile_number: str,
    **user_data,
) -> User | None:
    """
    Create a user only when the mobile number
    is not already registered.

    Returns:
        User: Created user.
        None: Mobile number already exists.
    """

    if get_user_by_mobile(mobile_number) is not None:
        return None

    return User.objects.create(
        mobile_number=mobile_number,
        **user_data,
    )