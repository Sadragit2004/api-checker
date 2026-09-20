from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Max, Min, Q
from django.utils import timezone

from ..models import (
    Asset,
    Category,
    CurrentPrice,
    PriceHistory,
    SourceAPI,
)
from ..utils import (
    gregorian_to_jalali,
    jalali_month_str,
    jalali_to_gregorian,
    unix_to_jalali,
)


# ============================================================
# Auth / Plan detection
# ============================================================

def get_plan_from_key(raw_key):
    """
    بررسی API key و برگرداندن پلن.
    خروجی: 'lite' یا 'pro' یا None
    """
    if not raw_key:
        return None

    from apiprice.apps.user.models.kapi import ApiKey  # مسیر ApiKey خودت

    key_hash = ApiKey.hash_key(raw_key)

    try:
        api_key = ApiKey.objects.get(
            key_hash=key_hash,
            is_active=True,
        )
    except ApiKey.DoesNotExist:
        return None

    if api_key.is_expired:
        return None

    api_key.mark_used()

    return api_key.plan


# ============================================================
# Real-time prices
# ============================================================

def _build_realtime_item(asset, current_price, plan):
    """ساخت یک آیتم realtime بر اساس پلن"""
    date_str, time_str, _ = unix_to_jalali(current_price.time_unix)

    item = {
        "category": asset.category.slug,
        "name": asset.name,
        "symbol": asset.symbol,
        "price": float(current_price.price),
        "unit": asset.unit,
        "time": time_str,
        "date": date_str,
        "time_unix": current_price.time_unix,
    }

    if plan == "pro":
        # محاسبه تغییرات از history
        changes = _calculate_changes(asset, current_price)

        item["change_last"] = changes["change_last"]
        item["change_24h"] = changes["change_24h"]
        item["change_close_prev"] = changes["change_close_prev"]

    return item


def _calculate_changes(asset, current_price):
    """محاسبه تغییرات برای پلن Pro"""
    result = {
        "change_last": 0,
        "change_24h": 0,
        "change_close_prev": 0,
    }

    # آخرین قیمت قبلی
    prev = (
        PriceHistory.objects
        .filter(asset=asset)
        .exclude(time_unix=current_price.time_unix)
        .order_by("-time_unix")
        .first()
    )

    if prev:
        result["change_last"] = float(
            current_price.price - prev.price
        )

    # تغییر ۲۴ ساعته
    now_unix = current_price.time_unix
    day_ago = now_unix - 86400

    old = (
        PriceHistory.objects
        .filter(asset=asset, time_unix__lte=day_ago)
        .order_by("-time_unix")
        .first()
    )

    if old:
        result["change_24h"] = float(
            current_price.price - old.price
        )

    # تغییر نسبت به close قبلی (آخرین روز قبل)
    yesterday = (
        PriceHistory.objects
        .filter(asset=asset, time_unix__lt=now_unix - 86400)
        .order_by("-time_unix")
        .first()
    )

    if yesterday:
        result["change_close_prev"] = float(
            current_price.price - yesterday.price
        )

    return result


def get_realtime_prices(plan, symbol=None, category=None):
    """
    دریافت قیمت‌های لحظه‌ای.
    - symbol: فیلتر بر اساس نماد
    - category: فیلتر بر اساس اسلاگ دسته‌بندی
    """
    qs = (
        CurrentPrice.objects
        .select_related("asset", "asset__category")
        .filter(
            asset__is_active=True,
            asset__category__is_active=True,
        )
    )

    if symbol:
        qs = qs.filter(asset__symbol=symbol)

    if category:
        qs = qs.filter(asset__category__slug=category)

    # فقط یک قیمت به ازای هر asset (جدیدترین)
    qs = qs.order_by("asset__priority", "asset__name")

    results = []
    seen = set()

    for cp in qs:
        if cp.asset_id in seen:
            continue
        seen.add(cp.asset_id)
        results.append(
            _build_realtime_item(cp.asset, cp, plan)
        )

    return results


