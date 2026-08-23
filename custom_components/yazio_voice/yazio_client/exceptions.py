class YazioError(Exception):
    """Erreur générique du client Yazio."""


class YazioAuthError(YazioError):
    """Échec d'authentification ou de rafraîchissement de token."""
