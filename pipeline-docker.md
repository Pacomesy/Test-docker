# CI/CD avec Docker – Gestion des versions et bonnes pratiques

## Contexte

L’application est packagée sous forme de **container Docker**.  
La question porte sur :
- la publication de nouvelles versions via un **pipeline CI/CD**
- la **gestion des versions** (Dockerfile, images)
- l’utilisation de **Git** et/ou d’un **artifact registry**
- les **meilleures pratiques** à adopter

---

## 1. Publication de nouvelles versions via un pipeline

✅ **Oui, c’est la pratique recommandée.**

Dans une architecture moderne, le pipeline CI/CD est responsable de :
- builder l’image Docker
- exécuter les tests
- versionner l’image
- publier l’image dans un **container registry**

Le pipeline devient la **chaîne officielle de livraison**.

Principe fondamental :

> **Build once → version → store → deploy everywhere**

---

## 2. Git vs Artifacts : rôles et responsabilités

La bonne pratique n’est **pas** “Git OU Artifacts”, mais **Git ET Artifacts**.

### 2.1 Git : source de vérité

Git doit contenir :
- le code applicatif
- le `Dockerfile`
- les scripts de build
- la configuration CI/CD
- les tags de version (ex: `v1.2.0`)

✅ Le `Dockerfile` doit toujours être versionné dans Git, au même titre que le code.

Cela garantit :
- traçabilité
- auditabilité
- reproductibilité des builds

---

### 2.2 Artifact Registry : livrables immuables

Un **container registry** (Docker Hub, GHCR, ACR, ECR, GCR, …) stocke :
- les images Docker construites
- chaque version de manière **immutable**
- les métadonnées (digest, date, provenance)

👉 Une image Docker est un **artefact de build**, exactement comme un `.jar` ou un `.zip`.

---

## 3. Stratégie de versionnement recommandée

### 3.1 Principe clé

> **On versionne les images, pas les environnements.**

Les environnements (dev, staging, prod) **consomment une version précise d’image**.

---

### 3.2 Tags d’images recommandés

Chaque build produit une image **unique**.

Exemples :
```text
myapp:1.4.2
myapp:1.4.2+sha.8f3a91c
myapp:sha-8f3a91c