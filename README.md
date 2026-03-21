# Horloge & météo (Python + Docker)

Application web **FastAPI** avec interface statique (`clock.html`, `meteo.html`, `app.css`) : **horloge multi-fuseaux** (`/`) et **historique de température** (`/meteo`, données externes).

## Fonctionnalités

### Page Horloge (`/`)

- Affichage de l’heure courante pour plusieurs **fuseaux IANA**.
- Mises à jour en **temps réel** via **WebSocket** (`/ws`), sans rechargement de page.
- **Ajout / suppression** de tuiles, **réordonnancement** par glisser-déposer.
- Configuration **persistée** dans un volume Docker : `DATA_DIR/tiles.json` (souvent `/data/tiles.json`).

### Page Température (`/meteo`)

- **Lieu** : recherche par nom via l’API de **géocodage Open-Meteo** (appel navigateur → `geocoding-api.open-meteo.com`).
- **Période** : deux dates (journées entières) ; récupération via l’**API archive** Open-Meteo (`archive-api.open-meteo.com`).
- **Résolution** : horaire (`temperature_2m`) ou journalière (max / min).
- **Graphique** : **Plotly.js** (CDN), avec zoom (molette, rectangle, barre d’outils) et double-clic pour réinitialiser les axes.
- **Persistance** : en passant sur la page horloge puis de retour sur `/meteo`, le **lieu choisi**, les **dates**, la **résolution** et la **recherche** sont repris depuis le **`localStorage`** du navigateur (clé `meteoUiState`). Si un lieu était enregistré, le **graphique est rechargé automatiquement** (nouvel appel Open-Meteo).

Les appels Open-Meteo et le chargement de Plotly se font **depuis le navigateur** (aucun proxy côté serveur). Un accès Internet depuis le poste client est donc nécessaire pour la page température.

### Autres

- Le mode **HTTPS** est pris en charge en exposant des certificats dans le conteneur (voir ci-dessous).
- **À propos** : versions applicatives, backend, image Docker, ainsi que les **composants front** déclarés côté API (Plotly.js, Open-Meteo, polices Google Fonts) — voir `GET /api/about`.

### Langues (DE / FR / IT / EN)

