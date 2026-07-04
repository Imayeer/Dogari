# Dogari — Projet PFE/Master IA

## 1. Présentation du projet

Dogari est un système intelligent de contrôle d'accès physique basé sur la vision par ordinateur, conçu pour fonctionner localement sur un nano-ordinateur de type Raspberry Pi 5.

Le projet vise à concevoir une solution embarquée capable d'identifier les personnes autorisées, de journaliser les accès, de fonctionner même sans connexion Internet et de servir de base à une plateforme de sécurité intelligente plus avancée.

## 2. Objectif général

Concevoir et réaliser un système de contrôle d'accès intelligent, local, modulaire et résilient, utilisant la reconnaissance faciale pour autoriser ou refuser l'accès à un espace physique.

## 3. Objectifs spécifiques

- Détecter un visage à partir d'un flux caméra.
- Identifier une personne autorisée par reconnaissance faciale.
- Refuser l'accès aux personnes inconnues.
- Enregistrer les tentatives d'accès dans une base locale.
- Fournir une interface web locale pour administrer le système.
- Prévoir une architecture extensible vers la détection d'anomalies, la génération automatique de rapports et la synchronisation différée.

## 4. Périmètre du MVP

La première version du projet doit permettre :

- la capture vidéo depuis une webcam ou caméra USB ;
- la détection et reconnaissance faciale ;
- l'enregistrement d'utilisateurs autorisés ;
- la simulation de l'ouverture d'une porte ;
- la journalisation des accès ;
- une interface web locale ;
- une base de données SQLite.

Le contrôle GPIO réel de la gâche électrique sera ajouté dans une phase ultérieure.

## 5. Fonctionnalités principales

### 5.1 Gestion des utilisateurs

- Ajouter un utilisateur autorisé.
- Associer un nom, un identifiant et une image de référence.
- Supprimer ou désactiver un utilisateur.
- Stocker les informations localement.

### 5.2 Reconnaissance faciale

- Capturer une image depuis la caméra.
- Détecter un ou plusieurs visages.
- Générer une représentation numérique du visage.
- Comparer le visage détecté avec les utilisateurs autorisés.
- Retourner un statut : autorisé, inconnu ou erreur.

### 5.3 Contrôle d'accès

- Autoriser l'accès si le visage est reconnu.
- Refuser l'accès si le visage est inconnu.
- Simuler l'ouverture de la porte dans le MVP.
- Prévoir une abstraction pour le futur contrôle GPIO.

### 5.4 Journalisation

Chaque tentative d'accès doit être enregistrée avec :

- identifiant de l'utilisateur si reconnu ;
- nom de l'utilisateur si reconnu ;
- statut de la tentative ;
- date et heure ;
- score de similarité ;
- source caméra ;
- message complémentaire.

### 5.5 Interface web locale

L'interface web doit permettre :

- de consulter les derniers accès ;
- d'ajouter un utilisateur ;
- de visualiser le statut du système ;
- de lancer une tentative de reconnaissance ;
- de gérer les utilisateurs autorisés.

## 6. Architecture technique

Le projet est organisé de manière modulaire :

```
dogari/
├── README.md
├── PROJECT.md
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── docs/
├── data/
│   ├── database/
│   ├── faces/
│   └── logs/
├── src/
│   └── dogari/
│       ├── core/
│       ├── vision/
│       ├── storage/
│       ├── access/
│       └── web/
└── tests/
```

## 7. Modules prévus

### core

Contient la configuration générale du projet (`config.py`), les constantes (`constants.py`), les exceptions personnalisées (`exceptions.py`) et les utilitaires communs.

### vision

Contient les fonctions liées à la caméra (`camera.py`), à la détection faciale (`detector.py`), à l'extraction d'embeddings (`embeddings.py`) et à la comparaison des visages (`recognizer.py`).

### storage

Contient la gestion de la base SQLite (`database.py`), les modèles de données (`models.py`) et les opérations CRUD (`users_repository.py`, `access_logs_repository.py`).

### access

Contient la logique métier du contrôle d'accès (`controller.py`) : décision d'autorisation, refus, simulation d'ouverture de porte (`door.py`) et future intégration GPIO.

### web

Contient l'interface web locale (`app.py`, `templates/`, `static/`) et les routes API (`routes/status.py`, `routes/users.py`, `routes/access.py`).

## 8. Stack technique

- Langage : Python 3.11+
- Vision par ordinateur : OpenCV
- Reconnaissance faciale : face-recognition, DeepFace ou InsightFace selon faisabilité
  (implémenté avec YuNet + SFace, modèles ONNX exécutés via `cv2.dnn` — retenu
  au lieu de `face-recognition`/dlib pour éviter sa compilation, coûteuse et peu
  fiable sur Raspberry Pi ; voir README pour le détail des modèles)
