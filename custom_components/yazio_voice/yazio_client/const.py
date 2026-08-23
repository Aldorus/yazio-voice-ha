API_VERSION = "v15"
BASE_URL = f"https://yzapi.yazio.com/{API_VERSION}"
TOKEN_ENDPOINT = f"{BASE_URL}/oauth/token"

# Identifiants de l'app mobile officielle, réutilisés par toute l'API non
# officielle (yazio-exporter, yazio_public_api, juriadams/yazio, ...). Pas de
# secret propre à ce projet : Yazio ne publie pas d'API partenaire.
CLIENT_ID = "1_4hiybetvfksgw40o0sog4s884kwc840wwso8go4k8c04goo4c"
CLIENT_SECRET = "6rok2m65xuskgkgogw40wkkk8sw0osg84s8cggsc4woos4s8o"

USER_AGENT = "Yazio/1.0 (HomeAssistant yazio_client)"

REQUEST_TIMEOUT = 10
