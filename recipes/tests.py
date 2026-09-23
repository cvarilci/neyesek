from django.test import TestCase

from .models import Allergen, Category, Ingredient, IngredientGroup, Recipe, RecipeIngredient
from .utils import normalize_tr, turkish_slugify


class NormalizeTrTests(TestCase):
    def test_dotted_i_lowercases_to_dotted_i(self):
        self.assertEqual(normalize_tr("İstanbul"), "istanbul")

    def test_dotless_i_lowercases_to_dotless_i(self):
        self.assertEqual(normalize_tr("Ispanak"), "ıspanak")

    def test_case_insensitive_matching(self):
        self.assertEqual(normalize_tr("DOMATES"), normalize_tr("domates"))
        self.assertEqual(normalize_tr("dom"), "dom")

    def test_other_turkish_letters(self):
        self.assertEqual(normalize_tr("ÇÖŞĞÜ"), "çöşğü")

    def test_empty_string(self):
        self.assertEqual(normalize_tr(""), "")
        self.assertEqual(normalize_tr(None), "")


class TurkishSlugifyTests(TestCase):
    def test_turkish_characters_become_ascii(self):
        self.assertEqual(turkish_slugify("Kırmızı Mercimek Çorbası"), "kirmizi-mercimek-corbasi")

    def test_dotless_i(self):
        self.assertEqual(turkish_slugify("Ispanaklı Börek"), "ispanakli-borek")

    def test_strips_non_alphanumeric(self):
        self.assertEqual(turkish_slugify("Fırın'da Tavuk!"), "firin-da-tavuk")


class RecipeModelTests(TestCase):
    def setUp(self):
        self.group = IngredientGroup.objects.create(name="Sebze", order=1)
        self.category = Category.objects.create(name="Çorba", order=1)

        self.gluten = Allergen.objects.create(code="gluten", name="Gluten")
        self.sut = Allergen.objects.create(code="sut", name="Süt")

        self.domates = Ingredient.objects.create(name="Domates", group=self.group)
        self.tuz = Ingredient.objects.create(name="Tuz", group=self.group, is_staple=True)
        self.un = Ingredient.objects.create(name="Un", group=self.group)
        self.un.allergens.add(self.gluten)
        self.sut_ing = Ingredient.objects.create(name="Süt", group=self.group)
        self.sut_ing.allergens.add(self.sut)

        self.recipe = Recipe.objects.create(
            title="Domates Çorbası",
            summary="Basit bir çorba",
            category=self.category,
            prep_minutes=10,
            cook_minutes=20,
            steps="Soğanları kavurun.\nDomatesleri ekleyin.\nSüzün ve servis edin.",
        )
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.domates, amount="4 adet")
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.tuz, amount="1 tutam")
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.un, amount="1 yemek kaşığı")

    def test_total_minutes_is_prep_plus_cook(self):
        self.assertEqual(self.recipe.total_minutes, 30)

    def test_slug_auto_generated_from_title(self):
        self.assertEqual(self.recipe.slug, "domates-corbasi")

    def test_allergens_derived_from_ingredients(self):
        allergens = set(self.recipe.allergens.values_list("code", flat=True))
        self.assertEqual(allergens, {"gluten"})

    def test_allergens_excludes_unused_ingredient_allergens(self):
        # Süt malzemesi bu tarifte kullanılmıyor, süt alerjeni gelmemeli.
        allergens = set(self.recipe.allergens.values_list("code", flat=True))
        self.assertNotIn("sut", allergens)

    def test_step_list_splits_lines(self):
        self.assertEqual(len(self.recipe.step_list), 3)

    def test_unique_slug_when_titles_collide_after_slugify(self):
        # Farklı başlıklar (unique constraint'i ihlal etmiyor) ama noktalama
        # farkı yüzünden aynı slug'a düşüyor; ikincisine "-2" eklenmeli.
        other = Recipe.objects.create(
            title="Domates, Çorbası!",
            summary="Aynı slug'a düşen başka bir tarif",
            category=self.category,
            prep_minutes=5,
            cook_minutes=15,
            steps="Karıştırın.",
        )
        self.assertNotEqual(other.slug, self.recipe.slug)
        self.assertEqual(other.slug, "domates-corbasi-2")

    def test_duplicate_title_raises_integrity_error(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Recipe.objects.create(
                title=self.recipe.title,
                summary="Aynı başlıklı başka bir tarif",
                category=self.category,
                prep_minutes=5,
                cook_minutes=15,
                steps="Karıştırın.",
            )


class IngredientModelTests(TestCase):
    def setUp(self):
        self.group = IngredientGroup.objects.create(name="Sebze", order=1)

    def test_slug_auto_generated_with_turkish_chars(self):
        ingredient = Ingredient.objects.create(name="Ispanak", group=self.group)
        self.assertEqual(ingredient.slug, "ispanak")

    def test_is_staple_default_false(self):
        ingredient = Ingredient.objects.create(name="Kabak", group=self.group)
        self.assertFalse(ingredient.is_staple)