# ============================================================
# 24-hour history
# ============================================================

def get_history_24h(symbol, plan):
    """تاریخچه ۲۴ ساعته یک نماد"""
    try:
        asset = Asset.objects.select_related("category").get(
            symbol=symbol,
            is_active=True,
        )
    except Asset.DoesNotExist:
        return []

    now_unix = int(timezone.now().timestamp())
    day_ago = now_unix - 86400

    history_qs = (
        PriceHistory.objects
        .filter(
            asset=asset,
            time_unix__gte=day_ago,
            time_unix__lte=now_unix,
        )
        .order_by("time_unix")
    )

    history_items = []

    for h in history_qs:
        date_str, _, time_short = unix_to_jalali(h.time_unix)

        entry = {
            "date": date_str,
            "time": time_short,
            "time_unix": h.time_unix,
            "price": float(h.price),
        }

        if plan == "pro":
            # تغییر نسبت به آیتم قبلی
            prev = (
                PriceHistory.objects
                .filter(asset=asset, time_unix__lt=h.time_unix)
                .order_by("-time_unix")
                .first()
            )

            if prev and prev.price:
                change_value = float(h.price - prev.price)
                change_percent = float(
                    (h.price - prev.price) / prev.price * 100
                )
            else:
                change_value = 0
                change_percent = 0

            entry["change_value"] = round(change_value, 2)
            entry["change_percent"] = round(change_percent, 2)

        history_items.append(entry)

    return [
        {
            "category": asset.category.slug,
            "symbol": asset.symbol,
            "name": asset.name,
            "unit": asset.unit,
            "history_24h": history_items,
        }
    ]


# ============================================================
# Daily history
# ============================================================

def get_history_daily(symbol, start, end, plan):
    """
    تاریخچه روزانه بین دو تاریخ شمسی.
    start/end: فرمت 1404/03/17
    """
    try:
        asset = Asset.objects.select_related("category").get(
            symbol=symbol,
            is_active=True,
        )
    except Asset.DoesNotExist:
        return []

    start_greg = jalali_to_gregorian(start)
    end_greg = jalali_to_gregorian(end)

    if not start_greg or not end_greg:
        return []

    start_unix = int(
        datetime.combine(start_greg, datetime.min.time()).timestamp()
    )
    end_unix = int(
        datetime.combine(end_greg, datetime.max.time()).timestamp()
    )

    history_qs = (
        PriceHistory.objects
        .filter(
            asset=asset,
            time_unix__gte=start_unix,
            time_unix__lte=end_unix,
        )
        .order_by("time_unix")
    )

    # گروه‌بندی بر اساس روز شمسی
    daily_groups = {}

    for h in history_qs:
        date_str, _, _ = unix_to_jalali(h.time_unix)

        if date_str not in daily_groups:
            daily_groups[date_str] = []

        daily_groups[date_str].append(h)

    daily_items = []

    for date_str in sorted(daily_groups.keys()):
        rows = daily_groups[date_str]
        prices = [r.price for r in rows]

        open_price = float(rows[0].price)
        close_price = float(rows[-1].price)
        high_price = float(max(prices))
        low_price = float(min(prices))

        item = {
            "date": date_str,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
        }

        if plan == "pro":
            # تغییر نسبت به close روز قبل
            prev_day_unix = rows[0].time_unix - 1
            prev_close = (
                PriceHistory.objects
                .filter(
                    asset=asset,
                    time_unix__lte=prev_day_unix,
                )
                .order_by("-time_unix")
                .first()
            )

            if prev_close and prev_close.price:
                change_close_prev = close_price - float(prev_close.price)
                change_close_percent = float(
                    (close_price - float(prev_close.price))
                    / float(prev_close.price) * 100
                )
            else:
                change_close_prev = 0
                change_close_percent = 0

            # تغییر ۷ روزه
            week_ago_unix = rows[-1].time_unix - 7 * 86400
            week_ago = (
                PriceHistory.objects
                .filter(asset=asset, time_unix__lte=week_ago_unix)
                .order_by("-time_unix")
                .first()
            )

            change_7d = 0
            if week_ago and week_ago.price:
                change_7d = close_price - float(week_ago.price)

            # تغییر ۳۰ روزه
            month_ago_unix = rows[-1].time_unix - 30 * 86400
            month_ago = (
                PriceHistory.objects
                .filter(asset=asset, time_unix__lte=month_ago_unix)
                .order_by("-time_unix")
                .first()
            )

            change_30d = 0
            if month_ago and month_ago.price:
                change_30d = close_price - float(month_ago.price)

            item["change_close_prev"] = round(change_close_prev, 2)
            item["change_close_percent"] = round(change_close_percent, 2)
            item["change_7d"] = round(change_7d, 2)
            item["change_30d"] = round(change_30d, 2)

        daily_items.append(item)

    return [
        {
            "category": asset.category.slug,
            "name": asset.name,
            "symbol": asset.symbol,
            "unit": asset.unit,
            "history_daily": daily_items,
        }
    ]


