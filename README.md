# Dogari

Système intelligent de contrôle d'accès physique basé sur la reconnaissance faciale, conçu pour fonctionner localement (sans Internet) et pour être déployé sur Raspberry Pi 5.

Voir [PROJECT.md](PROJECT.md) pour la spécification complète du projet (objectifs, architecture, phases de développement).

## Fonctionnalités du MVP

- Capture vidéo depuis une webcam/caméra USB, avec caméra IP secondaire optionnelle (OpenCV).
- Détection et reconnaissance faciale (YuNet + SFace, modèles ONNX via `cv2.dnn`).
- Détection de vivacité par analyse de mouvement inter-images (anti-usurpation par photo/écran statique).
- Enregistrement des utilisateurs autorisés (nom, rôle, image de référence, embedding facial).
- Décision d'accès (autorisé / refusé / erreur) avec simulation d'ouverture de porte.
- Journalisation de chaque tentative d'accès dans une base SQLite locale.
- Détection d'anomalies par règles (refus répétés, accès hors horaires, pics de fréquence).
- Génération de rapports de synthèse (quotidien/hebdomadaire), exportables en CSV/texte.
- Interface web locale (FastAPI) pour gérer les utilisateurs, lancer une reconnaissance et consulter les logs.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_models.py
```

`scripts/download_models.py` récupère les deux modèles ONNX nécessaires à la
reconnaissance faciale et les place dans `models/` :

- `face_detection_yunet_2023mar.onnx` (détection de visage, ~340 Ko)
- `face_recognition_sface_2021dec.onnx` (embedding facial, ~36 Mo)

Ils ne sont pas versionnés dans le dépôt (fichiers binaires volumineux, voir
`.gitignore`). Si le téléchargement échoue (réseau d'entreprise, pare-feu...),
téléchargez-les manuellement depuis
[opencv/opencv_zoo](https://github.com/opencv/opencv_zoo/tree/main/models)
(dossiers `face_detection_yunet` et `face_recognition_sface`) et placez-les
dans `models/` sous les noms ci-dessus, ou pointez `DOGARI_YUNET_MODEL_PATH` /
`DOGARI_SFACE_MODEL_PATH` vers un autre emplacement.

> Contrairement à `face-recognition`/`dlib` (envisagé initialement), YuNet et
> SFace ne nécessitent aucune compilation : ce sont des modèles ONNX exécutés
> directement par `opencv-python`, ce qui évite un point de blocage classique
> au déploiement sur Raspberry Pi (compilation de `dlib` longue et gourmande
> en mémoire, parfois indisponible en wheel précompilé sur ARM).

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
| `DOGARI_CAMERA_INDEX` | Index de la caméra principale (webcam USB) ou URL RTSP/HTTP | `0` |
| `DOGARI_SECONDARY_CAMERA_SOURCE` | URL RTSP/HTTP d'une caméra IP secondaire optionnelle | non configurée |
| `DOGARI_YUNET_MODEL_PATH` | Chemin du modèle de détection YuNet (`.onnx`) | `models/face_detection_yunet_2023mar.onnx` |
| `DOGARI_SFACE_MODEL_PATH` | Chemin du modèle de reconnaissance SFace (`.onnx`) | `models/face_recognition_sface_2021dec.onnx` |
| `DOGARI_RECOGNITION_TOLERANCE` | Seuil de distance L2 pour la reconnaissance faciale (plus petit = plus strict) | `1.128` |
| `DOGARI_LIVENESS_ENABLED` | Active la détection de vivacité (anti-photo/écran) avant la reconnaissance | `true` |
| `DOGARI_LIVENESS_FRAME_COUNT` | Nombre d'images capturées en rafale pour l'analyse de mouvement | `5` |
| `DOGARI_LIVENESS_CAPTURE_INTERVAL` | Délai (secondes) entre deux images de la rafale | `0.15` |
| `DOGARI_LIVENESS_MOTION_THRESHOLD` | Mouvement minimal (différence moyenne de pixels) pour considérer le visage comme vivant | `1.5` |
| `DOGARI_ANOMALY_DENIAL_WINDOW_MINUTES` | Fenêtre glissante (minutes) pour détecter des refus répétés | `10` |
| `DOGARI_ANOMALY_DENIAL_THRESHOLD` | Nombre de refus dans la fenêtre pour déclencher une alerte | `5` |
| `DOGARI_ANOMALY_OFF_HOURS_START` / `DOGARI_ANOMALY_OFF_HOURS_END` | Plage horaire (heures, 0-23) considérée comme normale | `7` / `20` |
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
├── models/                 # Modèles ONNX YuNet/SFace (non versionnés, voir download_models.py)
├── scripts/
│   ├── download_models.py       # Télécharge les modèles YuNet/SFace
│   ├── evaluate_recognition.py  # Évaluation de la précision (accuracy/FAR/FRR)
│   └── generate_report.py       # Génère un rapport de synthèse (console/fichier/cron)
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

## Détection de vivacité (anti-usurpation)

Avant de tenter la reconnaissance, le système capture une courte rafale
d'images (`DOGARI_LIVENESS_FRAME_COUNT`, espacées de `DOGARI_LIVENESS_CAPTURE_INTERVAL`
secondes) et mesure le mouvement du visage entre ces images
(`src/dogari/vision/liveness.py`). Une photo ou un écran statique présente un
visage quasi identique d'une image à l'autre et est rejeté (statut
`spoof_detected`) ; un vrai visage bouge toujours légèrement.

C'est une protection volontairement simple pour un MVP : le bruit du capteur
peut produire un écart non nul même sur une scène parfaitement immobile, et
cette méthode ne protège pas contre un rejeu vidéo. `DOGARI_LIVENESS_MOTION_THRESHOLD`
doit être calibré empiriquement (regardez le `motion_score` dans les logs pour
des essais vivants vs. une photo imprimée) ; si les faux refus sont trop
fréquents, augmentez `DOGARI_LIVENESS_FRAME_COUNT`/`DOGARI_LIVENESS_CAPTURE_INTERVAL`
ou baissez le seuil, ou désactivez temporairement avec `DOGARI_LIVENESS_ENABLED=false`.

## Détection d'anomalies

`src/dogari/access/anomaly.py` analyse l'historique des accès (`access_logs`)
par un jeu de règles simples, exposées sur `GET /api/access/anomalies` et
affichées sur le tableau de bord :

- **Refus répétés** : plusieurs tentatives refusées rapprochées (intrusion potentielle).
- **Accès hors horaires** : un accès autorisé en dehors de la plage horaire habituelle.
- **Fréquence inhabituelle** : un nombre élevé de tentatives (tous statuts) sur une courte période.

Ce sont des règles, pas un modèle appris (aucune donnée d'entraînement
disponible) : ajustez les seuils via les variables `DOGARI_ANOMALY_*`
ci-dessus selon le contexte de déploiement.

## Rapports de synthèse

`src/dogari/access/reports.py` agrège l'historique des accès sur une période
(tentatives par statut, utilisateurs distincts, répartition quotidienne,
anomalies incluses). Disponible de trois façons :

- Sur le tableau de bord, section "Rapport de synthèse" (choisissez le nombre de jours).
- Via l'API : `GET /api/reports/summary?days=7` (JSON), `GET /api/reports/export.csv?days=7`,
  `GET /api/reports/export.txt?days=7`.
- En ligne de commande, pour un vrai rapport *automatique* planifié (cron) :

  ```bash
  python scripts/generate_report.py --days 7 --output rapport.txt --csv rapport.csv
  ```

  Exemple de tâche cron pour un rapport hebdomadaire chaque lundi à 8h :

  ```
  0 8 * * 1 cd /chemin/vers/dogari && .venv/bin/python scripts/generate_report.py --days 7 --output data/logs/rapport_hebdo.txt
  ```

## Caméra IP secondaire

Une seconde caméra (URL RTSP/HTTP) peut être configurée via
`DOGARI_SECONDARY_CAMERA_SOURCE`, par exemple :

```bash
DOGARI_SECONDARY_CAMERA_SOURCE=rtsp://192.168.1.50:554/stream1 python -m dogari.web.app
```

Une fois configurée, elle apparaît dans le sélecteur "Caméra" du tableau de
bord et peut être ciblée directement via l'API :
`POST /api/access/recognize?camera=secondary` (`camera=primary` par défaut).
La caméra principale (`DOGARI_CAMERA_INDEX`) accepte elle aussi une URL
RTSP/HTTP à la place d'un index numérique, si vous préférez n'utiliser que des
caméras IP.

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
module caméra, reconnaissance faciale, contrôle d'accès et interface web. Les
améliorations de la Phase 8 sont également implémentées : détection de vivacité,
caméra IP secondaire, détection d'anomalies et rapports automatiques. Le
contrôle GPIO réel (Phase 7) est préparé via `GPIODoorController` dans
`src/dogari/access/door.py`, activable sur Raspberry Pi avec `DOGARI_USE_GPIO=true`
une fois le matériel branché — il reste à valider sur le matériel réel. Le détail
des phases est documenté dans [PROJECT.md](PROJECT.md).
