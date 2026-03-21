# Horloge multi-fuseaux (Python + Docker)

Application web affichant l’heure courante pour plusieurs fuseaux IANA. Les mises à jour sont poussées en **temps réel** via **WebSocket** (aucun rechargement de page). Vous pouvez **ajouter ou retirer des tuiles** à la volée ; la configuration est **persistée** dans un volume Docker (`/data/tiles.json`) sans redémarrer le conteneur.

Le mode **HTTPS** est pris en charge en exposant des certificats dans le conteneur (voir ci-dessous).

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) (Engine + plugin Compose intégré)
- Optionnel pour un run local hors Docker : [Python](https://www.python.org/) **3.12+**

Sous Windows, [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) convient.

## Installation et build (Docker)

À la racine du projet :

```bash
docker compose build
```

Pour figer la version dans l’image Docker (voir section **Version** ci-dessous) :

```bash
docker build --build-arg APP_VERSION=1.2.0 -t horloge:1.2.0 .
```

## Version de l’application

- **Code** : constante `__version__` dans [`app/version.py`](app/version.py) — point d’entrée pour les développements hors Docker.
- **Runtime** : variable d’environnement `APP_VERSION` (prioritaire sur `app/version.py`). Dans le `Dockerfile`, `ARG APP_VERSION` est recopié dans `ENV APP_VERSION` et `DOCKER_IMAGE_VERSION` au build.
- **Affichage** : le titre de la page affiche uniquement la version applicative (`GET /api/version`). Le bouton **À propos** ouvre une fenêtre avec les versions **Application**, **Interface (front-end)**, détail **Backend** (Python, FastAPI, Uvicorn) et **Docker (image)** (`GET /api/about`).
- **OpenAPI** : la version est aussi exposée sur [`/docs`](http://localhost:8000/docs) (métadonnées FastAPI).

## Démarrage (HTTP)

```bash
docker compose up app
```

- Interface : [http://localhost:8000](http://localhost:8000)
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
| `DATA_DIR`       | `/data` | Répertoire contenant `tiles.json` |
| `UVICORN_PORT`   | `8000` (HTTP) ou `8443` (compose HTTPS) | Port d’écoute |
| `SSL_CERTFILE`   | *(vide)* | Chemin du certificat PEM (active TLS si défini avec la clé) |
| `SSL_KEYFILE`    | *(vide)* | Chemin de la clé privée PEM |
| `APP_VERSION`    | valeur de `app/version.py` | Version affichée (titre + À propos + OpenAPI) |
| `DOCKER_IMAGE_VERSION` | souvent identique à `APP_VERSION` dans l’image | Libellé « Docker (image) » dans À propos ; surcharge possible au `docker run` |

## API utiles (sans recharger la page)

- `GET /api/version` — `{"version": "…"}` (version applicative seule)
- `GET /api/about` — détail des versions (app, front-end, backend, docker)
- `GET /api/tiles` — liste des tuiles
- `POST /api/tiles` — corps JSON `{"timezone":"Asia/Tokyo"}`
- `PUT /api/tiles/order` — corps JSON `{"order":["id1","id2",…]}` (même ensemble d’IDs que les tuiles actuelles, nouvel ordre)
- `DELETE /api/tiles/{id}` — supprime une tuile
- `GET /api/timezones?q=paris` — recherche dans les fuseaux IANA

L’interface permet de **réordonner les tuiles par glisser-déposer** ; l’ordre est enregistré dans `tiles.json` et synchronisé entre onglets via WebSocket.

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
  main.py          # FastAPI, WebSocket, API tuiles
  version.py       # __version__ applicative
  static/
    index.html     # Interface tuiles + client WebSocket
Dockerfile
docker-compose.yml
docker-entrypoint.sh
requirements.txt
```

## Dépannage

- **`exec /docker-entrypoint.sh: no such file or directory`** sous Linux : fins de ligne CRLF sur `docker-entrypoint.sh`. Le `Dockerfile` applique un `sed` pour les normaliser au build ; le fichier [`.gitattributes`](.gitattributes) force les `*.sh` en LF.
