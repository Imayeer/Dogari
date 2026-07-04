# Dogari

Système intelligent de contrôle d'accès physique basé sur la reconnaissance faciale, conçu pour fonctionner localement (sans Internet) et pour être déployé sur Raspberry Pi 5.

Voir [PROJECT.md](PROJECT.md) pour la spécification complète du projet (objectifs, architecture, phases de développement).

## Fonctionnalités du MVP

- Capture vidéo depuis une ou plusieurs caméras (webcam USB ou IP, OpenCV).
- Détection et reconnaissance faciale (YuNet + SFace, modèles ONNX via `cv2.dnn`).
- Détection de vivacité par analyse de mouvement inter-images (anti-usurpation par photo/écran statique).
- **Portails** : points d'accès nommés (caméra + porte simulée/GPIO), gérés dans la base (pas dans le code).
- **Rôles d'accès** : chaque utilisateur a un rôle, et chaque rôle n'a accès qu'aux portails et
  créneaux horaires hebdomadaires explicitement définis (voir section dédiée).
- Enregistrement des utilisateurs autorisés (nom, rôle, image de référence, embedding facial).
- Décision d'accès (autorisé / refusé / erreur) avec simulation d'ouverture de porte ou relais GPIO réel.
- Journalisation de chaque tentative d'accès dans une base SQLite locale.
- Détection d'anomalies par règles (refus répétés, accès hors horaires, pics de fréquence).
- Génération de rapports de synthèse (quotidien/hebdomadaire), exportables en CSV/texte.
- Recherche continue d'une personne nommée (déjà enregistrée) sur un flux caméra.
- Surveillance sécurité continue : détection de foule (fiable) et d'armes (**expérimentale**, désactivée par défaut).
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
| `DOGARI_CAMERA_INDEX` / `DOGARI_SECONDARY_CAMERA_SOURCE` | Utilisées **une seule fois**, au tout premier démarrage, pour créer un portail et une caméra IP par défaut dans la base. Sans effet ensuite : gérez les caméras via `/api/portals` et `/api/ip-cameras` (voir section dédiée). | `0` / non configurée |
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
| `DOGARI_SEARCH_POLL_INTERVAL_SECONDS` | Délai entre deux images lors d'une recherche de personne | `2.0` |
| `DOGARI_SEARCH_SIGHTING_COOLDOWN_SECONDS` | Délai minimal entre deux observations journalisées pour une même recherche | `30.0` |
| `DOGARI_MONITORING_POLL_INTERVAL_SECONDS` | Délai entre deux images lors d'une surveillance sécurité | `2.0` |
| `DOGARI_CROWD_SIZE_THRESHOLD` | Nombre de visages simultanés déclenchant une alerte de foule | `5` |
| `DOGARI_WEAPON_DETECTION_ENABLED` | Active la détection d'armes **expérimentale** (voir avertissement ci-dessous) | `false` |
| `DOGARI_WEAPON_MODEL_PATH` | Chemin du modèle YOLO de détection d'armes (`.pt`) | `models/weapon_detection.pt` |
| `DOGARI_WEAPON_CONFIDENCE_THRESHOLD` | Confiance minimale pour retenir une détection d'arme | `0.5` |
| `DOGARI_DOOR_HOLD_SECONDS` | Durée d'ouverture simulée de la porte | `5.0` |
| `DOGARI_USE_GPIO` | Active le contrôle GPIO réel (Raspberry Pi, Phase 7) | `false` |
| `DOGARI_GPIO_RELAY_PIN` | Broche GPIO (BCM) du relais de la gâche | `17` |
| `DOGARI_WEB_HOST` / `DOGARI_WEB_PORT` | Adresse d'écoute du serveur web | `0.0.0.0` / `8000` |

## Structure du projet

