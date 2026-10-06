# Note de livraison — Résistance des matériaux : traction, compression et cisaillement

> **Mise à jour : accueil et découpage en deux exercices.** La page est désormais `index.html`. Son
> accueil reprend la mise en page de la page « Ajustements » : un bandeau « Les cours » (Cours 1 —
> Traction et compression, Cours 2 — Cisaillement, tous deux « En cours d'édition ») et une grille
> d'exercices prête à accueillir d'autres cartes. Le sujet décrit ci-dessous est découpé en deux
> exercices indépendants, chacun avec son accueil, son choix de mode, sa note et son récapitulatif :
> **Exercice 1 — Traction et compression** (`?ex=traction` : parties 1 à 4 ci-dessous, 1 h 05) et
> **Exercice 2 — Cisaillement** (`?ex=cisaillement` : parties 5 à 11 ci-dessous, renumérotées 1 à 7,
> 1 h 20). Dans chaque exercice, les questions, figures et documents sont renumérotés à partir de 1
> (DP1, DT1, DT2) ; les tracés deviennent Q1.5 (traction) et Q7.2 (cisaillement), chacun sur une feuille DR1.
> Les contenus, réponses et tolérances sont inchangés. Le moteur applicatif lit désormais la durée
> conseillée dans `window.__CONSEIL_MIN__` (elle dépend de l'exercice ouvert). Tests : 56 tests unitaires
> et 7 parcours navigateur (accueil, cours, 20/20 dans chaque exercice, examen, impression, tracés).


**Fichier livré** : `exercice-rdm-traction-compression-cisaillement.html` (512 Kio, dont 290 Kio d'images
encodées ; `index.html` y redirige pour GitHub Pages).

**Sources fusionnées** : la page « Traction & Compression » (4 exercices, 23 questions) et la page
« Cisaillement » (7 exercices, 26 questions), chacune publiée dans son propre dépôt. Ces deux dépôts n'ont pas
été modifiés.

**Gabarit** : `gabarit-exercice-interactif.html`, dont le bloc `<style>`, le moteur `Grading` et le moteur
applicatif sont recopiés par le script de génération (`src/generer.py`). Les seules entrées remplacées dans le
moteur applicatif sont celles que le gabarit réserve au sujet, chaque remplacement étant vérifié : `DECOR`,
`DR_NAMES`, `CONSEIL_MIN` (145 min) et le texte « Quatre pages » de la fenêtre des DR (devenu « Deux pages »).

## Architecture retenue

Chaque exercice d'origine devient une **partie**, notée sur 20 et pondérée par sa durée conseillée. Deux
bandeaux de chapitre, « Traction et compression » puis « Cisaillement », séparent les deux familles.

| Partie | Exercice | Durée | Points | Poids |
|---|---|---|---|---|
| 1 | Traction : fil de maintien d'un siège | 30 min | 13 (9 questions + tracé de 4) | 20,7 % |
| 2 | Traction : barre de section rectangulaire | 10 min | 4 | 6,9 % |
| 3 | Compression : tube support de charge | 15 min | 6 | 10,3 % |
| 4 | Traction : dimensionnement d'un fer plat | 10 min | 4 | 6,9 % |
| 5 | Cisaillement : goupille d'une chape | 10 min | 5 | 6,9 % |
| 6 | Cisaillement : pince à goupille | 15 min | 6 | 10,3 % |
| 7 | Cisaillement : roue d'échafaudage | 10 min | 4 | 6,9 % |
| 8 | Cisaillement : platine boulonnée | 10 min | 4 | 6,9 % |
| 9 | Cisaillement : éclissage par plaques et boulons | 10 min | 3 | 6,9 % |
| 10 | Cisaillement : plaque vissée sur une poutre | 10 min | 4 | 6,9 % |
| 11 | Cisaillement : axe de chape | 15 min | 8 (4 questions + tracé de 4) | 10,3 % |
| | **Total** | **2 h 25** | **61** | **100 %** |

Les sources n'avaient ni dossier de présentation ni dossier technique : quatre documents ont été rédigés pour
que chaque question soit faisable avec les seules données fournies.

- **DP1** : démarche de résolution, conseils de calcul, représentation des actions mécaniques.
- **DT1** : formulaire traction et compression (contrainte, loi de Hooke, allongement, conversions, moment).
- **DT2** : formulaire cisaillement (sections cisaillées, contrainte admissible, dimensionnement d'un axe,
  loi de Hooke en cisaillement).
- **DT3** : aires des sections usuelles et gamme des largeurs de fers plats (nécessaire à la question Q4.4).

L'illustration d'accueil est un montage de quatre figures du sujet (siège suspendu, tube, pince, axe de chape).

## Erreurs corrigées dans le source

1. **Partie 1, module d'élasticité** : l'énoncé d'origine donnait *E* = 200 MPa pour l'acier du fil (erreur
   déjà signalée par la page source) ; la valeur retenue est *E* = 200 GPa = 200 000 MPa.
2. **Partie 3, signe** : l'énoncé impose une convention (compression négative) et demande de « tenir compte du
   signe », mais la page source acceptait aussi les valeurs positives de *N*, *σ*<sub>c</sub> et Δ*l*. Le signe
   est désormais exigé ; une valeur sans signe est fausse.
3. **Partie 3, Δ*l*** : « rétrécissement maximal Δ*l*<sub>max</sub> » est remplacé par « variation de longueur
   Δ*l* » : la charge est fixe, il n'y a pas de maximum à chercher.
4. **Partie 4, largeur normalisée** : la question demandait une largeur normalisée sans fournir de gamme. Le DT3
   donne désormais un extrait de gamme de fers plats (… 45, 50, 60, 70 … mm), d'où *a* = 60 mm.
5. **Cisaillement, unités** : la page source demandait de saisir la valeur seule, l'unité étant affichée à côté
   du champ. L'unité est désormais à saisir et compte pour la moitié des points, comme le prévoient les
   instructions du projet.

## Erreurs relevées dans le corrigé d'origine et arbitrage

| Question | Corrigé d'origine | Valeur recalculée | Arbitrage |
|---|---|---|---|
| Q1.6 (ex-Q5) *F*<sub>DE</sub> | 2 460 N, tolérance ± 45 N | 2 459,33 N (2 460,34 N avec sin *α* = 0,581) | attendu 2 459 N, ± 1,5 N : 2 459 et 2 460 acceptés |
| Q1.8 (ex-Q7) *σ*<sub>DE</sub> | 87,0 MPa alors que la consigne dit « au centième », tolérance ± 1,6 MPa | 86,98 MPa | attendu 86,98 MPa, ± 0,075 MPa : couvre 87,00 et 87,02 (calcul avec 2 460 N) |
| Q1.4 sin *α* | tolérance ± 0,008, qui acceptait 0,574 (*α* arrondi à 35°) | 0,58124 | ± 0,0015 : 0,580 à 0,582 acceptés, 0,574 refusé |
| Q1.3 *L*<sub>DE</sub> | tolérance ± 0,6 mm pour une consigne « au centième » | 860,2325 mm | ± 0,011 mm |
| Q3.4 *S* | tolérance ± 5 mm² | 1 745,33 mm² | ± 0,1 % (couvre *d*<sub>i</sub> arrondi et π = 3,14) |

Toutes les autres valeurs du corrigé d'origine ont été recalculées et confirmées (traction : 833,85 N ;
1 200 mm ; 28,27 mm² ; 4,35 × 10⁻⁴ ; 0,374 mm ; 100 MPa ; 2,38 mm ; −49 050 N ; 16,67 mm ; 400 mm ;
−28,10 MPa ; −0,0535 mm ; 140 MPa ; 57,14 mm — cisaillement : 57,01 kN ; 28,50 kN ; 962,11 mm² ;
29,63 MPa ; 2,98 ; 6 774,06 N ; 5 072,20 N ; 1 701,86 N ; 567,29 N ; 2,50 kN ; 28,27 mm² ; 88,42 MPa ;
78,54 mm² ; 31,83 MPa ; 133,33 MPa ; 12,93 mm ; 108,57 MPa ; 33,33 kN ; 307,02 mm² ; 10,87 mm ; 70 MPa ;
7,78 × 10⁻⁴ rad).

## Décisions d'interprétation et de tolérance

- **Valeur exacte** (1 200 mm, 400 mm, −49 050 N, 140 MPa, 60 mm…) : tolérance limitée à l'arrondi d'affichage.
- **Arrondi au centième sans résultat intermédiaire arrondi** : ± 0,006.
- **Résultat qui dépend de π ou d'un résultat intermédiaire arrondi demandé plus haut** : ± 0,1 % de la valeur,
  ce qui couvre π = 3,14 (annoncé comme toléré dans les consignes) et les arrondis demandés en amont.
- **Arrondi au millième** (sin *α*, *δ*<sub>DE</sub>, Δ*l*) : tolérance de l'ordre du millième, calculée pour
  accepter les deux chemins de calcul plausibles. Pour Δ*l*, −0,054 et −0,0535 mm sont acceptés, −0,053 mm est
  refusé.
- **Q11.4** : 70,00 et 70,04 MPa acceptés (± 0,1 MPa), comme dans la source, l'écart venant de l'arrondi de *d*.
- **Unités** : valeur juste et unité juste → 1 point ; unité absente ou fausse → ½ point. Les conversions
  correctes sont acceptées comme justes quand l'unité est écrite (0,834 kN pour 833,85 N, 1,2 m pour 1 200 mm,
  12 cm² pour 1 200 mm², 374 µm pour 0,374 mm, 778 µrad pour 7,78 × 10⁻⁴ rad…). MPa et N/mm² sont équivalents.
