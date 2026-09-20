import hashlib
import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from .services.service import get_market_data, get_plan_from_key


logger = logging.getLogger(__name__)


# ============================================================
# Type mapping
# ============================================================

TYPE_MAP = {
    "realtime": "realtime",
    "real-time": "realtime",
    "live": "realtime",

    "24h": "history24h",
    "history-24h": "history24h",
    "history24h": "history24h",

    "hourly": "historyhourly",
    "hour": "historyhourly",
    "history-hourly": "historyhourly",
    "historyhourly": "historyhourly",

    "daily": "historydaily",
    "dayli": "historydaily",
    "day": "historydaily",
    "history-daily": "historydaily",
    "historydaily": "historydaily",

    "monthly": "historymonthly",
    "mounth": "historymonthly",
    "month": "historymonthly",
    "history-monthly": "historymonthly",
    "historymonthly": "historymonthly",
}


# ============================================================
# Config
# ============================================================

CACHE_TTL = 60           # ثانیه
RATE_LIMIT_WINDOW = 60   # ثانیه
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


# ============================================================
# Helpers
# ============================================================

def _make_cache_key(plan, data_type, symbol, category, start, end, page, page_size):
    raw = "|".join([
        str(plan),
        str(data_type),
        str(symbol or ""),
        str(category or ""),
        str(start or ""),
        str(end or ""),
        str(page),
        str(page_size),
    ])
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"market_api:{digest}"


def _make_rate_key(token):
    digest = hashlib.md5(str(token).encode("utf-8")).hexdigest()
    return f"market_api:rate:{digest}"


def _paginate(items, page, page_size):
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "results": items[start_idx:end_idx],
    }


def _parse_int(value, default, min_value=1, max_value=None):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    if v < min_value:
        return min_value
    if max_value is not None and v > max_value:
        return max_value
    return v


# ============================================================
# View
# ============================================================

@csrf_exempt
@require_GET
def market_api(request):
    """
    URL واحد:

    /api/v1/market/?token=xxx&type=18k&timestart=1405.05.02
        &timeend=1405.05.09&timetype=daily&symbol=USD

    پارامترها:
    - token     : API key (اجباری)
    - type      : نوع درخواست (realtime | 24h | hourly | daily | monthly)
    - symbol    : نماد (اختیاری برای realtime، اجباری برای history)
    - category  : اسلاگ دسته‌بندی (اختیاری، فقط realtime)
    - timestart : تاریخ شروع شمسی (برای daily/hourly)
    - timeend   : تاریخ پایان شمسی (برای daily/hourly)
    - timetype  : همان type (برای سازگاری)
    - page      : شماره صفحه (پیش‌فرض 1)
    - page_size : تعداد در هر صفحه (پیش‌فرض 50، حداکثر 200)
    """

    # --------------------------------------------------------
    # Auth
    # --------------------------------------------------------
    token = request.GET.get("token") or request.GET.get("key")

    plan = get_plan_from_key(token)

    if not plan:
        return JsonResponse(
            {"error": "invalid or missing API key"},
            status=401,
        )

    # --------------------------------------------------------
    # Params
    # --------------------------------------------------------
    raw_type = (
        request.GET.get("type")
        or request.GET.get("timetype")
        or "realtime"
    ).lower()

    data_type = TYPE_MAP.get(raw_type, "realtime")

    symbol = request.GET.get("symbol")
    category = request.GET.get("category")

    start = request.GET.get("timestart") or request.GET.get("start")
    end = request.GET.get("timeend") or request.GET.get("end")

    page = _parse_int(request.GET.get("page"), 1, min_value=1)
    page_size = _parse_int(
        request.GET.get("page_size"),
        DEFAULT_PAGE_SIZE,
        min_value=1,
        max_value=MAX_PAGE_SIZE,
    )

    # --------------------------------------------------------
    # Cache key
    # --------------------------------------------------------
    cache_key = _make_cache_key(
        plan=plan,
        data_type=data_type,
        symbol=symbol,
        category=category,
        start=start,
        end=end,
        page=page,
        page_size=page_size,
    )

    # --------------------------------------------------------
    # Cache lookup
    # --------------------------------------------------------
    cached = cache.get(cache_key)

    if cached is not None:
        print("cash!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logger.info("CACHE HIT !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        response = JsonResponse(
            cached,
            safe=False,
            json_dumps_params={"ensure_ascii": False},
        )
        response["X-Cache"] = "HIT"
        return response

    # --------------------------------------------------------
    # Rate limit (فقط وقتی کش خالی است)
    # --------------------------------------------------------
    rate_key = _make_rate_key(token)

    if cache.get(rate_key) is not None:
        return JsonResponse(
            {
                "error": "rate limit exceeded",
                "detail": "لطفاً یک دقیقه صبر کنید.",
                "retry_after": RATE_LIMIT_WINDOW,
            },
            status=429,
        )

    # --------------------------------------------------------
    # Fetch
    # --------------------------------------------------------
    try:
        data = get_market_data(
            plan=plan,
            data_type=data_type,
            symbol=symbol,
            category=category,
            start=start,
            end=end,
        )
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------
    if not isinstance(data, list):
        data = []

    paginated = _paginate(data, page=page, page_size=page_size)

    # --------------------------------------------------------
    # Store cache + rate marker
    # --------------------------------------------------------
    cache.set(cache_key, paginated, timeout=CACHE_TTL)
    cache.set(rate_key, True, timeout=RATE_LIMIT_WINDOW)

    response = JsonResponse(
        paginated,
        safe=False,
        json_dumps_params={"ensure_ascii": False},
    )
    response["X-Cache"] = "MISS"
    return response