```
dogari/
├── PROJECT.md              # Spécification complète du projet
├── requirements.txt
├── requirements-weapon-detection.txt  # Dépendance optionnelle (détection d'armes expérimentale)
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

## Portails, caméras IP et rôles d'accès

C'est le cœur du contrôle d'accès multi-portes : au premier démarrage, un
portail par défaut ("Portail principal") est créé à partir de
`DOGARI_CAMERA_INDEX`/`DOGARI_USE_GPIO`. Au-delà, tout se gère via l'onglet
**Contrôle d'accès** / **Utilisateurs & Rôles** du tableau de bord, ou l'API.

### Portails vs. caméras IP

- **Portail** (`/api/portals`) : un point d'accès physique — nom, source
  caméra (index USB ou URL RTSP/HTTP), et une porte (simulée ou GPIO avec sa
  broche). C'est ce que cible une tentative de reconnaissance
  (`POST /api/access/recognize?portal_id=...`).
- **Caméra IP** (`/api/ip-cameras`) : une caméra de surveillance sans porte
  associée — utilisée uniquement par la recherche de personne et la
  surveillance sécurité, jamais pour décider d'un accès.

```bash
# Créer un portail (webcam USB, porte simulée)
curl -X POST http://localhost:8000/api/portals -H "Content-Type: application/json" \
  -d '{"name": "Entrée principale", "camera_source": "0", "camera_kind": "usb", "door_type": "simulated"}'

# Créer un portail avec une gâche GPIO réelle (Raspberry Pi)
curl -X POST http://localhost:8000/api/portals -H "Content-Type: application/json" \
  -d '{"name": "Portail Nord", "camera_source": "1", "door_type": "gpio", "gpio_relay_pin": 17}'

# Ajouter une caméra IP de surveillance (pas un portail)
curl -X POST http://localhost:8000/api/ip-cameras -H "Content-Type: application/json" \
  -d '{"name": "Parking", "source": "rtsp://192.168.1.50:554/stream1"}'
```

### Rôles et horaires d'accès

Un visage reconnu ne suffit pas : l'utilisateur doit avoir un **rôle**, et ce
rôle doit avoir un horaire configuré pour **ce portail précis**. Aucun horaire
pour un portail donné = aucun accès à ce portail, à aucun moment. Les horaires
sont définis **par jour de la semaine** (0 = lundi ... 6 = dimanche), pas
seulement par plage horaire globale.

```bash
# Créer un rôle
curl -X POST http://localhost:8000/api/roles -H "Content-Type: application/json" -d '{"name": "Professeur"}'

# Autoriser ce rôle sur un portail, le lundi de 8h à 18h
curl -X POST http://localhost:8000/api/roles/<role_id>/schedules -H "Content-Type: application/json" \
  -d '{"portal_id": <portal_id>, "weekday": 0, "start_time": "08:00", "end_time": "18:00"}'

# Retirer tout accès de ce rôle à ce portail
curl -X DELETE http://localhost:8000/api/roles/<role_id>/portals/<portal_id>
```

Un utilisateur reconnu mais dont le rôle n'a pas d'horaire valide pour le
portail visé est refusé avec le statut `portal_not_authorized` (son identité
reste journalisée, contrairement à un visage réellement inconnu). Assignez un
rôle à un utilisateur via `role_id` lors de sa création
(`POST /api/users`, champ de formulaire) ou depuis le tableau de bord.

Un rôle encore utilisé par un utilisateur ne peut pas être supprimé
(`DELETE /api/roles/{id}` renvoie alors 409) : réassignez d'abord ses
utilisateurs à un autre rôle.

## Recherche continue d'une personne sur un flux caméra

Retrouve un utilisateur **déjà enregistré** (visage connu du système) sur un
flux caméra en continu : démarre une tâche de fond qui échantillonne la
caméra choisie toutes les `DOGARI_SEARCH_POLL_INTERVAL_SECONDS` secondes,
compare chaque visage détecté à l'embedding de la personne nommée, et
journalise chaque observation ("sighting").

```bash
# Démarrer une recherche (sur un portail OU une caméra IP, pas les deux)
curl -X POST http://localhost:8000/api/search/start \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Alice Dupont", "ip_camera_id": <ip_camera_id>}'

# Lister les recherches actives, consulter les observations, arrêter
curl http://localhost:8000/api/search
curl http://localhost:8000/api/search/<search_id>/sightings
curl -X POST http://localhost:8000/api/search/<search_id>/stop
```

Également disponible sur le tableau de bord, section "Rechercher une
personne". Ne fonctionne que pour des utilisateurs déjà enregistrés (avec
consentement implicite via l'inscription) : ce n'est pas un outil de suivi de
personnes non enregistrées, et chaque recherche doit être arrêtée
explicitement (`.../stop`) une fois terminée.

> **Limite technique** : le registre des recherches actives est en mémoire
> dans le processus web — il ne survit pas à un redémarrage du serveur et ne
> fonctionne qu'avec un seul worker uvicorn (adapté au MVP).

## Surveillance sécurité continue (foule, armes)

Démarre une surveillance en tâche de fond sur une caméra, avec deux volets :

- **Détection de foule ("mouvements de masse")** : fiable, basée sur le
  comptage de visages détectés simultanément (`DOGARI_CROWD_SIZE_THRESHOLD`).
  Événement `crowd_detected` journalisé et affiché sur le tableau de bord.
- **Détection d'armes — ⚠️ EXPÉRIMENTALE, désactivée par défaut** :

  > Contrairement à la détection/reconnaissance faciale (YuNet/SFace), il
  > n'existe **aucun modèle de référence officiellement maintenu et validé**
  > pour la détection d'armes — les modèles COCO standards n'ont même pas de
  > classe "arme". Ce module (`src/dogari/vision/weapon_detector.py`) s'appuie
  > sur un modèle YOLO (Ultralytics) que vous devez fournir vous-même, dont le
  > taux de faux positifs/négatifs **n'est pas garanti**. **Ne l'utilisez
  > jamais comme seule mesure de sécurité** : il doit être combiné à une
  > supervision humaine et à d'autres contrôles physiques. Toute alerte doit
  > être vérifiée manuellement avant toute action.

  Pour l'activer :

  ```bash
  pip install -r requirements-weapon-detection.txt   # installe ultralytics (+ torch)
  # Fournissez un modèle YOLO entraîné pour la détection d'armes (poids .pt),
  # placé à DOGARI_WEAPON_MODEL_PATH (models/weapon_detection.pt par défaut).
  DOGARI_WEAPON_DETECTION_ENABLED=true python -m dogari.web.app
  ```

Utilisation (dashboard, section "Surveillance sécurité", ou API) :

```bash
curl -X POST http://localhost:8000/api/monitoring/start -H "Content-Type: application/json" -d '{"portal_id": <portal_id>}'
curl http://localhost:8000/api/monitoring/events
curl -X POST http://localhost:8000/api/monitoring/<monitor_id>/stop
```

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
détection d'anomalies et rapports automatiques. Le contrôle GPIO réel (Phase 7)
est préparé via `GPIODoorController` dans `src/dogari/access/door.py`,
configurable par portail (`door_type: "gpio"`) — il reste à valider sur le
matériel réel. Le détail des phases est documenté dans [PROJECT.md](PROJECT.md).

Au-delà de la Phase 8 initiale, plusieurs fonctionnalités ont été ajoutées sur
demande :

- **Portails, caméras IP et rôles d'accès** : le contrôle d'accès est passé
  d'un modèle "caméra principale/secondaire" figé par variables d'environnement
  à un modèle multi-portail géré en base (portails, caméras IP, rôles, horaires
  hebdomadaires par rôle/portail) — voir la section dédiée.
- Recherche continue d'une personne nommée sur un flux caméra.
- Détection de foule ("mouvements de masse").
- Détection d'armes, explicitement **expérimentale** (voir la section dédiée) :
  aucun modèle de référence validé n'existe pour cet usage, contrairement à la
  détection faciale.
- Tableau de bord réorganisé en onglets (Vue d'ensemble / Contrôle d'accès /
  Utilisateurs & Rôles / Surveillance / Rapports).
