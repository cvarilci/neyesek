"""Türkçe karakter normalizasyonu ve slug üretimi.

Python'un yerleşik `str.lower()` fonksiyonu 'İ' → 'i̇' (noktalı, bileşik)
ve 'I' → 'i' dönüşümü yapar; Türkçe'de doğrusu 'İ' → 'i' ve 'I' → 'ı'dır.
Arama/eşleştirme her yerde bu modüldeki `normalize_tr()` üzerinden yapılmalı.
"""

import re

_TR_DOTTED_MAP = str.maketrans({"İ": "i", "I": "ı"})

_TR_ASCII_MAP = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }
)


def normalize_tr(text):
    """Türkçe'ye duyarlı küçük harfe çevirme (arama ve eşleştirme için)."""
    if not text:
        return ""
    return text.translate(_TR_DOTTED_MAP).lower()


def turkish_slugify(text):
    """Türkçe karakterleri ASCII karşılığına çevirip URL dostu slug üretir."""
    text = normalize_tr(text).translate(_TR_ASCII_MAP)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def generate_unique_slug(instance, source_text, slug_field="slug"):
    """Verilen model örneği için benzersiz bir slug üretir (varsa `-2`, `-3` ekler)."""
    base_slug = turkish_slugify(source_text)
    model_class = instance.__class__
    slug = base_slug
    counter = 2
    queryset = model_class.objects.exclude(pk=instance.pk)
    while queryset.filter(**{slug_field: slug}).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug
