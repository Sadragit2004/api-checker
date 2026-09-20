# apps/core/api/errors.py

from typing import Any


def validation_error_response(
    fields: dict[str, dict[str, str]],
    message: str = "اطلاعات وارد شده صحیح نیست.",
    code: str = "VALIDATION_ERROR",
) -> dict[str, Any]:
    """
    Build a unified validation error response.

    The fields object is completely dynamic.
    """

    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "fields": fields,
        },
    }