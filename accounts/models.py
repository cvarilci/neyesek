from django.conf import settings
from django.db import models

from recipes.models import Ingredient, Recipe


class Pantry(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="kullanıcı",
        on_delete=models.CASCADE,
        related_name="pantry",
    )
    ingredients = models.ManyToManyField(
        Ingredient, verbose_name="malzemeler", blank=True, related_name="pantries"
    )
    updated_at = models.DateTimeField("güncellenme tarihi", auto_now=True)

    class Meta:
        verbose_name = "Dolap"
        verbose_name_plural = "Dolaplar"

    def __str__(self):
        return f"{self.user}'in dolabı"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="kullanıcı",
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    recipe = models.ForeignKey(
        Recipe, verbose_name="tarif", on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField("eklenme tarihi", auto_now_add=True)

    class Meta:
        verbose_name = "Favori"
        verbose_name_plural = "Favoriler"
        constraints = [
            models.UniqueConstraint(fields=["user", "recipe"], name="unique_user_recipe_favorite")
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.recipe}"


class ShoppingItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="kullanıcı",
        on_delete=models.CASCADE,
        related_name="shopping_items",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name="malzeme",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shopping_items",
    )
    text = models.CharField("metin", max_length=100)
    is_checked = models.BooleanField("işaretli", default=False)
    created_at = models.DateTimeField("eklenme tarihi", auto_now_add=True)

    class Meta:
        verbose_name = "Alışveriş Öğesi"
        verbose_name_plural = "Alışveriş Öğeleri"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "text"], name="unique_user_shopping_text")
        ]

    def __str__(self):
        return self.text
