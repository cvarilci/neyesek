import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recipes.models import (
    Allergen,
    Category,
    Ingredient,
    IngredientGroup,
    Recipe,
    RecipeIngredient,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


def _load(name):
    path = FIXTURES_DIR / name
    with path.open(encoding="utf-8") as f:
        return json.load(f)


class Command(BaseCommand):
    help = "Alerjen, malzeme grubu, kategori, malzeme ve tarif seed verisini yükler (tekrar çalıştırılınca çoğaltmaz)."

    @transaction.atomic
    def handle(self, *args, **options):
        allergens_created, allergens_updated = self._seed_allergens()
        groups_created, groups_updated = self._seed_ingredient_groups()
        categories_created, categories_updated = self._seed_categories()
        ingredients_created, ingredients_updated = self._seed_ingredients()
        recipes_created, recipes_updated = self._seed_recipes()

        self.stdout.write(self.style.SUCCESS("Seed tamamlandı:"))
        self.stdout.write(f"  Alerjenler: {allergens_created} yeni, {allergens_updated} güncellendi")
        self.stdout.write(f"  Malzeme grupları: {groups_created} yeni, {groups_updated} güncellendi")
        self.stdout.write(f"  Kategoriler: {categories_created} yeni, {categories_updated} güncellendi")
        self.stdout.write(f"  Malzemeler: {ingredients_created} yeni, {ingredients_updated} güncellendi")
        self.stdout.write(f"  Tarifler: {recipes_created} yeni, {recipes_updated} güncellendi")

    def _seed_allergens(self):
        created = updated = 0
        for item in _load("allergens.json"):
            obj, was_created = Allergen.objects.update_or_create(
                code=item["code"],
                defaults={"name": item["name"], "emoji": item.get("emoji", "")},
            )
            created += was_created
            updated += not was_created
        return created, updated

    def _seed_ingredient_groups(self):
        created = updated = 0
        for item in _load("ingredient_groups.json"):
            obj, was_created = IngredientGroup.objects.update_or_create(
                name=item["name"],
                defaults={"order": item["order"]},
            )
            created += was_created
            updated += not was_created
        return created, updated

    def _seed_categories(self):
        created = updated = 0
        for item in _load("categories.json"):
            obj, was_created = Category.objects.update_or_create(
                name=item["name"],
                defaults={"emoji": item.get("emoji", ""), "order": item["order"]},
            )
            created += was_created
            updated += not was_created
        return created, updated

    def _seed_ingredients(self):
        created = updated = 0
        for item in _load("ingredients.json"):
            try:
                group = IngredientGroup.objects.get(name=item["group"])
            except IngredientGroup.DoesNotExist as exc:
                raise CommandError(
                    f"'{item['name']}' malzemesi için '{item['group']}' grubu bulunamadı."
                ) from exc

            obj, was_created = Ingredient.objects.update_or_create(
                name=item["name"],
                defaults={
                    "group": group,
                    "synonyms": item.get("synonyms", ""),
                    "is_staple": item.get("is_staple", False),
                },
            )
            allergen_codes = item.get("allergens", [])
            if allergen_codes:
                allergens = Allergen.objects.filter(code__in=allergen_codes)
                obj.allergens.set(allergens)
            else:
                obj.allergens.clear()

            created += was_created
            updated += not was_created
        return created, updated

    def _seed_recipes(self):
        created = updated = 0
        for item in _load("recipes.json"):
            try:
                category = Category.objects.get(name=item["category"])
            except Category.DoesNotExist as exc:
                raise CommandError(
                    f"'{item['title']}' tarifi için '{item['category']}' kategorisi bulunamadı."
                ) from exc

            steps = item["steps"]
            steps_text = "\n".join(steps) if isinstance(steps, list) else steps

            recipe, was_created = Recipe.objects.update_or_create(
                title=item["title"],
                defaults={
                    "summary": item["summary"],
                    "category": category,
                    "prep_minutes": item["prep_minutes"],
                    "cook_minutes": item["cook_minutes"],
                    "servings": item.get("servings", 4),
                    "difficulty": item.get("difficulty", "kolay"),
                    "emoji": item.get("emoji", ""),
                    "steps": steps_text,
                    "tips": item.get("tips", ""),
                    "is_published": item.get("is_published", True),
                },
            )

            recipe_ingredient_ids = []
            for ri in item["ingredients"]:
                try:
                    ingredient = Ingredient.objects.get(name=ri["ingredient"])
                except Ingredient.DoesNotExist as exc:
                    raise CommandError(
                        f"'{item['title']}' tarifindeki '{ri['ingredient']}' malzemesi "
                        "ingredients.json içinde bulunamadı."
                    ) from exc

                recipe_ingredient, _ = RecipeIngredient.objects.update_or_create(
                    recipe=recipe,
                    ingredient=ingredient,
                    defaults={
                        "amount": ri["amount"],
                        "is_optional": ri.get("is_optional", False),
                    },
                )
                recipe_ingredient_ids.append(recipe_ingredient.id)

            # Fixture'dan kaldırılmış malzeme satırlarını temizle
            recipe.recipe_ingredients.exclude(id__in=recipe_ingredient_ids).delete()

            created += was_created
            updated += not was_created
        return created, updated