- **Déformations sans unité** (*ε*) : notation scientifique demandée, avec un exemple de saisie (`1,23e-4` ou
  `1,23×10^-4`).
- **Nombre de sections cisaillées** : réponse en chiffres (« 2 », « 2 sections », « 2 x 2 = 4 » sont lus
  correctement). Une réponse en lettres (« deux ») est refusée avec un message invitant à écrire un nombre ;
  en mode examen, elle compterait comme fausse. La consigne le précise.
- **Conclusions** (Q2.3, Q4.2) : réponse commençant par « oui » ou « non ».
- **Tracé Q1.5** : les composantes en A sont dessinées dans un sens supposé (vers la droite et vers le haut),
  comme dans le schéma d'aide d'origine ; la correction rappelle que le calcul donne en réalité *R*<sub>Ay</sub>
  vers le bas. La correction ne montre aucune valeur numérique et s'affiche dès la validation du tracé.
- **Tracé Q11.2** : la correction (sections et *P*/2) n'apparaît qu'après validation de Q11.1, qui demande le
  nombre de sections.

## Questions reformulées ou découpées

- **Q1.2** : « bras de levier AC » précisé en « distance AC, bras de levier du poids par rapport au pivot A ».
- **Q1.9** (ex-Q8) : la source demandait le seul coefficient *a* de « *a* × 10⁻⁴ » ; la question porte désormais
  sur la déformation *ε*<sub>DE</sub> complète, en notation scientifique.
