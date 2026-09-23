from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("favorilerim/", views.favorites_list, name="favorites_list"),
    path("favori/<slug:recipe_slug>/degistir/", views.favorite_toggle, name="favorite_toggle"),
    path("dolabim/kaydet/", views.pantry_save, name="pantry_save"),
    path("dolabim/veri/", views.pantry_data, name="pantry_data"),
    path("alisveris-listesi/veri/", views.shopping_list_data, name="shopping_list_data"),
    path("alisveris-listesi/ekle/", views.shopping_list_add, name="shopping_list_add"),
    path(
        "alisveris-listesi/<int:item_id>/isaretle/",
        views.shopping_list_toggle,
        name="shopping_list_toggle",
    ),
    path(
        "alisveris-listesi/<int:item_id>/sil/",
        views.shopping_list_delete,
        name="shopping_list_delete",
    ),
    path("alisveris-listesi/temizle/", views.shopping_list_clear, name="shopping_list_clear"),
    path("hesap/birlestir/", views.merge_local_data, name="merge_local_data"),
]
