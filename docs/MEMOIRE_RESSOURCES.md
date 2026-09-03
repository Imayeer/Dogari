# Dogari — Ressources pour la rédaction du mémoire

> Document de travail destiné à servir de base factuelle pour la rédaction du
> rapport de mémoire (avec Claude ou tout autre outil). Il recense tout ce qui
> a été réalisé techniquement, les choix effectués et pourquoi, ce qui reste
> à faire, et des pistes pour renforcer à la fois le projet et le mémoire.
>
> Dépôt : `Imayeer/Dogari` — branche `claude/dogari-access-control-n335v5` —
> PR #1 (ouverte, non fusionnée à `main`).

---

## 1. Présentation du projet

Dogari est un système de contrôle d'accès physique basé sur la reconnaissance
faciale, conçu pour fonctionner **localement** (sans dépendance à Internet en
fonctionnement normal) et pour être déployable sur **Raspberry Pi 5**.

Objectif général : remplacer un contrôle d'accès classique (badge, code) par
une reconnaissance faciale couplée à une politique d'accès fine (qui a le
droit d'entrer, où, et à quel moment), avec journalisation et détection
d'anomalies pour la traçabilité et la sécurité.

Le détail complet de la spécification (objectifs, architecture, phases) est
dans `PROJECT.md` à la racine du dépôt.

---

## 2. Ce qui a été réalisé

### 2.1 Socle du MVP (Phases 1 à 6)

- **Structure du projet** : architecture modulaire en 5 packages Python
  (`core`, `storage`, `vision`, `access`, `web`), séparant configuration,
  persistance, traitement d'image, logique métier et interface.
- **Base de données** : SQLite locale, schéma géré par script SQL idempotent
  (`CREATE TABLE IF NOT EXISTS` + migrations légères `ALTER TABLE`), pas de
  dépendance à un serveur de base de données externe — cohérent avec la
  contrainte "fonctionnement local, sans Internet".
- **Module caméra** : capture vidéo via OpenCV (`cv2.VideoCapture`), source
  configurable (webcam USB par index, ou caméra IP par URL RTSP/HTTP).
- **Reconnaissance faciale** : détection + identification par comparaison
  d'embeddings (voir détail technique en 3.1).
- **Décision d'accès** : orchestrée par `AccessController` — capture →
  détection de vivacité → détection de visage → reconnaissance → décision
  (autorisé/refusé/erreur) → commande de porte → journalisation.
- **Contrôle de porte** : abstraction `DoorController` avec deux
  implémentations — `SimulatedDoorController` (développement PC) et
  `GPIODoorController` (relais GPIO réel, Raspberry Pi).
- **Interface web** : API REST (FastAPI) + tableau de bord HTML/JS pour
  gérer les utilisateurs, déclencher une reconnaissance, consulter les logs.

### 2.2 Détection de vivacité (anti-usurpation)

Avant la reconnaissance, le système capture une rafale de plusieurs images
(par défaut 5, espacées de 0,15 s) et mesure le mouvement du visage entre ces
images (`vision/liveness.py`). Une photo ou un écran statique produit un
visage quasi identique d'une image à l'autre → rejet (`spoof_detected`).

**Limite assumée et documentée** : méthode volontairement simple pour un
MVP, sensible au bruit capteur, ne protège pas contre un rejeu vidéo. Le
seuil (`DOGARI_LIVENESS_MOTION_THRESHOLD`) doit être calibré empiriquement
sur le matériel réel (non fait à ce jour, voir section 4).

### 2.3 Détection d'anomalies

`access/anomaly.py` applique un jeu de règles simples sur l'historique des
accès :
- refus répétés rapprochés (fenêtre glissante configurable) ;
- accès hors des horaires habituels ;
- pic de fréquence de tentatives sur une courte période.

Ce sont des règles explicites, pas un modèle appris (choix assumé : pas de
données d'entraînement disponibles pour un modèle de détection d'anomalies).

### 2.4 Rapports de synthèse

`access/reports.py` agrège l'historique sur une période donnée (tentatives
par statut, utilisateurs distincts, répartition quotidienne, anomalies).
Trois modes d'accès : tableau de bord, API (JSON/CSV/TXT), et script CLI
exécutable en tâche cron pour des rapports automatiques périodiques.

