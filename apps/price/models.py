from django.core.exceptions import ValidationError
from django.db import models


# ============================================================
# Category
# ============================================================

class Category(models.Model):

    name = models.CharField(
        max_length=100,
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
    )

    max_price_change_percent = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=10,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "price_categories"
        ordering = (
            "name",
        )

    def __str__(self):
        return self.name


# ============================================================
# Asset
# ============================================================

class Asset(models.Model):

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="assets",
    )

    symbol = models.CharField(
        max_length=100,
        unique=True,
    )

    name = models.CharField(
        max_length=150,
    )

    name_en = models.CharField(
        max_length=150,
        blank=True,
    )

    priority = models.PositiveIntegerField(
        default=0,
    )

    unit = models.CharField(
        max_length=50,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "price_assets"

        ordering = (
            "priority",
            "name",
        )

    def __str__(self):
        return f"{self.symbol} - {self.name}"


# ============================================================
# Source API
# ============================================================

class SourceAPI(models.Model):

    class Method(models.TextChoices):
        GET = "GET", "GET"
        POST = "POST", "POST"

    # ========================================================
    # Basic Information
    # ========================================================

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="sources",
    )

    name = models.CharField(
        max_length=150,
    )

    url = models.URLField(
        max_length=1000,
    )

    method = models.CharField(
        max_length=10,
        choices=Method.choices,
        default=Method.GET,
    )

    priority = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    # ========================================================
    # Dynamic Request Script
    # ========================================================

    request_script = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "تنظیمات داینامیک درخواست HTTP. "
            "امکان تنظیم headers، query، body، "
            "form، raw_body و content_type."
        ),
    )

    # ========================================================
    # Authentication
    # ========================================================

    header_token = models.CharField(
        max_length=1000,
        blank=True,
    )

    # ========================================================
    # Universal Filter
    # ========================================================

    filter_field = models.CharField(
        max_length=255,
        blank=True,
    )

    filter_value = models.CharField(
        max_length=500,
        blank=True,
    )

    # ========================================================
    # Timestamps
    # ========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "price_source_apis"

        ordering = (
            "asset__priority",
            "asset__name",
            "priority",
            "name",
        )

    # ========================================================
    # Validation
    # ========================================================

    def clean(self):

        super().clean()

        # ----------------------------------------------------
        # Method
        # ----------------------------------------------------

        if self.method not in {
            self.Method.GET,
            self.Method.POST,
        }:
            raise ValidationError(
                {
                    "method": (
                        "فقط GET و POST مجاز هستند."
                    )
                }
            )

        # ----------------------------------------------------
        # Request Script
        # ----------------------------------------------------

        if self.request_script in (
            None,
            "",
        ):
            self.request_script = {}

        if not isinstance(
            self.request_script,
            dict,
        ):
            raise ValidationError(
                {
                    "request_script": (
                        "API Request Script "
                        "باید JSON Object باشد."
                    )
                }
            )

        # ----------------------------------------------------
        # Allowed Keys
        # ----------------------------------------------------

        allowed_keys = {
            "headers",
            "query",
            "body",
            "form",
            "raw_body",
            "content_type",
        }

        unknown_keys = (
            set(self.request_script.keys())
            - allowed_keys
        )

        if unknown_keys:
            raise ValidationError(
                {
                    "request_script": (
                        "کلیدهای غیرمجاز در "
                        "API Request Script: "
                        + ", ".join(
                            sorted(unknown_keys)
                        )
                    )
                }
            )

        # ----------------------------------------------------
        # Headers
        # ----------------------------------------------------

        headers = self.request_script.get(
            "headers"
        )

        if headers is not None:

            if not isinstance(
                headers,
                dict,
            ):
                raise ValidationError(
                    {
                        "request_script": (
                            "headers باید "
                            "JSON Object باشد."
                        )
                    }
                )

        # ----------------------------------------------------
        # Query
        # ----------------------------------------------------

        query = self.request_script.get(
            "query"
        )

        if query is not None:

            if not isinstance(
                query,
                dict,
            ):
                raise ValidationError(
                    {
                        "request_script": (
                            "query باید "
                            "JSON Object باشد."
                        )
                    }
                )

        # ----------------------------------------------------
        # Body / Form / Raw Body
        # ----------------------------------------------------

        body = self.request_script.get(
            "body"
        )

        form = self.request_script.get(
            "form"
        )

        raw_body = self.request_script.get(
            "raw_body"
        )

        # فقط یکی از این سه مورد مجاز است.

        body_modes = sum(
            value is not None
            for value in (
                body,
                form,
                raw_body,
            )
        )

        if body_modes > 1:
            raise ValidationError(
                {
                    "request_script": (
                        "فقط یکی از body، form "
                        "یا raw_body می‌تواند "
                        "استفاده شود."
                    )
                }
            )

        # ----------------------------------------------------
        # JSON Body
        # ----------------------------------------------------

        if body is not None:

            if not isinstance(
                body,
                dict,
            ):
                raise ValidationError(
                    {
                        "request_script": (
                            "body باید "
                            "JSON Object باشد."
                        )
                    }
                )

        # ----------------------------------------------------
        # Form
        # ----------------------------------------------------

        if form is not None:

            if not isinstance(
                form,
                dict,
            ):
                raise ValidationError(
                    {
                        "request_script": (
                            "form باید "
                            "JSON Object باشد."
                        )
                    }
                )

        # ----------------------------------------------------
        # Raw Body
        # ----------------------------------------------------

        if raw_body is not None:

            if not isinstance(
                raw_body,
                str,
            ):
                raise ValidationError(
                    {
                        "request_script": (
                            "raw_body باید "
                            "String باشد."
                        )
                    }
                )

        # ----------------------------------------------------
        # Content Type
        # ----------------------------------------------------

        content_type = self.request_script.get(
            "content_type"
        )

        if content_type is not None:

            if not isinstance(
                content_type,
                str,
            ):
                raise ValidationError(
                    {
                        "request_script": (
                            "content_type باید "
                            "String باشد."
                        )
                    }
                )

    # ========================================================
    # String
    # ========================================================

    def __str__(self):
        return self.name