- Base de données : SQLite
- Interface web : FastAPI
- Tests : Pytest
- Déploiement cible : Raspberry Pi 5
- Environnement initial : PC Windows/Linux

## 9. Contraintes importantes

- Le système doit fonctionner localement.
- Le système doit pouvoir fonctionner sans Internet.
- Le code doit être modulaire et maintenable.
- Le contrôle de porte doit être abstrait pour permettre une simulation sur PC et un contrôle GPIO sur Raspberry Pi.
- Les données sensibles ne doivent pas être exposées publiquement.
- Les images et embeddings doivent être stockés localement.

## 10. Phases de développement

### Phase 1 — Initialisation du projet ✅

- Créer la structure du dépôt.
- Préparer l'environnement Python.
- Ajouter le README.
- Ajouter la configuration de base.

### Phase 2 — Base de données ✅

- Créer la base SQLite.
- Définir les tables utilisateurs et logs d'accès.
- Implémenter les fonctions CRUD.

### Phase 3 — Module caméra ✅

- Tester l'accès à la webcam.
- Capturer une image.
- Sauvegarder une image de test.

### Phase 4 — Reconnaissance faciale ✅

- Détecter un visage.
- Extraire les caractéristiques.
- Comparer avec les utilisateurs enregistrés.
- Retourner un score de similarité.

### Phase 5 — Contrôle d'accès ✅

- Implémenter la logique autorisé/refusé.
- Simuler l'ouverture d'une porte.
- Journaliser chaque tentative.

### Phase 6 — Interface web ✅

- Créer une interface locale.
- Afficher les logs.
- Ajouter un utilisateur.
- Lancer une reconnaissance.

### Phase 7 — Déploiement Raspberry Pi (à venir)

- Adapter les dépendances.
- Tester la caméra sur Raspberry Pi.
- Ajouter le contrôle GPIO (`GPIODoorController` déjà préparé dans `access/door.py`).
- Tester la gâche électrique 12V.

### Phase 8 — Améliorations IA (à venir)

- Ajouter la détection de vie.
- Ajouter une caméra IP secondaire.
- Ajouter la détection d'anomalies.
- Ajouter la génération automatique de rapports.

## 11. Modèle de données

### Table users

| Champ | Type | Description |
|---|---|---|
| id | INTEGER | Identifiant unique |
| full_name | TEXT | Nom complet |
| role | TEXT | Rôle ou fonction |
| status | TEXT | active/inactive |
| face_image_path | TEXT | Chemin de l'image de référence |
| face_embedding | BLOB | Représentation numérique du visage |
| created_at | TEXT | Date de création |

### Table access_logs

| Champ | Type | Description |
|---|---|---|
| id | INTEGER | Identifiant unique |
| user_id | INTEGER | Utilisateur reconnu |
| full_name | TEXT | Nom reconnu |
| status | TEXT | granted/denied/error |
| similarity_score | REAL | Score de similarité |
| camera_source | TEXT | Source caméra |
| message | TEXT | Détail de la tentative |
| created_at | TEXT | Date et heure |

## 12. Critères de réussite du MVP

Le MVP est considéré comme réussi si :

- un utilisateur peut être ajouté au système ;
- son visage peut être enregistré ;
- une tentative d'accès peut être lancée ;
- le système reconnaît un utilisateur autorisé ;
- le système refuse un visage inconnu ;
- chaque tentative est enregistrée ;
- l'interface web affiche les utilisateurs et les logs ;
- le projet peut être lancé localement avec une commande simple.

## 13. Commandes attendues

```bash
python -m venv .venv
pip install -r requirements.txt
python -m dogari.web.app
```

ou avec uvicorn directement :

```bash
uvicorn dogari.web.app:app --reload
```

## 14. Principes de développement pour Codex

- Ne pas tout coder en un seul fichier.
- Toujours privilégier une architecture modulaire.
- Ajouter des commentaires utiles mais éviter les commentaires inutiles.
- Proposer des tests quand une fonctionnalité importante est ajoutée.
- Ne pas casser les modules existants.
- Documenter chaque nouvelle étape dans le README.
- Éviter les dépendances trop lourdes au début.
- Prévoir la compatibilité Raspberry Pi.

## 15. Vision long terme

Dogari doit pouvoir évoluer vers une plateforme intelligente de sécurité physique intégrant :

- contrôle d'accès facial ;
- détection d'intrusion ;
- analyse comportementale ;
- rapports automatiques générés par IA ;
- synchronisation différée ;
- tableau de bord d'administration ;
- déploiement dans des écoles, bureaux, laboratoires ou institutions.
