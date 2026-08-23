# CLAUDE.md — Tracker de calories vocal → Yazio

Projet perso, open-source, local-first. Logger vocalement ses repas dans Yazio
sans ressaisie manuelle.

## Objectif

L'utilisateur dicte ce qu'il a mangé ; l'outil parse la phrase en aliments +
quantités et crée les entrées correspondantes dans son journal **Yazio** via
l'API. Le but est que l'utilisateur garde son app habituelle (Yazio) — pas de
dashboard maison à adopter.

Yazio a été retenu parce que c'est là que se trouvent les utilisateurs.
MyFitnessPal est écarté (API partenaire fermée depuis 2019, inaccessible).
FatSecret est écarté (impliquerait que l'utilisateur change d'app).

## Contexte & contraintes de déploiement

- Tourne sur l'instance **Home Assistant** de chaque utilisateur — local-first,
  distribué. Pas de backend centralisé.
- Chaque instance détient ses propres credentials Yazio.
- Conséquence assumée : **pas de hotfix global**. Une casse de l'API Yazio =
  nouvelle release + mise à jour côté utilisateur.

## Stack & composants

- **Langage : Python**.
- **Parsing vocal** : pas de skill préexistant à réutiliser — « Mycroft » est
  le nom donné au satellite vocal (Home Assistant Voice PE) dans ce foyer,
  pas un projet Mycroft AI. Le pipeline Assist existe déjà (satellite +
  agent de conversation **Claude**, `conversation.claude_conversation`) ;
  c'est ce projet qui doit créer le "skill" — les outils que l'agent peut
  appeler pendant la conversation. Contrat de sortie du premier outil
  (search) : `{food: str, quantity: float, unit: str}` ; `meal:
  breakfast|lunch|dinner|snack` est fourni au second outil (log).
- **Client Yazio** : à construire en Python. Pas d'API officielle → API mobile
  reverse-engineered, endpoint versionné (`v15` actuellement).

## Bases à réutiliser (ne pas repartir de zéro)

- **`yazio-exporter`** (PyPI) : résout l'auth (`/oauth/token` en
  `x-www-form-urlencoded`, gestion du refresh token) et la structure de l'API.
  **Lecture seule** — sert de socle pour la couche auth/client.
- **Serveur MCP `yazio-community`** (Python) : référence pour l'**écriture**
  d'entrées (create intake). En extraire la logique de POST.
- **`juriadams/yazio`** (TS) : client mûr en TypeScript, utile comme référence
  de comportement même si on code en Python.
- **`saganos/yazio_public_api`** : description Swagger de l'API (v15) + OAuth.

## Décisions d'architecture

- **Auth** : échanger login/password **une seule fois** contre access token +
  refresh token. Ne stocker **que** les tokens. Jamais le mot de passe en clair.
- **Résolution d'aliment** : *search-first* dans la DB Yazio pour obtenir un
  `product_id` + serving réels (entrées natives, macros de leur base). *Fallback* :
  création d'un produit custom si aucun match satisfaisant.
- **Humain dans la boucle** : confirmation avant d'écrire (« j'ai trouvé X, je
  log ? »). Ne jamais écrire silencieusement un aliment mal résolu dans le
  journal de quelqu'un.
- **Intake** : POST avec date, meal, `product_id`, portion.
- **Isolation** : toute la logique Yazio derrière **une seule** couche cliente,
  endpoint versionné en constante, pour patcher vite quand l'API change.

## Règles non négociables

- Jamais de credentials (password ou token) dans les logs.
- Mimer le comportement réseau de l'app : User-Agent réaliste, pas de bursts ni
  de parallélisme agressif — l'API est non officielle, risque de throttle/ban.
- Documenter clairement pour les utilisateurs que l'automatisation de Yazio peut
  enfreindre ses ToS et exposer leur compte.

## Interface avec Assist (le "skill")

Aucun skill Mycroft/vocal n'existe déjà : ce projet doit le créer en
entier, installable depuis le repo. Les deux seules opérations manuelles
attendues : saisir les identifiants Yazio (config flow HA), et exposer les
entités créées à Assist dans Home Assistant.

Design retenu : une intégration Home Assistant native
(`custom_components/yazio_voice/`, `yazio_client` vendé dedans) qui
enregistre deux services (`yazio_voice.search_food`,
`yazio_voice.log_food`, avec réponse), wrappés par deux entités
`script.*` exposées à Assist (search-first puis confirmation humaine
avant écriture — jamais l'inverse). Pas de process séparé : ni AppDaemon,
ni rest_command/HTTP — tout tourne dans HA. Voir
[README.md](README.md) pour le détail et l'état d'avancement.

## Prochaine étape

Installer et valider l'intégration sur une instance Home Assistant réelle
(config flow, services, scripts), puis implémenter le fallback "créer un
produit custom" quand aucun match Yazio n'est satisfaisant.
