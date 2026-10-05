# Résistance des matériaux : traction, compression et cisaillement

Exercice interactif autonome (un seul fichier HTML, aucune dépendance externe, utilisable hors ligne),
qui réunit les anciens exercices « traction » et « cisaillement » en un sujet unique de 11 parties,
53 questions et 2 tracés auto-évalués, pour une durée conseillée de 2 h 25.

- **Page à distribuer** : [`exercice-rdm-traction-compression-cisaillement.html`](exercice-rdm-traction-compression-cisaillement.html)
  (`index.html` y redirige, pour GitHub Pages).
- **Note de livraison** (corrections apportées au source, tolérances, questions ajoutées) :
  [`NOTE-DE-LIVRAISON.md`](NOTE-DE-LIVRAISON.md).

## Régénérer la page

La page est produite par un script, à partir du gabarit (`src/gabarit-exercice-interactif.html`, recopié sans
modification de son style ni de ses moteurs) et du contenu décrit dans `src/generer.py`.

```sh
bash outils/preparer-images.sh   # seulement si les images de src/images/originaux changent (ImageMagick 6)
python3 src/generer.py           # écrit exercice-rdm-traction-compression-cisaillement.html
```

## Tester

```sh
node --test tests/correction.test.js                          # moteur de correction : 53 questions, cas justes, faux et limites
NODE_PATH=$(npm root -g) node --test tests/navigateur.test.js # parcours entraînement / examen, impression, tracés, DR (Playwright)
```

`tests/reponses.js` contient une réponse juste par question ; le parcours navigateur vérifie qu'un sujet
entièrement juste donne 20/20 sans erreur JavaScript.

## Organisation

| Chemin | Rôle |
|---|---|
| `src/gabarit-exercice-interactif.html` | gabarit de référence (charte, moteurs de correction et d'application) |
| `src/generer.py` | contenu du sujet et assemblage de la page |
| `src/images/originaux/` | figures d'origine, fond blanc |
| `src/images/` | figures quantifiées intégrées en data URI, montage de la page d'accueil |
| `outils/preparer-images.sh` | quantification des figures et montage d'accueil |
| `tests/` | tests Node et Playwright |
| `.github/workflows/static.yml` | publication GitHub Pages (déclenchée sur la branche `main`) |
