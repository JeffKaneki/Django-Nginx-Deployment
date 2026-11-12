from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AccountAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_staff", "created_at")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email")
    fieldsets = UserAdmin.fieldsets + (
        ("Application profile", {"fields": ("role", "phone", "address", "created_at")}),
    )
    readonly_fields = ("created_at",)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Application profile", {"fields": ("email", "role", "phone", "address")}),
    )