### 2.5 Évaluation quantitative de la reconnaissance

`scripts/evaluate_recognition.py` calcule l'**accuracy**, le **FAR** (taux
de faux acceptation) et le **FRR** (taux de faux rejet) sur un jeu de test
étiqueté (dossier `gallery/` + `probes/`), avec un mode `--sweep` qui balaie
plusieurs seuils de tolérance. **C'est l'outil à utiliser pour produire les
chiffres d'évaluation du mémoire** (chapitre validation/résultats).

### 2.6 Fonctionnalités de sécurité additionnelles (au-delà du périmètre initial)

Ajoutées sur demande explicite, au-delà de la spécification initiale :

- **Recherche continue d'une personne nommée** (`access/person_search.py`) :
  surveillance en tâche de fond d'une caméra, comparant chaque visage détecté
  à l'embedding d'un utilisateur déjà enregistré, avec journalisation des
  observations ("sightings") horodatées.
- **Détection de foule / mouvements de masse** (`access/security_monitor.py`) :
  comptage de visages simultanés sur une image, seuil configurable.
- **Détection d'armes — expérimentale** (`vision/weapon_detector.py`) :
  intégration d'un modèle YOLO (via `ultralytics`), désactivée par défaut,
  dépendance optionnelle lourde. **Point important pour le mémoire** :
  contrairement à la détection faciale (YuNet/SFace, modèles officiels
  OpenCV Zoo), il n'existe aucun modèle de référence validé pour la
  détection d'armes — ce choix de rendre la fonctionnalité explicitement
  opt-in et clairement documentée comme non fiable est en soi une décision
  de conception à valoriser (gestion responsable d'une fonctionnalité à
  risque de sécurité).

### 2.7 Refonte majeure : contrôle d'accès multi-portails avec rôles et horaires

C'est le chantier le plus substantiel de cette session, allant au-delà de la
spécification initiale (structure "caméra principale/secondaire" figée par
variables d'environnement) :

- **Portails** (`storage/portals_repository.py`) : points d'accès physiques
  nommés, chacun avec sa propre caméra (USB ou IP) et sa propre porte
  (simulée ou GPIO avec broche dédiée). C'est ce qu'une tentative de
  reconnaissance cible désormais (`portal_id`), et non plus un simple
  sélecteur "primaire/secondaire".
- **Caméras IP de surveillance** (`storage/ip_cameras_repository.py`) :
  caméras sans porte associée, utilisées uniquement par la recherche de
  personne et la surveillance sécurité — séparation nette entre "caméra
  d'accès" et "caméra de surveillance".
- **Rôles d'accès** (`storage/roles_repository.py`) : remplacent le champ
  libre `role` (texte) des utilisateurs. Un utilisateur a désormais un
  `role_id`.
- **Horaires hebdomadaires par rôle et par portail**
  (`storage/role_schedules_repository.py`, `access/role_access.py`) : un
  rôle n'a accès à un portail que dans les créneaux explicitement définis,
  **par jour de la semaine** (lundi à dimanche, pas seulement une plage
  horaire globale). Aucun horaire défini pour un portail = aucun accès à ce
  portail, à aucun moment.
- **Conséquence sur la logique de décision** : un visage reconnu ne suffit
  plus à obtenir l'accès. `AccessController` vérifie, après identification
  positive, si le rôle de l'utilisateur est autorisé sur *ce* portail à
  *cet* instant précis. Sinon, refus avec un nouveau statut dédié
  (`portal_not_authorized`), et — point de conception à souligner dans le
  mémoire — **l'identité de la personne reste journalisée**, contrairement à
  un visage réellement inconnu : distinction entre "je ne sais pas qui c'est"
  et "je sais qui c'est, mais ce n'est pas autorisé ici/maintenant", utile
  pour l'audit de sécurité.
- **Migration de schéma** : ajout de colonnes (`users.role_id`,
  `access_logs.portal_id`) via `ALTER TABLE` idempotent, pour ne pas casser
  les bases existantes. Une fonction de "seed" convertit automatiquement
  l'ancienne configuration par variables d'environnement en un portail par
  défaut au premier démarrage.

### 2.8 Tableau de bord réorganisé

Passage d'une page unique à liste plate de sections vers une interface à
**5 onglets** : Vue d'ensemble, Contrôle d'accès (gestion des portails,
déclenchement de reconnaissance, logs), Utilisateurs & Rôles (gestion des
utilisateurs, des rôles et de leurs horaires), Surveillance (caméras IP,
recherche de personne, surveillance sécurité), Rapports.

Implémentation en JavaScript vanilla (pas de framework front-end), cohérente
avec la contrainte de simplicité/légèreté pour un déploiement embarqué.

### 2.9 Tests et méthodologie de validation automatisée

**76 tests automatisés (pytest)**, tous passants. Approche méthodologique à
mentionner dans le mémoire :
- Base de données temporaire par test (isolation complète).
- Injection de dépendances pour simuler caméra et GPIO sans matériel réel
  (`monkeypatch` sur les fonctions de capture/détection).
- Tests découpés en logique pure testable séparément de la boucle
  d'acquisition temps réel (ex. la fonction qui décide "ce visage
  correspond-il à la cible ?" est testée indépendamment du thread qui
  interroge la caméra en continu).
