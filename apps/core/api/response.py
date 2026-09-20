from typing import Optional, Dict, Any


def api_response(
    *,
    success: bool,
    data: Any = None,
    error: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a unified API response.

    Success:
        {
            "success": True,
            "data": {...}
        }

    Error:
        {
            "success": False,
            "error": {...}
        }
    """

    response: Dict[str, Any] = {
        "success": success,
    }

    if success:
        response["data"] = data
    else:
        response["error"] = error

    return response


def success_response(
    data: Any = None,
) -> Dict[str, Any]:
    """
    Build a successful API response.
    """

    return api_response(
        success=True,
        data=data,
    )


def error_response(
    *,
    code: str,
    message: str,
    fields: Optional[Dict[str, Dict[str, str]]] = None,
    details: Any = None,
) -> Dict[str, Any]:
    """
    Build a unified API error response.
    """

    error: Dict[str, Any] = {
        "code": code,
        "message": message,
    }

    if fields:
        error["fields"] = fields

    if details is not None:
        error["details"] = details

    return api_response(
        success=False,
        error=error,
    )