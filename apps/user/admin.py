from django.contrib import admin, messages
from django.utils.html import format_html

from .models import User, ApiKey


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "mobile_number",
        "first_name",
        "last_name",
        "email",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "gender",
    )

    search_fields = (
        "mobile_number",
        "first_name",
        "last_name",
        "email",
        "national_code",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "key_prefix",
        "plan",
        "is_active",
        "expires_at",
        "last_used_at",
        "created_at",
    )

    list_filter = (
        "plan",
        "is_active",
    )

    search_fields = (
        "name",
        "key_prefix",
        "user__mobile_number",
        "user__email",
    )

    readonly_fields = (
        "key_prefix",
        "key_hash",
        "last_used_at",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    autocomplete_fields = (
        "user",
    )

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(
                request,
                obj,
                form,
                change,
            )
            return

        api_key, raw_key = ApiKey.create_key(
            user=obj.user,
            name=obj.name,
            plan=obj.plan,
            expires_at=obj.expires_at,
        )

        obj.pk = api_key.pk
        obj._state.adding = False

        message = format_html(
            "<strong>API Key created successfully.</strong><br><br>"
            "<strong>API Key:</strong><br>"
            "<input "
            "type='text' "
            "value='{}' "
            "readonly "
            "style='width: 100%; max-width: 700px; padding: 10px; "
            "font-family: monospace; margin-top: 8px;' "
            "onclick='this.select();'>"
            "<br><br>"
            "<strong>Important:</strong> "
            "Copy this API Key now. "
            "It will not be shown again.",
            raw_key,
        )

        self.message_user(
            request,
            message,
            messages.SUCCESS,
        )