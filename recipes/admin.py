from django.contrib import admin

from .models import Allergen, Category, Ingredient, IngredientGroup, Recipe, RecipeIngredient


@admin.register(Allergen)
class AllergenAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "emoji")
    search_fields = ("name", "code")


@admin.register(IngredientGroup)
class IngredientGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    ordering = ("order",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "group", "is_staple")
    list_filter = ("group", "is_staple", "allergens")
    search_fields = ("name", "synonyms")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "emoji", "order")
    ordering = ("order",)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ("ingredient",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "total_minutes", "difficulty", "is_published")
    list_filter = ("category", "difficulty", "is_published")
    search_fields = ("title", "summary")
    inlines = [RecipeIngredientInline]

    @admin.display(description="Süre (dk)")
    def total_minutes(self, obj):
        return obj.total_minutes