- **Q3.1** : « effort normal dans le tube », avec rappel de la convention de signe dans la consigne.
- **Q4.1** : « contrainte qui produit exactement l'allongement limite de 2 mm ».
- **Q4.4** : « à l'aide du DT3, choisir la largeur normalisée ».
- Toutes les consignes de saisie suivent la formule du projet (« Arrondir au centième. Saisis la valeur avec
  son unité… ») et n'annoncent plus l'unité attendue.
- Les énoncés reprennent les hypothèses implicites de la source (poids de la poutre et du fil négligés, poids
  propre du tube négligé, barre encastrée, efforts perpendiculaires sur la chape).

## Questions ajoutées

- **Q1.5 — tracé** : isoler la poutre AC et représenter les actions extérieures (4 critères). Fond : la figure 1
  d'origine ; correction dessinée en code.
- **Q6.2, Q8.1, Q10.1, Q11.1** : « Combien de sections … sont cisaillées ? », pour que chaque exercice de
  cisaillement fasse identifier le simple ou double cisaillement, ce que la source n'expliquait que dans le
  corrigé (pince, platine, plaque vissée, axe de chape).
- **Q11.2 — tracé** : repérer les deux sections cisaillées de l'axe et l'effort *P*/2 qu'elles transmettent
  (4 critères). Fond : la figure 11 d'origine.

La numérotation suit : ex-Q5 à Q9 de l'exercice du fil deviennent Q1.6 à Q1.10 ; dans les parties 6, 8, 10 et
11, les questions d'origine sont décalées d'un rang (de deux rangs pour la partie 11).

