import unicodedata

# Unités qui désignent directement l'unité de base du produit (g ou ml),
# donc pas de lookup de serving nécessaire.
_BASE_UNIT_ALIASES = {
    "g": {"g", "gramme", "grammes", "gram", "grams"},
    "ml": {"ml", "millilitre", "millilitres", "milliliter", "milliliters"},
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.strip().lower()
    if text.endswith("s") and len(text) > 1:
        text = text[:-1]
    return text


def is_base_unit_alias(unit: str, base_unit: str) -> bool:
    aliases = _BASE_UNIT_ALIASES.get(base_unit.lower())
    if not aliases:
        return normalize(unit) == normalize(base_unit)
    return normalize(unit) in {normalize(a) for a in aliases}
