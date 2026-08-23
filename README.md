# Tracker de calories vocal → Yazio

Voir [CLAUDE.md](.idea/CLAUDE.md) pour le cadrage complet du projet.

## Architecture

Le pipeline Assist de Home Assistant est déjà en place (satellite vocal +
agent de conversation Claude). Ce projet **crée le "skill"** qui manque :
une intégration Home Assistant qui expose deux outils à Assist pour
chercher un aliment dans Yazio puis le logger, avec confirmation humaine
obligatoire entre les deux.

```
Voix → satellite Assist → agent Claude (conversation.claude_conversation)
                              │
                              ├─ 1. script.yazio_search_food ──▶ service yazio_voice.search_food
                              │      (search-first, ne logge rien)
                              ├─ Claude relaie le résultat, attend confirmation
                              └─ 2. script.yazio_log_food ─────▶ service yazio_voice.log_food
                                     (add_consumed_item)
```

Tout tourne **dans Home Assistant lui-même** — pas de process séparé (pas
d'AppDaemon, pas de rest_command, pas de port HTTP à exposer).

- [`custom_components/yazio_voice/`](custom_components/yazio_voice/) — intégration HA : config flow pour les identifiants, deux services natifs (`yazio_voice.search_food`, `yazio_voice.log_food`).
- [`custom_components/yazio_voice/yazio_client/`](custom_components/yazio_voice/yazio_client/) — lib Python pure (auth, recherche, écriture Yazio), vendée dans l'intégration. Testée (`pytest`), sans dépendance à Home Assistant — c'est pour ça qu'elle est isolée dans son propre dossier.
- [`homeassistant/scripts_yazio_voice.yaml`](homeassistant/scripts_yazio_voice.yaml) — les deux entités `script.*` à exposer à Assist (les services natifs ne sont pas exposables directement, il faut ce fin wrapper `script:` pour qu'ils apparaissent comme outils Assist).

## Installation

1. **Copier le dossier** `custom_components/yazio_voice/` dans `config/custom_components/` de votre instance Home Assistant.
2. Redémarrer Home Assistant.
3. **Ajouter l'intégration** (seule saisie manuelle avec l'étape 4) : Paramètres → Appareils et services → Ajouter une intégration → « Yazio Voice » → entrer email/mot de passe Yazio. Le mot de passe n'est jamais stocké ensuite, seuls les tokens le sont (dans l'entrée de configuration HA).
4. Fusionner [`homeassistant/scripts_yazio_voice.yaml`](homeassistant/scripts_yazio_voice.yaml) dans `scripts.yaml`, recharger les scripts.
5. **Exposer les entités à Assist** (seconde saisie manuelle) : Paramètres → Voix → Exposer, activer `script.yazio_search_food` et `script.yazio_log_food`.

## Développement

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

## État / limites connues

- Pas de fallback "créer un produit custom" si aucun match Yazio
  satisfaisant (décision CLAUDE.md) — non implémenté pour l'instant.
- `custom_components/yazio_voice/__init__.py` n'a pas été testé dans une
  vraie instance HA (pas d'accès filesystem à l'instance de déploiement
  depuis cette session) — la logique métier (`yazio_client`) est testée,
  mais l'intégration HA elle-même (config flow, services) reste à valider
  après installation.
