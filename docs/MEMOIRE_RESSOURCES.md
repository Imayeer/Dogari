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

### 3.2 Détection d'armes : classification binaire vs. multi-classe (comparaison argumentée)

Point de conception à documenter explicitement dans le mémoire — c'est un
exemple concret d'arbitrage précision/finesse d'information sous contrainte
de données limitées, un raisonnement classique en apprentissage supervisé.

**Le choix fait** : entraîner sur un jeu de données à **classe unique**
("weapon" — présence/absence d'arme), plutôt que sur un jeu de données à
classes multiples (ex. "knife"/"pistol"/"rifle"/"shotgun" séparément).

**Comparaison :**

| Critère | Classe unique ("weapon") | Classes multiples (par type d'arme) |
|---|---|---|
| Volume de données nécessaire par classe | Tout le dataset alimente une seule classe → plus d'exemples par classe pour un volume total identique | Le même volume total se répartit entre N classes → moins d'exemples par classe (ex. ~200 images/classe sur un dataset de 2 800 images à 14 classes observé lors de la recherche de jeux de données) |
| Robustesse attendue avec un petit dataset | Plus élevée : moins de risque de sous-apprentissage par classe | Plus faible avec peu de données : risque de confusion inter-classes, faux négatifs plus fréquents sur les classes sous-représentées |
| Information apportée par une alerte | "Une arme potentielle a été détectée" | "Un couteau a été détecté" (plus précis) |
| Adéquation avec l'action déclenchée par le système | Suffisante : toute détection déclenche la **même** action (`security_events`, sévérité `critical`, vérification humaine obligatoire) | Le gain d'information n'est pas exploité par la logique métier actuelle — aucune action différenciée par type d'arme n'est prévue |
| Risque en cas d'erreur de classification | Aucun risque de confondre les *types* d'armes (un seul type possible) | Une arme mal classée (ex. pistolet identifié comme couteau) resterait correctement détectée comme "arme", mais le message d'alerte serait trompeur |

**Conclusion argumentée** : dans un contexte de contrôle d'accès où
l'action de sécurité est binaire (alerter/vérifier ou non), la classification
fine par type d'arme n'apporte pas de valeur opérationnelle proportionnelle
au coût en fiabilité qu'elle impose avec un jeu de données de taille limitée.
Le choix d'une classe unique est donc justifié par l'usage, pas seulement
par la disponibilité des données — argument à expliciter ainsi dans le
mémoire plutôt que de le présenter comme une simple contrainte subie.

*Piste d'ouverture pour la conclusion/perspectives* : si un jeu de données
plus volumineux (plusieurs milliers d'images par classe) devenait
disponible, une classification multi-classe redeviendrait pertinente,
notamment pour adapter la sévérité de l'alerte au type d'arme détecté.

### 3.3 Seuils et paramètres clés

- Tolérance de reconnaissance : distance L2 = 1.128 (valeur recommandée par
  OpenCV Zoo pour des embeddings SFace 128-D normalisés).
- Vivacité : rafale de 5 images, intervalle 0,15 s, seuil de mouvement 1.5
  (à calibrer sur le matériel réel, non fait à ce jour).
- Foule : seuil par défaut 5 visages simultanés.
- Recherche de personne : intervalle d'échantillonnage 2 s, "cooldown" de
  30 s entre deux observations journalisées (évite le spam de logs).

### 3.4 Limite technique assumée (registre en mémoire)

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

## 5. Structure imposée par l'école (canevas académique ESCEP-Niger)

Confirmée par l'analyse d'un mémoire d'un camarade de promotion (LSN/IDO,
même école, même diplôme) : ce n'est **pas** une suggestion, c'est un plan
**strictement imposé** en 3 parties / 6 chapitres — l'auteur le dit
lui-même : *"Ce mémoire s'organise en trois parties principales
conformément au canevas académique."* Toute déviation de ce squelette
(intitulés de parties/chapitres/sections) est donc à éviter ; seul le
contenu change selon le sujet.

> **Analyse d'un second mémoire de référence en attente** : le message qui a
> déclenché cette section mentionnait deux documents, un seul est arrivé.
> Compléter cette section si le second révèle des variantes.

### 5.1 Squelette exact à reproduire

```
Pages liminaires : Dédicace, Avant-propos, Remerciements, Résumé, Abstract,
                    Table des matières, Liste tableaux/figures/abréviations

INTRODUCTION GÉNÉRALE

PREMIÈRE PARTIE — Cadres théorique et méthodologique
  Chapitre I : CADRE THÉORIQUE
    1. Problématique
    2. Objectifs de l'étude (général + spécifiques)
    3. Hypothèses de recherche (générale + secondaires)
    4. Pertinence du sujet (scientifique / technologique / sociale)
    5. Revue critique de la littérature
  Chapitre II : CADRE MÉTHODOLOGIQUE
    1. Cadre de l'étude (terrain)
    2. Type et approche de recherche
    3. Méthodes de collecte des données
    4. Échantillonnage
    5. Techniques d'analyse
    6. Difficultés rencontrées

DEUXIÈME PARTIE — Cadres organisationnel et conceptuel
  Chapitre III : CADRE ORGANISATIONNEL (présentation de la structure d'accueil/cas)
    1. Présentation générale
    2. Historique et missions
    3. Organisation, ressources humaines, effectifs
    4. Moyens matériels et technologiques disponibles
    5. Contraintes (spécifiques au sujet)
    6. Justification du choix de cette structure pour le projet
  Chapitre IV : CADRE CONCEPTUEL (définitions des concepts mobilisés)
    1-6. Définitions et articulation des concepts clés

TROISIÈME PARTIE — Résultats et discussion
  Chapitre V : PRÉSENTATION ET ANALYSE DES RÉSULTATS
    1. Résultats des entretiens qualitatifs
    2. Résultats du questionnaire quantitatif
    3. Architecture du système (développement itératif)
    4. Performance du prototype
  Chapitre VI : DISCUSSION ET VÉRIFICATION DES HYPOTHÈSES
    1. Discussion des résultats
    2. Vérification des hypothèses (tableau récapitulatif)
    3. Limites de l'étude

RECOMMANDATIONS
CONCLUSION GÉNÉRALE
BIBLIOGRAPHIE
ANNEXES
```

### 5.2 Ce que ce template implique (au-delà d'un simple rapport technique)

Point essentiel, facile à manquer : ce n'est pas un canevas de rapport
technique, c'est un canevas de **recherche en sciences appliquées**, avec
deux exigences fortes qui ne sont pas déjà couvertes par le code/les tests :

1. **Une structure d'accueil réelle** ("Cas de [organisation]") sur laquelle
   repose tout le Chapitre III. Pour Dogari, c'est **ESCEP-Niger elle-même**
   (confirmé) — l'établissement sert à la fois d'école et de terrain d'étude,
   contrairement au mémoire de référence où l'école du diplôme et la
   structure étudiée étaient deux organisations différentes.
2. **Une collecte de terrain** (entretiens qualitatifs + questionnaire
   quantitatif) qui alimente tout le Chapitre V, section 1-2. **Rien de tout
   cela n'a été fait pour Dogari à ce jour** — seul le système a été
   construit. C'est le travail restant le plus important, humainement (pas
   techniquement), avant de pouvoir rédiger le Chapitre III et le Chapitre V
   en entier.

### 5.3 Mapping chapitre par chapitre — ce qu'on a déjà vs. ce qui manque

| Chapitre | Contenu attendu pour Dogari | Statut |
|---|---|---|
| I.1-2 Problématique, objectifs | Contrôle d'accès physique : failles des solutions classiques (badges, codes partagés/perdus), absence de granularité horaire/par-porte, absence de traçabilité — à ancrer si possible dans un constat réel à ESCEP (comment se gère l'accès aujourd'hui ?) | **À rédiger** — le "pourquoi" existe déjà informellement (README/PROJECT.md), à formaliser en problématique + objectifs généraux/spécifiques |
| I.3 Hypothèses | Ex. : "un système de reconnaissance faciale (YuNet+SFace) atteint une précision suffisante pour un contrôle d'accès fiable" ; "un modèle rôle+horaire par portail permet une restriction fine sans complexité excessive" ; "le système fonctionne en temps réel sur du matériel accessible" ; "le personnel/les étudiants d'ESCEP jugent le système acceptable" | **À formuler** — aucune hypothèse formelle rédigée à ce jour ; la dernière (acceptabilité) nécessite le questionnaire |
| I.4 Pertinence | Scientifique (IA appliquée à la sécurité physique en contexte à ressources limitées), technologique (architecture modulaire, coût réduit, Raspberry Pi), sociale/institutionnelle (sécurisation des locaux, traçabilité) | **À rédiger**, mais les arguments existent déjà dans README/PROJECT.md |
| I.5 Revue de littérature | État de l'art contrôle d'accès biométrique, comparaison des approches de reconnaissance faciale, systèmes similaires | **Partiellement prêt** : §3.1 de ce document (pourquoi YuNet/SFace plutôt que dlib) est un point de départ ; il manque une revue plus large (badges RFID, empreinte digitale, autres systèmes faciaux commerciaux) |
| II (méthodologie) | Approche mixte comme le mémoire de référence : itérations de développement (quantitatif/technique) + entretiens et questionnaire auprès du personnel/étudiants d'ESCEP sur leurs pratiques et attentes actuelles | **À faire entièrement** — guide d'entretien et questionnaire à concevoir (je peux aider à les rédiger) |
| II.6 Difficultés rencontrées | On en a une vraie liste, concrète et honnête : développement dans un environnement cloud sans caméra/matériel réel, dépendances lourdes bloquées par la politique réseau du bac à sable (GitHub raw, Roboflow, Kaggle inaccessibles), nécessité de tout valider ensuite en local | **Prêt** — reprendre les échanges de cette conversation |
| III (cadre organisationnel) | Présentation d'ESCEP-Niger : statut, tutelle (Ministère de la Communication, des Postes et de l'Économie Numérique — confirmé par le mémoire de référence, même école), historique, filières, effectifs, ressources, pratiques actuelles de contrôle d'accès, justification du choix | **À collecter** — nécessite des informations factuelles sur l'école (idéalement via un entretien avec l'administration) |
| IV (cadre conceptuel) | Contrôle d'accès physique (RBAC, moindre privilège), reconnaissance faciale (embeddings, similarité), IA/vision par ordinateur (CNN, YOLO), détection d'anomalies et vidéosurveillance (éthique, cas de la détection d'armes) | **Rédigeable dès maintenant** à partir des §2-3 de ce document |
| V.1-2 Résultats entretiens/questionnaire | Thèmes récurrents (pratiques actuelles, attentes), statistiques (acceptabilité, habitudes) | **À faire entièrement**, dépend de II |
| V.3 Architecture (développement itératif) | Quasiment un copier-coller structuré du §2 de ce document : Phases 1-6 (MVP) → Phase 8 (vivacité, anomalies, rapports) → extensions (recherche de personne, foule, armes) → refonte multi-portails/rôles/horaires → tableau de bord à onglets | **Prêt** |
| V.4 Performance du prototype | Résultats `evaluate_recognition.py` (accuracy/FAR/FRR), résultats des 76 tests automatisés, et **idéalement** des résultats d'essais réels (webcam, portails/rôles/horaires en conditions réelles — voir §4.1) | **Partiellement prêt** — dépend de la validation terrain non encore faite |
| VI.1-2 Discussion, vérification des hypothèses | Tableau hypothèse/statut/justification, à l'image du Tableau 9 du mémoire de référence | **À rédiger** une fois les hypothèses formulées (I.3) et les résultats disponibles |
| VI.3 Limites | Reprendre §4 de ce document (validation terrain manquante, détection d'armes non finalisée, Raspberry Pi non validé, pas d'authentification sur le tableau de bord, etc.) | **Prêt** |
| Recommandations, Conclusion | À rédiger en dernier, dans le même esprit que §4.4 de ce document | **Prêt comme base** |

### 5.4 Leçon de rigueur tirée du mémoire de référence

La Conclusion générale du mémoire analysé affirme *"le prototype IDO a
démontré une précision de reconnaissance de 91,6 % sur un vocabulaire de
base de la LSN, avec une latence moyenne de 312 ms"* — alors que le
Chapitre V/VI dit explicitement l'inverse : aucune évaluation spécifique à
la LSN n'a été conduite (seule l'ASL a été mesurée), et l'hypothèse
"corpus LSN" est marquée **NON RÉALISÉE**. Ces deux chiffres n'apparaissent
nulle part ailleurs dans le document — vraisemblablement un chiffre non
nettoyé d'un brouillon. **Règle à respecter pour Dogari** : ne jamais faire
apparaître dans la Conclusion un chiffre qui n'est pas déjà justifié et
sourcé dans le Chapitre V.

---

## 6. Historique du dépôt (pour référence)

- Dépôt GitHub : `Imayeer/Dogari`
- Branche de travail : `claude/dogari-access-control-n335v5`
- Pull request : #1, ouverte contre `main`, non fusionnée à ce jour
- Tous les commits de cette session sont poussés ; l'arbre de travail est
  propre (aucune modification locale non validée)
