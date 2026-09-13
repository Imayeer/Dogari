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

```
$ .venv/bin/python scripts/download_models.py
Téléchargement de face_detection_yunet_2023mar.onnx depuis
https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx ...
[ERREUR] Échec du téléchargement de face_detection_yunet_2023mar.onnx : HTTP Error 403: Forbidden

Téléchargement de face_recognition_sface_2021dec.onnx depuis
https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx ...
[ERREUR] Échec du téléchargement de face_recognition_sface_2021dec.onnx : HTTP Error 403: Forbidden

$ ls -la models/
total 8
drwxr-xr-x 2 root root 4096 ... .
drwxr-xr-x 11 root root 4096 ... ..
-rw-r--r-- 1 root root    0 ... .gitkeep
```

**ÉCHEC.** `403 Forbidden` sur `github.com` — cet environnement bloque le
trafic sortant vers ce domaine (même blocage déjà rencontré dans cette
session pour Roboflow Universe et Kaggle lors de la recherche d'un jeu de
données pour la détection d'armes). Aucun fichier `.onnx` réel obtenu ;
aucune valeur de taille de fichier n'est donc rapportée ici (voir mise en
garde en introduction : aucun résultat inventé).

**Conséquence directe** : les étapes 4 (évaluation FAR/FRR/accuracy) et 5
(latence) ci-dessous, qui nécessitent les modèles réels pour exécuter
`detect_single_face`/`generate_embedding`, ne peuvent pas être exécutées
dans cet environnement tant que les fichiers `.onnx` n'y sont pas présents
d'une manière ou d'une autre (voir section "Prochaine étape").

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

## Évaluation de la reconnaissance (FAR/FRR/accuracy)

**NON EXÉCUTÉE.** Deux blocages cumulés :
1. Pas de modèles `.onnx` réels dans cet environnement (voir ci-dessus).
2. Pas de jeu de photos réelles fourni (`test_dogari/gallery` /
   `test_dogari/probes`) — conformément à l'instruction de ne jamais
   fabriquer de fausses images, aucun jeu de données synthétique n'a été
   créé pour contourner ce manque.

## Latence et ressources

**NON EXÉCUTÉE**, même cause : nécessite les modèles réels et au moins une
image de test. Le script `scripts/benchmark_latency.py` a toutefois été
créé dans le dépôt (voir commit associé), prêt à être exécuté dès que les
modèles et des images seront disponibles — y compris sur le Raspberry Pi
cible, ce qui serait la mesure la plus pertinente pour le mémoire.

## Échecs ou anomalies rencontrés

- **Téléchargement des modèles YuNet/SFace : `HTTP Error 403: Forbidden`**
  sur `github.com/opencv/opencv_zoo/raw/main/...`. Bloqué par la politique
  réseau sortante de cet environnement sandbox, pas par le projet
  lui-même — le script fonctionne normalement sur un réseau standard (c'est
  ainsi qu'il a été conçu et documenté dans le README).
- Aucune autre anomalie : installation et tests automatisés se sont
  déroulés sans accroc.

## Prochaine étape pour compléter ce rapport

Deux options, non exclusives :

1. **Télécharger les modèles manuellement et me les transmettre** (via
   upload dans cette conversation) : les deux fichiers sont accessibles
   depuis n'importe quel réseau standard aux URLs ci-dessus, et pèsent
   ~230 Ko et ~36 Mo. Avec eux, plus 2-3 photos réelles (voir structure
   `gallery/`/`probes/` dans les instructions), je peux exécuter les
   étapes 4 et 5 dans cette session et compléter ce rapport avec de
   vraies mesures — sur cette VM, pas sur Raspberry Pi (à noter comme
   telles dans le mémoire).
2. **Exécuter les étapes 2, 4, 5 sur ta machine** (ou idéalement le
   Raspberry Pi cible) en suivant `INSTRUCTIONS_VERIFICATION_DOGARI.md`,
   et me transmettre les sorties obtenues pour que je les intègre ici.
   C'est la seule option qui donne des chiffres de latence réellement
   représentatifs de la plateforme visée par le mémoire.
