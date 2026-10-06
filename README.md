# Résistance des matériaux : cours et exercices interactifs

Page autonome (un seul fichier HTML, aucune dépendance externe, utilisable hors ligne), publiée par
GitHub Pages depuis `index.html`. Son accueil, sur le modèle de la page « Ajustements », mène à :

| Adresse | Contenu |
|---|---|
| `index.html` | accueil : grille des cours, grille des exercices (pastilles Niveau 1 / Niveau 2) |
| `?ex=cours-traction-n1` | Cours 1.1 — Traction (Niveau 1) : courbe de l'essai cliquable, simulateur, quiz |
| `?ex=cours-cisaillement-n1` | Cours 2.1 — Cisaillement (Niveau 1) : animation, simulateur, jeu des sections, quiz |
| `?ex=cours-traction`, `?ex=cours-cisaillement` | cours 1.2 et 2.2 (Niveau 2) — « En cours d'édition » |
| `?ex=traction-n1` | Exercice 1.1 — Traction (Niveau 1) : 5 parties, 30 questions, 1 tracé, 1 h 30 |
| `?ex=traction` | Exercice 1.2 — Traction et compression (Niveau 2) : 4 parties, 23 questions, 1 tracé, 1 h 05 |
| `?ex=cisaillement-n1` | Exercice 2.1 — Cisaillement (Niveau 1) : 3 parties, 27 questions, 3 tracés, 1 h 10 |
| `?ex=cisaillement` | Exercice 2.2 — Cisaillement (Niveau 2) : 7 parties, 30 questions, 1 tracé, 1 h 20 |

Chaque exercice propose le mode entraînement ou le mode examen, avec sa propre note pondérée par
la durée de ses parties. Corrections apportées au contenu d'origine, tolérances et questions ajoutées :
[`NOTE-DE-LIVRAISON.md`](NOTE-DE-LIVRAISON.md).

**Ajouter un exercice** : décrire ses parties dans `src/generer.py` (liste `PARTS`), puis l'ajouter à
`EXO_DEFS` ; la carte apparaît d'elle-même sur l'accueil.

## Régénérer la page

La page est produite par un script, à partir du gabarit (`src/gabarit-exercice-interactif.html`, recopié sans
modification de son style ni de ses moteurs) et du contenu décrit dans `src/generer.py`.

```sh
bash outils/preparer-images.sh   # seulement si les images de src/images/originaux changent (ImageMagick 6)
python3 src/generer.py           # écrit index.html
```

## Tester

```sh
node --test tests/correction.test.js                          # moteur de correction : 110 questions, cas justes, faux et limites
NODE_PATH=$(npm root -g) node --test tests/navigateur.test.js # accueil, cours, parcours entraînement / examen, impression, tracés, DR
```

`tests/reponses.js` contient une réponse juste par question ; le parcours navigateur vérifie qu'un sujet
entièrement juste donne 20/20 dans chaque exercice, sans erreur JavaScript.

## Organisation

| Chemin | Rôle |
|---|---|
| `src/gabarit-exercice-interactif.html` | gabarit de référence (charte, moteurs de correction et d'application) |
| `src/generer.py` | contenu (exercices, documents, cours interactif), accueil, aiguillage et assemblage |
| `src/images/originaux/` | figures d'origine, fond blanc |
| `src/images/` | figures quantifiées intégrées en data URI, montage de la page d'accueil |
| `outils/preparer-images.sh` | quantification des figures et montage d'accueil |
| `tests/` | tests Node et Playwright |
| `.github/workflows/static.yml` | publication GitHub Pages (déclenchée sur la branche `main`) |
