import json
from functools import wraps

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from recipes.models import Ingredient, Recipe

from .models import Favorite, Pantry, ShoppingItem

MAX_ITEMS = 30  # localStorage'dan/istekten gelen listelerde üst sınır


def json_login_required(view_func):
    """@login_required'ın yönlendirme yerine 401 JSON döndüren hâli (fetch uç noktaları için)."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Bu işlem için giriş yapmalısın."}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


def _parse_json_body(request):
    """Gövdeyi JSON olarak ayrıştırır; bozuksa veya dict değilse None döner.

    None ile boş-ama-geçerli bir {} karıştırılmamalı: çağıranlar None'ı hatalı
    istek (400) olarak ele almalı, aksi hâlde bozuk gövde "hiç değişiklik yok"
    yerine "her şeyi sil" olarak yorumlanabilir (bkz. pantry_save).
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def favorites_list(request):
    if not request.user.is_authenticated:
        return render(request, "recipes/favorites.html", {"login_required": True})

    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related("recipe", "recipe__category")
        .order_by("-created_at")
    )
    context = {
        "login_required": False,
        "favorites": favorites,
        "favorite_recipe_ids": {f.recipe_id for f in favorites},
    }
    return render(request, "recipes/favorites.html", context)


@json_login_required
@require_POST
def favorite_toggle(request, recipe_slug):
    recipe = get_object_or_404(Recipe, slug=recipe_slug, is_published=True)
    favorite, created = Favorite.objects.get_or_create(user=request.user, recipe=recipe)
    if not created:
        favorite.delete()
        return JsonResponse({"is_favorited": False})
    return JsonResponse({"is_favorited": True})


@json_login_required
@require_POST
def pantry_save(request):
    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Geçersiz veri."}, status=400)
    slugs = data.get("slugs", [])
    if not isinstance(slugs, list):
        return JsonResponse({"error": "Geçersiz veri."}, status=400)
    slugs = [str(s) for s in slugs][:MAX_ITEMS]

    ingredients = Ingredient.objects.filter(slug__in=slugs)
    pantry, _ = Pantry.objects.get_or_create(user=request.user)
    pantry.ingredients.set(ingredients)
    return JsonResponse({"saved": ingredients.count()})


@json_login_required
def pantry_data(request):
    try:
        pantry = request.user.pantry
        ingredients = pantry.ingredients.order_by("name")
    except Pantry.DoesNotExist:
        ingredients = Ingredient.objects.none()
    data = [{"slug": i.slug, "name": i.name} for i in ingredients]
    return JsonResponse({"ingredients": data})


@json_login_required
def shopping_list_data(request):
    items = ShoppingItem.objects.filter(user=request.user).order_by("created_at")
    data = [
        {"id": item.id, "text": item.text, "checked": item.is_checked} for item in items
    ]
    return JsonResponse({"items": data})


def _add_shopping_items(user, raw_items):
    # get_or_create + veritabanı seviyesindeki unique_user_shopping_text kısıtlaması
    # (bkz. ShoppingItem.Meta) tekilleştirmeyi eşzamanlı isteklerde de garanti eder;
    # yalnızca bellekte tutulan bir küme yarış durumunda aynı öğeyi iki kez oluşturabilirdi.
    added = 0
    for raw in raw_items[:MAX_ITEMS]:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name", "")).strip()[:100]
        if not name:
            continue
        slug = str(raw.get("slug", "")).strip()
        ingredient = Ingredient.objects.filter(slug=slug).first() if slug else None
        is_checked = bool(raw.get("checked", False))
        _, created = ShoppingItem.objects.get_or_create(
            user=user,
            text=name,
            defaults={"ingredient": ingredient, "is_checked": is_checked},
        )
        if created:
            added += 1
    return added


@json_login_required
@require_POST
def shopping_list_add(request):
    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Geçersiz veri."}, status=400)
    items = data.get("items", [])
    if not isinstance(items, list):
        return JsonResponse({"error": "Geçersiz veri."}, status=400)
    added = _add_shopping_items(request.user, items)
    return JsonResponse({"added": added})


@json_login_required
@require_POST
def shopping_list_toggle(request, item_id):
    item = get_object_or_404(ShoppingItem, pk=item_id, user=request.user)
    item.is_checked = not item.is_checked
    item.save(update_fields=["is_checked"])
    return JsonResponse({"checked": item.is_checked})


@json_login_required
@require_POST
def shopping_list_delete(request, item_id):
    item = get_object_or_404(ShoppingItem, pk=item_id, user=request.user)
    item.delete()
    return JsonResponse({"deleted": True})


@json_login_required
@require_POST
def shopping_list_clear(request):
    ShoppingItem.objects.filter(user=request.user).delete()
    return JsonResponse({"cleared": True})


@json_login_required
@require_POST
def merge_local_data(request):
    """Girişten hemen sonra, tarayıcıdaki localStorage verisini hesaba bir kerelik aktarır."""
    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Geçersiz veri."}, status=400)

    selected = data.get("selected", [])
    if isinstance(selected, list):
        slugs = [str(item.get("slug", "")) for item in selected if isinstance(item, dict)][
            :MAX_ITEMS
        ]
        ingredients = Ingredient.objects.filter(slug__in=slugs)
        if ingredients:
            pantry, _ = Pantry.objects.get_or_create(user=request.user)
            pantry.ingredients.add(*ingredients)

    shopping = data.get("shopping", [])
    added = 0
    if isinstance(shopping, list):
        added = _add_shopping_items(request.user, shopping)

    return JsonResponse({"merged": True, "shopping_added": added})