# ============================================================
# Monthly history
# ============================================================

def get_history_monthly(symbol, plan):
    """تاریخچه ماهانه یک نماد"""
    try:
        asset = Asset.objects.select_related("category").get(
            symbol=symbol,
            is_active=True,
        )
    except Asset.DoesNotExist:
        return []

    history_qs = (
        PriceHistory.objects
        .filter(asset=asset)
        .order_by("time_unix")
    )

    # گروه‌بندی بر اساس ماه شمسی
    monthly_groups = {}

    for h in history_qs:
        month_str = jalali_month_str(h.time_unix)

        if month_str not in monthly_groups:
            monthly_groups[month_str] = []

        monthly_groups[month_str].append(h)

    monthly_items = []
    sorted_months = sorted(monthly_groups.keys())

    for idx, month_str in enumerate(sorted_months):
        rows = monthly_groups[month_str]
        prices = [r.price for r in rows]

        open_price = float(rows[0].price)
        close_price = float(rows[-1].price)
        high_price = float(max(prices))
        low_price = float(min(prices))

        item = {
            "month": month_str,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
        }

        if plan == "pro" and idx > 0:
            prev_month_str = sorted_months[idx - 1]
            prev_rows = monthly_groups[prev_month_str]
            prev_close = float(prev_rows[-1].price)

            if prev_close:
                change = close_price - prev_close
                change_percent = (change / prev_close) * 100
            else:
                change = 0
                change_percent = 0

            item["change_close_prev_month"] = round(change, 2)
            item["change_close_percent_month"] = round(change_percent, 2)

        elif plan == "pro":
            item["change_close_prev_month"] = 0
            item["change_close_percent_month"] = 0

        monthly_items.append(item)

    return [
        {
            "category": asset.category.slug,
            "name": asset.name,
            "symbol": asset.symbol,
            "unit": asset.unit,
            "history_monthly": monthly_items,
        }
    ]


# ============================================================
# Dispatcher
# ============================================================

def get_market_data(
    plan,
    data_type="realtime",
    symbol=None,
    category=None,
    start=None,
    end=None,
):
    """
    تابع اصلی که view صدا می‌زند.

    data_type: realtime | history24h | historydaily | historymonthly
    """
    if data_type == "realtime":
        return get_realtime_prices(
            plan=plan,
            symbol=symbol,
            category=category,
        )

    if data_type == "history24h":
        if not symbol:
            return []
        return get_history_24h(symbol, plan)

    if data_type == "historydaily":
        if not symbol or not start or not end:
            return []
        return get_history_daily(symbol, start, end, plan)

    if data_type == "historymonthly":
        if not symbol:
            return []
        return get_history_monthly(symbol, plan)

    return []