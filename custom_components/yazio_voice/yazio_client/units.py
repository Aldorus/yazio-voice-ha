import unicodedata

# Units that directly designate the product's base unit (g or ml), so no
# serving lookup is needed. French aliases are kept on purpose: dictation
# may be in French.
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
