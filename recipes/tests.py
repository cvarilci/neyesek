from django.urls import reverse
from django.test import TestCase

from .models import Allergen, Category, Ingredient, IngredientGroup, Recipe, RecipeIngredient
from .services import match_recipes, search_ingredients, suggest_ingredients
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


def _ri(recipe, ingredient, is_optional=False):
    return RecipeIngredient.objects.create(
        recipe=recipe, ingredient=ingredient, amount="1 adet", is_optional=is_optional
    )


class MatchRecipesTests(TestCase):
    def setUp(self):
        self.group = IngredientGroup.objects.create(name="Sebze", order=1)
        self.cat_yumurtali = Category.objects.create(name="Yumurtalı", order=1)
        self.cat_corba = Category.objects.create(name="Çorba", order=2)

        def ing(name, is_staple=False):
            return Ingredient.objects.create(name=name, group=self.group, is_staple=is_staple)

        self.yumurta = ing("Yumurta")
        self.domates = ing("Domates")
        self.biber = ing("Yeşil biber")
        self.sogan = ing("Kuru soğan")
        self.patates = ing("Patates")
        self.mercimek = ing("Kırmızı mercimek")
        self.lor = ing("Lor peyniri")
        self.kasar = ing("Kaşar peyniri")
        self.tuz = ing("Tuz", is_staple=True)
        self.yag = ing("Sıvı yağ", is_staple=True)

        self.selected = {self.yumurta.id, self.domates.id, self.biber.id}

        # Hazır: tüm zorunlu malzemeler seçili, temel malzemeler görmezden gelinir.
        self.menemen = Recipe.objects.create(
            title="Menemen",
            summary="özet",
            category=self.cat_yumurtali,
            prep_minutes=5,
            cook_minutes=15,
            steps="Karıştır.",
        )
        _ri(self.menemen, self.yumurta)
        _ri(self.menemen, self.domates)
        _ri(self.menemen, self.biber)
        _ri(self.menemen, self.tuz)
        _ri(self.menemen, self.yag)
        _ri(self.menemen, self.kasar, is_optional=True)  # opsiyonel, sayılmamalı

        # 2 eksik: soğan + patates.
        self.recipe_2_eksik = Recipe.objects.create(
            title="İki Eksikli Tarif",
            summary="özet",
            category=self.cat_yumurtali,
            prep_minutes=5,
            cook_minutes=15,
            steps="Karıştır.",
        )
        for i in (self.yumurta, self.domates, self.biber, self.sogan, self.patates):
            _ri(self.recipe_2_eksik, i)

        # Tam sınırda 3 eksik: yumurta var, mercimek+soğan+patates yok.
        self.recipe_3_eksik = Recipe.objects.create(
            title="Üç Eksikli Tarif",
            summary="özet",
            category=self.cat_corba,
            prep_minutes=10,
            cook_minutes=20,
            steps="Karıştır.",
        )
        for i in (self.yumurta, self.mercimek, self.sogan, self.patates):
            _ri(self.recipe_3_eksik, i)

        # Sınırın üstü, 4 eksik: elenmeli.
        self.recipe_4_eksik = Recipe.objects.create(
            title="Dört Eksikli Tarif",
            summary="özet",
            category=self.cat_corba,
            prep_minutes=10,
            cook_minutes=20,
            steps="Karıştır.",
        )
        for i in (self.yumurta, self.mercimek, self.sogan, self.patates, self.lor):
            _ri(self.recipe_4_eksik, i)

        # Seçimle hiç ilgisi yok: elenmeli.
        self.recipe_alakasiz = Recipe.objects.create(
            title="Alakasız Tarif",
            summary="özet",
            category=self.cat_corba,
            prep_minutes=10,
            cook_minutes=20,
            steps="Karıştır.",
        )
        for i in (self.mercimek, self.sogan, self.patates):
            _ri(self.recipe_alakasiz, i)

        # Sadece temel malzeme: required boş kalır, yine de "hazır" sayılmalı.
        self.recipe_sadece_temel = Recipe.objects.create(
            title="Sadece Temel Tarif",
            summary="özet",
            category=self.cat_corba,
            prep_minutes=5,
            cook_minutes=5,
            steps="Karıştır.",
        )
        _ri(self.recipe_sadece_temel, self.tuz)
        _ri(self.recipe_sadece_temel, self.yag)

        # Süre filtresi testi için uzun süren bir tarif.
        self.recipe_uzun_sureli = Recipe.objects.create(
            title="Uzun Süreli Tarif",
            summary="özet",
            category=self.cat_yumurtali,
            prep_minutes=30,
            cook_minutes=30,
            steps="Karıştır.",
        )
        for i in (self.yumurta, self.domates, self.biber):
            _ri(self.recipe_uzun_sureli, i)

        # Yayında olmayan tarif hiçbir zaman çıkmamalı.
        self.recipe_yayinda_degil = Recipe.objects.create(
            title="Taslak Tarif",
            summary="özet",
            category=self.cat_yumurtali,
            prep_minutes=5,
            cook_minutes=5,
            steps="Karıştır.",
            is_published=False,
        )
        for i in (self.yumurta, self.domates, self.biber):
            _ri(self.recipe_yayinda_degil, i)

    def test_ready_group_has_no_missing_ingredients(self):
        result = match_recipes(self.selected)
        ready_titles = {r.recipe.title for r in result["ready"]}
        self.assertIn("Menemen", ready_titles)

    def test_optional_ingredient_not_counted_as_missing(self):
        result = match_recipes(self.selected)
        menemen_result = next(r for r in result["ready"] if r.recipe.title == "Menemen")
        self.assertEqual(menemen_result.missing_ingredients, [])

    def test_staples_excluded_from_required_and_missing(self):
        result = match_recipes(self.selected)
        menemen_result = next(r for r in result["ready"] if r.recipe.title == "Menemen")
        self.assertEqual(menemen_result.required_count, 3)  # tuz/yağ/kaşar sayılmadı

    def test_almost_group_includes_one_to_three_missing(self):
        result = match_recipes(self.selected)
        almost_titles = {r.recipe.title for r in result["almost"]}
        self.assertIn("İki Eksikli Tarif", almost_titles)
        self.assertIn("Üç Eksikli Tarif", almost_titles)

    def test_more_than_max_missing_is_excluded(self):
        result = match_recipes(self.selected)
        all_titles = {r.recipe.title for r in result["ready"] + result["almost"]}
        self.assertNotIn("Dört Eksikli Tarif", all_titles)

    def test_recipe_with_no_overlap_is_excluded(self):
        result = match_recipes(self.selected)
        all_titles = {r.recipe.title for r in result["ready"] + result["almost"]}
        self.assertNotIn("Alakasız Tarif", all_titles)

    def test_recipe_with_only_staples_counts_as_ready(self):
        result = match_recipes(self.selected)
        ready_titles = {r.recipe.title for r in result["ready"]}
        self.assertIn("Sadece Temel Tarif", ready_titles)

    def test_max_minutes_filter_excludes_long_recipes(self):
        result = match_recipes(self.selected, max_minutes=45)
        all_titles = {r.recipe.title for r in result["ready"] + result["almost"]}
        self.assertNotIn("Uzun Süreli Tarif", all_titles)

    def test_category_filter(self):
        result = match_recipes(self.selected, category=self.cat_corba)
        all_titles = {r.recipe.title for r in result["ready"] + result["almost"]}
        self.assertNotIn("Menemen", all_titles)
        self.assertIn("Üç Eksikli Tarif", all_titles)

    def test_unpublished_recipe_never_returned(self):
        result = match_recipes(self.selected)
        all_titles = {r.recipe.title for r in result["ready"] + result["almost"]}
        self.assertNotIn("Taslak Tarif", all_titles)

    def test_almost_sorted_by_missing_count_ascending(self):
        result = match_recipes(self.selected)
        missing_counts = [len(r.missing_ingredients) for r in result["almost"]]
        self.assertEqual(missing_counts, sorted(missing_counts))

    def test_sorted_by_score_when_missing_count_ties(self):
        # İki tarif de 1 eksikli ama farklı skorlarla; yüksek skorlu önce gelmeli.
        yuksek_skor = Recipe.objects.create(
            title="Yüksek Skor",
            summary="özet",
            category=self.cat_yumurtali,
            prep_minutes=5,
            cook_minutes=5,
            steps="Karıştır.",
        )
        for i in (self.yumurta, self.domates, self.biber, self.sogan):
            _ri(yuksek_skor, i)  # 4 gerekli, 3 var, 1 eksik -> skor 0.75

        dusuk_skor = Recipe.objects.create(
            title="Düşük Skor",
            summary="özet",
            category=self.cat_yumurtali,
            prep_minutes=5,
            cook_minutes=5,
            steps="Karıştır.",
        )
        for i in (self.yumurta, self.domates, self.patates):
            _ri(dusuk_skor, i)  # 3 gerekli, 2 var, 1 eksik -> skor 0.667

        result = match_recipes(self.selected)
        almost_titles = [r.recipe.title for r in result["almost"] if len(r.missing_ingredients) == 1]
        self.assertEqual(almost_titles.index("Yüksek Skor") < almost_titles.index("Düşük Skor"), True)

    def test_constant_query_count(self):
        with self.assertNumQueries(2):
            match_recipes(self.selected)

    def test_suggest_ingredients_finds_ingredient_closing_the_gap(self):
        # Sadece mercimek seçiliyken "Dört Eksikli Tarif" tam sınırın bir fazlası
        # (4 eksik) kadar yakın kalıyor; suggest_ingredients bu eksiklerden birini
        # (lor dahil) önerebilmeli.
        suggestions = suggest_ingredients({self.mercimek.id}, top_n=10)
        self.assertIn(self.lor, suggestions)


