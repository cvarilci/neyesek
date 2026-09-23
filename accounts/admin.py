from django.contrib import admin

from .models import Favorite, Pantry, ShoppingItem


@admin.register(Pantry)
class PantryAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    search_fields = ("user__email", "user__first_name")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe", "created_at")
    list_filter = ("recipe__category",)
    search_fields = ("user__email", "recipe__title")


@admin.register(ShoppingItem)
class ShoppingItemAdmin(admin.ModelAdmin):
    list_display = ("text", "user", "is_checked", "created_at")
    list_filter = ("is_checked",)
    search_fields = ("text", "user__email")
