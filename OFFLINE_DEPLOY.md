# Déploiement Docker sans accès Internet

## Sur une machine **connectée** (préparation)

1. Cloner ou copier le dépôt.
2. Lancer le script PowerShell (Windows) :

   ```powershell
   .\scripts\pack-offline.ps1 -OutDir C:\chemin\vers\offline-pack -Zip
   ```

   Options utiles : `-ImageName horloge-meteo`, `-Tag 1.2.0` (doit correspondre à la version voulue ; passée en `APP_VERSION` au build).

3. Transférer le dossier `offline-pack` (ou le fichier `offline-pack.zip`) vers la cible isolée (clé USB, etc.).

Contenu du pack :

| Fichier | Rôle |
|---------|------|
| `*.tar` | Image Docker (`docker save`) |
| `pack-manifest.env` | `OFFLINE_IMAGE` et `OFFLINE_TAR` |
| `docker-compose.offline.yml` | Démarrage sans `build` ni pull |
| `load-and-run-offline.sh` / `.ps1` | Chargement + `docker compose up` |

## Sur la machine **hors ligne** (cible)

**Prérequis** : Docker Engine + plugin Compose installés (sans besoin de registry).

### Linux / macOS

```sh
cd /chemin/vers/offline-pack
chmod +x load-and-run-offline.sh
./load-and-run-offline.sh
```

HTTPS (certificats PEM dans `./certs`, voir README principal) :

```sh
./load-and-run-offline.sh https
```

### Windows (PowerShell)

```powershell
cd C:\chemin\vers\offline-pack
.\load-and-run-offline.ps1
# ou HTTPS :
.\load-and-run-offline.ps1 -Mode https
```

- HTTP : [http://localhost:8000/](http://localhost:8000/)
- HTTPS : [https://localhost:8443](https://localhost:8443) (si profil `https` et dossier `certs` présent)

## Limites

- **Mise à jour** : toute nouvelle version d’image nécessite un nouveau pack depuis une machine en ligne.
- **Page météo** : le navigateur charge **Plotly.js** (CDN) et appelle **Open-Meteo** ; sans Internet sur le **poste client**, la température / graphique ne fonctionneront pas. L’**horloge** et l’API locale restent utilisables sur un réseau isolé.

## Compose figé dans le dépôt

Le fichier [`docker-compose.offline.yml`](docker-compose.offline.yml) à la racine du dépôt sert de référence (tag `horloge-meteo:1.2.0`). Après un `docker load` manuel de cette image, vous pouvez l’utiliser directement ; le script `pack-offline.ps1` régénère un compose aligné sur le tag choisi dans le dossier de sortie.
