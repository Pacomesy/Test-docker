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
    "index_missing": {
        "fr": "Fichier index.html introuvable.",
        "de": "Datei index.html fehlt.",
        "it": "File index.html mancante.",
        "en": "index.html file is missing.",
    },
    "page_missing": {
        "fr": "Fichier page HTML introuvable.",
        "de": "HTML-Seite fehlt.",
        "it": "Pagina HTML mancante.",
        "en": "HTML page file is missing.",
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
    "client_id_required": {
        "fr": "L’en-tête X-Client-Id (identifiant client UUID) est requis.",
        "de": "Der Header X-Client-Id (UUID) ist erforderlich.",
        "it": "L’header X-Client-Id (UUID client) è obbligatorio.",
        "en": "The X-Client-Id header (client UUID) is required.",
    },
    "client_id_invalid": {
        "fr": "L’en-tête X-Client-Id doit être un UUID valide.",
        "de": "Der Header X-Client-Id muss eine gültige UUID sein.",
        "it": "L’header X-Client-Id deve essere un UUID valido.",
        "en": "The X-Client-Id header must be a valid UUID.",
    },
    "not_controller": {
        "fr": "Seul l’utilisateur qui contrôle l’application peut effectuer cette action.",
        "de": "Nur der Benutzer, der die App steuert, darf diese Aktion ausführen.",
        "it": "Solo chi controlla l’app può eseguire questa azione.",
        "en": "Only the user in control of the app can perform this action.",
    },
    "control_not_controller": {
        "fr": "Vous n’êtes pas le contrôleur actuel.",
        "de": "Sie sind nicht der aktuelle Steuerer.",
        "it": "Non sei il controllore attuale.",
        "en": "You are not the current controller.",
    },
    "control_no_pending": {
        "fr": "Aucune demande de contrôle en attente.",
        "de": "Keine ausstehende Steuerungsanfrage.",
        "it": "Nessuna richiesta di controllo in sospeso.",
        "en": "No pending control request.",
    },
    "control_pending_mismatch": {
        "fr": "La demande en attente ne correspond pas à cet identifiant.",
        "de": "Die ausstehende Anfrage passt nicht zu dieser ID.",
        "it": "La richiesta in sospeso non corrisponde a questo ID.",
        "en": "The pending request does not match this ID.",
    },
    "control_force_not_pending": {
        "fr": "Vous n’avez pas de demande de contrôle en attente.",
        "de": "Sie haben keine ausstehende Steuerungsanfrage.",
        "it": "Non hai una richiesta di controllo in sospeso.",
        "en": "You have no pending control request.",
    },
}


def api_msg(locale: str, key: str, **kwargs: str) -> str:
    loc = parse_app_locale(locale)
    template = API_MESSAGES.get(key, {}).get(loc) or API_MESSAGES.get(key, {}).get(DEFAULT_LOCALE) or key
    return template.format(**kwargs) if kwargs else template
