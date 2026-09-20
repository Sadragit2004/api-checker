import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django import forms
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import (
    Asset,
    Category,
    CurrentPrice,
    PriceHistory,
    SourceAPI,
    SourceAPIMapping,
)


# ============================================================
# JSON Formatter
# ============================================================
class PrettyJSONField(forms.Textarea):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "attrs",
            {
                "rows": 14,
                "style": (
                    "font-family:monospace;"
                    "direction:ltr;"
                    "text-align:left;"
                    "width:100%;"
                    "resize:vertical;"
                ),
            },
        )
        super().__init__(*args, **kwargs)


# ============================================================
# Source API Admin Form
# ============================================================
class SourceAPIAdminForm(forms.ModelForm):
    class Meta:
        model = SourceAPI
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ----------------------------------------------------
        # Request Script
        # ----------------------------------------------------
        if "request_script" in self.fields:
            self.fields["request_script"].widget = PrettyJSONField()
            self.fields["request_script"].label = "API Request Script"
            self.fields["request_script"].help_text = (
                "تنظیمات درخواست API را به صورت JSON وارد کنید. "
                "امکان تنظیم Headers، Query، Body، Form، "
                "Raw Body و Content-Type وجود دارد."
            )

        # ----------------------------------------------------
        # Remove Old Request Fields
        # ----------------------------------------------------
        self.fields.pop("request_body", None)
        self.fields.pop("query_params", None)

        # ----------------------------------------------------
        # Authentication
        # ----------------------------------------------------
        if "header_token" in self.fields:
            self.fields["header_token"].label = "Header Token"
            self.fields["header_token"].help_text = (
                "در صورت وجود، Token به صورت "
                "Authorization: Bearer TOKEN "
                "ارسال می‌شود."
            )
            self.fields["header_token"].widget = forms.PasswordInput(
                render_value=True,
            )

        # ----------------------------------------------------
        # Filter
        # ----------------------------------------------------
        if "filter_field" in self.fields:
            self.fields["filter_field"].label = "Filter Field"
            self.fields["filter_field"].help_text = (
                "مثال: symbol، name_en، key، "
                "__key__ یا data.symbol"
            )
        if "filter_value" in self.fields:
            self.fields["filter_value"].label = "Filter Value"
            self.fields["filter_value"].help_text = (
                "مقداری که باید پیدا شود."
            )

        # ----------------------------------------------------
        # Priority
        # ----------------------------------------------------
        if "priority" in self.fields:
            self.fields["priority"].label = "API Priority"
            self.fields["priority"].help_text = (
                "عدد کمتر یعنی اولویت بالاتر."
            )

    # ========================================================
    # Clean
    # ========================================================
    def clean(self):
        cleaned_data = super().clean()
        request_script = cleaned_data.get("request_script") or {}
        if request_script and not isinstance(request_script, dict):
            self.add_error(
                "request_script",
                "API Request Script باید JSON Object باشد.",
            )
        return cleaned_data


