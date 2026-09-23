"""Malzeme seçimine göre tarif eşleştirme mantığı (view'lardan ayrı, PLAN.md'deki algoritma)."""

from collections import Counter, namedtuple

from django.db.models import Prefetch

from .models import Ingredient, Recipe, RecipeIngredient
from .utils import normalize_tr

DEFAULT_MAX_MISSING = 3
AUTOCOMPLETE_LIMIT = 10

MatchResult = namedtuple(
    "MatchResult",
    ["recipe", "missing_ingredients", "have_count", "required_count", "score"],
)


def _required_recipes_queryset(category=None):
    """Yayında olan tarifleri, zorunlu (opsiyonel olmayan) malzemeleriyle birlikte
    sabit sayıda sorguyla getirir (select_related + prefetch_related)."""
    queryset = (
        Recipe.objects.filter(is_published=True)
        .select_related("category")
        .prefetch_related(
            Prefetch(
                "recipe_ingredients",
                queryset=RecipeIngredient.objects.select_related("ingredient").filter(
                    is_optional=False
                ),
                to_attr="required_links",
            )
        )
    )
    if category is not None:
        queryset = queryset.filter(category=category)
    return queryset


def match_recipes(
    selected_ingredient_ids,
    max_minutes=None,
    category=None,
    max_missing=DEFAULT_MAX_MISSING,
):
    """PLAN.md'deki eşleştirme algoritmasını uygular.

    Döndürür: {"ready": [MatchResult...], "almost": [MatchResult...]}
    - ready: eksik malzemesi olmayan tarifler ("Hemen yapabilirsin")
    - almost: 1..max_missing arası eksik malzemesi olan tarifler ("N malzeme alırsan")
    Her iki grup da (eksik sayısı artan, skor azalan, toplam süre artan) sıralanır.
    """
    selected = set(selected_ingredient_ids)

    ready = []
    almost = []

    for recipe in _required_recipes_queryset(category=category):
        if max_minutes is not None and recipe.total_minutes > max_minutes:
            continue

        required_links = [link for link in recipe.required_links if not link.ingredient.is_staple]
        required_ids = {link.ingredient_id for link in required_links}

        have_ids = required_ids & selected
        missing_ids = required_ids - selected

        # Seçimle hiç ilgisi olmayan tarifi ele (ama malzemesiz/tamamen temel
        # malzemeli bir tarif varsa -required_ids boşsa- bu eleme uygulanmaz).
        if required_ids and not have_ids:
            continue
        if len(missing_ids) > max_missing:
            continue

        missing_ingredients = [
            link.ingredient for link in required_links if link.ingredient_id in missing_ids
        ]
        score = (len(have_ids) / len(required_ids)) if required_ids else 1.0

        result = MatchResult(
            recipe=recipe,
            missing_ingredients=missing_ingredients,
            have_count=len(have_ids),
            required_count=len(required_ids),
            score=score,
        )
        (ready if not missing_ids else almost).append(result)

    def sort_key(result):
        return (len(result.missing_ingredients), -result.score, result.recipe.total_minutes)

    ready.sort(key=sort_key)
    almost.sort(key=sort_key)

    return {"ready": ready, "almost": almost}


def suggest_ingredients(selected_ingredient_ids, max_minutes=None, category=None, top_n=3):
    """Sonuç boş çıktığında: hangi malzeme(ler) eklenince en çok tarif "az eksik"
    sınırına (bir fazlasıyla) girer? Yalnızca boş sonuç durumunda çağrılır."""
    relaxed = match_recipes(
        selected_ingredient_ids,
        max_minutes=max_minutes,
        category=category,
        max_missing=DEFAULT_MAX_MISSING + 1,
    )
    close_misses = [
        result
        for result in relaxed["almost"]
        if len(result.missing_ingredients) == DEFAULT_MAX_MISSING + 1
    ]
    counter = Counter()
    for result in close_misses:
        for ingredient in result.missing_ingredients:
            counter[ingredient] += 1
    return [ingredient for ingredient, _ in counter.most_common(top_n)]


def search_ingredients(query, limit=AUTOCOMPLETE_LIMIT):
    """Ad ve eş anlamlılarda Türkçe'ye duyarlı arama (bkz. `normalize_tr`).

    Tek sorguda tüm malzemeleri çekip Python tarafında eşler; veri seti küçük
    olduğu için (~125 malzeme) bu, doğru Türkçe davranışı DB harmanlamasından
    (collation) bağımsız garanti etmenin en güvenilir yoludur.
    """
    normalized_query = normalize_tr((query or "").strip())
    if not normalized_query:
        return []

    starts_with = []
    contains = []
    for ingredient in Ingredient.objects.select_related("group").all():
        haystacks = [normalize_tr(ingredient.name)]
        if ingredient.synonyms:
            haystacks += [
                normalize_tr(synonym.strip())
                for synonym in ingredient.synonyms.split(",")
                if synonym.strip()
            ]

        if any(haystack.startswith(normalized_query) for haystack in haystacks):
            starts_with.append(ingredient)
        elif any(normalized_query in haystack for haystack in haystacks):
            contains.append(ingredient)

    starts_with.sort(key=lambda ingredient: normalize_tr(ingredient.name))
    contains.sort(key=lambda ingredient: normalize_tr(ingredient.name))

    return (starts_with + contains)[:limit]
