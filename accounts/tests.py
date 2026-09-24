import json

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from recipes.models import Category, Ingredient, IngredientGroup, Recipe

from .models import Favorite, Pantry, ShoppingItem

User = get_user_model()


class SignupLoginTests(TestCase):
    def test_signup_form_has_no_username_field(self):
        response = self.client.get(reverse("account_signup"))
        self.assertNotContains(response, 'name="username"')

    def test_signup_creates_user_with_first_name(self):
        response = self.client.post(
            reverse("account_signup"),
            {
                "first_name": "Ayşe",
                "email": "ayse@example.com",
                "password1": "cok-guclu-parola-123",
                "password2": "cok-guclu-parola-123",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="ayse@example.com")
        self.assertEqual(user.first_name, "Ayşe")
        # Kayıt formunda kullanıcı adı alanı yoktu; allauth arka planda
        # e-postadan teknik bir username üretir ama kullanıcı hiç görmez/girmez.

    def test_signup_sends_confirmation_email_to_console_backend(self):
        self.client.post(
            reverse("account_signup"),
            {
                "first_name": "Mehmet",
                "email": "mehmet@example.com",
                "password1": "cok-guclu-parola-123",
                "password2": "cok-guclu-parola-123",
            },
        )
        self.assertGreaterEqual(len(mail.outbox), 1)

    def test_login_with_email_and_password(self):
        User.objects.create_user(
            username="zeynep@example.com",
            email="zeynep@example.com",
            password="cok-guclu-parola-123",
            first_name="Zeynep",
        )
        response = self.client.post(
            reverse("account_login"),
            {"login": "zeynep@example.com", "password": "cok-guclu-parola-123"},
        )
        self.assertEqual(response.status_code, 302)
        response2 = self.client.get(reverse("recipes:home"))
        self.assertTrue(response2.wsgi_request.user.is_authenticated)

    def test_password_reset_sends_email(self):
        User.objects.create_user(
            username="fatma@example.com",
            email="fatma@example.com",
            password="eski-parola-123",
            first_name="Fatma",
        )
        response = self.client.post(
            reverse("account_reset_password"), {"email": "fatma@example.com"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertGreaterEqual(len(mail.outbox), 1)
        self.assertIn("fatma@example.com", mail.outbox[0].to)


class AnonymousExperienceUnaffectedTests(TestCase):
    """Üyeliksiz kullanım Faz 2/3'teki gibi çalışmaya devam etmeli."""

    def test_home_page_renders_for_anonymous_user(self):
        response = self.client.get(reverse("recipes:home"))
        self.assertEqual(response.status_code, 200)

    def test_shopping_list_page_renders_for_anonymous_user(self):
        response = self.client.get(reverse("recipes:shopping_list"))
        self.assertEqual(response.status_code, 200)

    def test_favorites_page_shows_login_prompt_for_anonymous_user(self):
        response = self.client.get(reverse("accounts:favorites_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "giriş yapmalısın")

    def test_json_endpoints_require_login(self):
        for url in [
            reverse("accounts:pantry_data"),
            reverse("accounts:shopping_list_data"),
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401)


class AccountFeatureTests(TestCase):
    def setUp(self):
        self.group = IngredientGroup.objects.create(name="Sebze", order=1)
        self.category = Category.objects.create(name="Çorba", order=1)
        self.domates = Ingredient.objects.create(name="Domates", group=self.group)
        self.sogan = Ingredient.objects.create(name="Kuru soğan", group=self.group)
        self.recipe = Recipe.objects.create(
            title="Domates Çorbası",
            summary="özet",
            category=self.category,
            prep_minutes=10,
            cook_minutes=20,
            steps="Karıştır.",
        )

        self.user = User.objects.create_user(
            username="user1@example.com",
            email="user1@example.com",
            password="parola-123-abc",
            first_name="Birinci",
        )
        self.other_user = User.objects.create_user(
            username="user2@example.com",
            email="user2@example.com",
            password="parola-123-abc",
            first_name="Ikinci",
        )
        self.client.login(username="user1@example.com", password="parola-123-abc")

    # ---- Dolap ----

    def test_pantry_save_replaces_ingredients(self):
        response = self.client.post(
            reverse("accounts:pantry_save"),
            data=json.dumps({"slugs": [self.domates.slug, self.sogan.slug]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        pantry = Pantry.objects.get(user=self.user)
        self.assertEqual(set(pantry.ingredients.values_list("slug", flat=True)), {"domates", "kuru-sogan"})

    def test_pantry_data_returns_saved_ingredients(self):
        pantry = Pantry.objects.create(user=self.user)
        pantry.ingredients.add(self.domates)
        response = self.client.get(reverse("accounts:pantry_data"))
        data = response.json()
        self.assertEqual(len(data["ingredients"]), 1)
        self.assertEqual(data["ingredients"][0]["slug"], "domates")

    def test_pantry_save_caps_at_max_items(self):
        many_slugs = [f"uydurma-{i}" for i in range(50)]
        response = self.client.post(
            reverse("accounts:pantry_save"),
            data=json.dumps({"slugs": many_slugs}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)  # çökmemeli, sadece eşleşen 0 malzeme kaydedilir

    def test_pantry_save_rejects_malformed_json_without_wiping_pantry(self):
        pantry = Pantry.objects.create(user=self.user)
        pantry.ingredients.add(self.domates)

        response = self.client.post(
            reverse("accounts:pantry_save"),
            data=b'{"slugs": [oops malformed',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        pantry.refresh_from_db()
        self.assertEqual(set(pantry.ingredients.values_list("slug", flat=True)), {"domates"})

    # ---- Favoriler ----

    def test_favorite_toggle_creates_and_removes(self):
        url = reverse("accounts:favorite_toggle", args=[self.recipe.slug])
        response = self.client.post(url)
        self.assertEqual(response.json(), {"is_favorited": True})
        self.assertTrue(Favorite.objects.filter(user=self.user, recipe=self.recipe).exists())

        response = self.client.post(url)
        self.assertEqual(response.json(), {"is_favorited": False})
        self.assertFalse(Favorite.objects.filter(user=self.user, recipe=self.recipe).exists())

    def test_favorite_unique_per_user_and_recipe(self):
        Favorite.objects.create(user=self.user, recipe=self.recipe)
        with self.assertRaises(Exception):
            Favorite.objects.create(user=self.user, recipe=self.recipe)

    def test_favorites_list_only_shows_own_favorites(self):
        Favorite.objects.create(user=self.user, recipe=self.recipe)
        other_recipe = Recipe.objects.create(
            title="Başka Tarif",
            summary="özet",
            category=self.category,
            prep_minutes=5,
            cook_minutes=5,
            steps="Karıştır.",
        )
        Favorite.objects.create(user=self.other_user, recipe=other_recipe)

        response = self.client.get(reverse("accounts:favorites_list"))
        self.assertContains(response, "Domates Çorbası")
        self.assertNotContains(response, "Başka Tarif")

    # ---- Alışveriş listesi ----

    def test_shopping_list_add_and_dedup(self):
        url = reverse("accounts:shopping_list_add")
        payload = {"items": [{"slug": "domates", "name": "Domates"}]}
        self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(ShoppingItem.objects.filter(user=self.user).count(), 1)

    def test_shopping_list_toggle_and_delete(self):
        item = ShoppingItem.objects.create(user=self.user, text="Domates")
        toggle_url = reverse("accounts:shopping_list_toggle", args=[item.id])
        response = self.client.post(toggle_url)
        self.assertEqual(response.json(), {"checked": True})
        item.refresh_from_db()
        self.assertTrue(item.is_checked)

        delete_url = reverse("accounts:shopping_list_delete", args=[item.id])
        self.client.post(delete_url)
        self.assertFalse(ShoppingItem.objects.filter(id=item.id).exists())

    def test_shopping_list_clear_only_clears_own_items(self):
        ShoppingItem.objects.create(user=self.user, text="Domates")
        other_item = ShoppingItem.objects.create(user=self.other_user, text="Soğan")

        self.client.post(reverse("accounts:shopping_list_clear"))

        self.assertEqual(ShoppingItem.objects.filter(user=self.user).count(), 0)
        self.assertTrue(ShoppingItem.objects.filter(id=other_item.id).exists())

    # ---- Girişte localStorage birleştirme ----

    def test_merge_local_data_adds_pantry_and_shopping_items(self):
        payload = {
            "selected": [{"slug": "domates", "name": "Domates"}],
            "shopping": [{"slug": "kuru-sogan", "name": "Kuru soğan", "checked": False}],
        }
        response = self.client.post(
            reverse("accounts:merge_local_data"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        pantry = Pantry.objects.get(user=self.user)
        self.assertIn(self.domates, pantry.ingredients.all())
        self.assertTrue(ShoppingItem.objects.filter(user=self.user, text="Kuru soğan").exists())


class AuthorizationTests(TestCase):
    """Bir kullanıcı başka birinin favori veya liste öğesine erişemiyor/silemiyor."""

    def setUp(self):
        self.category = Category.objects.create(name="Çorba", order=1)
        self.recipe = Recipe.objects.create(
            title="Domates Çorbası",
            summary="özet",
            category=self.category,
            prep_minutes=10,
            cook_minutes=20,
            steps="Karıştır.",
        )
        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="parola-123-abc",
            first_name="Sahip",
        )
        self.attacker = User.objects.create_user(
            username="attacker@example.com",
            email="attacker@example.com",
            password="parola-123-abc",
            first_name="Saldirgan",
        )
        self.owner_item = ShoppingItem.objects.create(user=self.owner, text="Domates")
        self.client.login(username="attacker@example.com", password="parola-123-abc")

    def test_cannot_toggle_other_users_shopping_item(self):
        url = reverse("accounts:shopping_list_toggle", args=[self.owner_item.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        self.owner_item.refresh_from_db()
        self.assertFalse(self.owner_item.is_checked)

    def test_cannot_delete_other_users_shopping_item(self):
        url = reverse("accounts:shopping_list_delete", args=[self.owner_item.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ShoppingItem.objects.filter(id=self.owner_item.id).exists())

    def test_clear_does_not_touch_other_users_items(self):
        self.client.post(reverse("accounts:shopping_list_clear"))
        self.assertTrue(ShoppingItem.objects.filter(id=self.owner_item.id).exists())

    def test_cannot_see_other_users_pantry(self):
        pantry = Pantry.objects.create(user=self.owner)
        response = self.client.get(reverse("accounts:pantry_data"))
        data = response.json()
        self.assertEqual(data["ingredients"], [])
