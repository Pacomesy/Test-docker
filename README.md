# Horloge & météo (Python + Docker)

Application web **FastAPI** avec deux pages statiques : **[`/` — horloge](app/static/clock.html)** et **[`/meteo` — température](app/static/meteo.html)** (styles communs [`app/static/app.css`](app/static/app.css)).

## Fonctionnalités

### Page Horloge (`/`)

- Affichage de l’heure courante pour plusieurs **fuseaux IANA**.
- Mises à jour en **temps réel** via **WebSocket** (`/ws`), sans rechargement de page.
- **Ajout / suppression** de tuiles, **réordonnancement** par glisser-déposer.
- Configuration **persistée** dans un volume Docker : `DATA_DIR/tiles.json` (souvent `/data/tiles.json`).
- Indicateur de **connexion WebSocket** dans l’en-tête.

### Page Température (`/meteo`)

- **Lieu** : recherche par nom via l’API de **géocodage Open-Meteo** (appel navigateur → `geocoding-api.open-meteo.com`).
- **Période** : deux dates (journées entières) ; récupération via l’**API archive** Open-Meteo (`archive-api.open-meteo.com`).
- **Résolution** : horaire (`temperature_2m`) ou journalière (max / min).
- **Graphique** : **Plotly.js** (CDN), avec zoom (molette, rectangle, barre d’outils) et double-clic pour réinitialiser les axes.
- Connexion **WebSocket en arrière-plan** (sans voyant) pour recevoir les mises à jour du formulaire et de la navigation partagées.

Les appels Open-Meteo et le chargement de Plotly se font **depuis le navigateur** (aucun proxy côté serveur). Un accès Internet depuis le poste client est donc nécessaire pour cette page.

### Contrôle exclusif (édition)

Un seul navigateur à la fois peut **modifier** l’application (tuiles, météo, navigation synchronisée). Les autres clients restent en **lecture seule** : le contenu principal est grisé et inerte ; le bandeau de statut et les actions « langue » / « à propos » restent utilisables.

- **Identité** : chaque onglet stocke un UUID dans **`localStorage`** (`appClientId`). Toutes les requêtes `fetch` mutatrices envoient l’en-tête **`X-Client-Id`** avec cet UUID. Sans en-tête valide, le serveur répond **400** ; si un contrôleur est désigné et que l’UUID ne correspond pas, les mutations renvoient **403**.
- **Premier arrivant** : tant qu’aucun contrôleur n’est enregistré, l’interface reste en lecture seule avec le bouton **Prendre le contrôle** visible ; le premier clic envoie **`POST /api/control/request`** et devient contrôleur **sans** dialogue d’approbation.
- **Demande** : si quelqu’un d’autre contrôle déjà, une demande est mise en **attente** ; le contrôleur voit une modale **Approuver** / **Refuser**. Le demandeur voit une modale d’attente avec **« Forcer le contrôle »**, **désactivé pendant 30 secondes** avec un **compte à rebours** dans la boîte de dialogue, puis activé : **`POST /api/control/force`** permet de reprendre le contrôle sans accord (comportement type *break glass*, volontairement autorisé côté serveur pour le client en attente). Si le contrôleur **refuse**, un message explicite s’affiche dans l’en-tête (lecture seule).
- **État** : **`GET /api/control`** et le message WebSocket **`init`** incluent un objet `control` ; les changements diffusent **`control_updated`**.
- **Persistance** : l’état est sauvegardé dans **`DATA_DIR/control.json`** pour survivre au redémarrage du processus.

### Synchronisation multi-clients

- **Tuiles horloge** : déjà partagées via le serveur + messages WebSocket `tiles_updated` / `tick` / `init`.
- **Formulaire température** (lieu, dates, résolution, recherche) : état persistant `DATA_DIR/meteo_ui.json`, API `GET`/`PUT /api/meteo/ui`, diffusion **`meteo_updated`** sur `/ws` ; **dernier `PUT` gagne** (last-write-wins). Chaque client **re-télécharge** la série Open-Meteo pour redessiner le graphique après une mise à jour distante.
- **Page affichée** (`/` ou `/meteo`) : persistante dans `DATA_DIR/app_nav.json`, API `GET`/`PUT /api/nav`, message **`nav_updated`** ; un clic sur la navigation enregistre la route côté serveur puis **tous les navigateurs connectés** sont alignés sur la même URL (via `location.assign`). Au chargement, si le serveur indique une autre route, le client est réaligné **sauf** un lien direct vers `/meteo` lorsque le serveur est encore sur `/` (évite une boucle de rechargements). Un autre utilisateur qui choisit explicitement l’horloge (`nav_updated` vers `/`) ramène tout le monde sur `/`.
- **Limite** : une seule instance Uvicorn / un seul process — pas de synchronisation automatique entre plusieurs réplicas derrière un load-balancer sans couche pub/sub (Redis, etc.).

### Autres

- Le mode **HTTPS** est pris en charge en exposant des certificats dans le conteneur (voir ci-dessous).
- **À propos** : versions applicatives, backend, image Docker, ainsi que les **composants front** déclarés côté API (Plotly.js, Open-Meteo, polices Google Fonts) — voir `GET /api/about`.

### Langues (DE / FR / IT / EN)

