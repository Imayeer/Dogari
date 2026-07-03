# Dogari

Système intelligent de contrôle d'accès physique basé sur la reconnaissance faciale, conçu pour fonctionner localement (sans Internet) et pour être déployé sur Raspberry Pi 5.

Voir [PROJECT.md](PROJECT.md) pour la spécification complète du projet (objectifs, architecture, phases de développement).

## Fonctionnalités du MVP

- Capture vidéo depuis une webcam/caméra USB (OpenCV).
- Détection et reconnaissance faciale (`face-recognition`).
- Enregistrement des utilisateurs autorisés (nom, rôle, image de référence, embedding facial).
- Décision d'accès (autorisé / refusé / erreur) avec simulation d'ouverture de porte.
- Journalisation de chaque tentative d'accès dans une base SQLite locale.
- Interface web locale (FastAPI) pour gérer les utilisateurs, lancer une reconnaissance et consulter les logs.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

> `face-recognition` dépend de `dlib`, qui nécessite un compilateur C++ et `cmake`
> installés sur le système pour se compiler depuis les sources sur certaines
> plateformes (notamment Raspberry Pi). Voir la documentation de
> [face-recognition](https://github.com/ageitgey/face_recognition) en cas de
> difficulté d'installation.

## Lancement

```bash
python -m dogari.web.app
```

ou directement avec uvicorn :

```bash
uvicorn dogari.web.app:app --reload
```

L'interface web est ensuite disponible sur <http://localhost:8000>.

## Configuration

Le comportement du système peut être ajusté via des variables d'environnement (préfixe `DOGARI_`), sans modifier le code :

| Variable | Description | Défaut |
|---|---|---|
| `DOGARI_DATA_DIR` | Dossier de données (base SQLite, images, logs) | `data/` |
| `DOGARI_CAMERA_INDEX` | Index de la caméra OpenCV | `0` |
| `DOGARI_RECOGNITION_TOLERANCE` | Seuil de distance pour la reconnaissance faciale (plus petit = plus strict) | `0.6` |
| `DOGARI_DOOR_HOLD_SECONDS` | Durée d'ouverture simulée de la porte | `5.0` |
| `DOGARI_USE_GPIO` | Active le contrôle GPIO réel (Raspberry Pi, Phase 7) | `false` |
| `DOGARI_GPIO_RELAY_PIN` | Broche GPIO (BCM) du relais de la gâche | `17` |
| `DOGARI_WEB_HOST` / `DOGARI_WEB_PORT` | Adresse d'écoute du serveur web | `0.0.0.0` / `8000` |

## Structure du projet

```
dogari/
├── PROJECT.md              # Spécification complète du projet
├── requirements.txt
├── pyproject.toml
├── data/                   # Base SQLite, images de visages, logs (non versionné)
├── scripts/
│   └── evaluate_recognition.py  # Évaluation de la précision (accuracy/FAR/FRR)
├── src/dogari/
│   ├── core/                # Configuration, constantes, exceptions
│   ├── vision/               # Caméra, détection faciale, embeddings, reconnaissance
│   ├── storage/               # Base SQLite, modèles, opérations CRUD
│   ├── access/                # Décision d'accès, contrôle de porte (simulé/GPIO)
│   └── web/                   # API FastAPI + interface web (templates/static)
└── tests/                    # Tests unitaires (pytest)
```

## Tests

```bash
pytest
```

Les tests de stockage et de contrôle d'accès s'exécutent sans dépendre du matériel
(caméra, GPIO) grâce à une base de données temporaire et à l'injection de
dépendances (voir `tests/conftest.py`).

## Évaluer la précision de la reconnaissance faciale

`scripts/evaluate_recognition.py` mesure l'exactitude réelle du modèle sur un
jeu de test étiqueté (utile pour un rapport PFE/Master, ou pour choisir la
bonne valeur de `DOGARI_RECOGNITION_TOLERANCE`). Il calcule l'accuracy ainsi
que le taux de faux positifs (FAR) et de faux négatifs (FRR).

Préparez un dossier avec la structure suivante :

```
mon_jeu_de_test/
├── gallery/            # images de référence, une par utilisateur connu
│   ├── alice/*.jpg
│   └── bob/*.jpg
└── probes/             # images à tester
    ├── alice/*.jpg     # doivent être reconnues comme "alice"
    ├── bob/*.jpg       # doivent être reconnues comme "bob"
    └── unknown/*.jpg   # doivent être rejetées (personnes non enregistrées)
```

Puis lancez :

```bash
python scripts/evaluate_recognition.py mon_jeu_de_test
python scripts/evaluate_recognition.py mon_jeu_de_test --tolerance 0.5
python scripts/evaluate_recognition.py mon_jeu_de_test --sweep          # balaie plusieurs seuils
python scripts/evaluate_recognition.py mon_jeu_de_test --csv resultats.csv
```

## État d'avancement

Les phases 1 à 6 du MVP sont implémentées : structure du projet, base de données,
module caméra, reconnaissance faciale, contrôle d'accès et interface web. Le
contrôle GPIO réel (Phase 7) est préparé via `GPIODoorController` dans
`src/dogari/access/door.py`, activable sur Raspberry Pi avec `DOGARI_USE_GPIO=true`
une fois le matériel branché. Le détail des phases est documenté dans
[PROJECT.md](PROJECT.md).
