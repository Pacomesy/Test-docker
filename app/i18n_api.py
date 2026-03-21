"""Messages API HTTP localisés (en-tête X-App-Locale: de|fr|it|en)."""

from __future__ import annotations

LOCALES = frozenset({"de", "fr", "it", "en"})
DEFAULT_LOCALE = "fr"


def parse_app_locale(header: str | None) -> str:
    if not header:
        return DEFAULT_LOCALE
    v = header.strip().lower()
    if v in LOCALES:
        return v
    if len(v) >= 2 and v[:2] in LOCALES:
        return v[:2]
    return DEFAULT_LOCALE


class UnknownTimezoneError(Exception):
    def __init__(self, tz_name: str) -> None:
        self.tz_name = tz_name


API_MESSAGES: dict[str, dict[str, str]] = {
    "page_missing": {
        "fr": "Fichier de page introuvable.",
        "de": "Seitendatei fehlt.",
        "it": "File di pagina mancante.",
        "en": "Page file is missing.",
    },
    "unknown_tz": {
        "fr": "Fuseau inconnu : {name}",
        "de": "Unbekannte Zeitzone: {name}",
        "it": "Fuso orario sconosciuto: {name}",
        "en": "Unknown timezone: {name}",
    },
    "duplicate_tile": {
        "fr": "Ce fuseau est déjà affiché.",
        "de": "Diese Zeitzone wird bereits angezeigt.",
        "it": "Questo fuso è già mostrato.",
        "en": "This timezone is already shown.",
    },
    "tile_not_found": {
        "fr": "Tuile introuvable.",
        "de": "Kachel nicht gefunden.",
        "it": "Riquadro non trovato.",
        "en": "Tile not found.",
    },
    "order_invalid": {
        "fr": "La liste « order » doit contenir exactement les mêmes identifiants que les tuiles actuelles.",
        "de": "Die Liste « order » muss genau dieselben IDs wie die aktuellen Kacheln enthalten.",
        "it": "L'elenco « order » deve contenere esattamente gli stessi ID delle tessere attuali.",
        "en": "The « order » list must contain exactly the same IDs as the current tiles.",
    },
}


def api_msg(locale: str, key: str, **kwargs: str) -> str:
    loc = parse_app_locale(locale)
    template = API_MESSAGES.get(key, {}).get(loc) or API_MESSAGES.get(key, {}).get(DEFAULT_LOCALE) or key
    return template.format(**kwargs) if kwargs else template