- Quatre boutons dans l’en-tête choisissent la langue de l’interface ; le choix est mémorisé dans **`localStorage`** (`appLocale`).
- Les libellés, messages d’erreur côté page, tableau « À propos » et textes Plotly suivent la langue active. Sur les **tuiles horloge** : **ligne 1** date **`dd.MM.yyyy`**, **ligne 2** heure **`HH:mm:ss`** suivie du décalage (**`UTC ±h`** ou **`UTC ±h:mm`** si demi-fuseaux).
- Les requêtes **`fetch`** vers l’API applicative envoient l’en-tête **`X-App-Locale`** (`de`, `fr`, `it`, `en`) pour que les messages d’erreur HTTP (`detail`) soient dans la même langue.
- Fichier des chaînes : [`app/static/locales.js`](app/static/locales.js) ; logique dans [`app/static/clock-page.js`](app/static/clock-page.js) et [`app/static/meteo-page.js`](app/static/meteo-page.js).

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

- Horloge : [http://localhost:8000/](http://localhost:8000/) — Température : [http://localhost:8000/meteo](http://localhost:8000/meteo)
- WebSocket : `ws://localhost:8000/ws`

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

- Interface : [https://localhost:8443](https://localhost:8443) (le navigateur avertira sur un certificat auto-signé : acceptation manuelle possible en local)
- WebSocket : `wss://localhost:8443/ws`

En production, utilisez des certificats émis par une AC de confiance (Let’s Encrypt, PKI interne, etc.) et montez-les en lecture seule comme dans `docker-compose.yml`.

## Variables d’environnement

| Variable         | Défaut  | Rôle |
|------------------|---------|------|
| `DATA_DIR`       | `/data` | Répertoire contenant `tiles.json`, `meteo_ui.json`, `app_nav.json`, `control.json` |
| `UVICORN_PORT`   | `8000` (HTTP) ou `8443` (compose HTTPS) | Port d’écoute |
| `SSL_CERTFILE`   | *(vide)* | Chemin du certificat PEM (active TLS si défini avec la clé) |
| `SSL_KEYFILE`    | *(vide)* | Chemin de la clé privée PEM |
| `APP_VERSION`    | valeur de `app/version.py` | Version affichée (titre + À propos + OpenAPI) |
| `DOCKER_IMAGE_VERSION` | souvent identique à `APP_VERSION` dans l’image | Libellé « Docker (image) » dans À propos ; surcharge possible au `docker run` |

## API HTTP (backend)

En appelant l’API hors navigateur, vous pouvez passer **`X-App-Locale: de`** (ou `fr`, `it`, `en`) pour les textes d’erreur renvoyés dans `detail`. Les routes qui **modifient** des données exigent en plus **`X-Client-Id`** (UUID) et, lorsqu’un contrôleur est défini, que cet UUID soit celui du contrôleur actuel (sinon **403**).

- `GET /api/version` — `{"version": "…"}` (version applicative seule)
- `GET /api/about` — versions app, front-end, backend (Python, FastAPI, Uvicorn), Docker, et `components` (Plotly.js, Open-Meteo, polices)
- `GET /api/tiles` — liste des tuiles
- `POST /api/tiles` — corps JSON `{"timezone":"Asia/Tokyo"}`
- `PUT /api/tiles/order` — corps JSON `{"order":["id1","id2",…]}` (même ensemble d’IDs que les tuiles actuelles, nouvel ordre)
- `DELETE /api/tiles/{id}` — supprime une tuile
- `GET /api/timezones?q=paris` — recherche dans les fuseaux IANA
- `GET /api/meteo/ui`, `PUT /api/meteo/ui` — état du formulaire météo (PUT mutateur : `X-Client-Id` + contrôle)
- `GET /api/nav`, `PUT /api/nav` — route active partagée (PUT mutateur : `X-Client-Id` + contrôle)
- `GET /api/control` — `controllerClientId`, `pendingRequesterId`, `pendingSince` (ISO ou `null`)
- `POST /api/control/request` — prendre le contrôle ou enregistrer une demande
- `POST /api/control/approve` — corps `{"requesterClientId":"<uuid>"}` (contrôleur uniquement)
- `POST /api/control/deny` — même corps (contrôleur uniquement)
- `POST /api/control/force` — le demandeur en attente reprend le contrôle

**WebSocket** : `GET /ws` (protocole WebSocket) — init (tuiles, horloge, météo, nav, **control**) + ticks + `tiles_updated` / `meteo_updated` / `nav_updated` / **`control_updated`**.

L’interface permet de **réordonner les tuiles par glisser-déposer** ; l’ordre est enregistré dans `tiles.json` et synchronisé entre onglets / navigateurs via WebSocket.

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
  main.py          # FastAPI, WebSocket, API tuiles / météo / nav / contrôle, pages HTML
  version.py       # __version__ applicative
  i18n_api.py      # Messages HTTP localisés (X-App-Locale)
  static/
    app.css        # Styles partagés
    clock.html     # Page horloge
    meteo.html     # Page température
    clock-page.js
    meteo-page.js
    control-client.js # UUID client, bandeau contrôle, modales, inert lecture seule
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
- **Page `/meteo` vide ou erreurs réseau** : vérifier que le navigateur peut joindre les domaines Open-Meteo et le CDN Plotly (pare-feu, politique réseau).
- **Modifications d’interface non visibles** après `docker compose build` : reconstruire l’image (`docker compose build --no-cache`) ou s’assurer que le volume ne remplace pas les fichiers sous `static/` (ce projet ne monte pas le code source sur `app` par défaut — seul `/data` est en volume).
