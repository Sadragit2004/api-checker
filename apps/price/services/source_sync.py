import json
import logging

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import jdatetime
import requests

from django.db import transaction

from apps.price.models import (
    Asset,
    CurrentPrice,
    PriceHistory,
    SourceAPI,
    SourceAPIMapping,
)


logger = logging.getLogger(__name__)


# ============================================================
# Configuration
# ============================================================

SOURCE_TIMEOUT = 20

MAX_SOURCE_TIME_DELAY_SECONDS = 7200   # ۲ ساعت

SOURCE_DEFAULT_TIMEZONE = ZoneInfo("Asia/Tehran")


# ============================================================
# Exceptions
# ============================================================

class SourceValidationError(Exception):
    pass


# ============================================================
# JSON Path Resolver
# ============================================================

def resolve_path(data, path):
    if not path:
        raise SourceValidationError("Source path is empty.")

    current = data

    for part in path.split("."):

        if isinstance(current, dict):

            if part not in current:
                raise SourceValidationError(f"Path not found: {path}")

            current = current[part]

        elif isinstance(current, list):

            try:
                index = int(part)
            except (TypeError, ValueError) as exc:
                raise SourceValidationError(
                    f"Invalid list index in path: {path}"
                ) from exc

            if index < 0 or index >= len(current):
                raise SourceValidationError(
                    f"List index out of range: {path}"
                )

            current = current[index]

        else:
            raise SourceValidationError(f"Cannot continue path: {path}")

    return current


# ============================================================
# Universal Finder: همه استراتژی‌ها در یک تابع
# ============================================================

def _walk_all(node):
    """
    پیمایش بازگشتی همه دیکشنری‌ها و لیست‌ها.
    خروجی: ژنراتور از (node, parent_dict, key_in_parent) ها
    """
    yield node, None, None

    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                for sub_node, parent, key in _walk_all(v):
                    yield sub_node, (node if parent is None else parent), (k if key is None else key)

    elif isinstance(node, list):
        for idx, item in enumerate(node):
            if isinstance(item, (dict, list)):
                for sub_node, parent, key in _walk_all(item):
                    yield sub_node, (node if parent is None else parent), (idx if key is None else key)


def universal_find_record(data, filter_field, filter_value):
    """
    جستجوی جهان‌شمول. همه حالت‌ها را پوشش می‌دهد.

    استراتژی‌ها به ترتیب اولویت:
    1. __key__ + value → کلید دیکشنری با آن نام
    2. field + value → آبجکتی که field در آن = value
    3. field → آبجکتی که field را دارد
    4. value (بدون field):
       a. به عنوان کلید
       b. به عنوان مقدار اسکالر
       c. به عنوان dot-path داخل هر آبجکت
    """

    ff = (filter_field or "").strip()
    fv = (filter_value or "").strip()

    # --------------------------------------------------------
    # 1. بدون فیلتر
    # --------------------------------------------------------
    if not ff and not fv:
        return data

    # --------------------------------------------------------
    # 2. __key__ + value  →  کلید دیکشنری
    # --------------------------------------------------------
    if ff == "__key__":
        if not fv:
            raise SourceValidationError(
                "Filter Value الزامی است وقتی Filter Field = __key__."
            )

        result = _find_by_dict_key(data, fv)
        if result is not None:
            return result

        raise SourceValidationError(f"Object key not found: {fv}")

    # --------------------------------------------------------
    # 3. field + value  →  آبجکتی که field = value
    # --------------------------------------------------------
    if ff and fv:
        result = _find_by_field_value(data, ff, fv)
        if result is not None:
            return result

        # تلاش: filter_field خودش dot-path است
        if "." in ff:
            result = _find_by_dotpath_value(data, ff, fv)
            if result is not None:
                return result

        raise SourceValidationError(
            f"Matching record not found: {ff}={fv}"
        )

    # --------------------------------------------------------
    # 4. فقط field
    # --------------------------------------------------------
    if ff and not fv:
        result = _find_by_field_only(data, ff)
        if result is not None:
            return result

        raise SourceValidationError(
            f"Filter Field not found: {ff}"
        )

    # --------------------------------------------------------
    # 5. فقط value  →  سه استراتژی
    # --------------------------------------------------------
    if fv and not ff:

        # a) کلید دیکشنری
        result = _find_by_dict_key(data, fv)
        if result is not None:
            return result

        # b) مقدار اسکالر
        result = _find_by_scalar_value(data, fv)
        if result is not None:
            return result

        # c) dot-path سراسری
        if "." in fv:
            result = _find_by_dotpath_value(data, fv, None)
            if result is not None:
                return result

        raise SourceValidationError(f"Filter Value not found: {fv}")

    return data