class SearchIngredientsTests(TestCase):
    def setUp(self):
        self.group = IngredientGroup.objects.create(name="Sebze", order=1)
        self.domates = Ingredient.objects.create(
            name="Domates", group=self.group, synonyms="domatesler, çeri domates"
        )
        self.ispanak = Ingredient.objects.create(name="Ispanak", group=self.group)

    def test_search_is_case_insensitive_and_turkish_aware(self):
        for query in ("dom", "DOM", "Dom"):
            results = search_ingredients(query)
            self.assertIn(self.domates, results, f"'{query}' domatesi bulamadı")

    def test_search_matches_synonyms(self):
        results = search_ingredients("domatesler")
        self.assertIn(self.domates, results)

    def test_dotless_and_dotted_i_find_same_ingredient(self):
        results_lower = search_ingredients("ıspanak")
        results_upper = search_ingredients("Ispanak")
        self.assertIn(self.ispanak, results_lower)
        self.assertIn(self.ispanak, results_upper)

    def test_empty_query_returns_empty_list(self):
        self.assertEqual(search_ingredients(""), [])
        self.assertEqual(search_ingredients("   "), [])

    def test_constant_query_count(self):
        with self.assertNumQueries(1):
            search_ingredients("dom")


class ViewTests(TestCase):
    def setUp(self):
        self.group = IngredientGroup.objects.create(name="Sebze", order=1)
        self.category = Category.objects.create(name="Yumurtalı", order=1)

        self.yumurta = Ingredient.objects.create(name="Yumurta", group=self.group)
        self.domates = Ingredient.objects.create(name="Domates", group=self.group)
        self.biber = Ingredient.objects.create(name="Yeşil biber", group=self.group)
        self.sogan = Ingredient.objects.create(name="Kuru soğan", group=self.group)
        self.tuz = Ingredient.objects.create(name="Tuz", group=self.group, is_staple=True)

        self.menemen = Recipe.objects.create(
            title="Menemen",
            summary="özet",
            category=self.category,
            prep_minutes=10,
            cook_minutes=15,
            emoji="🍳",
            steps="Karıştır.",
        )
        for i in (self.yumurta, self.domates, self.biber, self.tuz):
            _ri(self.menemen, i)

        self.eksikli = Recipe.objects.create(
            title="Soğanlı Yumurta",
            summary="özet",
            category=self.category,
            prep_minutes=5,
            cook_minutes=10,
            emoji="🥚",
            steps="Karıştır.",
        )
        for i in (self.yumurta, self.sogan):
            _ri(self.eksikli, i)

    def test_results_page_no_selection_shows_empty_state(self):
        response = self.client.get(reverse("recipes:recipe_results"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Henüz malzeme seçmedin")

    def test_results_page_shows_ready_recipe(self):
        response = self.client.get(
            reverse("recipes:recipe_results"),
            {"m": "yumurta,domates,yesil-biber"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Menemen")
        self.assertContains(response, "Hemen yapabilirsin")

    def test_results_page_invalid_params_do_not_crash(self):
        response = self.client.get(
            reverse("recipes:recipe_results"),
            {"m": "yumurta,uydurma-malzeme", "sure": "abc", "kategori": "yoktur"},
        )
        self.assertEqual(response.status_code, 200)

    def test_results_page_caps_ingredient_count_at_30(self):
        slugs = ",".join(["uydurma-{}".format(i) for i in range(50)])
        response = self.client.get(reverse("recipes:recipe_results"), {"m": slugs})
        self.assertEqual(response.status_code, 200)

    def test_results_page_constant_query_count(self):
        with self.assertNumQueries(3):
            self.client.get(
                reverse("recipes:recipe_results"),
                {"m": "yumurta,domates,yesil-biber"},
            )

    def test_detail_page_marks_have_and_missing(self):
        response = self.client.get(
            reverse("recipes:recipe_detail", args=[self.eksikli.slug]),
            {"m": "yumurta"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Eksikleri listeye ekle")

    def test_detail_page_404_for_unpublished_recipe(self):
        self.eksikli.is_published = False
        self.eksikli.save()
        response = self.client.get(reverse("recipes:recipe_detail", args=[self.eksikli.slug]))
        self.assertEqual(response.status_code, 404)

    def test_autocomplete_endpoint_returns_json(self):
        response = self.client.get(
            reverse("recipes:ingredient_autocomplete"), {"q": "dom"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        names = [item["name"] for item in data["results"]]
        self.assertIn("Domates", names)

    def test_autocomplete_empty_query_returns_empty_results(self):
        response = self.client.get(reverse("recipes:ingredient_autocomplete"), {"q": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": []})

    def test_shopping_list_page_renders(self):
        response = self.client.get(reverse("recipes:shopping_list"))
        self.assertEqual(response.status_code, 200)

    def test_home_page_excludes_staples_from_popular_ingredients(self):
        response = self.client.get(reverse("recipes:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, ">Tuz<")