# ============================================================
# Category
# ============================================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "max_price_change_percent",
        "is_active",
        "asset_count",
        "created_at",
    )
    list_display_links = ("name",)
    list_editable = (
        "max_price_change_percent",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "slug",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = ("name",)
    fieldsets = (
        (
            "Category",
            {
                "fields": (
                    "name",
                    "slug",
                    "max_price_change_percent",
                    "is_active",
                ),
            },
        ),
        (
            "Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    @admin.display(description="تعداد Asset")
    def asset_count(self, obj):
        return obj.assets.count()


# ============================================================
# Source API Inline
# ============================================================
class SourceAPIInline(admin.TabularInline):
    model = SourceAPI
    form = SourceAPIAdminForm
    extra = 0
    show_change_link = True
    fields = (
        "priority",
        "name",
        "method",
        "filter_field",
        "filter_value",
        "is_active",
    )
    ordering = (
        "priority",
        "name",
    )
    verbose_name = "Source API"
    verbose_name_plural = "Source APIs"


# ============================================================
# Asset
# ============================================================
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        "priority",
        "symbol",
        "name",
        "name_en",
        "category",
        "unit",
        "source_count",
        "is_active",
        "created_at",
    )
    list_display_links = ("symbol",)
    list_editable = (
        "priority",
        "is_active",
    )
    list_filter = (
        "category",
        "is_active",
    )
    search_fields = (
        "symbol",
        "name",
        "name_en",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = (
        "priority",
        "name",
    )
    inlines = (SourceAPIInline,)
    fieldsets = (
        (
            "Asset",
            {
                "fields": (
                    "category",
                    "symbol",
                    "name",
                    "name_en",
                    "priority",
                    "unit",
                    "is_active",
                ),
            },
        ),
        (
            "Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    @admin.display(description="Source APIs")
    def source_count(self, obj):
        return obj.sources.count()


# ============================================================
# Source API Mapping Inline
# ============================================================
class SourceAPIMappingInline(admin.TabularInline):
    model = SourceAPIMapping
    extra = 0
    fields = (
        "target_field",
        "source_path",
        "is_active",
    )
    ordering = ("target_field",)
    verbose_name = "Mapping"
    verbose_name_plural = "Mappings"


# ============================================================
# Source API
# ============================================================
@admin.register(SourceAPI)
class SourceAPIAdmin(admin.ModelAdmin):
    form = SourceAPIAdminForm
    list_display = (
        "priority",
        "name",
        "asset",
        "filter_display",
        "method",
        "url_short",
        "is_active",
        "mapping_status",
        "test_api_button",
        "created_at",
    )
    list_display_links = ("name",)
    list_editable = (
        "priority",
        "is_active",
    )
    list_filter = (
        "is_active",
        "method",
        "asset__category",
    )
    search_fields = (
        "name",
        "url",
        "filter_field",
        "filter_value",
        "asset__symbol",
        "asset__name",
        "asset__name_en",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = (
        "asset__priority",
        "asset__name",
        "priority",
        "name",
    )
    inlines = (SourceAPIMappingInline,)
    fieldsets = (
        # ----------------------------------------------------
        # Source API
        # ----------------------------------------------------
        (
            "Source API",
            {
                "fields": (
                    "asset",
                    "name",
                    "url",
                    "method",
                    "priority",
                    "is_active",
                ),
            },
        ),
        # ----------------------------------------------------
        # API Request
        # ----------------------------------------------------
        (
            "API Request",
            {
                "description": (
                    "URL فقط آدرس Endpoint است. "
                    "تنظیمات درخواست در "
                    "API Request Script قرار می‌گیرد."
                ),
                "fields": ("request_script",),
            },
        ),
        # ----------------------------------------------------
        # Authentication
        # ----------------------------------------------------
        (
            "Authentication",
            {
                "description": (
                    "در صورت وجود، Token با "
                    "Authorization: Bearer ارسال می‌شود."
                ),
                "fields": ("header_token",),
            },
        ),
        # ----------------------------------------------------
        # Universal Filter
        # ----------------------------------------------------
        (
            "Universal Filter",
            {
                "description": (
                    "برای پیدا کردن رکورد مربوط به Asset "
                    "در هر ساختار JSON."
                ),
                "fields": (
                    "filter_field",
                    "filter_value",
                ),
            },
        ),
        # ----------------------------------------------------
        # Information
        # ----------------------------------------------------
        (
            "Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    # ========================================================
    # Custom URLs
    # ========================================================
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/test-api/",
                self.admin_site.admin_view(self.test_api_view),
                name=(
                    f"{self.opts.app_label}_"
                    f"{self.opts.model_name}_test_api"
                ),
            ),
        ]
        return custom_urls + urls

    # ========================================================
    # Filter Display
    # ========================================================
    @admin.display(description="Filter")
    def filter_display(self, obj):
        if not obj.filter_field and not obj.filter_value:
            return mark_safe(
                '<span style="color:#999;">—</span>'
            )
        return format_html(
            "<strong>{}</strong> = {}",
            obj.filter_field or "—",
            obj.filter_value or "—",
        )

    # ========================================================
    # URL Display
    # ========================================================
    @admin.display(description="URL")
    def url_short(self, obj):
        if len(obj.url) <= 70:
            return obj.url
        return f"{obj.url[:67]}..."

    # ========================================================
    # Mapping Status
    # ========================================================
    @admin.display(description="Mappings")
    def mapping_status(self, obj):
        mappings = obj.mappings.filter(is_active=True)
        target_fields = set(
            mappings.values_list("target_field", flat=True)
        )
        required = {
            SourceAPIMapping.TargetField.PRICE,
            SourceAPIMapping.TargetField.TIME_UNIX,
        }
        if required.issubset(target_fields):
            return mark_safe(
                '<span style="color:#16803c;'
                'font-weight:600;">✓ کامل</span>'
            )
        missing = required - target_fields
        return format_html(
            '<span style="color:#b42318;'
            'font-weight:600;">✗ ناقص: {}</span>',
            ", ".join(sorted(missing)),
        )

    # ========================================================
    # Test API Button
    # ========================================================
    @admin.display(description="Test")
    def test_api_button(self, obj):
        url = reverse(
            f"admin:{self.opts.app_label}_"
            f"{self.opts.model_name}_test_api",
            args=[obj.pk],
        )
        return format_html(
            '<a class="button" href="{}">Test API</a>',
            url,
        )

    # ========================================================
    # Basic Path Resolver
    # ========================================================
    @staticmethod
    def resolve_path(data, path):
        if path in ("", None):
            return data
        current = data
        for part in path.split("."):
            if isinstance(current, dict):
                if part not in current:
                    raise KeyError(f"Path not found: {path}")
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                except (TypeError, ValueError):
                    raise KeyError(
                        f"Invalid list index in path: {path}"
                    )
                if index < 0 or index >= len(current):
                    raise KeyError(
                        f"List index out of range: {path}"
                    )
                current = current[index]
            else:
                raise KeyError(f"Cannot continue path: {path}")
        return current

    # ========================================================
    # Recursive Path Resolver
    # ========================================================
    @classmethod
    def find_by_path_recursive(cls, data, path_parts):
        if not path_parts:
            return data
        if isinstance(data, dict):
            remaining_path = ".".join(path_parts)
            try:
                return cls.resolve_path(data, remaining_path)
            except KeyError:
                pass
            for value in data.values():
                result = cls.find_by_path_recursive(
                    value, path_parts
                )
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = cls.find_by_path_recursive(
                    item, path_parts
                )
                if result is not None:
                    return result
        return None

    # ========================================================
    # Find Parent Object
    # ========================================================
    @classmethod
    def find_parent_object(cls, data, path_parts):
        if not path_parts:
            return data
        if isinstance(data, dict):
            first = path_parts[0]
            if first in data:
                if len(path_parts) == 1:
                    return data
                result = cls.find_parent_object(
                    data[first], path_parts[1:]
                )
                if result is not None:
                    return result
            for value in data.values():
                result = cls.find_parent_object(
                    value, path_parts
                )
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = cls.find_parent_object(
                    item, path_parts
                )
                if result is not None:
                    return result
        return None

    # ========================================================
    # Find Object By Field
    # ========================================================
    @classmethod
    def find_by_field(cls, data, filter_field):
        if not filter_field:
            return None
        if isinstance(data, dict):
            if filter_field in data:
                return data
            if "." in filter_field:
                parts = filter_field.split(".")
                try:
                    cls.resolve_path(data, filter_field)
                    parent = cls.find_parent_object(data, parts)
                    if parent is not None:
                        return parent
                except KeyError:
                    pass
                recursive_result = cls.find_by_path_recursive(
                    data, parts
                )
                if recursive_result is not None:
                    parent = cls.find_parent_object(data, parts)
                    if parent is not None:
                        return parent
            for value in data.values():
                result = cls.find_by_field(value, filter_field)
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = cls.find_by_field(item, filter_field)
                if result is not None:
                    return result
        return None

    # ========================================================
    # Find Object By Field + Value
    # ========================================================
    @classmethod
    def find_by_field_value(cls, data, filter_field, filter_value):
        expected = str(filter_value).strip()
        if isinstance(data, dict):
            if filter_field in data:
                actual = str(data[filter_field]).strip()
                if actual == expected:
                    return data
            for value in data.values():
                result = cls.find_by_field_value(
                    value, filter_field, expected
                )
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = cls.find_by_field_value(
                    item, filter_field, expected
                )
                if result is not None:
                    return result
        return None

    # ========================================================
    # Find By Value
    # ========================================================
    @classmethod
    def find_by_value(cls, data, filter_value):
        expected = str(filter_value).strip()
        if isinstance(data, dict):
            for key, value in data.items():
                if not isinstance(value, (dict, list)):
                    actual = str(value).strip()
                    if actual == expected:
                        return data
                result = cls.find_by_value(value, expected)
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = cls.find_by_value(item, expected)
                if result is not None:
                    return result
        else:
            actual = str(data).strip()
            if actual == expected:
                return data
        return None

    # ========================================================
    # Object Key Resolver
    # ========================================================
    @classmethod
    def find_by_object_key(cls, data, filter_value):
        expected = str(filter_value).strip()
        if isinstance(data, dict):
            if expected in data:
                return data[expected]
            for value in data.values():
                result = cls.find_by_object_key(value, expected)
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = cls.find_by_object_key(item, expected)
                if result is not None:
                    return result
        return None

    # ========================================================
    # Universal Filter
    # ========================================================
    @classmethod
    def apply_filter(cls, data, source_api):
        filter_field = (source_api.filter_field or "").strip()
        filter_value = (source_api.filter_value or "").strip()

        # ----------------------------------------------------
        # No Filter
        # ----------------------------------------------------
        if not filter_field and not filter_value:
            return data

        # ----------------------------------------------------
        # Field + Value
        # ----------------------------------------------------
        if filter_field and filter_value:
            if filter_field == "__key__":
                result = cls.find_by_object_key(
                    data, filter_value
                )
                if result is None:
                    raise ValueError(
                        f"Object key not found: {filter_value}"
                    )
                return result
            result = cls.find_by_field_value(
                data, filter_field, filter_value
            )
            if result is not None:
                return result
            raise ValueError(
                "Matching record not found: "
                f"{filter_field}={filter_value}"
            )

        # ----------------------------------------------------
        # Field Only
        # ----------------------------------------------------
        if filter_field:
            if filter_field == "__key__":
                raise ValueError(
                    "Filter Value is required "
                    "when Filter Field is __key__."
                )
            result = cls.find_by_field(data, filter_field)
            if result is None:
                raise ValueError(
                    f"Filter Field not found: {filter_field}"
                )
            return result

        # ----------------------------------------------------
        # Value Only
        # ----------------------------------------------------
        if filter_value:
            result = cls.find_by_value(data, filter_value)
            if result is None:
                raise ValueError(
                    f"Filter Value not found: {filter_value}"
                )
            return result

        return data

    # ========================================================
    # Build Request
    # ========================================================
    @staticmethod
    def build_request(source_api):
        method = source_api.method.upper()
        if method not in {
            SourceAPI.Method.GET,
            SourceAPI.Method.POST,
        }:
            raise RuntimeError(
                "Only GET and POST are supported."
            )

        request_script = (
            getattr(source_api, "request_script", None) or {}
        )
        if not isinstance(request_script, dict):
            raise RuntimeError(
                "API Request Script must be a JSON object."
            )

        allowed_keys = {
            "headers",
            "query",
            "body",
            "form",
            "raw_body",
            "content_type",
        }
        unknown_keys = set(request_script.keys()) - allowed_keys
        if unknown_keys:
            raise RuntimeError(
                "Unsupported Request Script keys: "
                + ", ".join(sorted(unknown_keys))
            )

        # ----------------------------------------------------
        # Default Headers
        # ----------------------------------------------------
        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
        }

        # ----------------------------------------------------
        # Dynamic Headers
        # ----------------------------------------------------
        script_headers = request_script.get("headers") or {}
        if not isinstance(script_headers, dict):
            raise RuntimeError(
                "Request Script 'headers' must be an object."
            )
        headers.update(
            {
                str(key): str(value)
                for key, value in script_headers.items()
            }
        )

        # ----------------------------------------------------
        # Dedicated Token
        # ----------------------------------------------------
        if source_api.header_token:
            headers["Authorization"] = (
                f"Bearer {source_api.header_token}"
            )

        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------
        url = source_api.url

        # ----------------------------------------------------
        # Query
        # ----------------------------------------------------
        query = request_script.get("query")
        if query is None:
            query = {}
        if not isinstance(query, dict):
            raise RuntimeError(
                "Request Script 'query' must be an object."
            )
        if query:
            separator = "&" if "?" in url else "?"
            url = (
                f"{url}{separator}"
                f"{urlencode(query, doseq=True)}"
            )

        # ----------------------------------------------------
        # Body
        # ----------------------------------------------------
        body = request_script.get("body")
        form = request_script.get("form")
        raw_body = request_script.get("raw_body")
        body_modes = sum(
            value is not None
            for value in (body, form, raw_body)
        )
        if body_modes > 1:
            raise RuntimeError(
                "Only one of body, form or raw_body "
                "can be used."
            )

        request_data = None

        # ----------------------------------------------------
        # JSON Body
        # ----------------------------------------------------
        if body is not None:
            if not isinstance(body, dict):
                raise RuntimeError(
                    "Request Script 'body' must be an object."
                )
            request_data = json.dumps(
                body, ensure_ascii=False
            ).encode("utf-8")
            headers.setdefault(
                "Content-Type", "application/json"
            )

        # ----------------------------------------------------
        # Form Body
        # ----------------------------------------------------
        elif form is not None:
            if not isinstance(form, dict):
                raise RuntimeError(
                    "Request Script 'form' must be an object."
                )
            request_data = urlencode(
                form, doseq=True
            ).encode("utf-8")
            headers.setdefault(
                "Content-Type",
                "application/x-www-form-urlencoded",
            )

        # ----------------------------------------------------
        # Raw Body
        # ----------------------------------------------------
        elif raw_body is not None:
            if not isinstance(raw_body, str):
                raise RuntimeError(
                    "Request Script 'raw_body' must be a string."
                )
            request_data = raw_body.encode("utf-8")

        # ----------------------------------------------------
        # Content Type
        # ----------------------------------------------------
        content_type = request_script.get("content_type")
        if content_type:
            headers["Content-Type"] = str(content_type)

        # ----------------------------------------------------
        # Request
        # ----------------------------------------------------
        return Request(
            url,
            data=request_data,
            headers=headers,
            method=method,
        )

    # ========================================================
    # Execute API
    # ========================================================
    @classmethod
    def execute_api(cls, source_api):
        request = cls.build_request(source_api)
        started_at = time.monotonic()
        try:
            with urlopen(request, timeout=20) as response:
                response_body = response.read()
                elapsed = time.monotonic() - started_at
                status_code = response.status
                content_type = response.headers.get(
                    "Content-Type", ""
                )
        except HTTPError as exc:
            body = exc.read()
            raise RuntimeError(
                f"HTTP {exc.code}: "
                f"{body.decode('utf-8', errors='replace')[:1000]}"
            )
        except URLError as exc:
            raise RuntimeError(
                f"Connection failed: {exc.reason}"
            )
        except TimeoutError:
            raise RuntimeError("Request timed out.")

        try:
            text = response_body.decode(
                "utf-8", errors="replace"
            )
            data = json.loads(text)
        except json.JSONDecodeError:
            raise RuntimeError(
                "API response is not valid JSON."
            )

        return {
            "status_code": status_code,
            "content_type": content_type,
            "elapsed": elapsed,
            "data": data,
        }

    # ========================================================
    # Test API View
    # ========================================================
    def test_api_view(self, request, object_id):
        source_api = self.get_object(request, object_id)
        if source_api is None:
            return HttpResponse(
                "Source API not found.", status=404
            )

        result = None
        filtered = None
        error = None

        try:
            result = self.execute_api(source_api)
            filtered = self.apply_filter(
                result["data"], source_api
            )
        except Exception as exc:
            error = str(exc)

        html = [
            "<!doctype html>",
            "<html>",
            "<head>",
            '<meta charset="utf-8">',
            "<title>Test Source API</title>",
            """
            <style>
                body {
                    font-family: Arial, sans-serif;
                    direction: ltr;
                    margin: 40px;
                    background: #f6f7f9;
                }
                .box {
                    background: #fff;
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                }
                pre {
                    white-space: pre-wrap;
                    word-break: break-word;
                    background: #111;
                    color: #eee;
                    padding: 16px;
                    border-radius: 8px;
                    overflow-x: auto;
                }
                .success { color: #16803c; }
                .error { color: #b42318; }
                .method {
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 5px;
                    background: #eee;
                    font-weight: 600;
                }
            </style>
            """,
            "</head>",
            "<body>",
            "<h1>Source API Test</h1>",
        ]

        # ----------------------------------------------------
        # Information
        # ----------------------------------------------------
        html.append("<div class='box'>")
        html.append(
            f"<strong>Name:</strong> {source_api.name}<br>"
        )
        html.append(
            f"<strong>URL:</strong> {source_api.url}<br>"
        )
        html.append(
            f"<strong>Method:</strong> "
            f"<span class='method'>{source_api.method}</span><br>"
        )
        html.append(
            f"<strong>Asset:</strong> {source_api.asset}<br>"
        )
        html.append(
            f"<strong>Priority:</strong> "
            f"{source_api.priority}<br>"
        )
        html.append(
            f"<strong>Filter Field:</strong> "
            f"{source_api.filter_field or '—'}<br>"
        )
        html.append(
            f"<strong>Filter Value:</strong> "
            f"{source_api.filter_value or '—'}<br>"
        )

        # ----------------------------------------------------
        # Request Script
        # ----------------------------------------------------
        request_script = (
            getattr(source_api, "request_script", None) or {}
        )
        html.append(
            "<strong>Request Script:</strong>"
            "<pre>"
            + json.dumps(
                request_script,
                ensure_ascii=False,
                indent=2,
            )
            + "</pre>"
        )

        if source_api.header_token:
            html.append(
                "<strong>Header Token:</strong> "
                "Configured<br>"
            )

        html.append("</div>")

        # ----------------------------------------------------
        # Error
        # ----------------------------------------------------
        if error:
            html.append(
                "<div class='box error'>"
                "<strong>Error:</strong><br>"
                f"{error}"
                "</div>"
            )

        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------
        if result:
            html.append(
                "<div class='box success'>"
                "<strong>Request successful</strong><br>"
                f"HTTP: {result['status_code']}<br>"
                f"Content-Type: {result['content_type']}<br>"
                f"Time: {result['elapsed']:.3f}s"
                "</div>"
            )
            html.append(
                "<div class='box'>"
                "<h2>Filtered Record</h2>"
                "<pre>"
                + json.dumps(
                    filtered,
                    ensure_ascii=False,
                    indent=2,
                )
                + "</pre>"
                "</div>"
            )
            html.append(
                "<div class='box'>"
                "<h2>Raw Response</h2>"
                "<pre>"
                + json.dumps(
                    result["data"],
                    ensure_ascii=False,
                    indent=2,
                )
                + "</pre>"
                "</div>"
            )

        html.append(
            "<p>"
            '<a href="javascript:history.back()">Back</a>'
            "</p>"
        )
        html.append("</body></html>")

        return HttpResponse("".join(html))


# ============================================================
# Price History
# ============================================================
@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "source_api",
        "price",
        "time_unix",
        "created_at",
    )
    list_filter = (
        "asset__category",
        "source_api",
    )
    search_fields = (
        "asset__symbol",
        "asset__name",
        "source_api__name",
    )
    readonly_fields = (
        "asset",
        "source_api",
        "price",
        "time_unix",
        "created_at",
    )
    ordering = ("-time_unix",)


# ============================================================
# Current Price
# ============================================================
@admin.register(CurrentPrice)
class CurrentPriceAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "source_api",
        "price",
        "time_unix",
        "updated_at",
    )
    list_filter = (
        "asset__category",
        "source_api",
    )
    search_fields = (
        "asset__symbol",
        "asset__name",
        "source_api__name",
    )
    readonly_fields = (
        "asset",
        "source_api",
        "price",
        "time_unix",
        "updated_at",
    )
    ordering = ("-updated_at",)