## Points signalés sans modification

- **Figures** : les images d'origine sont de faible définition (127 à 464 px de large). Elles sont intégrées
  telles quelles (PNG quantifiés) ; les fonds de tracé sont affichés agrandis 2,5 fois.
- **Figure 3** : l'image porte « m = 5000 Kg » (coquille sur l'unité, kg). Le texte de l'énoncé utilise kg ;
  l'image n'a pas été retouchée.
- **Fenêtre des DR** : sans document réponse dans la source, les deux fonds de tracé sont les figures d'origine.
  Aucune échelle n'étant à respecter, les feuilles ne portent pas d'avertissement d'impression à 100 %.
- **Limites du moteur de correction** (non modifié) : « 4,35×10⁻⁴ » écrit avec des exposants Unicode, ou
  « 4,35×10-4 » sans le symbole ^, est lu comme 4,35 : les consignes donnent donc le format de saisie. Le
  symbole % n'est pas reconnu comme unité.

## Défauts relevés dans le gabarit

1. **Impression en mode examen avant la remise** : la règle `.sketch .q-expl[hidden]` (spécificité 0,3,0)
   l'emporte sur `body:not(.corrections-open) .q-expl` (0,2,1) : la correction rédigée des tracés s'imprimait
   sur une copie non corrigée. Le bloc de style du gabarit n'est pas modifié ; une règle correctrice plus
   spécifique est ajoutée dans le petit bloc de style de contenu, et un test navigateur le vérifie. À reporter
   dans le gabarit.
2. **Texte figé dans `printDR`** : « Quatre pages, une par document » ne dépend pas du nombre de tracés ;
   remplacé ici par « Deux pages ». À rendre automatique dans le gabarit.
3. **Commentaire d'en-tête** : il contient la chaîne « <style> », ce qui piège une extraction naïve du bloc de
   style par expression régulière (le script de génération part donc de `<style>:root{`).
4. **Outil Texte** : le champ reçoit le focus au tick suivant le clic (`setTimeout`). Sans effet pour un
   utilisateur ; un test automatisé doit attendre ce focus avant de taper.

Le bloc de style de contenu ajouté après celui du gabarit ne contient que l'écriture des calculs (fractions,
racines), le bandeau de chapitre, la mise en forme des listes des documents et le correctif 1 ci-dessus.

## Vérifications effectuées

- `node --test tests/correction.test.js` : 56 tests, soit les 53 questions (réponse juste, saisies fausses,
  unités absentes, voisines ou converties, virgule ou point, séparateurs de milliers, notation scientifique,
  signes), les saisies vides, la cohérence du barème (points par partie, 145 min, critères des tracés,
  dépendances).
- `tests/navigateur.test.js` (Playwright, Chromium) : 6 parcours, tous réussis.
  - Accueil : seul écran visible, quatre chiffres clés, un seul bouton « Imprimer ma copie », aucune mention
    de diplôme, de session ni d'épreuve.
  - Entraînement : sujet entièrement juste = **20,0/20** (11 parties à 20,0) ; réponses verrouillées ;
    correction du tracé Q11.2 retenue jusqu'à Q11.1 ; chronomètre ; impression avec nom, mode, temps, note et
    deux images par tracé ; export PDF.
  - Entraînement : demi-point « unité manquante » et « unité incorrecte », réponse fausse, saisie vide refusée,
    note provisoire renormalisée sur les parties entamées.
  - Examen : note masquée, pas de bouton Valider, réponses modifiables ; impression « Copie non corrigée »
    sans aucune correction ; remise en deux temps annonçant les réponses vides ; verrouillage, corrections,
    grilles d'auto-évaluation, arrêt du chronomètre ; note pondérée attendue (19,0/20) et imprimée.
  - Tracés : flèche, ligne, gomme, annuler, texte, zoom, plein écran (et Échap), « Tout effacer » en deux temps ;
    fenêtre « Imprimer les DR » avec les deux feuilles DR1 et DR2.
  - Documents : rail, boutons des en-têtes, zoom, Échap ; à 420 px, bouton « Documents » et aucun
    défilement horizontal.
- Aucune erreur JavaScript dans aucun parcours.
