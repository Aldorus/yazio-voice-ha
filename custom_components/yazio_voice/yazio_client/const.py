API_VERSION = "v15"
BASE_URL = f"https://yzapi.yazio.com/{API_VERSION}"
TOKEN_ENDPOINT = f"{BASE_URL}/oauth/token"

# Credentials of the official mobile app, reused by the whole unofficial
# API ecosystem (yazio-exporter, yazio_public_api, juriadams/yazio, ...).
# No secret specific to this project: Yazio does not publish a partner API.
CLIENT_ID = "1_4hiybetvfksgw40o0sog4s884kwc840wwso8go4k8c04goo4c"
CLIENT_SECRET = "6rok2m65xuskgkgogw40wkkk8sw0osg84s8cggsc4woos4s8o"

USER_AGENT = "Yazio/1.0 (HomeAssistant yazio_client)"

REQUEST_TIMEOUT = 10
