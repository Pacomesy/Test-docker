#!/usr/bin/env sh
# Déploiement hors ligne : charger l'image puis démarrer (à exécuter depuis le dossier du pack).
set -eu
DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
MANIFEST="$DIR/pack-manifest.env"
if [ ! -f "$MANIFEST" ]; then
  echo "Fichier manquant : pack-manifest.env (utilisez le dossier produit par pack-offline.ps1)." >&2
  exit 1
fi
# shellcheck disable=SC1090
. "$MANIFEST"
if [ -z "${OFFLINE_TAR:-}" ] || [ -z "${OFFLINE_IMAGE:-}" ]; then
  echo "pack-manifest.env doit définir OFFLINE_TAR et OFFLINE_IMAGE." >&2
  exit 1
fi
TAR_PATH="$DIR/$OFFLINE_TAR"
if [ ! -f "$TAR_PATH" ]; then
  echo "Archive introuvable : $TAR_PATH" >&2
  exit 1
fi
echo "Chargement de l'image $OFFLINE_IMAGE ..."
docker load -i "$TAR_PATH"
COMPOSE="$DIR/docker-compose.offline.yml"
if [ ! -f "$COMPOSE" ]; then
  echo "Fichier manquant : docker-compose.offline.yml" >&2
  exit 1
fi
if [ "${1:-}" = "https" ]; then
  echo "Démarrage HTTPS (profil https, certificats dans ./certs) ..."
  docker compose --profile https -f "$COMPOSE" up -d app-https
else
  echo "Démarrage HTTP sur le port 8000 ..."
  docker compose -f "$COMPOSE" up -d app
fi
