# Résultats de vérification Dogari

> Rapport généré en exécutant réellement les étapes de
> `INSTRUCTIONS_VERIFICATION_DOGARI.md`, dans l'environnement cloud sandbox
> Claude Code (et non un Raspberry Pi, la plateforme cible du mémoire —
> voir la mise en garde en fin de document). Aucun résultat n'est inventé :
> les étapes non exécutées sont marquées comme telles, pas remplacées par
> une valeur plausible.

## Environnement

```
$ uname -a
Linux vm 6.18.44-fc-v24 #1 SMP PREEMPT_DYNAMIC @0 x86_64 x86_64 x86_64 GNU/Linux

$ python3 -c "import platform; print(platform.processor())"
x86_64

$ nproc
4

$ free -h
               total        used        free      shared  buff/cache   available
Mem:            15Gi       637Mi        14Gi        12Mi       886Mi        15Gi
Swap:             0B          0B          0B

$ lscpu | grep -E "Model name|CPU\(s\)"
CPU(s):                                  4
On-line CPU(s) list:                     0-3
Model name:                              Intel(R) Xeon(R) Processor @ 2.80GHz
NUMA node0 CPU(s):                       0-3
```

**⚠️ Ce n'est PAS un Raspberry Pi 5** (plateforme cible du mémoire, Phase 7).
C'est une VM cloud x86_64 (Xeon, 4 vCPU, 15 Gio RAM), largement plus
puissante qu'un Raspberry Pi. Toute mesure de latence obtenue ici serait
donc **optimiste** par rapport au déploiement réel visé et ne peut pas
remplacer une mesure sur le matériel cible.

## Installation

Python 3.11.15, environnement virtuel `.venv` créé à la racine du dépôt.
`pip install -r requirements.txt` a réussi sans erreur (33 paquets installés,
y compris `dogari` en mode éditable). Sortie complète disponible sur demande
si nécessaire pour le mémoire ; résumé : succès total, aucun avertissement
bloquant.

## Modèles téléchargés

**Depuis le sandbox Claude Code** : ÉCHEC. `403 Forbidden` sur `github.com`
(même blocage déjà rencontré dans cette session pour Roboflow Universe et
Kaggle lors de la recherche d'un jeu de données pour la détection d'armes) :

```
$ .venv/bin/python scripts/download_models.py
Téléchargement de face_detection_yunet_2023mar.onnx depuis
https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx ...
[ERREUR] Échec du téléchargement de face_detection_yunet_2023mar.onnx : HTTP Error 403: Forbidden
[ERREUR] Échec du téléchargement de face_recognition_sface_2021dec.onnx : HTTP Error 403: Forbidden
```

**Depuis la machine réelle de l'utilisateur** (réseau standard) : SUCCÈS.
Tailles confirmées, correspondant exactement aux valeurs attendues :

```
$ dir models\
face_detection_yunet_2023mar.onnx       232589 octets
face_recognition_sface_2021dec.onnx   38696353 octets
```

(232 589 octets = exactement la taille attendue ; 38 696 353 octets ≈ 36,9 Mo,
cohérent avec les ~36 Mo annoncés dans le README — ce sont bien les modèles
réels, pas des pointeurs Git LFS.)

## Tests automatisés

```
$ .venv/bin/pytest -v
[...]
76 passed, 3 warnings in 1.92s
```

Les 76 tests passent. Liste complète des tests exécutés disponible dans
`/tmp/pytest_output.txt` généré lors de cette session si besoin de la
coller intégralement dans le mémoire. Ces tests s'exécutent sans les
modèles réels : les appels de vision (`detect_single_face`,
`generate_embedding`, etc.) sont simulés (mocks/injection de dépendances),
ce qui explique qu'ils ne soient pas affectés par l'échec de téléchargement
ci-dessus.

## Anomalie détectée et corrigée : échec de détection sur photos haute résolution

Première tentative d'évaluation avec deux vraies photos de référence
(`gallery/amino/`, `gallery/soraya/`) : les deux ont été rejetées avec
`[AVERTISSEMENT] Aucun visage détecté` malgré des visages nets, droits et
bien éclairés à l'inspection visuelle. Diagnostic avec
`scripts/debug_face_detection.py` sur la photo de `soraya`
(1408×1470 px) :