# ============================================================
# استراتژی‌های جستجو
# ============================================================

def _find_by_dict_key(data, key_name):
    """
    پیدا کردن مقدار دیکشنری با کلید مشخص در هر عمقی.
    مثال: data={"prices": {"GOLD18K": {...}}}, key="GOLD18K"
    → {"...GOLD18K content..."}
    """
    if isinstance(data, dict):
        if key_name in data:
            value = data[key_name]
            if isinstance(value, dict):
                return value

        for v in data.values():
            result = _find_by_dict_key(v, key_name)
            if result is not None:
                return result

    elif isinstance(data, list):
        for item in data:
            result = _find_by_dict_key(item, key_name)
            if result is not None:
                return result

    return None


def _find_by_field_value(data, field, value):
    """
    پیدا کردن آبجکتی که field در آن = value.
    """
    expected = str(value).strip()

    if isinstance(data, dict):
        if field in data:
            actual = str(data[field]).strip()
            if actual == expected:
                return data

        for v in data.values():
            result = _find_by_field_value(v, field, expected)
            if result is not None:
                return result

    elif isinstance(data, list):
        for item in data:
            result = _find_by_field_value(item, field, expected)
            if result is not None:
                return result

    return None


def _find_by_field_only(data, field):
    """
    پیدا کردن آبجکتی که field یک کلید داخلی دارد.
    """
    if isinstance(data, dict):
        if field in data:
            return data

        for v in data.values():
            result = _find_by_field_only(v, field)
            if result is not None:
                return result

    elif isinstance(data, list):
        for item in data:
            result = _find_by_field_only(item, field)
            if result is not None:
                return result

    return None


def _find_by_scalar_value(data, value):
    """
    پیدا کردن آبجکتی که یکی از مقادیر اسکالرش = value.
    """
    expected = str(value).strip()

    if isinstance(data, dict):
        for v in data.values():
            if not isinstance(v, (dict, list)):
                if str(v).strip() == expected:
                    return data

        for v in data.values():
            result = _find_by_scalar_value(v, expected)
            if result is not None:
                return result

    elif isinstance(data, list):
        for item in data:
            result = _find_by_scalar_value(item, expected)
            if result is not None:
                return result

    return None


def _find_by_dotpath_value(data, dotpath, value):
    """
    پیدا کردن آبجکتی که resolve_path روی آن dotpath برابر value می‌دهد.
    اگر value=None باشد، فقط resolve شدن کافیست.
    """
    expected = str(value).strip() if value is not None else None

    def walk(node):
        if isinstance(node, dict):
            try:
                resolved = resolve_path(node, dotpath)
                if expected is None or str(resolved).strip() == expected:
                    return node
            except SourceValidationError:
                pass

            for v in node.values():
                result = walk(v)
                if result is not None:
                    return result

        elif isinstance(node, list):
            for item in node:
                result = walk(item)
                if result is not None:
                    return result

        return None

    return walk(data)


# ============================================================
# Public API
# ============================================================

def resolve_source_record(source_api, data):
    return universal_find_record(
        data,
        source_api.filter_field or "",
        source_api.filter_value or "",
    )


# ============================================================
# Normalize Price
# ============================================================

def normalize_price(value):

    if value is None:
        raise SourceValidationError("Price is null.")

    try:
        price = Decimal(str(value).replace(",", "").strip())

    except (InvalidOperation, ValueError, TypeError) as exc:
        raise SourceValidationError("Price is not numeric.") from exc

    if not price.is_finite():
        raise SourceValidationError("Price is not finite.")

    if price <= 0:
        raise SourceValidationError("Price must be greater than zero.")

    return price


# ============================================================
# Normalize Time (میلادی + شمسی + Unix)
# ============================================================

GREGORIAN_FORMATS = (
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d",
    "%Y-%m-%d",
)

JALALI_FORMATS = (
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d",
    "%Y-%m-%d",
)


def _looks_like_jalali_year(date_string):
    year_str = date_string[:4]
    if not year_str.isdigit():
        return False
    year = int(year_str)
    return 1300 <= year <= 1500


