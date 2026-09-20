from django.core.exceptions import ValidationError


# ============================================================
# Constants
# ============================================================

_DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


# ============================================================
# Helpers
# ============================================================

def _normalize_digits(value: object) -> str:
    """
    Convert Persian and Arabic digits to English digits.

    Returns:
        str: Normalized string or empty string for invalid input.
    """

    if not isinstance(value, str):
        return ""

    return value.strip().translate(_DIGIT_TRANSLATION)


# ============================================================
# Iranian National Code
# ============================================================

def normalize_iranian_national_code(value: object) -> str:
    """
    Normalize an Iranian national code.

    Supported:

        0012345678
        ۰۰۱۲۳۴۵۶۷۸
    """

    return _normalize_digits(value)


def is_valid_iranian_national_code(value: object) -> bool:
    """
    Validate an Iranian national code.

    Rules:

        - Exactly 10 digits.
        - Persian and Arabic digits are supported.
        - All digits cannot be identical.
        - Check digit must be valid according to the
          Iranian national code checksum algorithm.

    Returns:
        bool: True if valid, otherwise False.
    """

    national_code = normalize_iranian_national_code(value)

    # Must contain exactly 10 digits.
    if len(national_code) != 10:
        return False

    if not national_code.isdigit():
        return False

    # Reject values such as:
    # 0000000000
    # 1111111111
    # ...
    if len(set(national_code)) == 1:
        return False

    digits = [
        int(digit)
        for digit in national_code
    ]

    # Calculate checksum using the first 9 digits.
    checksum = sum(
        digits[index] * (10 - index)
        for index in range(9)
    )

    remainder = checksum % 11

    check_digit = digits[9]

    if remainder < 2:
        return check_digit == remainder

    return check_digit == 11 - remainder


def validate_iranian_national_code(value: object) -> None:
    """
    Django validator for Iranian national codes.

    Raises:
        ValidationError: if the national code is invalid.
    """

    if not is_valid_iranian_national_code(value):
        raise ValidationError(
            message="کد ملی وارد شده معتبر نیست.",
            code="INVALID_NATIONAL_CODE",
        )