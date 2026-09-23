from django.db import models

from .utils import generate_unique_slug


class Allergen(models.Model):
    CODE_CHOICES = [
        ("gluten", "Gluten"),
        ("sut", "Süt"),
        ("yumurta", "Yumurta"),
        ("kuruyemis", "Kuruyemiş"),
        ("yer_fistigi", "Yer Fıstığı"),
        ("balik", "Balık"),
        ("kabuklu_deniz", "Kabuklu Deniz Ürünleri"),
        ("soya", "Soya"),
        ("susam", "Susam"),
        ("kereviz", "Kereviz"),
        ("hardal", "Hardal"),
    ]

    code = models.CharField("kod", max_length=20, choices=CODE_CHOICES, unique=True)
    name = models.CharField("ad", max_length=50)
    emoji = models.CharField("emoji", max_length=8, blank=True)

    class Meta:
        verbose_name = "Alerjen"
        verbose_name_plural = "Alerjenler"
        ordering = ["name"]

    def __str__(self):
        return self.name


class IngredientGroup(models.Model):
    name = models.CharField("ad", max_length=50, unique=True)
    order = models.PositiveSmallIntegerField("sıra", default=0)

    class Meta:
        verbose_name = "Malzeme Grubu"
        verbose_name_plural = "Malzeme Grupları"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField("ad", max_length=100, unique=True)
    slug = models.SlugField("slug", max_length=120, unique=True, blank=True)
    group = models.ForeignKey(
        IngredientGroup,
        verbose_name="grup",
        on_delete=models.PROTECT,
        related_name="ingredients",
    )
    synonyms = models.CharField(
        "eş anlamlılar",
        max_length=255,
        blank=True,
        help_text="Virgülle ayırarak yazın, örn: domatesler, çeri domates",
    )
    is_staple = models.BooleanField(
        "temel malzeme",
        default=False,
        help_text="Her evde bulunduğu varsayılan malzeme (tuz, su, sıvı yağ, karabiber gibi)",
    )
    allergens = models.ManyToManyField(
        Allergen, verbose_name="alerjenler", blank=True, related_name="ingredients"
    )

    class Meta:
        verbose_name = "Malzeme"
        verbose_name_plural = "Malzemeler"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)


class Category(models.Model):
    name = models.CharField("ad", max_length=50, unique=True)
    slug = models.SlugField("slug", max_length=60, unique=True, blank=True)
    emoji = models.CharField("emoji", max_length=8, blank=True)
    order = models.PositiveSmallIntegerField("sıra", default=0)

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)


class Recipe(models.Model):
    DIFFICULTY_CHOICES = [
        ("kolay", "Kolay"),
        ("orta", "Orta"),
    ]

    title = models.CharField("başlık", max_length=150, unique=True)
    slug = models.SlugField("slug", max_length=170, unique=True, blank=True)
    summary = models.CharField("özet", max_length=200)
    category = models.ForeignKey(
        Category, verbose_name="kategori", on_delete=models.PROTECT, related_name="recipes"
    )
    prep_minutes = models.PositiveSmallIntegerField("hazırlık süresi (dk)")
    cook_minutes = models.PositiveSmallIntegerField("pişirme süresi (dk)")
    servings = models.PositiveSmallIntegerField("porsiyon", default=4)
    difficulty = models.CharField(
        "zorluk", max_length=10, choices=DIFFICULTY_CHOICES, default="kolay"
    )
    emoji = models.CharField("emoji", max_length=8, blank=True)
    steps = models.TextField("adımlar", help_text="Her satıra bir adım yazın")
    tips = models.TextField("ipuçları", blank=True)
    is_published = models.BooleanField("yayında", default=True)
    created_at = models.DateTimeField("oluşturulma tarihi", auto_now_add=True)

    ingredients = models.ManyToManyField(
        Ingredient, through="RecipeIngredient", related_name="recipes"
    )

    class Meta:
        verbose_name = "Tarif"
        verbose_name_plural = "Tarifler"
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)
        super().save(*args, **kwargs)

    @property
    def total_minutes(self):
        return self.prep_minutes + self.cook_minutes

    @property
    def step_list(self):
        return [step.strip() for step in self.steps.splitlines() if step.strip()]

    @property
    def allergens(self):
        return Allergen.objects.filter(ingredients__recipes=self).distinct()


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, verbose_name="tarif", on_delete=models.CASCADE, related_name="recipe_ingredients"
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name="malzeme",
        on_delete=models.PROTECT,
        related_name="recipe_ingredients",
    )
    amount = models.CharField("miktar", max_length=50)
    is_optional = models.BooleanField("opsiyonel", default=False)

    class Meta:
        verbose_name = "Tarif Malzemesi"
        verbose_name_plural = "Tarif Malzemeleri"
        constraints = [
            models.UniqueConstraint(fields=["recipe", "ingredient"], name="unique_recipe_ingredient")
        ]
        ordering = ["id"]

    def __str__(self):
        return f"{self.recipe.title} - {self.ingredient.name}"