def normalize_time_unix(value):

    if value is None:
        raise SourceValidationError("time_unix is null.")

    if isinstance(value, bool):
        raise SourceValidationError("time_unix is invalid.")

    raw_value = str(value).strip()

    if not raw_value:
        raise SourceValidationError("time_unix is empty.")

    # Unix
    try:
        numeric_value = int(raw_value)
        if numeric_value >= 10_000_000_000:
            numeric_value //= 1000
        if numeric_value <= 0:
            raise SourceValidationError("time_unix must be > 0.")
        return numeric_value
    except ValueError:
        pass

    # Datetime
    if isinstance(value, datetime):
        dt = value
    else:
        date_string = raw_value

        if date_string.endswith("Z"):
            date_string = date_string[:-1] + "+00:00"

        dt = None

        try:
            dt = datetime.fromisoformat(date_string)
        except ValueError:
            pass

        # میلادی
        if dt is None and not _looks_like_jalali_year(date_string):
            for fmt in GREGORIAN_FORMATS:
                try:
                    dt = datetime.strptime(date_string, fmt)
                    break
                except ValueError:
                    continue

        # شمسی
        if dt is None and _looks_like_jalali_year(date_string):
            for fmt in JALALI_FORMATS:
                try:
                    j_dt = jdatetime.datetime.strptime(date_string, fmt)
                    dt = j_dt.togregorian()
                    break
                except ValueError:
                    continue

        # آخرین تلاش
        if dt is None:
            for fmt in GREGORIAN_FORMATS:
                try:
                    dt = datetime.strptime(date_string, fmt)
                    break
                except ValueError:
                    continue

        if dt is None:
            raise SourceValidationError(
                f"Unsupported source time format: {value}"
            )

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SOURCE_DEFAULT_TIMEZONE)

    try:
        timestamp = int(dt.astimezone(timezone.utc).timestamp())
    except (OverflowError, ValueError, OSError) as exc:
        raise SourceValidationError(
            "Unable to convert source time to Unix timestamp."
        ) from exc

    if timestamp <= 0:
        raise SourceValidationError("time_unix must be > 0.")

    return timestamp


# ============================================================
# Server Time / Validation
# ============================================================

def get_server_timestamp():
    return int(datetime.now(timezone.utc).timestamp())


def validate_source_time(time_unix, max_delay=None):
    if max_delay is None:
        max_delay = MAX_SOURCE_TIME_DELAY_SECONDS

    server_time = get_server_timestamp()
    difference = abs(server_time - time_unix)

    if difference > max_delay:
        raise SourceValidationError(
            f"Source time is too old/new. difference={difference}s"
        )

    return True


# ============================================================
# Calculate Change
# ============================================================

def calculate_change_percent(old_price, new_price):

    if old_price is None:
        return Decimal("0")

    old_price = Decimal(old_price)
    new_price = Decimal(new_price)

    if old_price <= 0:
        raise SourceValidationError("Previous price is invalid.")

    change = abs(new_price - old_price)
    return change / old_price * Decimal("100")


# ============================================================
# Source Mapping
# ============================================================

def get_source_mapping(source_api):

    mappings = source_api.mappings.filter(is_active=True)

    mapping_map = {}

    for mapping in mappings:
        mapping_map[mapping.target_field] = mapping.source_path

    return mapping_map


# ============================================================
# Deep Merge
# ============================================================

def deep_merge(base, extra):

    if not isinstance(base, dict):
        base = {}

    if not isinstance(extra, dict):
        return base

    result = dict(base)

    for key, value in extra.items():

        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


# ============================================================
# Parse Request Script
# ============================================================

