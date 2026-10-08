# Résistance des matériaux : cours et exercices interactifs

Page autonome (un seul fichier HTML, aucune dépendance externe, utilisable hors ligne), publiée par
GitHub Pages depuis `index.html`. Son accueil, sur le modèle de la page « Ajustements », mène à :

| Adresse | Contenu |
|---|---|
| `index.html` | accueil : cours, exercices et études de cas (pastilles Niveau 1 / Niveau 2) |
| `?ex=cours-traction-n1` | Cours 1.1 — Traction (Niveau 1) : courbe de l'essai cliquable, simulateur, quiz |
| `?ex=cours-cisaillement-n1` | Cours 1.2 — Cisaillement (Niveau 1) : animation, simulateur, jeu des sections, quiz |
| `?ex=cours-rdm` | Cours 2 — Résistance des matériaux (Niveau 2) : cartes, sollicitations, jeu, simulateur de Hooke, synthèse, quiz |
| `?ex=traction-n1` | Exercice 1.1 — Traction (Niveau 1) : 5 parties, 30 questions, 1 tracé, 1 h 30 |
| `?ex=cisaillement-n1` | Exercice 1.2 — Cisaillement (Niveau 1) : 3 parties, 27 questions, 3 tracés, 1 h 10 |
| `?ex=traction` | Exercice 2.1 — Traction et compression (Niveau 2) : 4 parties, 23 questions, 1 tracé, 1 h 05 |
| `?ex=cisaillement` | Exercice 2.2 — Cisaillement (Niveau 2) : 7 parties, 30 questions, 1 tracé, 1 h 20 |
| `?ex=traction-essais` | Exercice 2.3 — Traction (Niveau 2) : 5 parties, 43 questions, 1 h 20 |
| `?ex=cisaillement-poinconnage` | Exercice 2.4 — Cisaillement (Niveau 2) : 2 parties, 10 questions, 30 min |
| `?ex=concentration` | Exercice 2.5 — Concentration de contraintes (Niveau 2) : 2 parties, 17 questions, 1 tracé, 50 min |
| `?ex=etude-potence` | Étude 1 — Potence de trottinette : 3 parties, 15 questions, 1 tracé, 1 h |
| `?ex=etude-transbordeur` | Étude 2 — Pont transbordeur : 3 parties, 16 questions, 55 min |
| `?ex=etude-futuroscope` | Étude 3 — Futuroscope, sièges basculants : 2 parties, 13 questions, 1 tracé, 50 min |

Chaque exercice propose le mode entraînement ou le mode examen, avec sa propre note pondérée par
la durée de ses parties. Corrections apportées au contenu d'origine, tolérances et questions ajoutées :
[`NOTE-DE-LIVRAISON.md`](NOTE-DE-LIVRAISON.md).

**Ajouter un exercice** : décrire ses parties dans `src/generer.py` (liste `PARTS`), puis l'ajouter à
`EXO_DEFS` (avec `"etude": True` pour la rubrique « Études de cas », `"img"` pour l'image de sa carte et `"kw"` pour 3 à 5 mots clés) ; la carte apparaît d'elle-même sur l'accueil.

## Régénérer la page

La page est produite par un script, à partir du gabarit (`src/gabarit-exercice-interactif.html`, recopié sans
modification de son style ni de ses moteurs) et du contenu décrit dans `src/generer.py`.

```sh
bash outils/preparer-images.sh   # seulement si les images de src/images/originaux changent (ImageMagick 6)
python3 src/generer.py           # écrit index.html
```

## Tester

```sh
node --test tests/correction.test.js                          # moteur de correction : 209 questions, cas justes, faux et limites
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
