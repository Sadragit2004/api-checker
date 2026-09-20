from datetime import datetime, date
import jdatetime


def gregorian_to_jalali(dt):
    """تبدیل datetime میلادی به شمسی"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        j = jdatetime.datetime.fromgregorian(datetime=dt)
        return j.strftime("%Y/%m/%d"), j.strftime("%H:%M:%S"), j.strftime("%H:%M")
    if isinstance(dt, date):
        j = jdatetime.date.fromgregorian(date=dt)
        return j.strftime("%Y/%m/%d")
    return None


def unix_to_jalali(time_unix):
    """تبدیل unix timestamp به (تاریخ، ساعت، دقیقه) شمسی"""
    dt = datetime.fromtimestamp(time_unix)
    j = jdatetime.datetime.fromgregorian(datetime=dt)
    return j.strftime("%Y/%m/%d"), j.strftime("%H:%M:%S"), j.strftime("%H:%M")


def jalali_to_gregorian(jalali_str):
    """
    تبدیل رشته شمسی به date میلادی
    پشتیبانی از فرمت‌های: 1404/03/17 یا 1404-03-17 یا 1405.05.02
    """
    if not jalali_str:
        return None

    # نرمال‌سازی جداکننده‌ها
    normalized = jalali_str.replace("-", "/").replace(".", "/")
    parts = normalized.split("/")

    if len(parts) != 3:
        raise ValueError(f"فرمت تاریخ نامعتبر: {jalali_str}")

    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

    j_date = jdatetime.date(year, month, day)
    return j_date.togregorian()


def jalali_month_str(time_unix):
    """دریافت ماه شمسی به فرمت 1404/03"""
    dt = datetime.fromtimestamp(time_unix)
    j = jdatetime.datetime.fromgregorian(datetime=dt)
    return j.strftime("%Y/%m")