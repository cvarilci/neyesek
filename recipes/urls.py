from django.urls import path

from . import views

app_name = "recipes"

urlpatterns = [
    path("", views.home, name="home"),
    path("api/malzemeler/", views.ingredient_autocomplete, name="ingredient_autocomplete"),
    path("tarifler/", views.recipe_results, name="recipe_results"),
    path("tarif/<slug:slug>/", views.recipe_detail, name="recipe_detail"),
    path("alisveris-listesi/", views.shopping_list, name="shopping_list"),
]
