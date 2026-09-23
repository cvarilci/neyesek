from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from accounts.models import Favorite

from . import services
from .models import Category, Ingredient, IngredientGroup, Recipe

MAX_SELECTED_INGREDIENTS = 30
VALID_DURATIONS = (15, 30, 45)


def _parse_ingredient_slugs(request):
    raw = request.GET.get("m", "")
    slugs = [slug.strip() for slug in raw.split(",") if slug.strip()][:MAX_SELECTED_INGREDIENTS]
    return slugs


def _parse_max_minutes(request):
    raw = request.GET.get("sure", "")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value


def _parse_category(request):
    slug = request.GET.get("kategori", "").strip()
    if not slug:
        return None
    return Category.objects.filter(slug=slug).first()


def home(request):
    groups = IngredientGroup.objects.prefetch_related(
        Prefetch(
            "ingredients",
            queryset=Ingredient.objects.filter(is_staple=False).order_by("name"),
            to_attr="browsable_ingredients",
        )
    ).order_by("order", "name")
    categories = Category.objects.order_by("order", "name")
    context = {
        "groups": groups,
        "categories": categories,
        "durations": VALID_DURATIONS,
    }
    return render(request, "recipes/home.html", context)


def ingredient_autocomplete(request):
    query = request.GET.get("q", "")
    results = services.search_ingredients(query)
    data = [
        {"name": ingredient.name, "slug": ingredient.slug, "group": ingredient.group.name}
        for ingredient in results
    ]
    return JsonResponse({"results": data})


def recipe_results(request):
    slugs = _parse_ingredient_slugs(request)
    max_minutes = _parse_max_minutes(request)
    category = _parse_category(request)

    if not slugs:
        return render(
            request,
            "recipes/results.html",
            {"no_selection": True, "categories": Category.objects.order_by("order", "name")},
        )

    selected_ingredients = list(Ingredient.objects.filter(slug__in=slugs).select_related("group"))
    selected_ids = {ingredient.id for ingredient in selected_ingredients}

    match = services.match_recipes(selected_ids, max_minutes=max_minutes, category=category)

    suggestions = []
    if not match["ready"] and not match["almost"]:
        suggestions = services.suggest_ingredients(
            selected_ids, max_minutes=max_minutes, category=category
        )

    favorite_recipe_ids = set()
    if request.user.is_authenticated:
        favorite_recipe_ids = set(
            Favorite.objects.filter(user=request.user).values_list("recipe_id", flat=True)
        )

    context = {
        "no_selection": False,
        "selected_ingredients": selected_ingredients,
        "m_param": ",".join(slugs),
        "ready": match["ready"],
        "almost": match["almost"],
        "suggestions": suggestions,
        "max_minutes": max_minutes,
        "category": category,
        "categories": Category.objects.order_by("order", "name"),
        "favorite_recipe_ids": favorite_recipe_ids,
    }
    return render(request, "recipes/results.html", context)


def recipe_detail(request, slug):
    recipe = get_object_or_404(
        Recipe.objects.select_related("category").prefetch_related(
            "recipe_ingredients__ingredient__allergens"
        ),
        slug=slug,
        is_published=True,
    )

    slugs = _parse_ingredient_slugs(request)
    selected_slugs = set(slugs)

    ingredient_rows = []
    for link in recipe.recipe_ingredients.all():
        ingredient = link.ingredient
        have = ingredient.is_staple or ingredient.slug in selected_slugs
        ingredient_rows.append(
            {
                "ingredient": ingredient,
                "amount": link.amount,
                "is_optional": link.is_optional,
                "have": have,
            }
        )

    missing_items = [
        {"slug": row["ingredient"].slug, "name": row["ingredient"].name}
        for row in ingredient_rows
        if not row["have"] and not row["is_optional"]
    ]

    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, recipe=recipe).exists()

    context = {
        "recipe": recipe,
        "ingredient_rows": ingredient_rows,
        "missing_items": missing_items,
        "allergens": recipe.allergens,
        "m_param": ",".join(slugs),
        "is_favorited": is_favorited,
    }
    return render(request, "recipes/detail.html", context)


def shopping_list(request):
    return render(request, "recipes/shopping_list.html")