```
1. Taille originale, seuil 0.9 (défaut)       visages_trouvés=0  meilleur_score=None
2. Taille originale, seuil 0.3                visages_trouvés=1  meilleur_score=0.889
3. Redimensionnée ~640px, seuil 0.9           visages_trouvés=1  meilleur_score=0.934
4. Redimensionnée ~640px, seuil 0.3           visages_trouvés=1  meilleur_score=0.934
```

**Cause identifiée** : à pleine résolution, YuNet retourne un score de
confiance (0,889) juste sous le seuil par défaut (0,90) utilisé par
`cv2.FaceDetectorYN` — le visage est bien localisé mais rejeté de justesse.
Une fois l'image réduite à ~640 px de plus grand côté, le même visage est
détecté avec un score plus élevé (0,934). Ce n'était pas qu'un problème de
jeu de test : un utilisateur réel s'inscrivant via le tableau de bord avec
une photo de téléphone haute résolution aurait rencontré le même échec
silencieux.

**Correctif appliqué** : `vision/detector.py` réduit désormais
automatiquement toute image dont le plus grand côté dépasse
`DOGARI_MAX_DETECTION_DIMENSION` (640 px par défaut) avant détection, puis
rescale les coordonnées retournées (bbox + 5 points de repère) vers les
dimensions de l'image d'origine, pour rester compatibles avec
`embeddings.generate_embedding` qui aligne le visage sur l'image originale.
Trois nouveaux tests (`tests/test_detector.py`) couvrent ce comportement,
dont un avec les dimensions exactes (1408×1470) de la photo ayant révélé le
problème. Les 79 tests automatisés passent après correction.

## Évaluation de la reconnaissance (FAR/FRR/accuracy)

**EN ATTENTE DE NOUVEL ESSAI**, avec le correctif ci-dessus. La toute
première exécution a échoué à charger la moindre image de galerie (cause
identifiée et corrigée ci-dessus) ; aucune métrique FAR/FRR/accuracy n'a
donc encore pu être calculée. Un nouvel essai avec les mêmes photos et le
code à jour (`git pull`) est nécessaire pour obtenir ces chiffres.

## Latence et ressources

**NON EXÉCUTÉE À CE STADE**, en attente d'un jeu de photos qui charge
correctement (voir ci-dessus). `scripts/benchmark_latency.py` est prêt à
être exécuté dès que possible — idéalement sur le Raspberry Pi cible, ce
qui donnerait la mesure la plus pertinente pour le mémoire.

## Échecs ou anomalies rencontrés

- **Téléchargement des modèles depuis le sandbox Claude Code : `HTTP Error
  403: Forbidden`** sur `github.com/opencv/opencv_zoo/raw/main/...`. Bloqué
  par la politique réseau sortante de cet environnement sandbox, pas par le
  projet lui-même — confirmé en réussissant le téléchargement sur une
  machine réseau standard (voir "Modèles téléchargés" ci-dessus).
- **Échec de détection de visage sur deux photos réelles haute résolution**
  (score de confiance juste sous le seuil par défaut) — cause identifiée et
  corrigée dans le code, voir section dédiée ci-dessus. C'est l'anomalie la
  plus significative de cette vérification : elle aurait affecté de vrais
  utilisateurs en production, pas seulement ce test.
- Installation et suite de tests automatisés (avant comme après le
  correctif) : aucune anomalie.

## Prochaine étape pour compléter ce rapport

Relancer, avec le code à jour (`git pull`) et les mêmes photos :

```powershell
.venv\Scripts\python scripts\evaluate_recognition.py test_dogari --sweep --csv resultats_recognition.csv
.venv\Scripts\python scripts\benchmark_latency.py test_dogari\probes --runs 50 --csv latence.csv
```

et transmettre les sorties (+ contenu des deux CSV) pour intégration finale
dans ce rapport, le Chapitre V (résultats) et le Chapitre VI (vérification
de H1/H2) du mémoire.