- Quatre boutons dans l’en-tête choisissent la langue de l’interface ; le choix est mémorisé dans **`localStorage`** (`appLocale`).
- Les libellés, messages d’erreur côté page, tableau « À propos » et textes Plotly suivent la langue active. Sur les **tuiles horloge** : **ligne 1** date **`dd.MM.yyyy`**, **ligne 2** heure **`HH:mm:ss`** suivie du décalage (**`UTC ±h`** ou **`UTC ±h:mm`** si demi-fuseaux).
- Les requêtes **`fetch`** vers l’API applicative envoient l’en-tête **`X-App-Locale`** (`de`, `fr`, `it`, `en`) pour que les messages d’erreur HTTP (`detail`) soient dans la même langue.
- Fichier des chaînes : [`app/static/locales.js`](app/static/locales.js) ; pages [`app/static/clock.html`](app/static/clock.html) et [`app/static/meteo.html`](app/static/meteo.html) ; styles partagés [`app/static/app.css`](app/static/app.css).

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) (Engine + plugin Compose intégré)
- Optionnel pour un run local hors Docker : [Python](https://www.python.org/) **3.12+**

Sous Windows, [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) convient.

## Tests (pytest)

En local, avec Python 3.12+ :

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests isolent `DATA_DIR` dans un répertoire temporaire et neutralisent la boucle `tick` WebSocket pour des exécutions rapides et déterministes.

## Installation et build (Docker)

À la racine du projet :

```bash
docker compose build
```

Pour figer la version dans l’image Docker (voir section **Version** ci-dessous) :

```bash
docker build --build-arg APP_VERSION=1.2.0 -t horloge-meteo:1.2.0 .
```

## Version de l’application

- **Code** : constante `__version__` dans [`app/version.py`](app/version.py) — point d’entrée pour les développements hors Docker.
- **Runtime** : variable d’environnement `APP_VERSION` (prioritaire sur `app/version.py`). Dans le `Dockerfile`, `ARG APP_VERSION` est recopié dans `ENV APP_VERSION` et `DOCKER_IMAGE_VERSION` au build.
- **Affichage** : le titre de la page affiche la version applicative (`GET /api/version`). Le bouton **À propos** ouvre une fenêtre avec les versions **Application**, **Interface (front-end)**, détail **Backend** (Python, FastAPI, Uvicorn), **Docker (image)**, et la clé **`components`** (Plotly.js, Open-Meteo, polices) — `GET /api/about`.
- **OpenAPI** : la version est aussi exposée sur [`/docs`](http://localhost:8000/docs) (métadonnées FastAPI).

## Démarrage (HTTP)

```bash
docker compose up app
```

- Horloge : [http://localhost:8000/](http://localhost:8000/)
- Température : [http://localhost:8000/meteo](http://localhost:8000/meteo)
- WebSocket (page horloge) : `ws://localhost:8000/ws`

Arrêt : `Ctrl+C` ou `docker compose down`.

Les tuiles ajoutées sont enregistrées dans le volume nommé `app_data`. Pour repartir de zéro :

```bash
docker compose down -v
```

## Démarrage (HTTPS)

1. Créez un dossier `certs` à la racine du projet.
2. Générez une paire certificat / clé (exemple auto-signé, **développement uniquement**) :

   ```bash
   mkdir -p certs
   openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/CN=localhost"
   ```

3. Lancez le service avec le profil `https` :

   ```bash
   docker compose --profile https up app-https
   ```

- Horloge : [https://localhost:8443/](https://localhost:8443/) — température : `/meteo`
- WebSocket (page horloge) : `wss://localhost:8443/ws`

En production, utilisez des certificats émis par une AC de confiance (Let’s Encrypt, PKI interne, etc.) et montez-les en lecture seule comme dans `docker-compose.yml`.

## Variables d’environnement

| Variable         | Défaut  | Rôle |
|------------------|---------|------|
| `DATA_DIR`       | `/data` | Répertoire contenant `tiles.json` |
| `UVICORN_PORT`   | `8000` (HTTP) ou `8443` (compose HTTPS) | Port d’écoute |
| `SSL_CERTFILE`   | *(vide)* | Chemin du certificat PEM (active TLS si défini avec la clé) |
| `SSL_KEYFILE`    | *(vide)* | Chemin de la clé privée PEM |
| `APP_VERSION`    | valeur de `app/version.py` | Version affichée (titre + À propos + OpenAPI) |
| `DOCKER_IMAGE_VERSION` | souvent identique à `APP_VERSION` dans l’image | Libellé « Docker (image) » dans À propos ; surcharge possible au `docker run` |

## API HTTP (backend)

En appelant l’API hors navigateur, vous pouvez passer **`X-App-Locale: de`** (ou `fr`, `it`, `en`) pour les textes d’erreur renvoyés dans `detail`.

- `GET /api/version` — `{"version": "…"}` (version applicative seule)
- `GET /api/about` — versions app, front-end, backend (Python, FastAPI, Uvicorn), Docker, et `components` (Plotly.js, Open-Meteo, polices)
- `GET /api/tiles` — liste des tuiles
- `POST /api/tiles` — corps JSON `{"timezone":"Asia/Tokyo"}`
- `PUT /api/tiles/order` — corps JSON `{"order":["id1","id2",…]}` (même ensemble d’IDs que les tuiles actuelles, nouvel ordre)
- `DELETE /api/tiles/{id}` — supprime une tuile
- `GET /api/timezones?q=paris` — recherche dans les fuseaux IANA

**WebSocket** : `GET /ws` (protocole WebSocket) — init + ticks horloge + synchronisation des tuiles entre clients.

Sur la page horloge, **réordonner les tuiles par glisser-déposer** enregistre l’ordre dans `tiles.json` et le synchronise entre navigateurs / fenêtres ouvertes via WebSocket.

## Dépendances externes (navigateur)

| Ressource | Usage |
|-----------|--------|
| [Open-Meteo](https://open-meteo.com) | Géocodage et série historique de température (page `/meteo`) |
| [Plotly.js](https://plotly.com/javascript/) | Graphique interactif (zoom, barre d’outils) |
| [Google Fonts](https://fonts.google.com) | Outfit, JetBrains Mono |

## Exécution locale (sans Docker)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set DATA_DIR=data
mkdir data
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Sous Linux/macOS : `export DATA_DIR=./data` puis `mkdir -p data`.

## Structure du projet

```
app/
  main.py          # FastAPI, WebSocket, API tuiles, pages / et /meteo
  version.py       # __version__ applicative
  i18n_api.py      # Messages HTTP localisés (X-App-Locale)
  static/
    clock.html     # Page horloge, WebSocket, tuiles
    meteo.html     # Page température, Plotly + Open-Meteo (navigateur)
    app.css        # Styles partagés
    locales.js     # Chaînes DE / FR / IT / EN pour l’interface
Dockerfile
docker-compose.yml
docker-entrypoint.sh
requirements.txt
README.md
CAHIER_DES_CHARGES.md
```

## Dépannage

- **`exec /docker-entrypoint.sh: no such file or directory`** sous Linux : fins de ligne CRLF sur `docker-entrypoint.sh`. Le `Dockerfile` applique un `sed` pour les normaliser au build ; le fichier [`.gitattributes`](.gitattributes) force les `*.sh` en LF.
- **Page température vide ou erreurs réseau** : vérifier que le navigateur peut joindre les domaines Open-Meteo et le CDN Plotly (pare-feu, politique réseau).
- **Modifications d’interface non visibles** après `docker compose build` : reconstruire l’image (`docker compose build --no-cache`) ou s’assurer que le volume ne remplace pas les fichiers sous `app/static` (ce projet ne monte pas le code source sur `app` par défaut — seul `/data` est en volume).