def parse_request_script(source_api):

    script = source_api.request_script or {}

    if isinstance(script, str):
        script = script.strip()
        if not script:
            return {}
        try:
            script = json.loads(script)
        except (TypeError, ValueError) as exc:
            raise SourceValidationError(
                "Request Script must contain valid JSON."
            ) from exc

    if not isinstance(script, dict):
        raise SourceValidationError(
            "Request Script must be a JSON object."
        )

    allowed_keys = {
        "headers", "query", "body",
        "form", "raw_body", "content_type",
    }

    unknown_keys = set(script.keys()) - allowed_keys
    if unknown_keys:
        raise SourceValidationError(
            "Unsupported Request Script fields: "
            + ", ".join(sorted(unknown_keys))
        )

    if "headers" in script and not isinstance(script["headers"], dict):
        raise SourceValidationError("headers must be JSON object.")
    if "query" in script and not isinstance(script["query"], dict):
        raise SourceValidationError("query must be JSON object.")
    if "body" in script and not isinstance(script["body"], dict):
        raise SourceValidationError("body must be JSON object.")
    if "form" in script and not isinstance(script["form"], dict):
        raise SourceValidationError("form must be JSON object.")
    if "raw_body" in script and not isinstance(script["raw_body"], str):
        raise SourceValidationError("raw_body must be string.")
    if "content_type" in script and not isinstance(script["content_type"], str):
        raise SourceValidationError("content_type must be string.")

    body_modes = sum(
        v is not None
        for v in (
            script.get("body"),
            script.get("form"),
            script.get("raw_body"),
        )
    )

    if body_modes > 1:
        raise SourceValidationError(
            "Only one of body, form or raw_body."
        )

    return script


# ============================================================
# Build Request
# ============================================================

