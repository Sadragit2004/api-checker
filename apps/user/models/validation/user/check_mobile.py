import re

from django.core.exceptions import ValidationError


# ============================================================
# Constants
# ============================================================

_IRAN_MOBILE_PATTERN = re.compile(
    r"^09\d{9}$"
)


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
# Iranian Mobile Number
# ============================================================

def normalize_iranian_mobile_number(value: object) -> str:
    """
    Normalize an Iranian mobile number.

    Supported formats:

        09123456789
        +989123456789
        00989123456789
        ۰۹۱۲۳۴۵۶۷۸۹
        +۹۸۹۱۲۳۴۵۶۷۸۹
    """

    value = _normalize_digits(value)

    if not value:
        return ""

    # Remove common formatting characters.
    value = re.sub(
        r"[\s\-\(\)]",
        "",
        value,
    )

    # Convert international format to local format.
    if value.startswith("+98"):
        value = "0" + value[3:]

    elif value.startswith("0098"):
        value = "0" + value[4:]

    return value


def is_valid_iranian_mobile_number(value: object) -> bool:
    """
    Return True only when the value is a valid Iranian mobile number.
    """

    normalized = normalize_iranian_mobile_number(value)

    return bool(
        _IRAN_MOBILE_PATTERN.fullmatch(normalized)
    )


def validate_iranian_mobile_number(value: object) -> None:
    """
    Django validator for Iranian mobile numbers.

    Raises:
        ValidationError: if the number is invalid.
    """

    if not is_valid_iranian_mobile_number(value):
        raise ValidationError(
            message="شماره موبایل وارد شده معتبر نیست.",
            code="INVALID_MOBILE_NUMBER",
        )

# =================