# ============================================================
# Source API Mapping
# ============================================================

class SourceAPIMapping(models.Model):

    class TargetField(models.TextChoices):
        PRICE = "price", "Price"
        TIME_UNIX = "time_unix", "Time Unix"

    source_api = models.ForeignKey(
        SourceAPI,
        on_delete=models.CASCADE,
        related_name="mappings",
    )

    target_field = models.CharField(
        max_length=50,
        choices=TargetField.choices,
    )

    source_path = models.CharField(
        max_length=500,
        help_text=(
            "مسیر فیلد در JSON. "
            "مثال: price یا data.price"
        ),
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "price_source_api_mappings"

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "source_api",
                    "target_field",
                ),
                name=(
                    "unique_source_api_target_field"
                ),
            ),
        ]

        ordering = (
            "target_field",
        )

    def __str__(self):
        return (
            f"{self.source_api.name} - "
            f"{self.target_field}"
        )


# ============================================================
# Current Price
# ============================================================

class CurrentPrice(models.Model):

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="current_prices",
    )

    source_api = models.ForeignKey(
        SourceAPI,
        on_delete=models.CASCADE,
        related_name="current_prices",
    )

    price = models.DecimalField(
        max_digits=30,
        decimal_places=8,
    )

    time_unix = models.BigIntegerField()

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "price_current_prices"

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "asset",
                    "source_api",
                ),
                name=(
                    "unique_current_price_asset_source"
                ),
            ),
        ]

    def __str__(self):
        return (
            f"{self.asset.symbol} - "
            f"{self.price}"
        )


# ============================================================
# Price History
# ============================================================

class PriceHistory(models.Model):

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="price_history",
    )

    source_api = models.ForeignKey(
        SourceAPI,
        on_delete=models.CASCADE,
        related_name="price_history",
    )

    price = models.DecimalField(
        max_digits=30,
        decimal_places=8,
    )

    time_unix = models.BigIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "price_history"

        indexes = [
            models.Index(
                fields=(
                    "asset",
                    "-time_unix",
                ),
                name=(
                    "price_history_asset_time_idx"
                ),
            ),
        ]

        ordering = (
            "-time_unix",
        )

    def __str__(self):
        return (
            f"{self.asset.symbol} - "
            f"{self.price}"
        )