def build_source_request(source_api):

    method = (source_api.method or SourceAPI.Method.GET).upper()

    if method not in (SourceAPI.Method.GET, SourceAPI.Method.POST):
        raise SourceValidationError("Only GET and POST.")

    headers = {
        "Accept": "application/json",
        "User-Agent": "ApiPrice-MarketWorker/1.0",
    }

    params = {}
    json_body = {}
    form_data = {}
    raw_body = ""
    content_type = ""

    script = parse_request_script(source_api)

    script_headers = script.get("headers", {})
    if script_headers:
        headers.update({str(k): str(v) for k, v in script_headers.items()})

    script_query = script.get("query", {})
    if script_query:
        params.update(script_query)

    script_body = script.get("body", {})
    if script_body:
        json_body = deep_merge(json_body, script_body)

    script_form = script.get("form", {})
    if script_form:
        form_data.update(script_form)

    if "raw_body" in script:
        raw_body = script.get("raw_body") or ""

    if "content_type" in script:
        content_type = (script.get("content_type") or "").strip()

    if not content_type:
        content_type = (headers.get("Content-Type", "") or "").strip()

    if content_type:
        headers["Content-Type"] = content_type

    token = (source_api.header_token or "").strip()
    if token:
        if token.lower().startswith("bearer "):
            headers["Authorization"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"

    return {
        "method": method,
        "url": source_api.url,
        "headers": headers,
        "params": params,
        "json": json_body,
        "data": form_data,
        "raw_body": raw_body,
        "content_type": content_type,
    }


# ============================================================
# HTTP Request
# ============================================================

def request_source_api(source_api):

    cfg = build_source_request(source_api)

    request_kwargs = {
        "method": cfg["method"],
        "url": cfg["url"],
        "timeout": SOURCE_TIMEOUT,
        "headers": cfg["headers"],
    }

    if cfg["params"]:
        request_kwargs["params"] = cfg["params"]

    if cfg["raw_body"]:
        request_kwargs["data"] = cfg["raw_body"]

    elif cfg["content_type"] == "multipart/form-data":
        request_kwargs["data"] = cfg["data"]
        request_kwargs["headers"].pop("Content-Type", None)

    elif cfg["content_type"] == "application/x-www-form-urlencoded":
        request_kwargs["data"] = cfg["data"]

    elif cfg["content_type"] == "application/json":
        if cfg["json"] or cfg["method"] == SourceAPI.Method.POST:
            request_kwargs["json"] = cfg["json"]

    elif cfg["json"]:
        request_kwargs["json"] = cfg["json"]

    try:
        response = requests.request(**request_kwargs)
    except requests.RequestException as exc:
        raise SourceValidationError(
            f"Source request failed: {exc}"
        ) from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise SourceValidationError(
            f"Source returned HTTP {response.status_code}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise SourceValidationError(
            "Source response is not valid JSON."
        ) from exc

    if data is None:
        raise SourceValidationError("Source response is empty.")

    return data


# ============================================================
# Parse Source Response
# ============================================================

def parse_source_response(source_api, data):

    record = resolve_source_record(source_api, data)

    mapping = get_source_mapping(source_api)

    price_path = mapping.get(SourceAPIMapping.TargetField.PRICE)
    time_path = mapping.get(SourceAPIMapping.TargetField.TIME_UNIX)

    if not price_path:
        raise SourceValidationError("price mapping missing.")
    if not time_path:
        raise SourceValidationError("time_unix mapping missing.")

    raw_price = resolve_path(record, price_path)
    raw_time = resolve_path(record, time_path)

    price = normalize_price(raw_price)
    time_unix = normalize_time_unix(raw_time)

    return {
        "record": record,
        "price": price,
        "time_unix": time_unix,
    }


# ============================================================
# Last Valid Price
# ============================================================

def get_last_valid_price(asset):
    return (
        PriceHistory.objects
        .filter(asset=asset)
        .order_by("-time_unix", "-id")
        .first()
    )


# ============================================================
# Validate Price Change
# ============================================================

def validate_price_change(asset, new_price):

    previous = get_last_valid_price(asset)

    if previous is None:
        return {
            "valid": True,
            "change_percent": Decimal("0"),
            "previous_price": None,
        }

    change_percent = calculate_change_percent(previous.price, new_price)

    max_change = Decimal(asset.category.max_price_change_percent)

    if change_percent > max_change:
        raise SourceValidationError(
            f"Price change too high. "
            f"change={change_percent:.3f}% max={max_change:.3f}%"
        )

    return {
        "valid": True,
        "change_percent": change_percent,
        "previous_price": previous.price,
    }


# ============================================================
# Save Valid Price
# ============================================================

@transaction.atomic
def save_valid_price(source_api, price, time_unix):

    asset = source_api.asset

    history = PriceHistory.objects.create(
        asset=asset,
        source_api=source_api,
        price=price,
        time_unix=time_unix,
    )

    current_price, _ = CurrentPrice.objects.update_or_create(
        asset=asset,
        defaults={
            "source_api": source_api,
            "price": price,
            "time_unix": time_unix,
        },
    )

    return {
        "history": history,
        "current_price": current_price,
    }


# ============================================================
# Validate + Save One Source
# ============================================================

def validate_and_save_source(source_api):

    data = request_source_api(source_api)
    parsed = parse_source_response(source_api, data)

    price = parsed["price"]
    time_unix = parsed["time_unix"]

    validate_source_time(time_unix)

    validation = validate_price_change(source_api.asset, price)

    saved = save_valid_price(
        source_api=source_api,
        price=price,
        time_unix=time_unix,
    )

    return {
        "success": True,
        "asset": source_api.asset.symbol,
        "source": source_api.name,
        "price": price,
        "time_unix": time_unix,
        "change_percent": validation["change_percent"],
        "history_id": saved["history"].id,
    }


# ============================================================
# Sync One Asset
# ============================================================

def sync_asset(asset):

    sources = (
        SourceAPI.objects
        .filter(asset=asset, is_active=True)
        .prefetch_related("mappings")
        .order_by("priority", "id")
    )

    if not sources.exists():
        return {
            "success": False,
            "asset": asset.symbol,
            "reason": "no_active_source",
        }

    rejected_sources = []

    for source_api in sources:

        try:
            result = validate_and_save_source(source_api)

            logger.info(
                "Source accepted | asset=%s | source=%s | "
                "price=%s | time=%s | change=%s%%",
                asset.symbol,
                source_api.name,
                result["price"],
                result["time_unix"],
                result["change_percent"],
            )

            return result

        except SourceValidationError as exc:

            reason = str(exc)

            rejected_sources.append({
                "source": source_api.name,
                "reason": reason,
            })

            logger.warning(
                "Source rejected | asset=%s | source=%s | reason=%s",
                asset.symbol,
                source_api.name,
                reason,
            )

            continue

        except Exception:

            logger.exception(
                "Unexpected source error | asset=%s | source=%s",
                asset.symbol,
                source_api.name,
            )

            rejected_sources.append({
                "source": source_api.name,
                "reason": "unexpected_error",
            })

            continue

    return {
        "success": False,
        "asset": asset.symbol,
        "reason": "all_sources_rejected",
        "rejected_sources": rejected_sources,
    }


# ============================================================
# Sync All Assets
# ============================================================

def sync_all_assets():

    assets = (
        Asset.objects
        .filter(is_active=True, category__is_active=True)
        .select_related("category")
    )

    results = []

    for asset in assets:
        results.append(sync_asset(asset))

    return results