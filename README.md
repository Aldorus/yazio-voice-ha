# Voice calorie tracker → Yazio

(The detailed project brief, CLAUDE.md, is not published in this repo.)

## Architecture

The Home Assistant Assist pipeline is already in place (voice satellite +
Claude conversation agent). This project **builds the missing "skill"**:
a Home Assistant integration that exposes two tools to Assist to search for
a food in Yazio and then log it, with mandatory human confirmation between
the two.

```
Voice → Assist satellite → Claude agent (conversation.claude_conversation)
                              │
                              ├─ 1. script.yazio_search_food ──▶ service yazio_voice.search_food
                              │      (search-first, logs nothing)
                              ├─ Claude relays the result, waits for confirmation
                              └─ 2. script.yazio_log_food ─────▶ service yazio_voice.log_food
                                     (add_consumed_item)
```

Everything runs **inside Home Assistant itself** — no separate process (no
AppDaemon, no rest_command, no HTTP port to expose).

- [`custom_components/yazio_voice/`](custom_components/yazio_voice/) — HA integration: config flow for the credentials, two native services (`yazio_voice.search_food`, `yazio_voice.log_food`).
- [`custom_components/yazio_voice/yazio_client/`](custom_components/yazio_voice/yazio_client/) — pure Python library (auth, search, writing to Yazio), vendored into the integration. Tested (`pytest`) and independent of Home Assistant — which is why it lives in its own folder.
- [`homeassistant/scripts_yazio_voice.yaml`](homeassistant/scripts_yazio_voice.yaml) — the two `script.*` entities to expose to Assist (native services cannot be exposed directly; this thin `script:` wrapper is needed for them to show up as Assist tools).

## Installation

### Via HACS (recommended)

1. HACS → ⋮ menu → **Custom repositories** → add `https://github.com/Aldorus/yazio-voice-ha`, category **Integration**.
2. Install "Yazio Voice" from HACS, then restart Home Assistant.
3. **Add the integration** (one of only two manual steps, the other being step 5): Settings → Devices & services → Add integration → "Yazio Voice" → enter your Yazio email/password. The password is never stored afterwards; only the tokens are (in the HA config entry).
4. Merge [`homeassistant/scripts_yazio_voice.yaml`](homeassistant/scripts_yazio_voice.yaml) into `scripts.yaml`, then reload scripts.
5. **Expose the entities to Assist** (second manual step): Settings → Voice assistants → Expose, enable `script.yazio_search_food` and `script.yazio_log_food`.

### Manually

1. Copy `custom_components/yazio_voice/` into `config/custom_components/`.
2. Follow steps 2 to 5 above.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

## Status / known limitations

- No "create a custom product" fallback when there is no satisfactory Yazio
  match (decision recorded in CLAUDE.md) — not implemented yet.
- `custom_components/yazio_voice/__init__.py` has not been tested in a real
  HA instance (no filesystem access to the deployment instance from this
  session) — the business logic (`yazio_client`) is tested, but the HA
  integration itself (config flow, services) still needs to be validated
  after installation.