- Vérification de bout en bout de l'API web via `TestClient` (FastAPI), y
  compris les scénarios d'erreur (portail inconnu, rôle non autorisé...).
- Vérification manuelle du tableau de bord avec Playwright (navigation par
  onglets, création de portails/rôles/horaires via l'interface, absence
  d'erreurs JavaScript).

### 2.10 Stack technique (pour le chapitre "choix technologiques")

| Composant | Choix | Justification |
|---|---|---|
| Backend web | FastAPI | Léger, typé, documentation OpenAPI automatique |
| Base de données | SQLite | Aucune dépendance serveur, adapté à un déploiement local/embarqué |
| Détection de visage | YuNet (ONNX, OpenCV Zoo) | Modèle officiel léger (~340 Ko), pas de compilation requise |
| Reconnaissance faciale | SFace (ONNX, OpenCV Zoo) | Modèle officiel (~36 Mo), embeddings 128-D normalisés |
| Détection d'armes | YOLO via `ultralytics` (optionnel) | Seule option réaliste pour de la détection d'objets, mais sans modèle de référence validé — dépendance isolée et désactivable |
| Frontend | HTML/CSS/JS vanilla | Pas de build step, cohérent avec un déploiement embarqué simple |
| Tests | pytest | Standard, intégration naturelle avec FastAPI `TestClient` |

---

## 3. Détails techniques utiles pour le mémoire

### 3.1 Pourquoi YuNet + SFace plutôt que `dlib`/`face_recognition`

Choix initial envisagé : `dlib`/`face_recognition` (bibliothèque très
utilisée dans les tutoriels de reconnaissance faciale). **Abandonné et
remplacé** par YuNet (détection) + SFace (reconnaissance), tous deux des
modèles ONNX exécutés via `cv2.dnn`, pour une raison de déploiement :
`dlib` nécessite une compilation C++ longue et gourmande en mémoire, parfois
indisponible en wheel précompilé sur architecture ARM (Raspberry Pi) — un
point de blocage classique identifié *avant* qu'il ne devienne un problème
en fin de projet. C'est un exemple concret d'anticipation de contrainte de
déploiement à valoriser dans le mémoire (chapitre choix techniques).

### 3.2 Seuils et paramètres clés

- Tolérance de reconnaissance : distance L2 = 1.128 (valeur recommandée par
  OpenCV Zoo pour des embeddings SFace 128-D normalisés).
- Vivacité : rafale de 5 images, intervalle 0,15 s, seuil de mouvement 1.5
  (à calibrer sur le matériel réel, non fait à ce jour).
- Foule : seuil par défaut 5 visages simultanés.
- Recherche de personne : intervalle d'échantillonnage 2 s, "cooldown" de
  30 s entre deux observations journalisées (évite le spam de logs).

### 3.3 Limite technique assumée (registre en mémoire)

Le registre des recherches/surveillances actives est en mémoire dans le
processus web : il ne survit pas à un redémarrage et ne fonctionne qu'avec
un seul worker uvicorn. Limite documentée et acceptée pour le périmètre
actuel (MVP mono-instance), à mentionner explicitement comme telle plutôt
que découverte par le jury.

---

## 4. Ce qui reste à faire

### 4.1 Validation terrain (priorité pour le mémoire : apporte la preuve empirique)

Rien de ce qui suit n'a été testé sur du matériel réel dans cette session
(uniquement avec des caméras simulées/mockées) :
- Le système portails/rôles/horaires en conditions réelles.
- La recherche continue de personne.
- La détection de foule.
- Calibrage du seuil de détection de vivacité sur la webcam réelle utilisée.

**Pour le mémoire** : documenter ces essais (captures d'écran, logs réels,
éventuellement un tableau de résultats) donne une validation empirique bien
plus convaincante que la seule mention "76 tests automatisés passent".

### 4.2 Détection d'armes

Décision en attente : choisir un modèle YOLO pré-entraîné (pistes identifiées
sur Roboflow Universe, à tester en ligne avant de télécharger), le déployer
localement. Aucune modification de code nécessaire une fois le modèle choisi.

### 4.3 Phase 7 — Déploiement Raspberry Pi réel

Le contrôle GPIO (`GPIODoorController`) est implémenté et testé
unitairement (avec simulation), configurable indépendamment par portail,
mais **jamais validé sur du matériel Raspberry Pi réel** (non disponible
pendant cette session). À faire : test d'ouverture de gâche réelle, mesure
de performance (temps de traitement d'une image, charge CPU/mémoire) sur le
matériel cible — donnée importante pour un mémoire évoquant un déploiement
embarqué.

### 4.4 Autres pistes d'amélioration (pour renforcer le projet ET le mémoire)

- **Sécurité du tableau de bord lui-même** : à ce stade, aucune
  authentification ne protège l'accès à l'interface web/API — un point à
  traiter (au minimum le documenter comme limite connue, idéalement ajouter
  une authentification basique) avant toute mise en situation réelle. C'est
  un bon sujet de discussion critique pour le mémoire (contrôler l'accès
  physique sans contrôler l'accès au système qui le pilote serait
  incohérent).
- **Chiffrement au repos** des données sensibles (embeddings faciaux,
  images de référence) — actuellement stockées en clair dans SQLite.
- **CI/CD** : aucune intégration continue configurée à ce jour (les tests
  s'exécutent localement uniquement).
- **Tests de charge** sur le matériel cible (Raspberry Pi) pour caractériser
  les limites (nombre de portails simultanés, latence de reconnaissance).

---

## 5. Suggestions pour la structure du mémoire

Basé sur ce qui existe et ce qui manque, une trame possible :

1. **Introduction** — contexte, problématique, objectifs.
2. **État de l'art** — solutions existantes de contrôle d'accès biométrique,
   limites, positionnement de Dogari.
3. **Analyse et spécification** — cahier des charges (voir `PROJECT.md`),
   choix d'architecture modulaire.
4. **Conception technique** — architecture (5 modules), modèle de données
   (portails/rôles/horaires en particulier — c'est le point de conception
   le plus intéressant à détailler), choix technologiques justifiés (§3.1).
5. **Réalisation** — parcourir les fonctionnalités (§2), avec extraits de
   code pertinents et captures d'écran du tableau de bord.
6. **Validation et résultats** — résultats de `evaluate_recognition.py`
   (accuracy/FAR/FRR), résultats des tests automatisés, et **idéalement**
   des résultats d'essais réels (§4.1) une fois effectués.
7. **Limites et perspectives** — reprendre honnêtement la section 4 de ce
   document : c'est un standard académique valorisé par les jurys, pas un
   aveu de faiblesse.
8. **Conclusion**.

---

## 6. Historique du dépôt (pour référence)

- Dépôt GitHub : `Imayeer/Dogari`
- Branche de travail : `claude/dogari-access-control-n335v5`
- Pull request : #1, ouverte contre `main`, non fusionnée à ce jour
- Tous les commits de cette session sont poussés ; l'arbre de travail est
  propre (aucune modification locale non validée)
