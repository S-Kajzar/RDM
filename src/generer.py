#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Génère la page « Résistance des matériaux » (index.html) : un accueil sur le modèle de la page
« Ajustements », deux cours (en cours d'édition) et deux exercices, Traction et compression
(?ex=traction) et Cisaillement (?ex=cisaillement), à partir du gabarit et du contenu décrit ici.

    python3 src/generer.py

Le bloc <style> du gabarit, le moteur de correction (Grading) et le moteur applicatif sont recopiés
tels quels ; seules les entrées propres au sujet du moteur applicatif sont remplacées, chaque
remplacement étant vérifié : DECOR, DR_NAMES, le texte de la fenêtre « Imprimer les DR » et
CONSEIL_MIN, lu dans window.__CONSEIL_MIN__ puisque la durée conseillée dépend de l'exercice ouvert.
Un petit script d'aiguillage, exécuté avant les moteurs, installe le contenu demandé par l'adresse.
"""
import base64
import copy
import html
import json
import pathlib
import re
import struct

ROOT = pathlib.Path(__file__).resolve().parent.parent
GABARIT = ROOT / "src" / "gabarit-exercice-interactif.html"
IMAGES = ROOT / "src" / "images"
SORTIE = ROOT / "index.html"
TITRE = "Résistance des matériaux"


# ============================================================ outils
def png(name):
    data = (IMAGES / f"{name}.png").read_bytes()
    w, h = struct.unpack(">II", data[16:24])
    return "data:image/png;base64," + base64.b64encode(data).decode(), w, h


def esc(s):
    return html.escape(s, quote=True)


def frac(a, b):
    return f'<span class="frac"><span>{a}</span><span>{b}</span></span>'


def sqrt(x):
    return f'<span class="sqrt"><span class="radix">√</span><span class="rad">{x}</span></span>'


def eq(s):
    return f'<div class="eq">{s}</div>'


def fr(x, d=1):
    s = f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
    return s


def figure(name, alt, caption, maxw):
    src, w, h = png(name)
    return (f'<figure class="fig" style="max-width:{maxw}px"><img src="{src}" alt="{esc(alt)}" '
            f'width="{w}" height="{h}"><figcaption>{caption}</figcaption></figure>')


def cor_img(name, alt, caption, maxw):
    src, w, h = png(name)
    return (f'<div class="cor-imgs"><figure style="max-width:{maxw}px"><img src="{src}" alt="{esc(alt)}" '
            f'width="{w}" height="{h}"><figcaption>{caption}</figcaption></figure></div>')


# ============================================================ unités
def unit(label, *accept):
    return {"label": label, "accept": list(accept)}


U = {
    "N": unit("N", "n", "newton", "newtons"),
    "kN": unit("kN", "kn", "kilonewton", "kilonewtons"),
    "mm": unit("mm", "mm", "millimetre", "millimetres"),
    "cm": unit("cm", "cm", "centimetre", "centimetres"),
    "m": unit("m", "m", "metre", "metres"),
    "um": unit("µm", "µm", "μm", "um", "micrometre", "micrometres", "micron", "microns"),
    "mm2": unit("mm²", "mm2", "millimetrecarre", "millimetrescarres", "millimetre2", "millimetres2"),
    "cm2": unit("cm²", "cm2", "centimetrecarre", "centimetrescarres"),
    "m2": unit("m²", "m2", "metrecarre", "metrescarres"),
    "MPa": unit("MPa", "mpa", "n/mm2", "nmm-2", "megapascal", "megapascals"),
    "Pa": unit("Pa", "pa", "pascal", "pascals", "n/m2", "nm-2"),
    "rad": unit("rad", "rad", "radian", "radians"),
    "mrad": unit("mrad", "mrad", "milliradian", "milliradians"),
    "urad": unit("µrad", "µrad", "μrad", "urad", "microradian", "microradians"),
}


def num(value, unit_key=None, absTol=None, relTol=None, variants=()):
    g = {"type": "num", "value": value}
    if absTol is not None:
        g["absTol"] = absTol
    if relTol is not None:
        g["relTol"] = relTol
    if unit_key:
        g["unit"] = U[unit_key]
    if variants:
        g["variants"] = [dict(v, strictUnit=True, unit=U[v.pop("u")]) for v in [dict(x) for x in variants]]
    return g


def var(value, u, absTol=None, relTol=None):
    v = {"value": value, "u": u}
    if absTol is not None:
        v["absTol"] = absTol
    if relTol is not None:
        v["relTol"] = relTol
    return v


YES = {"type": "yesno", "value": True}

# Consignes de saisie
UNITE = "Saisis la valeur <strong>avec son unité</strong> : l'unité vaut la moitié des points de la question."
H_C = "Arrondir au centième. " + UNITE
H_M = "Arrondir au millième. " + UNITE
H_U = "Arrondir à l'unité. " + UNITE
H_EX = "Valeur exacte. " + UNITE
H_C_SIGNE = "Arrondir au centième. Respecte la convention de signe de l'énoncé. " + UNITE
H_M_SIGNE = "Arrondir au millième. Respecte la convention de signe de l'énoncé. " + UNITE
H_EX_SIGNE = "Valeur exacte. Respecte la convention de signe de l'énoncé. " + UNITE
H_C_SANS = "Arrondir au centième. Nombre sans unité."
H_M_SANS = "Arrondir au millième. Nombre sans unité."
H_SCI_SANS = ("Écriture scientifique, mantisse arrondie au centième : saisis par exemple 1,23e-4 "
              "ou 1,23×10^-4 (avec le symbole ^). Nombre sans unité.")
H_SCI = ("Écriture scientifique, mantisse arrondie au centième : saisis par exemple 1,23e-4 "
         "ou 1,23×10^-4 (avec le symbole ^). " + UNITE)
H_ENTIER = "Donne un nombre entier, en chiffres."
H_OUINON = "Commence ta réponse par « oui » ou « non »."


# ============================================================ blocs de contenu
def Q(qid, stem, hint, grader, expected, why):
    return {"kind": "q", "id": qid, "stem": stem, "hint": hint, "grader": grader,
            "expected": expected, "why": why, "pts": 1}


def QBAR(label, docs, ans="ci-dessous"):
    return {"kind": "qbar", "label": label, "docs": docs, "ans": ans}


def SK(sid, label, bg, stem, criteria, deps, side, expl):
    return {"kind": "sk", "id": sid, "label": label, "bg": bg, "stem": stem,
            "criteria": criteria, "deps": deps, "side": side, "expl": expl}


def HTML(raw):
    return {"kind": "html", "html": raw}


def data_box(items):
    return ('<div class="data"><p class="data-title">Données</p><ul>' +
            "".join(f"<li>{i}</li>" for i in items) + "</ul></div>")


FDE = "<i>F</i><sub>DE</sub>"
LDE = "<i>L</i><sub>DE</sub>"
SDE = "<i>S</i><sub>DE</sub>"
TAU = "<i>τ</i>"
NS = "<i>n</i><sub>s</sub>"


# ============================================================ PARTIES
PARTS = []

# ------------------------------------------------------------ Partie 1
PARTS.append({
    "num": "1", "minutes": 30, "chapitre": "Traction et compression",
    "title": "Traction : fil de maintien d'un siège",
    "intro": [
        "<p>Un siège C est porté par une poutre AC, articulée en A sur un mur. La poutre est maintenue "
        "horizontale par un fil d'acier DE, accroché au mur en E, à la verticale de A, et à la poutre en D, "
        "à la verticale de B. Un homme est assis sur le siège.</p>"
        "<p>On cherche l'allongement du fil DE.</p>",
        figure("t1-siege-fil", "Poutre AC articulée en A sur un mur, maintenue par le fil DE ; un homme est assis "
               "sur le siège en C", "Figure 1 — Siège suspendu", 430),
        data_box([
            "Fil DE en acier, de diamètre <i>d</i> = 6 mm ; module d'élasticité <i>E</i> = 200 GPa",
            "Masse de l'homme <i>m</i> = 85 kg ; <i>g</i> = 9,81 m·s<sup>−2</sup>",
            "AB = 700 mm ; BC = 500 mm ; AE = 500 mm",
            "Poids de la poutre et du fil négligés ; liaison pivot parfaite en A ; le poids de l'homme "
            "s'applique en C",
        ]),
    ],
    "blocks": [
        QBAR("Q1.1 – Q1.4", ["DT1", "DT3"]),
        Q("q1_1", "Calculer le poids <i>P</i> exercé par l'homme sur le siège C.", H_C,
          num(833.85, "N", absTol=0.006, variants=[var(0.83385, "kN", absTol=0.000006)]),
          "<i>P</i> = 833,85 N",
          "<p>Le poids est l'action de la pesanteur sur l'homme :</p>" +
          eq("<i>P</i> = <i>m</i> · <i>g</i> = 85 × 9,81 = <b>833,85 N</b>") +
          "<p>C'est la charge verticale, dirigée vers le bas, que le siège transmet à la poutre en C.</p>"),
        Q("q1_2", "Quelle est la distance AC, bras de levier du poids <i>P</i> par rapport au pivot A ?", H_EX,
          num(1200, "mm", absTol=0.5, variants=[var(1.2, "m", absTol=0.0005), var(120, "cm", absTol=0.05)]),
          "AC = 1 200 mm",
          "<p>Le poids, vertical, s'applique en C et la poutre est horizontale : son bras de levier par rapport "
          "à A est la distance horizontale de A à C.</p>" +
          eq("AC = AB + BC = 700 + 500 = <b>1 200 mm</b>") + "<p>soit 1,2 m.</p>"),
        Q("q1_3", f"Calculer la longueur {LDE} du fil.", H_C,
          num(860.2325, "mm", absTol=0.011, variants=[var(0.8602325, "m", absTol=0.000011)]),
          f"{LDE} ≈ 860,23 mm",
          "<p>E est à la verticale de A et D à la verticale de B : le triangle AED est rectangle en A, de côtés "
          "AE = 500 mm (vertical) et AD = AB = 700 mm (horizontal). Le fil DE en est l'hypoténuse ; "
          "d'après le théorème de Pythagore :</p>" +
          eq(f"{LDE} = " + sqrt("AE² + AB²") + " = " + sqrt("500² + 700²") + " = " + sqrt("740 000") +
             " ≈ <b>860,23 mm</b>")),
        Q("q1_4", "En déduire sin <i>α</i>, <i>α</i> étant l'angle entre le fil DE et la poutre.", H_M_SANS,
          num(0.58124, absTol=0.0015),
          "sin <i>α</i> ≈ 0,581",
          "<p>Dans le triangle rectangle AED, l'angle <i>α</i> en D est opposé au côté AE :</p>" +
          eq("sin <i>α</i> = " + frac("AE", LDE) + " = " + frac("500", "860,23") + " ≈ <b>0,581</b>") +
          "<p>soit <i>α</i> ≈ 35,5°. Calculer sin <i>α</i> directement à partir des longueurs évite l'erreur "
          "due à un angle arrondi : avec <i>α</i> = 35°, on trouverait 0,574.</p>"),
        QBAR("Q1.5", ["DP1"], ans="sur la figure"),
        SK("sk_q1_5", "Q1.5", "POUTRE",
           "Isoler la poutre AC (siège compris) et représenter, sur la figure, les actions mécaniques extérieures "
           "qu'elle subit.",
           ["Le poids <i>P</i> est représenté en C, vertical, vers le bas.",
            "L'action du fil est appliquée en D, portée par la droite DE et orientée de D vers E (le fil tire sur "
            "la poutre).",
            "L'action du mur en A est représentée, soit par deux composantes horizontale et verticale, soit par une "
            "force oblique.",
            "Chaque flèche porte le nom de l'action qu'elle représente (<i>P</i>, " + FDE +
            ", <i>R</i><sub>A</sub> ou ses composantes)."],
           [],
           "<p>Outils : <b>Flèche</b> pour chaque action, <b>Texte</b> pour la nommer. La longueur des flèches "
           "n'est pas imposée : seuls le point d'application, la direction et le sens comptent.</p>"
           "<p>Pense aux trois liaisons de la poutre avec l'extérieur : le siège, le fil et le mur.</p>",
           "<p>La poutre AC isolée subit trois actions extérieures :</p><ul>"
           "<li><b><i>P</i></b>, poids de l'homme transmis par le siège : appliqué en C, vertical, vers le bas ;</li>"
           f"<li><b>{FDE}</b>, action du fil : appliquée en D et portée par la droite DE. Un fil ne peut que tirer : "
           "la flèche part de D en direction de E ;</li>"
           "<li><b><i>R</i><sub>A</sub></b>, action du mur au pivot A : sa direction est inconnue a priori. On la "
           "représente par ses composantes <i>R</i><sub>Ax</sub> et <i>R</i><sub>Ay</sub> dans un sens supposé ; "
           "le signe obtenu par le calcul donne le sens réel (ici, <i>R</i><sub>Ay</sub> est en réalité dirigée "
           "vers le bas, car la composante verticale de l'action du fil dépasse le poids).</li></ul>"
           "<p>L'angle <i>α</i> est repéré en D, entre le fil et la poutre. <i>R</i><sub>A</sub> passe par A : "
           f"elle n'a pas de moment par rapport à A. C'est pourquoi l'équilibre des moments en A donne {FDE} "
           "avec une seule équation (question suivante).</p>"),
        QBAR("Q1.6 – Q1.10", ["DT1", "DT3"]),
        Q("q1_6", f"Écrire l'équilibre des moments en A et en déduire la tension {FDE} du fil.", H_U,
          num(2459.33, "N", absTol=1.5, variants=[var(2.45933, "kN", absTol=0.0015)]),
          f"{FDE} ≈ 2 459 N (2 460 N avec sin <i>α</i> = 0,581)",
          f"<p>On décompose {FDE} en D : sa composante horizontale {FDE} · cos <i>α</i> passe par A et n'a pas de "
          f"moment ; sa composante verticale {FDE} · sin <i>α</i> a pour bras de levier AB. Le poids <i>P</i> a "
          "pour bras de levier AC.</p>" +
          eq(f"Σ<i>M</i><sub>/A</sub> = 0 ⇒ {FDE} · sin <i>α</i> · AB − <i>P</i> · AC = 0") +
          eq(f"{FDE} = " + frac("<i>P</i> · AC", "sin <i>α</i> · AB") + " = " +
             frac("833,85 × 1 200", "0,58124 × 700") + " ≈ <b>2 459 N</b>") +
          "<p>Avec sin <i>α</i> arrondi à 0,581, on trouve 2 460 N : les deux valeurs sont acceptées. Le fil est "
          "près de trois fois plus chargé que le poids de l'homme, car son bras de levier (AB · sin <i>α</i> ≈ "
          "407 mm) est bien plus court que celui du poids (1 200 mm).</p>" +
          cor_img("t1-isolement-poutre", "Poutre AC isolée : action du fil en D, composantes RAx et RAy en A, "
                  "poids de l'homme", "Poutre isolée (sens de <i>R</i><sub>Ax</sub> et <i>R</i><sub>Ay</sub> "
                  "supposés)", 400)),
        Q("q1_7", f"Calculer la section {SDE} du fil.", H_C,
          num(28.2743, "mm2", absTol=0.015,
              variants=[var(0.282743, "cm2", relTol=0.001), var(2.82743e-5, "m2", relTol=0.001)]),
          f"{SDE} ≈ 28,27 mm²",
          "<p>Le fil a une section circulaire pleine :</p>" +
          eq(f"{SDE} = " + frac("π · <i>d</i>²", "4") + " = " + frac("π × 6²", "4") + " ≈ <b>28,27 mm²</b>")),
        Q("q1_8", "En déduire la contrainte normale <i>σ</i><sub>DE</sub> dans le fil.", H_C,
          num(86.981, "MPa", absTol=0.075, variants=[var(86.981e6, "Pa", relTol=0.001)]),
          "<i>σ</i><sub>DE</sub> ≈ 86,98 MPa",
          f"<p>Le fil est sollicité en traction simple : son effort normal vaut <i>N</i> = {FDE}.</p>" +
          eq("<i>σ</i><sub>DE</sub> = " + frac("<i>N</i>", SDE) + " = " + frac("2 459,33", "28,27") +
             " ≈ <b>86,98 MPa</b>") +
          "<p>Avec <i>N</i> en newtons et <i>S</i> en mm², le résultat sort directement en N/mm², c'est-à-dire "
          "en MPa. Avec " + FDE + " = 2 460 N, on obtient 87,0 MPa : la tolérance couvre les deux chemins de "
          "calcul.</p>"),
        Q("q1_9", "Calculer la déformation <i>ε</i><sub>DE</sub> du fil à l'aide de la loi de Hooke.", H_SCI_SANS,
          num(4.3490e-4, relTol=0.003),
          "<i>ε</i><sub>DE</sub> ≈ 4,35 × 10<sup>−4</sup>",
          "<p>Loi de Hooke : <i>σ</i> = <i>E</i> · <i>ε</i>, donc <i>ε</i> = <i>σ</i> / <i>E</i>. Il faut exprimer "
          "<i>E</i> dans la même unité que <i>σ</i> : <i>E</i> = 200 GPa = 200 000 MPa.</p>" +
          eq("<i>ε</i><sub>DE</sub> = " + frac("86,98", "200 000") + " ≈ <b>4,35 × 10<sup>−4</sup></b>") +
          "<p>La déformation est le rapport de deux longueurs : elle n'a pas d'unité.</p>"),
        Q("q1_10", "En déduire l'allongement <i>δ</i><sub>DE</sub> du fil.", H_M,
          num(0.37412, "mm", absTol=0.001, variants=[var(374.12, "um", absTol=1)]),
          "<i>δ</i><sub>DE</sub> ≈ 0,374 mm",
          eq("<i>ε</i> = " + frac("<i>δ</i>", "<i>L</i>") + " ⇒ <i>δ</i><sub>DE</sub> = <i>ε</i><sub>DE</sub> · " +
             LDE + " = 4,349 × 10<sup>−4</sup> × 860,23 ≈ <b>0,374 mm</b>") +
          "<p>Vérification par la formule directe : <i>δ</i> = " + frac("<i>N</i> · <i>L</i>", "<i>E</i> · <i>S</i>") +
          " = " + frac("2 459,33 × 860,23", "200 000 × 28,27") + " ≈ 0,374 mm. Le fil s'allonge d'un peu plus "
          "d'un tiers de millimètre.</p>"),
    ],
})

# ------------------------------------------------------------ Partie 2
PARTS.append({
    "num": "2", "minutes": 10, "title": "Traction : barre de section rectangulaire",
    "intro": [
        "<p>Une barre de section rectangulaire, encastrée à une extrémité, est tirée à l'autre extrémité par un "
        "effort <i>F</i> dirigé selon son axe.</p>",
        figure("t2-barre", "Barre encastrée à gauche, tirée vers la droite par la force F", "Figure 2 — Barre en traction", 420),
        data_box([
            "Section rectangulaire 40 mm × 30 mm ; longueur <i>L</i> = 5 m",
            "<i>F</i> = 120 kN",
            "Contrainte admissible [<i>σ</i>] = 144 MPa ; <i>E</i> = 2,1 × 10<sup>5</sup> MPa",
        ]),
    ],
    "blocks": [
        QBAR("Q2.1 – Q2.4", ["DT1", "DT3"]),
        Q("q2_1", "Calculer l'aire <i>S</i> de la section droite de la barre.", H_EX,
          num(1200, "mm2", absTol=0.5, variants=[var(12, "cm2", absTol=0.005), var(0.0012, "m2", relTol=0.001)]),
          "<i>S</i> = 1 200 mm²",
          eq("<i>S</i> = 40 × 30 = <b>1 200 mm²</b>")),
        Q("q2_2", "Calculer la contrainte de traction <i>σ</i> dans la barre.", H_C,
          num(100, "MPa", absTol=0.006, variants=[var(1e8, "Pa", relTol=0.001)]),
          "<i>σ</i> = 100 MPa",
          "<p>L'effort normal vaut <i>N</i> = <i>F</i> = 120 kN = 120 000 N (traction).</p>" +
          eq("<i>σ</i> = " + frac("<i>N</i>", "<i>S</i>") + " = " + frac("120 000", "1 200") + " = <b>100 MPa</b>")),
        Q("q2_3", "La condition de résistance est-elle satisfaite ?", H_OUINON, YES,
          "Oui",
          "<p>Condition de résistance en traction : <i>σ</i> ≤ [<i>σ</i>]. Ici <i>σ</i> = 100 MPa ≤ [<i>σ</i>] = "
          "144 MPa : la condition est <b>satisfaite</b>. La barre travaille à 69 % de la contrainte admissible.</p>"),
        Q("q2_4", "Calculer l'allongement Δ<i>L</i> de la barre.", H_C,
          num(2.38095, "mm", absTol=0.006, variants=[var(0.00238095, "m", relTol=0.003)]),
          "Δ<i>L</i> ≈ 2,38 mm",
          "<p>Loi de Hooke : <i>σ</i> = <i>E</i> · <i>ε</i>, avec <i>ε</i> = Δ<i>L</i> / <i>L</i>.</p>" +
          eq("Δ<i>L</i> = " + frac("<i>σ</i> · <i>L</i>", "<i>E</i>") + " = " + frac("100 × 5 000", "210 000") +
             " ≈ <b>2,38 mm</b>") +
          "<p>Cohérence des unités : <i>σ</i> et <i>E</i> en MPa, <i>L</i> en mm, donc Δ<i>L</i> en mm.</p>"),
    ],
})

# ------------------------------------------------------------ Partie 3
PARTS.append({
    "num": "3", "minutes": 15, "title": "Compression : tube support de charge",
    "intro": [
        "<p>Un tube en acier, posé verticalement sur un socle, supporte une charge de masse <i>m</i>. On néglige "
        "le poids propre du tube.</p>"
        "<p><strong>Convention :</strong> en compression, l'effort normal, la contrainte et la variation de "
        "longueur sont comptés négativement.</p>",
        figure("t3-tube", "Tube vertical de diamètres de et di, de longueur L, supportant une masse de 5000 kg",
               "Figure 3 — Tube en compression", 400),
        data_box([
            "<i>m</i> = 5 000 kg ; <i>g</i> = 9,81 m·s<sup>−2</sup>",
            "Diamètre extérieur <i>d</i><sub>e</sub> = 50 mm ; diamètre intérieur <i>d</i><sub>i</sub> = "
            "<i>d</i><sub>e</sub> / 3",
            "Longueur <i>L</i> = 8 · <i>d</i><sub>e</sub> ; <i>E</i> = 2,1 × 10<sup>5</sup> MPa",
        ]),
    ],
    "blocks": [
        QBAR("Q3.1 – Q3.6", ["DT1", "DT3"]),
        Q("q3_1", "Calculer l'effort normal <i>N</i> dans le tube.", H_EX_SIGNE,
          num(-49050, "N", absTol=0.5, variants=[var(-49.05, "kN", absTol=0.0005)]),
          "<i>N</i> = −49 050 N",
          "<p>Le tube isolé subit, à son sommet, le poids de la charge <i>P</i> = <i>m</i> · <i>g</i> = "
          "5 000 × 9,81 = 49 050 N vers le bas, et à sa base l'action du socle, vers le haut. Ces deux forces "
          "opposées raccourcissent le tube : il est comprimé.</p>" +
          eq("<i>N</i> = −<i>P</i> = −<i>m</i> · <i>g</i> = <b>−49 050 N</b>") +
          "<p>Le signe fait partie de la réponse : +49 050 N désignerait une traction.</p>"),
        Q("q3_2", "Calculer le diamètre intérieur <i>d</i><sub>i</sub> du tube.", H_C,
          num(50 / 3, "mm", absTol=0.006, variants=[var(0.0166667, "m", absTol=0.000006)]),
          "<i>d</i><sub>i</sub> ≈ 16,67 mm",
          eq("<i>d</i><sub>i</sub> = " + frac("<i>d</i><sub>e</sub>", "3") + " = " + frac("50", "3") +
             " ≈ <b>16,67 mm</b>")),
        Q("q3_3", "Calculer la longueur <i>L</i> du tube.", H_EX,
          num(400, "mm", absTol=0.5, variants=[var(0.4, "m", absTol=0.0005), var(40, "cm", absTol=0.05)]),
          "<i>L</i> = 400 mm",
          eq("<i>L</i> = 8 · <i>d</i><sub>e</sub> = 8 × 50 = <b>400 mm</b>")),
        Q("q3_4", "Calculer l'aire <i>S</i> de la section droite du tube.", H_C,
          num(1745.329, "mm2", relTol=0.001,
              variants=[var(17.45329, "cm2", relTol=0.001), var(0.001745329, "m2", relTol=0.001)]),
          "<i>S</i> ≈ 1 745,33 mm²",
          "<p>La section droite est une couronne : le disque de diamètre <i>d</i><sub>e</sub>, privé du disque "
          "de diamètre <i>d</i><sub>i</sub>.</p>" +
          eq("<i>S</i> = " + frac("π · (<i>d</i><sub>e</sub>² − <i>d</i><sub>i</sub>²)", "4") + " = " +
             frac("π × (50² − 16,667²)", "4") + " = " + frac("π × 2 222,22", "4") + " ≈ <b>1 745,33 mm²</b>") +
          "<p>Avec <i>d</i><sub>i</sub> arrondi à 16,67 mm, on obtient 1 745,24 mm² : la tolérance couvre cet "
          "écart.</p>" +
          cor_img("t3-couronne", "Section en couronne de diamètres de et di", "Section droite du tube", 230)),
        Q("q3_5", "Calculer la contrainte normale <i>σ</i><sub>c</sub> dans le tube.", H_C_SIGNE,
          num(-28.1036, "MPa", relTol=0.001, variants=[var(-28.1036e6, "Pa", relTol=0.001)]),
          "<i>σ</i><sub>c</sub> ≈ −28,10 MPa",
          eq("<i>σ</i><sub>c</sub> = " + frac("<i>N</i>", "<i>S</i>") + " = " + frac("−49 050", "1 745,33") +
             " ≈ <b>−28,10 MPa</b>") +
          "<p>Le signe négatif traduit la compression. L'acier supporte largement une telle contrainte.</p>"),
        Q("q3_6", "Calculer la variation de longueur Δ<i>l</i> du tube sous la charge.", H_M_SIGNE,
          num(-0.053531, "mm", absTol=0.0005, variants=[var(-53.531, "um", absTol=0.5)]),
          "Δ<i>l</i> ≈ −0,054 mm",
          eq("Δ<i>l</i> = " + frac("<i>N</i> · <i>L</i>", "<i>E</i> · <i>S</i>") + " = " +
             frac("−49 050 × 400", "210 000 × 1 745,33") + " ≈ −0,0535 mm, soit <b>−0,054 mm</b> au millième") +
          "<p>Le tube raccourcit d'environ 54 µm : la déformation reste très faible "
          "(<i>ε</i> ≈ −1,3 × 10<sup>−4</sup>).</p>"),
    ],
})

# ------------------------------------------------------------ Partie 4
PARTS.append({
    "num": "4", "minutes": 10, "title": "Traction : dimensionnement d'un fer plat",
    "intro": [
        "<p>Une barre en fer plat, fixée à une extrémité, est tirée à l'autre par un effort <i>F</i>. On cherche "
        "sa largeur <i>a</i> pour que son allongement ne dépasse pas 2 mm, tout en respectant la condition de "
        "résistance.</p>",
        figure("t4-fer-plat", "Barre en fer plat de largeur a et d'épaisseur 10 mm, longue de 3 m, tirée par F",
               "Figure 4 — Barre en fer plat", 440),
        data_box([
            "Longueur <i>L</i> = 3 m ; épaisseur <i>b</i> = 10 mm",
            "<i>F</i> = 80 kN ; allongement maximal Δ<i>L</i><sub>max</sub> = 2 mm",
            "<i>E</i> = 2,1 × 10<sup>5</sup> MPa ; [<i>σ</i>] = 144 MPa",
        ]),
    ],
    "blocks": [
        QBAR("Q4.1 – Q4.4", ["DT1", "DT3"]),
        Q("q4_1", "Calculer la contrainte <i>σ</i><sub>max</sub> qui produit exactement l'allongement limite de "
          "2 mm.", H_EX,
          num(140, "MPa", absTol=0.5, variants=[var(140e6, "Pa", relTol=0.001)]),
          "<i>σ</i><sub>max</sub> = 140 MPa",
          "<p>Loi de Hooke : <i>σ</i> = <i>E</i> · <i>ε</i> = <i>E</i> · Δ<i>L</i> / <i>L</i>.</p>" +
          eq("<i>σ</i><sub>max</sub> = " + frac("<i>E</i> · Δ<i>L</i><sub>max</sub>", "<i>L</i>") + " = " +
             frac("210 000 × 2", "3 000") + " = <b>140 MPa</b>") +
          "<p>Au-delà de cette contrainte, la barre s'allongerait de plus de 2 mm.</p>"),
        Q("q4_2", "La contrainte <i>σ</i><sub>max</sub> respecte-t-elle la condition de résistance ?", H_OUINON, YES,
          "Oui",
          "<p><i>σ</i><sub>max</sub> = 140 MPa ≤ [<i>σ</i>] = 144 MPa : <b>oui</b>. La condition d'allongement "
          "est donc plus sévère que la condition de résistance, qui autoriserait 144 MPa : c'est elle qui "
          "dimensionne la barre.</p>"),
        Q("q4_3", "Calculer la largeur minimale <i>a</i><sub>min</sub> de la barre.", H_C,
          num(57.1429, "mm", absTol=0.006),
          "<i>a</i><sub>min</sub> ≈ 57,14 mm",
          "<p>La contrainte ne doit pas dépasser <i>σ</i><sub>max</sub> :</p>" +
          eq(frac("<i>F</i>", "<i>a</i> · <i>b</i>") + " ≤ <i>σ</i><sub>max</sub> ⇒ <i>a</i> ≥ " +
             frac("<i>F</i>", "<i>σ</i><sub>max</sub> · <i>b</i>") + " = " + frac("80 000", "140 × 10") +
             " ≈ <b>57,14 mm</b>") +
          "<p>Pour comparaison, la seule condition de résistance donnerait <i>a</i> ≥ 80 000 / (144 × 10) ≈ "
          "55,56 mm.</p>"),
        Q("q4_4", "À l'aide du DT3, choisir la largeur normalisée <i>a</i> de la barre.", H_EX,
          num(60, "mm", absTol=0.01, variants=[var(6, "cm", absTol=0.001)]),
          "<i>a</i> = 60 mm",
          "<p>On retient la largeur de la gamme immédiatement supérieure à <i>a</i><sub>min</sub> = 57,14 mm : "
          "dans le DT3, la gamme passe de 50 à 60 mm, donc <b><i>a</i> = 60 mm</b> (fer plat 60 × 10). "
          "Une largeur de 50 mm ne conviendrait pas : la barre s'allongerait de plus de 2 mm.</p>"
          "<p>Vérification : <i>σ</i> = 80 000 / (60 × 10) ≈ 133,3 MPa et Δ<i>L</i> = 133,3 × 3 000 / 210 000 ≈ "
          "1,90 mm ≤ 2 mm.</p>"),
    ],
})

# ------------------------------------------------------------ Partie 5
PARTS.append({
    "num": "5", "minutes": 10, "chapitre": "Cisaillement",
    "title": "Cisaillement : goupille d'une chape",
    "intro": [
        "<p>Un levier est articulé sur une chape par une goupille. Il reçoit deux efforts perpendiculaires "
        "entre eux. On cherche la contrainte de cisaillement dans la goupille, supposée uniformément répartie "
        "dans chaque section cisaillée.</p>",
        figure("c1-chape-goupille", "Levier articulé sur une chape par une goupille, soumis à un effort vertical "
               "de 35 kN et à un effort horizontal de 45 kN", "Figure 5 — Levier et chape", 300),
        data_box([
            "Diamètre de la goupille <i>d</i> = 35 mm",
            "Efforts appliqués au levier : 35 kN (vertical) et 45 kN (horizontal)",
        ]),
    ],
    "blocks": [
        QBAR("Q5.1 – Q5.5", ["DT2", "DT3"]),
        Q("q5_1", "Calculer l'intensité <i>F</i> de la résultante des deux efforts appliqués, transmise à la "
          "goupille.", H_C,
          num(57.00877, "kN", absTol=0.006, variants=[var(57008.77, "N", absTol=6)]),
          "<i>F</i> ≈ 57,01 kN",
          "<p>Le levier est en équilibre sous l'action des deux efforts et de la goupille : la goupille reprend "
          "donc la résultante de ces deux efforts. Ils sont perpendiculaires ; on applique le théorème de "
          "Pythagore :</p>" +
          eq("<i>F</i> = " + sqrt("35² + 45²") + " = " + sqrt("3 250") + " ≈ <b>57,01 kN</b>")),
        Q("q5_2", "Combien de sections de la goupille sont cisaillées ?", H_ENTIER,
          num(2, absTol=0),
          "2 (double cisaillement)",
          "<p>La goupille traverse les deux flasques de la chape et le levier placé entre elles. Elle risque "
          "d'être coupée à chaque interface flasque / levier, soit <b>deux sections</b> : c'est un <b>double "
          "cisaillement</b>.</p>"),
        Q("q5_3", "Calculer l'effort tranchant <i>T</i> supporté par une section cisaillée.", H_C,
          num(28.50439, "kN", absTol=0.006, variants=[var(28504.39, "N", absTol=6)]),
          "<i>T</i> ≈ 28,50 kN",
          "<p>L'effort <i>F</i> se partage également entre les deux sections cisaillées :</p>" +
          eq("<i>T</i> = " + frac("<i>F</i>", "2") + " = " + frac("57,01", "2") + " ≈ <b>28,50 kN</b>")),
        Q("q5_4", "Calculer l'aire <i>S</i> de la section droite de la goupille.", H_C,
          num(962.1128, "mm2", relTol=0.001, variants=[var(9.621128, "cm2", relTol=0.001)]),
          "<i>S</i> ≈ 962,11 mm²",
          eq("<i>S</i> = " + frac("π · <i>d</i>²", "4") + " = " + frac("π × 35²", "4") + " ≈ <b>962,11 mm²</b>")),
        Q("q5_5", f"En déduire la contrainte de cisaillement {TAU} dans la goupille.", H_C,
          num(29.62687, "MPa", relTol=0.001, variants=[var(29.62687e6, "Pa", relTol=0.001)]),
          f"{TAU} ≈ 29,63 MPa",
          "<p>On convertit <i>T</i> en newtons pour obtenir directement des MPa (1 MPa = 1 N/mm²) :</p>" +
          eq(f"{TAU} = " + frac("<i>T</i>", "<i>S</i>") + " = " + frac("28 504,39", "962,11") +
             " ≈ <b>29,63 MPa</b>")),
    ],
})

# ------------------------------------------------------------ Partie 6
PARTS.append({
    "num": "6", "minutes": 15, "title": "Cisaillement : pince à goupille",
    "intro": [
        "<p>Une pince est actionnée par deux charges <i>P</i> appliquées sur les poignées. On cherche la force "
        "de serrage maximale <i>C</i> dans les mâchoires, puis la charge <i>P</i> admissible si l'on impose un "
        "coefficient de sécurité par rapport à la rupture de la goupille.</p>",
        figure("c2-pince", "Pince : charges P sur les poignées à la distance a de la goupille, force de serrage à "
               "la distance b", "Figure 6 — Pince", 420),
        data_box([
            "<i>a</i> = 76 mm (charge <i>P</i> → goupille) ; <i>b</i> = 25,5 mm (goupille → serrage)",
            "Diamètre de la goupille <i>d</i> = 5 mm ; contrainte ultime de cisaillement "
            "<i>τ</i><sub>ult</sub> = 345 MPa",
            f"Coefficient de sécurité {NS} = 3,0",
        ]),
    ],
    "blocks": [
        QBAR("Q6.1 – Q6.6", ["DP1", "DT2", "DT3"]),
        Q("q6_1", "En isolant une branche de la pince, écrire l'équilibre des moments par rapport à l'axe de la "
          "goupille, puis calculer le rapport <i>C</i> / <i>P</i>.", H_C_SANS,
          num(2.98039, absTol=0.006),
          "<i>C</i> / <i>P</i> ≈ 2,98",
          "<p>Branche isolée : elle subit la charge <i>P</i> (bras de levier <i>a</i>), la réaction de la mâchoire "
          "opposée <i>C</i> (bras de levier <i>b</i>) et la réaction <i>R</i> de la goupille, qui passe par l'axe "
          "et n'a donc pas de moment.</p>" +
          cor_img("c2-branche-isolee", "Branche isolée : P vers le haut à gauche, R vers le bas à la goupille, C "
                  "vers le haut à droite", "Branche isolée", 380) +
          eq("Σ<i>M</i><sub>/goupille</sub> = 0 ⇒ <i>C</i> · <i>b</i> − <i>P</i> · <i>a</i> = 0 ⇒ " +
             frac("<i>C</i>", "<i>P</i>") + " = " + frac("<i>a</i>", "<i>b</i>") + " = " + frac("76", "25,5") +
             " ≈ <b>2,98</b>") +
          "<p>La pince multiplie par près de 3 l'effort exercé par la main.</p>"),
        Q("q6_2", "Combien de sections de la goupille sont cisaillées ?", H_ENTIER,
          num(1, absTol=0),
          "1 (simple cisaillement)",
          "<p>Les deux branches de la pince se croisent au niveau de la goupille : celle-ci n'est cisaillée que "
          "dans le plan de contact entre les deux branches, soit <b>une seule section</b> (simple cisaillement). "
          "L'effort tranchant dans la goupille est donc égal à la réaction <i>R</i> qu'elle exerce sur une "
          "branche.</p>"),
        Q("q6_3", "Calculer l'effort tranchant ultime <i>T</i><sub>ult</sub> que peut supporter la goupille avant "
          "rupture.", H_C,
          num(6774.059, "N", relTol=0.001, variants=[var(6.774059, "kN", relTol=0.001)]),
          "<i>T</i><sub>ult</sub> ≈ 6 774,06 N",
          "<p>La rupture survient quand la contrainte de cisaillement atteint <i>τ</i><sub>ult</sub> dans "
          "l'unique section cisaillée :</p>" +
          eq("<i>S</i> = " + frac("π × 5²", "4") + " ≈ 19,63 mm²") +
          eq("<i>T</i><sub>ult</sub> = <i>τ</i><sub>ult</sub> · <i>S</i> = 345 × 19,635 ≈ <b>6 774,06 N</b>")),
        Q("q6_4", "Calculer la force de serrage maximale <i>C</i><sub>ult</sub> dans les mâchoires.", H_C,
          num(5072.202, "N", relTol=0.001, variants=[var(5.072202, "kN", relTol=0.001)]),
          "<i>C</i><sub>ult</sub> ≈ 5 072,20 N",
          "<p>Équilibre des forces verticales de la branche isolée : <i>P</i> + <i>C</i> − <i>R</i> = 0, soit "
          "<i>R</i> = <i>P</i> + <i>C</i>. Avec <i>P</i> = <i>C</i> · <i>b</i> / <i>a</i> :</p>" +
          eq("<i>T</i> = <i>R</i> = <i>C</i> · (1 + " + frac("<i>b</i>", "<i>a</i>") + ") ⇒ <i>C</i><sub>ult</sub> = " +
             frac("<i>T</i><sub>ult</sub>", "1 + <i>b</i>/<i>a</i>") + " = " + frac("6 774,06", "1 + 25,5/76") +
             " ≈ <b>5 072,20 N</b>")),
        Q("q6_5", "Calculer la charge <i>P</i><sub>ult</sub> appliquée sur les poignées qui provoque la rupture "
          "de la goupille.", H_C,
          num(1701.857, "N", relTol=0.001, variants=[var(1.701857, "kN", relTol=0.001)]),
          "<i>P</i><sub>ult</sub> ≈ 1 701,86 N",
          eq("<i>T</i> = <i>R</i> = <i>P</i> · (1 + " + frac("<i>a</i>", "<i>b</i>") + ") ⇒ <i>P</i><sub>ult</sub> = " +
             frac("<i>T</i><sub>ult</sub>", "1 + <i>a</i>/<i>b</i>") + " = " + frac("6 774,06", "1 + 76/25,5") +
             " ≈ <b>1 701,86 N</b>") +
          "<p>Vérification : <i>P</i><sub>ult</sub> + <i>C</i><sub>ult</sub> = 1 701,86 + 5 072,20 = 6 774,06 N "
          "= <i>T</i><sub>ult</sub>.</p>"),
        Q("q6_6", f"Calculer la charge admissible <i>P</i><sub>adm</sub> avec le coefficient de sécurité {NS} = 3,0.",
          H_C,
          num(567.2857, "N", relTol=0.001, variants=[var(0.5672857, "kN", relTol=0.001)]),
          "<i>P</i><sub>adm</sub> ≈ 567,29 N",
          eq("<i>P</i><sub>adm</sub> = " + frac("<i>P</i><sub>ult</sub>", NS) + " = " + frac("1 701,86", "3") +
             " ≈ <b>567,29 N</b>") +
          "<p>Une main exerce couramment 200 à 400 N : la pince est utilisable sans risque de rompre la "
          "goupille.</p>"),
    ],
})

# ------------------------------------------------------------ Partie 7
PARTS.append({
    "num": "7", "minutes": 10, "title": "Cisaillement : roue d'échafaudage",
    "intro": [
        "<p>La roue de support d'un échafaudage est maintenue sur le pied par une goupille qui traverse les deux "
        "tubes emboîtés. La roue reçoit du sol un effort vertical. On cherche la contrainte de cisaillement dans "
        "la goupille.</p>",
        figure("c3-roue", "Roue d'échafaudage fixée au pied par une goupille, force de 5 kN appliquée par le sol",
               "Figure 7 — Roue d'échafaudage", 170),
        data_box([
            "Diamètre de la goupille <i>d</i> = 6 mm",
            "Effort du sol sur la roue <i>F</i> = 5 kN",
        ]),
    ],
    "blocks": [
        QBAR("Q7.1 – Q7.4", ["DT2", "DT3"]),
        Q("q7_1", "Combien de sections de la goupille sont cisaillées ?", H_ENTIER,
          num(2, absTol=0),
          "2 (double cisaillement)",
          "<p>La goupille traverse de part en part les deux tubes emboîtés (pied de l'échafaudage et support de "
          "roue). L'effort passe de l'un à l'autre de chaque côté : <b>deux sections cisaillées</b>, c'est un "
          "double cisaillement.</p>"),
        Q("q7_2", "Calculer l'effort tranchant <i>T</i> supporté par une section cisaillée.", H_C,
          num(2.5, "kN", absTol=0.006, variants=[var(2500, "N", absTol=0.5)]),
          "<i>T</i> = 2,50 kN",
          eq("<i>T</i> = " + frac("<i>F</i>", "2") + " = " + frac("5", "2") + " = <b>2,50 kN</b>")),
        Q("q7_3", "Calculer l'aire <i>S</i> de la section droite de la goupille.", H_C,
          num(28.2743, "mm2", relTol=0.001, variants=[var(0.282743, "cm2", relTol=0.001)]),
          "<i>S</i> ≈ 28,27 mm²",
          eq("<i>S</i> = " + frac("π · <i>d</i>²", "4") + " = " + frac("π × 6²", "4") + " ≈ <b>28,27 mm²</b>") +
          "<p>Travailler en millimètres et en newtons évite les puissances de 10 : on obtient directement des "
          "MPa.</p>"),
        Q("q7_4", f"En déduire la contrainte de cisaillement {TAU} dans la goupille.", H_C,
          num(88.41941, "MPa", relTol=0.001, variants=[var(88.41941e6, "Pa", relTol=0.001)]),
          f"{TAU} ≈ 88,42 MPa",
          eq(f"{TAU} = " + frac("<i>T</i>", "<i>S</i>") + " = " + frac("2 500", "28,27") + " ≈ <b>88,42 MPa</b>") +
          "<p>Attention aux arrondis intermédiaires : arrondir <i>S</i> à 28 mm² fausserait le résultat de près "
          "de 1 %.</p>"),
    ],
})

# ------------------------------------------------------------ Partie 8
PARTS.append({
    "num": "8", "minutes": 10, "title": "Cisaillement : platine boulonnée",
    "intro": [
        "<p>Une platine est fixée contre une poutre par quatre boulons. Elle supporte une charge verticale "
        "<i>P</i>, que l'on suppose répartie de manière égale entre les quatre boulons. On cherche la contrainte "
        "de cisaillement dans les boulons.</p>",
        figure("c4-platine", "Platine fixée par quatre boulons sur une poutre en bois, charge P verticale",
               "Figure 8 — Platine boulonnée", 290),
        data_box([
            "Quatre boulons de diamètre <i>d</i> = 10 mm",
            "Charge <i>P</i> = 10 kN",
        ]),
    ],
    "blocks": [
        QBAR("Q8.1 – Q8.4", ["DT2", "DT3"]),
        Q("q8_1", "Combien de sections de chaque boulon sont cisaillées ?", H_ENTIER,
          num(1, absTol=0),
          "1 (simple cisaillement)",
          "<p>Chaque boulon traverse la platine et la poutre : il n'est cisaillé que dans le plan de contact "
          "platine / poutre, soit <b>une section</b> par boulon (simple cisaillement).</p>"),
        Q("q8_2", "Calculer l'effort tranchant <i>T</i><sub>b</sub> supporté par chaque boulon.", H_C,
          num(2.5, "kN", absTol=0.006, variants=[var(2500, "N", absTol=0.5)]),
          "<i>T</i><sub>b</sub> = 2,50 kN",
          "<p>Chaque boulon, cisaillé dans une seule section, reprend un quart de la charge :</p>" +
          eq("<i>T</i><sub>b</sub> = " + frac("<i>P</i>", "4") + " = " + frac("10", "4") + " = <b>2,50 kN</b>")),
        Q("q8_3", "Calculer l'aire <i>S</i> de la section droite d'un boulon.", H_C,
          num(78.53982, "mm2", relTol=0.001, variants=[var(0.7853982, "cm2", relTol=0.001)]),
          "<i>S</i> ≈ 78,54 mm²",
          eq("<i>S</i> = " + frac("π · <i>d</i>²", "4") + " = " + frac("π × 10²", "4") + " ≈ <b>78,54 mm²</b>")),
        Q("q8_4", f"En déduire la contrainte de cisaillement {TAU} dans chaque boulon.", H_C,
          num(31.83099, "MPa", relTol=0.001, variants=[var(31.83099e6, "Pa", relTol=0.001)]),
          f"{TAU} ≈ 31,83 MPa",
          eq(f"{TAU} = " + frac("<i>T</i><sub>b</sub>", "<i>S</i>") + " = " + frac("2 500", "78,54") +
             " ≈ <b>31,83 MPa</b>")),
    ],
})

# ------------------------------------------------------------ Partie 9
PARTS.append({
    "num": "9", "minutes": 10, "title": "Cisaillement : éclissage par plaques et boulons",
    "intro": [
        "<p>Deux barres tirées par un effort <i>F</i> sont assemblées bout à bout par deux plaques "
        "rectangulaires, une au-dessus et une au-dessous, et par quatre boulons, deux par barre. On cherche le "
        "diamètre minimal des boulons.</p>",
        figure("c5-eclissage", "Deux barres bout à bout reliées par deux plaques et quatre boulons, efforts F "
               "opposés", "Figure 9 — Éclissage", 440),
        data_box([
            "<i>F</i> = 70 kN",
            "Contrainte limite de cisaillement des boulons <i>τ</i><sub>l</sub> = 400 MPa",
            f"Coefficient de sécurité {NS} = 3",
        ]),
    ],
    "blocks": [
        QBAR("Q9.1 – Q9.3", ["DT2", "DT3"]),
        Q("q9_1", "Pour une barre, combien de sections cisaillées (tous boulons confondus) transmettent l'effort "
          "<i>F</i> aux plaques ?", H_ENTIER,
          num(4, absTol=0),
          "4",
          "<p>Chaque barre est traversée par deux boulons. Chaque boulon est cisaillé à l'interface avec la plaque "
          "du dessus et à l'interface avec la plaque du dessous (double cisaillement). On a donc 2 × 2 = "
          "<b>4 sections</b>, chacune reprenant <i>F</i> / 4.</p>" +
          cor_img("c5-coupe-boulon", "Coupe d'un boulon : la barre tirée par P, chaque plaque reprend P/4 à "
                  "travers une section cisaillée S", "Coupe au droit d'un boulon (ici <i>P</i> = <i>F</i>)", 380)),
        Q("q9_2", "Calculer la contrainte admissible de cisaillement <i>τ</i><sub>adm</sub>.", H_C,
          num(133.3333, "MPa", absTol=0.006, variants=[var(133.3333e6, "Pa", relTol=0.001)]),
          "<i>τ</i><sub>adm</sub> ≈ 133,33 MPa",
          eq("<i>τ</i><sub>adm</sub> = " + frac("<i>τ</i><sub>l</sub>", NS) + " = " + frac("400", "3") +
             " ≈ <b>133,33 MPa</b>")),
        Q("q9_3", "Calculer le diamètre minimal <i>d</i> des boulons.", H_C,
          num(12.92721, "mm", relTol=0.001, variants=[var(0.01292721, "m", relTol=0.001)]),
          "<i>d</i> ≈ 12,93 mm",
          "<p>Condition de résistance sur les quatre sections cisaillées :</p>" +
          eq(frac("<i>F</i>", "4 · <i>S</i>") + " ≤ <i>τ</i><sub>adm</sub> avec <i>S</i> = " +
             frac("π · <i>d</i>²", "4") + " ⇒ " + frac("<i>F</i>", "π · <i>d</i>²") + " ≤ <i>τ</i><sub>adm</sub>") +
          eq("<i>d</i> ≥ " + sqrt(frac("<i>F</i>", "π · <i>τ</i><sub>adm</sub>")) + " = " +
             sqrt(frac("70 000", "π × 133,33")) + " ≈ <b>12,93 mm</b>") +
          "<p>Formule équivalente sans arrondi intermédiaire : <i>d</i> ≥ √(<i>F</i> · " + NS +
          " / (π · <i>τ</i><sub>l</sub>)) = √(70 000 × 3 / (π × 400)). En pratique, on retient ensuite le "
          "diamètre normalisé immédiatement supérieur.</p>"),
    ],
})

# ------------------------------------------------------------ Partie 10
PARTS.append({
    "num": "10", "minutes": 10, "title": "Cisaillement : plaque vissée sur une poutre",
    "intro": [
        "<p>Une plaque est fixée sur une poutre en bois par trois vis en acier et doit supporter une charge "
        "verticale. On cherche l'aire minimale de la section de chaque vis.</p>",
        figure("c6-plaque-vis", "Plaque fixée par trois vis sur une poutre en bois, charge de 100 kN vers le bas",
               "Figure 10 — Plaque vissée", 270),
        data_box([
            "Trois vis ; charge <i>P</i> = 100 kN, répartie également entre les vis",
            "Contrainte ultime de cisaillement de l'acier <i>τ</i><sub>ult</sub> = 380 MPa",
            f"Coefficient de sécurité {NS} = 3,5",
        ]),
    ],
    "blocks": [
        QBAR("Q10.1 – Q10.4", ["DT2", "DT3"]),
        Q("q10_1", "Combien de sections de chaque vis sont cisaillées ?", H_ENTIER,
          num(1, absTol=0),
          "1 (simple cisaillement)",
          "<p>Chaque vis traverse la plaque et pénètre dans la poutre : elle n'est cisaillée que dans le plan de "
          "contact plaque / poutre, soit <b>une section</b> (simple cisaillement).</p>"),
        Q("q10_2", "Calculer la contrainte admissible de cisaillement <i>τ</i><sub>adm</sub> de l'acier.", H_C,
          num(108.5714, "MPa", absTol=0.006, variants=[var(108.5714e6, "Pa", relTol=0.001)]),
          "<i>τ</i><sub>adm</sub> ≈ 108,57 MPa",
          eq("<i>τ</i><sub>adm</sub> = " + frac("<i>τ</i><sub>ult</sub>", NS) + " = " + frac("380", "3,5") +
             " ≈ <b>108,57 MPa</b>")),
        Q("q10_3", "Calculer l'effort tranchant <i>T</i><sub>v</sub> supporté par chaque vis.", H_C,
          num(33.33333, "kN", absTol=0.006, variants=[var(33333.33, "N", absTol=6)]),
          "<i>T</i><sub>v</sub> ≈ 33,33 kN",
          "<p>La charge se répartit également entre les trois vis, chacune cisaillée dans une seule section :</p>" +
          cor_img("c6-plaque-isolee", "Plaque isolée : la charge P vers le bas est reprise par trois efforts P/3 "
                  "au niveau des vis", "Plaque isolée", 210) +
          eq("<i>T</i><sub>v</sub> = " + frac("<i>P</i>", "3") + " = " + frac("100", "3") + " ≈ <b>33,33 kN</b>")),
        Q("q10_4", "Calculer l'aire minimale <i>S</i> de la section de chaque vis.", H_C,
          num(307.0175, "mm2", relTol=0.001, variants=[var(3.070175, "cm2", relTol=0.001)]),
          "<i>S</i> ≈ 307,02 mm²",
          eq(frac("<i>T</i><sub>v</sub>", "<i>S</i>") + " ≤ <i>τ</i><sub>adm</sub> ⇒ <i>S</i> ≥ " +
             frac("<i>T</i><sub>v</sub>", "<i>τ</i><sub>adm</sub>") + " = " +
             frac("<i>P</i> · " + NS, "3 · <i>τ</i><sub>ult</sub>") + " = " + frac("100 000 × 3,5", "3 × 380") +
             " ≈ <b>307,02 mm²</b>") +
          "<p>À titre indicatif, cela correspond à un diamètre d'environ 19,77 mm.</p>"),
    ],
})

# ------------------------------------------------------------ Partie 11
PARTS.append({
    "num": "11", "minutes": 15, "title": "Cisaillement : axe de chape",
    "intro": [
        "<p>L'axe de la chape ci-dessous relie une tige à une fourche et doit transmettre l'effort <i>P</i>. "
        "On dimensionne l'axe, puis on calcule sa déformation.</p>",
        figure("c7-axe-chape", "Chape : tige tirée par P reliée à une fourche par un axe de diamètre d",
               "Figure 11 — Axe de chape", 420),
        data_box([
            "<i>P</i> = 13 kN",
            "Contrainte limite de cisaillement du matériau de l'axe <i>τ</i><sub>l</sub> = 175 MPa",
            "Module d'élasticité transversal <i>G</i> = 90 000 MPa",
            f"Coefficient de sécurité {NS} = 2,5",
        ]),
    ],
    "blocks": [
        QBAR("Q11.1", ["DT2"]),
        Q("q11_1", "Combien de sections de l'axe sont cisaillées ?", H_ENTIER,
          num(2, absTol=0),
          "2 (double cisaillement)",
          "<p>L'axe traverse les deux branches de la fourche et la tige placée entre elles : il est cisaillé à "
          "chaque interface tige / branche, soit <b>deux sections</b> (double cisaillement). Chaque section "
          "transmet <i>P</i> / 2.</p>"),
        QBAR("Q11.2", ["DT2"], ans="sur la figure"),
        SK("sk_q11_2", "Q11.2", "AXE",
           "Repérer, sur la figure, les sections cisaillées de l'axe et noter l'effort tranchant que transmet "
           "chacune d'elles.",
           ["Deux sections cisaillées sont repérées, et deux seulement.",
            "Chaque section est placée dans un plan de contact entre la tige et une branche de la fourche (bord "
            "supérieur et bord inférieur de la tige).",
            "Chaque section coupe l'axe en travers, perpendiculairement à sa longueur (trait horizontal sur la "
            "figure).",
            "L'effort transmis par chaque section est noté <i>P</i> / 2 (soit 6,5 kN)."],
           ["q11_1"],
           "<p>Outils : <b>Ligne</b> pour tracer chaque section cisaillée, <b>Texte</b> pour la nommer et noter "
           "l'effort qu'elle transmet.</p><p>Une section cisaillée est un plan où deux pièces voisines tendent à "
           "faire glisser l'axe en sens contraires.</p>",
           "<p>La tige, tirée vers la gauche, entraîne la partie centrale de l'axe ; les deux branches de la "
           "fourche, tirées vers la droite, retiennent ses extrémités. L'axe tend donc à être coupé dans les "
           "<b>deux plans de contact tige / fourche</b>, qui correspondent aux bords supérieur et inférieur de la "
           "tige sur la figure.</p><p>Chaque section coupe l'axe perpendiculairement à sa longueur et transmet "
           "<i>T</i> = <i>P</i> / 2 = 6,5 kN : c'est un double cisaillement.</p>"),
        QBAR("Q11.3 – Q11.5", ["DT2", "DT3"]),
        Q("q11_3", "Calculer le diamètre minimal <i>d</i> de l'axe.", H_C,
          num(10.87333, "mm", relTol=0.001, variants=[var(0.01087333, "m", relTol=0.001)]),
          "<i>d</i> ≈ 10,87 mm",
          "<p>En double cisaillement, chaque section reprend <i>P</i> / 2 :</p>" +
          eq(frac("<i>P</i>", "2 · <i>S</i>") + " ≤ " + frac("<i>τ</i><sub>l</sub>", NS) + " avec <i>S</i> = " +
             frac("π · <i>d</i>²", "4")) +
          eq("<i>d</i> ≥ " + sqrt(frac("2 · <i>P</i> · " + NS, "π · <i>τ</i><sub>l</sub>")) + " = " +
             sqrt(frac("2 × 13 000 × 2,5", "π × 175")) + " ≈ <b>10,87 mm</b>")),
        Q("q11_4", f"Pour un axe de ce diamètre minimal, calculer la contrainte de cisaillement {TAU} dans l'axe.",
          "Arrondir au centième, en utilisant le diamètre trouvé à la question précédente. " + UNITE,
          num(70, "MPa", absTol=0.1, variants=[var(70e6, "Pa", relTol=0.0015)]),
          f"{TAU} = 70,00 MPa (70,04 MPa avec <i>d</i> = 10,87 mm)",
          eq(f"{TAU} = " + frac("<i>P</i>", "2 · <i>S</i>") + " = " + frac("13 000", "2 × π × 10,87² / 4") +
             " ≈ <b>70,04 MPa</b>") +
          "<p>Sans arrondir <i>d</i>, on trouve exactement " + TAU + " = <i>τ</i><sub>l</sub> / " + NS +
          " = 175 / 2,5 = 70 MPa : le diamètre minimal est justement celui pour lequel la contrainte atteint la "
          "contrainte admissible. Toute valeur entre 69,90 et 70,10 MPa est acceptée.</p>"),
        Q("q11_5", "Calculer la déformation angulaire (glissement) <i>γ</i> correspondante.", H_SCI,
          num(7.77778e-4, "rad", relTol=0.002,
              variants=[var(777.778, "urad", relTol=0.002), var(0.777778, "mrad", relTol=0.002)]),
          "<i>γ</i> ≈ 7,78 × 10<sup>−4</sup> rad",
          "<p>Loi de Hooke en cisaillement : " + TAU + " = <i>G</i> · <i>γ</i>.</p>" +
          eq("<i>γ</i> = " + frac(TAU, "<i>G</i>") + " = " + frac("70", "90 000") +
             " ≈ <b>7,78 × 10<sup>−4</sup> rad</b>") +
          "<p>Le glissement est parfois noté <i>δ</i>. Ordre de grandeur : moins d'un millième de radian, soit "
          "environ 0,045°.</p>"),
    ],
})


# ============================================================ PARTIES — EXERCICE 1.1 (niveau bac pro)
# Documents propres à cet exercice (DP1, DT1 à DT3), écrits directement sous leur nom final.
H_LIRE = "Lis la valeur dans le DT2. " + UNITE
RPE = "<i>R</i><sub>pe</sub>"
RE = "<i>R</i><sub>e</sub>"
SIG = "<i>σ</i>"
PARTS_BP = []

PARTS_BP.append({
    "num": "1", "minutes": 10, "title": "Treuil de levage : coefficient de sécurité d'un câble",
    "intro": [
        "<p>Vous êtes technicien dans une agence de location de matériel. Après une maintenance corrective sur "
        "les treuils, votre chef d'atelier vous demande de mettre à jour leur documentation technique.</p>",
        figure("bp-treuil", "Treuil électrique de levage suspendu à une poutre, câble et crochet",
               "Figure 1 — Treuil électrique de levage", 340),
        data_box([
            "Câble de diamètre 8 mm et de longueur 300 m, en acier <b>E295</b>",
            f"Contrainte dans le câble : {SIG} = 40 MPa",
        ]),
    ],
    "blocks": [
        QBAR("Q1.1 – Q1.3", ["DT1", "DT2"]),
        Q("q1_1", f"Déterminer la résistance élastique {RE} de l'acier du câble.", H_LIRE,
          num(295, "MPa", absTol=0.5, variants=[var(295e6, "Pa", relTol=0.001)]),
          f"{RE} = 295 MPa",
          "<p>Dans le tableau des matériaux (DT2), on cherche la ligne <b>E295</b> et on lit la colonne "
          f"<i>R</i><sub>e</sub> min : <b>{RE} = 295 MPa</b>. Le nombre dans le nom de la nuance donne d'ailleurs "
          "cette valeur.</p>"),
        Q("q1_2", f"Le câble résiste-t-il ? Compare la contrainte {SIG} à {RE}.", H_OUINON, YES,
          "Oui",
          f"<p>{SIG} = 40 MPa est bien plus petite que {RE} = 295 MPa : le câble reste dans sa zone élastique, "
          "il <b>résiste</b>. Il reprendra sa longueur quand on relâchera la charge.</p>"),
        Q("q1_3", "Calculer le coefficient de sécurité <i>s</i> de cette installation.", H_C_SANS,
          num(7.375, absTol=0.006),
          "<i>s</i> ≈ 7,38",
          "<p>Le coefficient de sécurité dit combien de fois la contrainte pourrait être multipliée avant "
          "d'atteindre la limite élastique :</p>" +
          eq("<i>s</i> = " + frac(RE, SIG) + " = " + frac("295", "40") + " ≈ <b>7,38</b>") +
          "<p>Le coefficient de sécurité n'a pas d'unité (MPa divisé par MPa). D'après le DT2, une valeur de 5 à 8 "
          "convient pour un appareil de levage.</p>"),
    ],
})

PARTS_BP.append({
    "num": "2", "minutes": 20, "title": "Treuil de levage : câble dans un puits",
    "intro": [
        "<p>Un treuil descend une charge au fond d'un puits de 800 m de profondeur. On vérifie que le câble, "
        "qui doit porter la charge <em>et son propre poids</em>, résiste.</p>",
        data_box([
            "Câble en acier <b>E360</b>, de diamètre <i>d</i> = 6 mm",
            "Masse du câble (800 m) : 178 kg ; masse de la charge : 80 kg",
            "<i>g</i> = 9,81 N/kg",
            "Coefficient de sécurité souhaité : <i>s</i> = 8",
        ]),
    ],
    "blocks": [
        QBAR("Q2.1 – Q2.6", ["DT1", "DT2"]),
        Q("q2_1", "Calculer la section <i>S</i> du câble.", H_C,
          num(28.2743, "mm2", relTol=0.001, variants=[var(0.282743, "cm2", relTol=0.001)]),
          "<i>S</i> ≈ 28,27 mm²",
          "<p>La section du câble est un disque :</p>" +
          eq("<i>S</i> = " + frac("π × <i>d</i>²", "4") + " = " + frac("π × 6²", "4") + " ≈ <b>28,27 mm²</b>")),
        Q("q2_2", "Calculer le poids <i>P</i><sub>câble</sub> du câble.", H_C,
          num(1746.18, "N", relTol=0.001, variants=[var(1.74618, "kN", relTol=0.001)]),
          "<i>P</i><sub>câble</sub> = 1 746,18 N",
          "<p>Le poids se calcule à partir de la masse :</p>" +
          eq("<i>P</i> = <i>m</i> × <i>g</i> = 178 × 9,81 = <b>1 746,18 N</b>") +
          "<p>Attention : la masse est en kg, le poids (une force) en newtons.</p>"),
        Q("q2_3", "Calculer le poids total <i>P</i><sub>total</sub> que doit porter le haut du câble (câble de 800 m "
          "et charge).", H_C,
          num(2530.98, "N", relTol=0.001, variants=[var(2.53098, "kN", relTol=0.001)]),
          "<i>P</i><sub>total</sub> = 2 530,98 N",
          "<p>En haut du puits, le câble porte la charge <em>et</em> tout le câble déroulé :</p>" +
          eq("<i>P</i><sub>total</sub> = (178 + 80) × 9,81 = 258 × 9,81 = <b>2 530,98 N</b>") +
          "<p>Ici, le câble pèse plus de deux fois plus lourd que la charge !</p>"),
        Q("q2_4", f"Calculer la contrainte {SIG} dans le câble.", H_C,
          num(89.5155, "MPa", relTol=0.001, variants=[var(89.5155e6, "Pa", relTol=0.001)]),
          f"{SIG} ≈ 89,52 MPa",
          eq(f"{SIG} = " + frac("<i>F</i>", "<i>S</i>") + " = " + frac("2 530,98", "28,27") +
             " ≈ <b>89,52 MPa</b>") +
          "<p>La force est en N et la section en mm² : le résultat est en N/mm², c'est-à-dire en MPa.</p>"),
        Q("q2_5", f"Calculer la résistance pratique {RPE} de ce câble.", H_C,
          num(45, "MPa", absTol=0.006, variants=[var(45e6, "Pa", relTol=0.001)]),
          f"{RPE} = 45 MPa",
          f"<p>Pour l'acier E360, {RE} = 360 MPa (DT2). Avec un coefficient de sécurité de 8 :</p>" +
          eq(f"{RPE} = " + frac(RE, "<i>s</i>") + " = " + frac("360", "8") + " = <b>45 MPa</b>")),
        Q("q2_6", "La condition de résistance est-elle vérifiée ?", H_OUINON,
          {"type": "yesno", "value": False},
          "Non",
          f"<p>Condition de résistance : {SIG} ≤ {RPE}. Ici {SIG} ≈ 89,52 MPa est <b>plus grande</b> que "
          f"{RPE} = 45 MPa : la condition n'est <b>pas vérifiée</b>.</p>"
          "<p>Le câble ne casserait pas tout de suite (89,52 MPa reste sous les 360 MPa de la limite élastique), "
          "mais la sécurité demandée n'est pas assurée : il faut un câble plus gros ou un acier plus résistant.</p>"),
    ],
})

PARTS_BP.append({
    "num": "3", "minutes": 15, "title": "Maillon de chaîne : joue de chaîne",
    "intro": [
        "<p>Après une maintenance corrective, vous remplacez une chaîne de transmission. On vous demande de "
        "déterminer le coefficient de sécurité de la nouvelle installation.</p>",
        figure("bp-chaine", "Chaîne à rouleaux : maillons intérieur, extérieur et de jonction, rouleau, douille, axe, "
               "plaques", "Figure 2 — Constitution d'une chaîne à rouleaux", 420),
        figure("bp-maillon", "Joue de chaîne cotée : entraxe 15, largeur 12, diamètre extérieur 18, trou de diamètre "
               "6, épaisseur 2 mm, sections 1 et 2", "Figure 3 — Joue de chaîne (épaisseur 2 mm)", 380),
        data_box([
            "Joue en acier de résistance élastique <i>R</i><sub>e</sub> = 600 MPa",
            "Effort de traction : <i>F</i> = 2 000 N ; épaisseur de la joue : 2 mm",
            "Section 1 : partie droite de largeur 12 mm ; section 2 : au droit du trou (Ø18 extérieur, trou Ø6)",
        ]),
    ],
    "blocks": [
        QBAR("Q3.1 – Q3.5", ["DT1"]),
        Q("q3_1", "Calculer l'aire de la section 1.", H_EX,
          num(24, "mm2", absTol=0.05), "<i>S</i><sub>1</sub> = 24 mm²",
          "<p>La section 1 est un rectangle de 12 mm (largeur) sur 2 mm (épaisseur) :</p>" +
          eq("<i>S</i><sub>1</sub> = 12 × 2 = <b>24 mm²</b>")),
        Q("q3_2", "Calculer l'aire de la section 2.", H_EX,
          num(24, "mm2", absTol=0.05), "<i>S</i><sub>2</sub> = 24 mm²",
          "<p>Au droit du trou, il ne reste de la matière que de part et d'autre du trou : la largeur utile vaut "
          "18 − 6 = 12 mm.</p>" +
          eq("<i>S</i><sub>2</sub> = (18 − 6) × 2 = <b>24 mm²</b>") +
          "<p>Les deux sections sont égales : la joue a été dessinée pour que le trou ne la fragilise pas.</p>"),
        Q("q3_3", "Calculer la contrainte <i>σ</i><sub>1</sub> dans la section 1.", H_C,
          num(83.3333, "MPa", absTol=0.006), "<i>σ</i><sub>1</sub> ≈ 83,33 MPa",
          eq("<i>σ</i><sub>1</sub> = " + frac("<i>F</i>", "<i>S</i><sub>1</sub>") + " = " + frac("2 000", "24") +
             " ≈ <b>83,33 MPa</b>")),
        Q("q3_4", "Calculer la contrainte <i>σ</i><sub>2</sub> dans la section 2.", H_C,
          num(83.3333, "MPa", absTol=0.006), "<i>σ</i><sub>2</sub> ≈ 83,33 MPa",
          eq("<i>σ</i><sub>2</sub> = " + frac("<i>F</i>", "<i>S</i><sub>2</sub>") + " = " + frac("2 000", "24") +
             " ≈ <b>83,33 MPa</b>") + "<p>Même section, même effort : même contrainte.</p>"),
        Q("q3_5", "Calculer le coefficient de sécurité <i>s</i> de cette joue de chaîne.", H_C_SANS,
          num(7.2, absTol=0.006), "<i>s</i> = 7,2",
          eq("<i>s</i> = " + frac(RE, SIG) + " = " + frac("600", "83,33") + " ≈ <b>7,2</b>") +
          "<p>La joue pourrait supporter un effort 7,2 fois plus grand avant d'atteindre sa limite élastique.</p>"),
    ],
})


def _dr_sections_svg():
    """Document réponse de la barre percée : trois cadres quadrillés au millimètre (5 px = 1 mm)."""
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="400" viewBox="0 0 900 400">',
           '<rect width="900" height="400" fill="#fff"/>',
           '<text x="450" y="38" text-anchor="middle" font-family="Arial,sans-serif" font-size="20" '
           'font-weight="700" fill="#1C2530">Sections droites à l\'échelle 1:1 — 1 petit carreau = 1 mm</text>']
    for k, fx in enumerate((70, 355, 640)):
        fy, fw, fh = 90, 190, 250
        for i in range(0, fw + 1, 5):
            c = "#C5CDD6" if i % 25 == 0 else "#E6EAEE"
            out.append(f'<line x1="{fx + i}" y1="{fy}" x2="{fx + i}" y2="{fy + fh}" stroke="{c}" stroke-width="1"/>')
        for j in range(0, fh + 1, 5):
            c = "#C5CDD6" if j % 25 == 0 else "#E6EAEE"
            out.append(f'<line x1="{fx}" y1="{fy + j}" x2="{fx + fw}" y2="{fy + j}" stroke="{c}" stroke-width="1"/>')
        out.append(f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="none" stroke="#1C2530" stroke-width="2"/>')
        out.append(f'<text x="{fx + fw / 2}" y="{fy - 12}" text-anchor="middle" font-family="Arial,sans-serif" '
                   f'font-size="22" font-weight="700" fill="#1C2530">S{k + 1}</text>')
    out.append("</svg>")
    return "".join(out)


DR_SECTIONS_SVG = _dr_sections_svg()

PARTS_BP.append({
    "num": "4", "minutes": 25, "title": "Barre percée : quelle section est la plus sollicitée ?",
    "intro": [
        "<p>La barre ci-dessous, de section rectangulaire 24 mm × 15 mm, est tirée par un effort de 5 000 N. Elle "
        "est percée de deux trous Ø4 et d'un trou Ø10, qui traversent toute son épaisseur de 15 mm. On étudie trois "
        "sections : S1 (sans trou), S2 (au droit des deux trous Ø4) et S3 (au droit du trou Ø10).</p>",
        figure("bp-barre", "Barre de section 24 × 15 tirée par deux forces de 5000 N, percée de deux trous de "
               "diamètre 4 et d'un trou de diamètre 10 ; sections S1, S2, S3 repérées en rouge",
               "Figure 4 — Barre percée", 560),
        data_box([
            "Effort de traction : <i>F</i> = 5 000 N",
            "Section pleine : 24 mm (hauteur) × 15 mm (épaisseur)",
            "S2 : deux trous Ø4, d'axes à 8 mm du haut et à 8 mm du bas ; S3 : un trou Ø10 au milieu",
            "Barre en acier <b>E295</b> ; coefficient de sécurité <i>s</i> = 6",
        ]),
    ],
    "blocks": [
        QBAR("Q4.1", ["DP1"], ans="sur le document réponse"),
        SK("sk_q4_1", "Q4.1", "SECTIONS",
           "Dessiner les trois sections S1, S2 et S3 à l'échelle 1:1 dans les cadres du document réponse.",
           ["Les trois sections sont des rectangles de 15 mm de large et 24 mm de haut (15 × 24 petits carreaux).",
            "S1 est entièrement pleine (hachurée ou coloriée).",
            "S2 montre deux bandes vides de 4 mm de haut, centrées à 8 mm du haut et à 8 mm du bas.",
            "S3 montre une seule bande vide de 10 mm de haut, au milieu de la section."],
           [],
           "<p>Outils : <b>Ligne</b> pour les contours, <b>Crayon</b> pour hachurer la matière. Un petit carreau "
           "vaut 1 mm ; l'outil Ligne affiche la longueur tracée.</p>"
           "<p>Un trou qui traverse la barre enlève, dans la section, une bande de matière aussi haute que son "
           "diamètre.</p>",
           "<p>Les trois sections ont le même contour : un rectangle de 15 mm de large (l'épaisseur) et 24 mm de "
           "haut.</p><ul><li><b>S1</b> : rien n'est enlevé, toute la section est pleine.</li>"
           "<li><b>S2</b> : chaque trou Ø4 enlève une bande de 4 mm de haut sur toute la largeur. Il reste trois "
           "bandes de matière : 6 mm, 4 mm et 6 mm.</li>"
           "<li><b>S3</b> : le trou Ø10 enlève une bande de 10 mm au milieu. Il reste deux bandes de 7 mm.</li>"
           "</ul>"),
        QBAR("Q4.2 – Q4.10", ["DT1", "DT2"]),
        Q("q4_2", "Calculer l'aire de la section S1.", H_EX,
          num(360, "mm2", absTol=0.5), "<i>S</i><sub>1</sub> = 360 mm²",
          eq("<i>S</i><sub>1</sub> = 24 × 15 = <b>360 mm²</b>")),
        Q("q4_3", "Calculer l'aire de la section S2.", H_EX,
          num(240, "mm2", absTol=0.5), "<i>S</i><sub>2</sub> = 240 mm²",
          "<p>On enlève à la section pleine les deux bandes de 4 mm × 15 mm :</p>" +
          eq("<i>S</i><sub>2</sub> = 360 − 2 × (4 × 15) = 360 − 120 = <b>240 mm²</b>") +
          "<p>Autre méthode : il reste 6 + 4 + 6 = 16 mm de hauteur de matière, soit 16 × 15 = 240 mm².</p>"),
        Q("q4_4", "Calculer l'aire de la section S3.", H_EX,
          num(210, "mm2", absTol=0.5), "<i>S</i><sub>3</sub> = 210 mm²",
          eq("<i>S</i><sub>3</sub> = 360 − 10 × 15 = 360 − 150 = <b>210 mm²</b>")),
        Q("q4_5", "Calculer la contrainte <i>σ</i><sub>1</sub> dans la section S1.", H_C,
          num(13.8889, "MPa", absTol=0.006), "<i>σ</i><sub>1</sub> ≈ 13,89 MPa",
          eq("<i>σ</i><sub>1</sub> = " + frac("5 000", "360") + " ≈ <b>13,89 MPa</b>")),
        Q("q4_6", "Calculer la contrainte <i>σ</i><sub>2</sub> dans la section S2.", H_C,
          num(20.8333, "MPa", absTol=0.006), "<i>σ</i><sub>2</sub> ≈ 20,83 MPa",
          eq("<i>σ</i><sub>2</sub> = " + frac("5 000", "240") + " ≈ <b>20,83 MPa</b>")),
        Q("q4_7", "Calculer la contrainte <i>σ</i><sub>3</sub> dans la section S3.", H_C,
          num(23.8095, "MPa", absTol=0.006), "<i>σ</i><sub>3</sub> ≈ 23,81 MPa",
          eq("<i>σ</i><sub>3</sub> = " + frac("5 000", "210") + " ≈ <b>23,81 MPa</b>")),
        Q("q4_8", "Quelle est la section la plus sollicitée ?", "Réponds par le nom de la section (S1, S2 ou S3).",
          {"type": "intset", "value": [3]}, "S3",
          "<p>La section la plus sollicitée est celle où la contrainte est la plus grande, c'est-à-dire celle qui a "
          "le <b>moins de matière</b> : <b>S3</b> (210 mm², 23,81 MPa). C'est là que la barre casserait en "
          "premier.</p>"),
        Q("q4_9", f"Déterminer la résistance pratique {RPE} de la barre.", H_C,
          num(49.1667, "MPa", absTol=0.006, variants=[var(49.1667e6, "Pa", relTol=0.001)]),
          f"{RPE} ≈ 49,17 MPa",
          f"<p>Acier E295 : {RE} = 295 MPa (DT2).</p>" +
          eq(f"{RPE} = " + frac(RE, "<i>s</i>") + " = " + frac("295", "6") + " ≈ <b>49,17 MPa</b>")),
        Q("q4_10", "La condition de résistance est-elle vérifiée pour les trois sections ?", H_OUINON, YES,
          "Oui",
          f"<p>Il suffit de vérifier la section la plus sollicitée : {SIG}<sub>3</sub> ≈ 23,81 MPa ≤ {RPE} ≈ "
          "49,17 MPa. Si S3 résiste, S1 et S2, moins chargées, résistent aussi : la condition est <b>vérifiée</b> "
          "pour toute la barre.</p>"),
    ],
})

PARTS_BP.append({
    "num": "5", "minutes": 20, "title": "Vis d'assemblage d'un couvercle",
    "intro": [
        "<p>Un joint plat est placé entre un couvercle et un carter. Pour bien l'écraser, il faut une force totale "
        "de 2 000 N, répartie sur 6 vis d'assemblage identiques. Chaque vis, tirée par le serrage, travaille en "
        "traction.</p>",
        figure("bp-vis", "Couvercle fixé sur un carter par 6 vis, joint plat entre les deux ; diamètre de vis à "
               "déterminer", "Figure 5 — Couvercle, joint plat et vis", 260),
        data_box([
            "Force totale de serrage : <i>F</i> = 2 000 N, répartie sur 6 vis",
            "Vis en acier : <i>R</i><sub>e</sub> = 260 MPa ; coefficient de sécurité <i>s</i> = 3",
            "Section du noyau des vis : DT3",
        ]),
    ],
    "blocks": [
        QBAR("Q5.1 – Q5.7", ["DT1", "DT3"]),
        Q("q5_1", "Déterminer la force <i>F</i><sub>vis</sub> exercée sur une vis.", H_C,
          num(333.3333, "N", absTol=0.006), "<i>F</i><sub>vis</sub> ≈ 333,33 N",
          "<p>Les 6 vis se partagent l'effort à parts égales :</p>" +
          eq("<i>F</i><sub>vis</sub> = " + frac("2 000", "6") + " ≈ <b>333,33 N</b>")),
        Q("q5_2", f"Calculer la résistance pratique {RPE} des vis.", H_C,
          num(86.6667, "MPa", absTol=0.006), f"{RPE} ≈ 86,67 MPa",
          eq(f"{RPE} = " + frac(RE, "<i>s</i>") + " = " + frac("260", "3") + " ≈ <b>86,67 MPa</b>")),
        Q("q5_3", "Calculer la section minimale <i>S</i><sub>mini</sub> d'une vis pour respecter la condition de "
          "résistance.", H_C,
          num(3.8462, "mm2", absTol=0.006), "<i>S</i><sub>mini</sub> ≈ 3,85 mm²",
          f"<p>La condition {SIG} = <i>F</i> / <i>S</i> ≤ {RPE} donne <i>S</i> ≥ <i>F</i> / {RPE} :</p>" +
          eq("<i>S</i><sub>mini</sub> = " + frac("333,33", "86,67") + " ≈ <b>3,85 mm²</b>")),
        Q("q5_4", "À l'aide du DT3, choisir le diamètre <i>d</i> de vis qui convient.",
          "Valeur du tableau. " + UNITE,
          num(3, "mm", absTol=0.01), "<i>d</i> = 3 mm (vis M3)",
          "<p>On cherche dans le DT3 la première section de noyau <b>supérieure ou égale</b> à 3,85 mm² : 2,98 mm² "
          "(d = 2,5) est trop petite, <b>4,47 mm²</b> convient. On choisit <b>d = 3 mm</b>.</p>"),
        Q("q5_5", "Le filetage concentre les contraintes : la contrainte maximale vaut <i>σ</i><sub>maxi</sub> = "
          "<i>σ</i> × <i>K</i><sub>t</sub>, avec <i>K</i><sub>t</sub> = 2,5. Calculer <i>σ</i><sub>maxi</sub> pour la "
          "vis choisie.", H_C,
          num(186.4281, "MPa", relTol=0.001), "<i>σ</i><sub>maxi</sub> ≈ 186,43 MPa",
          "<p>On calcule d'abord la contrainte dans le noyau de la vis M3 (4,47 mm²), puis on la multiplie par "
          "<i>K</i><sub>t</sub> :</p>" +
          eq(f"{SIG} = " + frac("333,33", "4,47") + " ≈ 74,57 MPa") +
          eq("<i>σ</i><sub>maxi</sub> = 74,57 × 2,5 ≈ <b>186,43 MPa</b>")),
        Q("q5_6", "La condition de résistance est-elle vérifiée avec cette vis ?", H_OUINON,
          {"type": "yesno", "value": False}, "Non",
          f"<p><i>σ</i><sub>maxi</sub> ≈ 186,43 MPa est plus grande que {RPE} ≈ 86,67 MPa : la condition n'est "
          "<b>pas vérifiée</b>. La concentration de contrainte au fond des filets oblige à choisir une vis plus "
          "grosse.</p>"),
        Q("q5_7", "Quel diamètre de vis faut-il choisir pour que la condition soit vérifiée malgré "
          "<i>K</i><sub>t</sub> = 2,5 ?", "Valeur du tableau. " + UNITE,
          num(5, "mm", absTol=0.01), "<i>d</i> = 5 mm (vis M5)",
          f"<p>Il faut <i>σ</i> × 2,5 ≤ {RPE}, donc une section au moins 2,5 fois plus grande :</p>" +
          eq("<i>S</i> ≥ 2,5 × 3,85 ≈ 9,62 mm²") +
          "<p>Dans le DT3, la vis M4 (7,75 mm²) est encore trop petite ; la vis <b>M5</b> (12,7 mm²) convient. "
          "Vérification : <i>σ</i><sub>maxi</sub> = 333,33 / 12,7 × 2,5 ≈ 65,6 MPa ≤ 86,67 MPa.</p>"),
    ],
})


# ============================================================ TRACÉS (fonds et décor)
SK_BG = {
    # clé : (image, largeur déclarée, hauteur déclarée)
    "POUTRE": ("t1-siege-fil", 810, 460),
    "AXE": ("c7-axe-chape", 860, 373),
    "SECTIONS": ("svg:DR_SECTIONS_SVG", 900, 400),
}


def bg_src(name):
    if name.startswith("svg:"):
        return "data:image/svg+xml;base64," + base64.b64encode(globals()[name[4:]].encode()).decode()
    return png(name)[0]

DECOR_JS = r"""  var DECOR = {
    // Document réponse de la barre percée : 5 px = 1 mm ; section 15 × 24 mm dessinée à 55 px du bord gauche
    // de chaque cadre et à 65 px de son bord haut
    SECTIONS: {
      pad: { t: 10, r: 10, b: 10, l: 10 }, rs: 2.4, pxPerCm: 50,
      decorate: function () {},
      correction: function (c) {
        var mm = 5, frames = [70, 355, 640];
        // bandes de matière (en mm depuis le haut de la section) pour S1, S2, S3
        var solid = [[[0, 24]], [[0, 6], [10, 14], [18, 24]], [[0, 7], [17, 24]]];
        frames.forEach(function (fx, k) {
          var x0 = fx + 55, y0 = 90 + 65, w = 15 * mm;
          solid[k].forEach(function (b) {
            c.save(); c.fillStyle = "rgba(198,40,40,.30)"; c.fillRect(x0, y0 + b[0] * mm, w, (b[1] - b[0]) * mm);
            c.strokeStyle = CORR; c.lineWidth = 2.4; c.strokeRect(x0, y0 + b[0] * mm, w, (b[1] - b[0]) * mm); c.restore();
          });
          c.save(); c.setLineDash([6, 4]); c.strokeStyle = CORR; c.lineWidth = 1.6;
          c.strokeRect(x0, y0, w, 24 * mm); c.restore();
        });
        text(c, "15 mm", 70 + 55 + 37, 155 + 120 + 22, CORR, 15, "center", "700");
        text(c, "24 mm", 70 + 55 + 75 + 34, 215, CORR, 15, "center", "700");
      }
    },
    // Figure 1 (siège suspendu), agrandie 2,5 fois : A(100;328) E(100;108) D(385;323) C(595;328)
    POUTRE: {
      pad: { t: 20, r: 170, b: 40, l: 30 }, rs: 2.4,
      decorate: function (c) {
        text(c, "Repère", 850, 300, "#000", 18, "left", "700");
        arrow(c, 860, 420, 950, 420, "#000", 2); arrow(c, 860, 420, 860, 335, "#000", 2);
        vlabel(c, 956, 426, "x", "", "#000", 18); vlabel(c, 872, 340, "y", "", "#000", 18);
      },
      correction: function (c) {
        // poids de l'homme, en C
        arrow(c, 595, 330, 595, 455, CORR, 3.6); vlabel(c, 612, 430, "P", "", CORR, 22);
        // action du fil, en D, de D vers E
        arrow(c, 385, 322, 249, 220, CORR, 3.6); vlabel(c, 300, 222, "F", "DE", CORR, 22, "right");
        // action du pivot A : composantes supposées
        arrow(c, -20, 328, 96, 328, CORR, 3.6); vlabel(c, -10, 300, "R", "Ax", CORR, 20);
        arrow(c, 100, 455, 100, 334, CORR, 3.6); vlabel(c, 112, 425, "R", "Ay", CORR, 20);
        // angle alpha entre le fil et la poutre
        c.save(); c.strokeStyle = CORR; c.lineWidth = 2.4;
        c.beginPath(); c.arc(385, 323, 62, Math.PI, Math.PI + Math.atan2(215, 285), false); c.stroke(); c.restore();
        text(c, "α", 300, 306, CORR, 24, "center", "800");
        text(c, "Correction", 850, 40, CORR, 18, "left", "800");
        text(c, "RAx et RAy :", 850, 70, CORR, 15, "left", "600");
        text(c, "sens supposés", 850, 92, CORR, 15, "left", "600");
      }
    },
    // Figure 11 (axe de chape), agrandie 2,5 fois : axe x 352 → 413, bords de la tige y 158 et 248
    AXE: {
      pad: { t: 50, r: 210, b: 20, l: 20 }, rs: 2.4,
      decorate: function (c) {
        line(c, 383, -22, 383, 30, "#000", 1.2); text(c, "Axe", 392, -30, "#000", 18, "left", "700");
        text(c, "Tige", 240, 182, "#000", 18, "center", "700");
        text(c, "Fourche", 600, 120, "#000", 18, "center", "700");
      },
      correction: function (c) {
        line(c, 330, 158, 436, 158, CORR, 4.4); line(c, 330, 248, 436, 248, CORR, 4.4);
        text(c, "S1", 446, 150, CORR, 20, "left", "800"); text(c, "S2", 446, 258, CORR, 20, "left", "800");
        text(c, "Correction", 875, 40, CORR, 18, "left", "800");
        text(c, "2 sections cisaillées", 875, 150, CORR, 17, "left", "700");
        text(c, "(S1 et S2)", 875, 175, CORR, 17, "left", "700");
        text(c, "T = P/2 = 6,5 kN", 875, 215, CORR, 17, "left", "700");
        text(c, "par section", 875, 240, CORR, 17, "left", "700");
      }
    }
  };
"""

DR_NAMES_JS = """  var DR_NAMES = {
    SECTIONS: { doc: "DR1", q: "Q4.1", t: "Barre percée : sections S1, S2 et S3 à l'échelle 1:1", scale: false },
    POUTRE: { doc: "DR1", q: "Q1.5", t: "Poutre AC isolée : actions mécaniques extérieures", scale: false },
    AXE: { doc: "DR1", q: "Q7.2", t: "Axe de chape : sections cisaillées", scale: false }
  };
"""

# ============================================================ DOCUMENTS
DOCS = [
    ("DP1", "Démarche de résolution", "Dossier présentation", False, """
<div class="doc-text"><h3>Démarche de résolution en résistance des matériaux</h3>
<ol>
<li><strong>Isoler</strong> la pièce étudiée et faire le <strong>bilan des actions mécaniques extérieures</strong>
qu'elle subit : point d'application, direction, sens, intensité connue ou inconnue.</li>
<li>Appliquer le <strong>principe fondamental de la statique</strong> (équilibre des forces, équilibre des
moments) pour trouver les actions inconnues. Choisir le point de calcul des moments là où passent les
inconnues qu'on ne cherche pas.</li>
<li>Identifier la <strong>sollicitation</strong> :
<ul><li><em>traction</em> ou <em>compression</em> : effort normal <i>N</i> porté par la ligne moyenne de la
pièce ;</li>
<li><em>cisaillement</em> : effort tranchant <i>T</i> contenu dans le plan de la section, qui tend à faire
glisser deux parties de la pièce l'une sur l'autre.</li></ul></li>
<li>Calculer l'<strong>aire de la section</strong> sollicitée (DT3).</li>
<li>Calculer la <strong>contrainte</strong> (<i>σ</i> ou <i>τ</i>), puis vérifier la <strong>condition de
résistance</strong> ou en déduire une dimension minimale.</li>
<li>Si l'énoncé le demande, calculer la <strong>déformation</strong> (loi de Hooke).</li>
</ol>
<h3>Conseils de calcul</h3>
<ul>
<li>Travailler en <strong>newtons et en millimètres</strong> : les contraintes sortent directement en N/mm²,
c'est-à-dire en MPa.</li>
<li>Garder les valeurs non arrondies dans la calculatrice et n'arrondir que le résultat demandé. Les
tolérances de correction couvrent les arrondis des résultats intermédiaires demandés dans le sujet.</li>
<li>Pour π, utiliser la touche de la calculatrice ; la valeur 3,14 est tolérée.</li>
<li>Toujours écrire l'unité du résultat : elle compte pour la moitié des points.</li>
</ul>
<h3>Isoler un solide : représentation des actions</h3>
<ul>
<li>Un poids est vertical, dirigé vers le bas, appliqué au centre de gravité (ou au point indiqué).</li>
<li>Un fil ou un câble tendu exerce une force portée par sa direction, qui <em>tire</em> sur la pièce.</li>
<li>Une articulation (pivot) parfaite exerce une force passant par son centre, de direction inconnue :
on la représente par deux composantes, dans un sens supposé.</li>
</ul></div>"""),
    ("DT1", "Formulaire — traction et compression", "Dossier technique", True, """
<div class="doc-text"><h3>Traction et compression</h3>
<table class="t"><thead><tr><th>Grandeur</th><th>Relation</th><th>Unités usuelles</th></tr></thead><tbody>
<tr><td>Poids</td><td><i>P</i> = <i>m</i> · <i>g</i></td><td>N ; kg ; m·s<sup>−2</sup></td></tr>
<tr><td>Effort normal</td><td><i>N</i> &gt; 0 en traction, <i>N</i> &lt; 0 en compression</td><td>N</td></tr>
<tr><td>Contrainte normale</td><td><i>σ</i> = <i>N</i> / <i>S</i></td><td>MPa = N/mm²</td></tr>
<tr><td>Déformation (allongement relatif)</td><td><i>ε</i> = Δ<i>L</i> / <i>L</i></td><td>sans unité</td></tr>
<tr><td>Loi de Hooke</td><td><i>σ</i> = <i>E</i> · <i>ε</i></td><td><i>E</i> en MPa</td></tr>
<tr><td>Variation de longueur</td><td>Δ<i>L</i> = <i>N</i> · <i>L</i> / (<i>E</i> · <i>S</i>)</td><td>mm</td></tr>
<tr><td>Condition de résistance</td><td>|<i>σ</i>| ≤ [<i>σ</i>]</td><td>MPa</td></tr>
</tbody></table>
<h3>Conversions</h3>
<ul><li>1 MPa = 1 N/mm² = 10<sup>6</sup> Pa ; 1 GPa = 10<sup>3</sup> MPa</li>
<li>1 kN = 10<sup>3</sup> N ; 1 m = 10<sup>3</sup> mm ; 1 µm = 10<sup>−3</sup> mm</li>
<li>Acier : <i>E</i> ≈ 200 000 à 210 000 MPa</li></ul>
<h3>Moment d'une force</h3>
<p><i>M</i><sub>/A</sub> = ± <i>F</i> · <i>d</i>, où <i>d</i> est la distance de A à la droite d'action de la
force (bras de levier). Une force qui passe par A a un moment nul par rapport à A.</p></div>"""),
    ("DT2", "Formulaire — cisaillement", "Dossier technique", True, """
<div class="doc-text"><h3>Cisaillement</h3>
<table class="t"><thead><tr><th>Grandeur</th><th>Relation</th><th>Unités usuelles</th></tr></thead><tbody>
<tr><td>Effort tranchant par section</td><td><i>T</i> = <i>F</i> / <i>n</i>, <i>n</i> : nombre de sections
cisaillées</td><td>N</td></tr>
<tr><td>Contrainte de cisaillement</td><td><i>τ</i> = <i>T</i> / <i>S</i></td><td>MPa = N/mm²</td></tr>
<tr><td>Contrainte admissible</td><td><i>τ</i><sub>adm</sub> = <i>τ</i><sub>l</sub> / <i>n</i><sub>s</sub>
(ou <i>τ</i><sub>ult</sub> / <i>n</i><sub>s</sub>)</td><td>MPa</td></tr>
<tr><td>Condition de résistance</td><td><i>τ</i> ≤ <i>τ</i><sub>adm</sub></td><td>MPa</td></tr>
<tr><td>Loi de Hooke en cisaillement</td><td><i>τ</i> = <i>G</i> · <i>γ</i></td><td><i>G</i> en MPa ;
<i>γ</i> en rad</td></tr>
</tbody></table>
<h3>Nombre de sections cisaillées</h3>
<ul>
<li><strong>Simple cisaillement</strong> : l'organe (goupille, boulon, vis) relie deux pièces ; il est cisaillé
dans un seul plan, celui du contact entre les deux pièces.</li>
<li><strong>Double cisaillement</strong> : l'organe traverse trois pièces (une pièce prise entre deux autres,
comme dans une chape) ; il est cisaillé dans deux plans.</li>
<li>Avec plusieurs organes identiques qui se partagent l'effort également : <i>n</i> = (nombre d'organes) ×
(nombre de sections par organe).</li>
</ul>
<h3>Dimensionnement d'un axe circulaire</h3>
<p><i>S</i> = π · <i>d</i>² / 4 ≥ <i>T</i> / <i>τ</i><sub>adm</sub> ⇒ <i>d</i> ≥ √(4 · <i>T</i> /
(π · <i>τ</i><sub>adm</sub>))</p>
<h3>Notations</h3>
<ul><li><i>τ</i><sub>l</sub> : contrainte limite ; <i>τ</i><sub>ult</sub> : contrainte ultime (rupture) ;
<i>n</i><sub>s</sub> : coefficient de sécurité</li></ul></div>"""),
    ("DT3", "Sections usuelles et fers plats", "Dossier technique", True, """
<div class="doc-text"><h3>Aire des sections usuelles</h3>
<table class="t"><thead><tr><th>Section</th><th>Aire</th></tr></thead><tbody>
<tr><td>Disque plein de diamètre <i>d</i></td><td><i>S</i> = π · <i>d</i>² / 4</td></tr>
<tr><td>Couronne (tube) de diamètres <i>d</i><sub>e</sub> et <i>d</i><sub>i</sub></td><td><i>S</i> =
π · (<i>d</i><sub>e</sub>² − <i>d</i><sub>i</sub>²) / 4</td></tr>
<tr><td>Rectangle <i>a</i> × <i>b</i></td><td><i>S</i> = <i>a</i> · <i>b</i></td></tr>
</tbody></table>
<h3>Fers plats laminés : largeurs disponibles (extrait de gamme)</h3>
<table class="t"><tbody><tr><th>Largeur <i>a</i> (mm)</th><td>10</td><td>12</td><td>15</td><td>16</td><td>20</td>
<td>25</td><td>30</td><td>35</td><td>40</td><td>45</td><td>50</td><td>60</td><td>70</td><td>80</td><td>90</td>
<td>100</td><td>120</td><td>150</td></tr></tbody></table>
<p>On choisit la largeur disponible immédiatement supérieure à la largeur minimale calculée.</p></div>"""),
]


# Documents de l'exercice 1.1 (niveau bac pro), tirés du cours de traction : peu de formules.
MATERIAUX = [("S185 (A33)", 290, 185), ("S235 (E24)", 340, 235), ("S275 (E28)", 410, 275), ("S355 (E36)", 490, 355),
             ("E295 (A50)", 470, 295), ("E335 (A60)", 570, 335), ("E360 (A70)", 670, 360)]
COEFS = [("1,5 à 2", "Cas exceptionnels de grande légèreté ; charges surévaluées."),
         ("2 à 3", "Construction où l'on recherche la légèreté (aviation) ; hypothèses les plus défavorables "
                   "(charpente avec vent ou neige)."),
         ("3 à 4", "Bonne construction, calculs soignés, haubans fixes."),
         ("4 à 5", "Construction courante (légers efforts dynamiques non pris en compte) ; treuils."),
         ("5 à 8", "Calculs sommaires, efforts difficiles à évaluer (chocs, mouvements alternatifs, appareils de "
                   "levage, manutention)."),
         ("8 à 10", "Matériaux non homogènes ; chocs ; élingues de levage."),
         ("10 à 15", "Chocs très importants, très mal connus (presses) ; ascenseurs.")]
NOYAUX = [(1.6, 0.35, 1.08), (2, 0.4, 1.79), (2.5, 0.45, 2.98), (3, 0.5, 4.47), (4, 0.7, 7.75), (5, 0.8, 12.7),
          (6, 1, 17.9), (8, 1.25, 32.9), (10, 1.5, 52.3), (12, 1.75, 76.2)]


def _frn(x):
    return f"{x:g}".replace(".", ",")


DOCS += [
    ("BDP1", "Méthode — vérifier une pièce en traction", "Dossier présentation", False, """
<div class="doc-text"><h3>Vérifier une pièce en traction : 4 étapes</h3>
<ol>
<li><strong>La force</strong> <i>F</i> qui tire sur la pièce, en newtons (N). Si l'on connaît une masse :
<i>P</i> = <i>m</i> × <i>g</i>, avec <i>g</i> = 9,81 N/kg. Si plusieurs pièces se partagent l'effort, on le divise.</li>
<li><strong>La section</strong> <i>S</i> qui travaille, en mm² : la « tranche » de la pièce, perpendiculaire à
la force. Un trou enlève de la matière, donc de la section.</li>
<li><strong>La contrainte</strong> <i>σ</i> = <i>F</i> / <i>S</i>, en MPa (1 MPa = 1 N/mm²).</li>
<li><strong>La comparaison</strong> avec la résistance pratique <i>R</i><sub>pe</sub> = <i>R</i><sub>e</sub> / <i>s</i> :
si <i>σ</i> ≤ <i>R</i><sub>pe</sub>, la pièce résiste en toute sécurité.</li>
</ol>
<h3>Conseils</h3>
<ul>
<li>Force en N et section en mm² : la contrainte sort directement en MPa.</li>
<li>Toujours écrire l'unité : elle compte pour la moitié des points.</li>
<li>La section la plus petite est la plus sollicitée : c'est elle qu'il faut vérifier.</li>
</ul></div>"""),
    ("BDT1", "Formulaire — traction", "Dossier technique", True, """
<div class="doc-text"><h3>Les relations à connaître</h3>
<table class="t"><thead><tr><th>Grandeur</th><th>Relation</th><th>Unités</th></tr></thead><tbody>
<tr><td>Contrainte normale</td><td><i>σ</i> = <i>F</i> / <i>S</i></td><td>MPa ; N ; mm²</td></tr>
<tr><td>Résistance pratique</td><td><i>R</i><sub>pe</sub> = <i>R</i><sub>e</sub> / <i>s</i></td><td>MPa</td></tr>
<tr><td>Condition de résistance</td><td><i>σ</i> ≤ <i>R</i><sub>pe</sub></td><td>MPa</td></tr>
<tr><td>Coefficient de sécurité obtenu</td><td><i>s</i> = <i>R</i><sub>e</sub> / <i>σ</i></td><td>sans unité</td></tr>
<tr><td>Poids</td><td><i>P</i> = <i>m</i> × <i>g</i></td><td>N ; kg ; N/kg</td></tr>
</tbody></table>
<h3>Aire des sections</h3>
<table class="t"><tbody>
<tr><th>Disque de diamètre <i>d</i></th><td><i>S</i> = π × <i>d</i>² / 4</td></tr>
<tr><th>Rectangle <i>a</i> × <i>b</i></th><td><i>S</i> = <i>a</i> × <i>b</i></td></tr>
</tbody></table>
<p>1 MPa = 1 N/mm² · 1 kN = 1 000 N</p></div>"""),
    ("BDT2", "Matériaux et coefficients de sécurité", "Dossier technique", True,
     '<div class="doc-text"><h3>Caractéristiques de quelques aciers</h3><table class="t"><thead><tr><th>Nuance</th>'
     '<th><i>R</i> min (MPa)<br><small>rupture</small></th><th><i>R</i><sub>e</sub> min (MPa)<br>'
     '<small>limite élastique</small></th></tr></thead><tbody>' +
     "".join(f"<tr><td>{n}</td><td>{r}</td><td>{e}</td></tr>" for n, r, e in MATERIAUX) +
     '</tbody></table><h3>Choix du coefficient de sécurité <i>s</i></h3><table class="t"><thead><tr><th><i>s</i></th>'
     '<th>Conditions générales de calcul (sauf réglementation particulière)</th></tr></thead><tbody>' +
     "".join(f"<tr><td><b>{c}</b></td><td>{t}</td></tr>" for c, t in COEFS) + "</tbody></table></div>"),
    ("BDT3", "Vis : section du noyau", "Dossier technique", True,
     '<div class="doc-text"><h3>Vis à filetage métrique : section résistante du noyau</h3>'
     '<table class="t"><thead><tr><th>Diamètre <i>d</i> (mm)</th><th>Pas (mm)</th><th>Section du noyau (mm²)</th>'
     '</tr></thead><tbody>' +
     "".join(f"<tr><td>{_frn(d)}</td><td>{_frn(p)}</td><td>{_frn(a)}</td></tr>" for d, p, a in NOYAUX) +
     '</tbody></table><p>Une vis travaille dans son noyau (le cylindre au fond des filets) : on choisit la '
     'première section supérieure ou égale à la section minimale calculée.</p></div>'),
]


# ============================================================ rendu HTML
def render_q(q, part):
    qid, label = q["id"], q["label"]
    return f"""
        <div class="q" id="{qid}" data-q="{qid}">
          <p class="q-stem"><span class="q-num">{label}</span> <strong>{q['stem']}</strong></p>
          <p class="q-hint" id="h-{qid}">{q['hint']}</p>
          <div class="q-row">
            <input type="text" class="q-input" id="in-{qid}" aria-label="Réponse {label}" aria-describedby="h-{qid}" autocomplete="off" autocapitalize="off" spellcheck="false">
            <button type="button" class="btn btn-validate">Valider</button>
            <span class="q-status" aria-live="polite"></span>
            <span class="print-only pstat">Non validée : comptée fausse</span>
          </div>
          <p class="q-msg" role="alert"></p>
          <div class="q-expl" hidden>
            <p class="q-unit-msg" hidden></p>
            <p class="q-expected"><span>Réponse attendue :</span> {q['expected']}</p>
            <div class="q-why">{q['why']}</div>
          </div>
        </div>"""


def render_qbar(b):
    chips = " ".join(f'<button type="button" class="doc-chip" data-doc="{d}" aria-pressed="false">{d}</button>'
                     for d in b["docs"])
    return (f'\n      <div class="qbar" role="group" aria-label="{b["label"]}"><div class="qb-num">{b["label"]}</div>'
            f'<div class="qb-docs">Documents à consulter : {chips}</div><div class="qb-ans">Répondre : {b["ans"]}</div></div>')


def render_sk(s, part, total_pts):
    sid, label = s["id"], s["label"]
    img_name, w, h = SK_BG[s["bg"]]
    src = bg_src(img_name)
    crit = "".join(f'<label class="se-item"><input type="checkbox" data-crit="{i}"><span>{c}</span></label>'
                   for i, c in enumerate(s["criteria"]))
    n = len(s["criteria"])
    if s["deps"]:
        labels = ", ".join(QLABEL[d] for d in s["deps"])
        note = f"La correction se superposera à ton tracé une fois la question {labels} validée."
    else:
        note = "La correction se superpose à ton tracé dès que tu le valides."
    return f"""
        <div class="sketch" data-sketch="{sid}" id="{sid}">
          <p class="q-stem"><span class="q-num">{label}</span> <strong>{s['stem']}</strong></p>
          <div class="sk-layout">
            <div class="sk-main">
              <div class="sk-toolbar" role="toolbar" aria-label="Outils de tracé {label}">
                <button type="button" data-tool="pen" aria-pressed="true">Crayon</button>
                <button type="button" data-tool="line" aria-pressed="false">Ligne</button>
                <button type="button" data-tool="arrow" aria-pressed="false">Flèche</button>
                <button type="button" data-tool="text" aria-pressed="false">Texte</button>
                <button type="button" data-tool="erase" aria-pressed="false">Gomme</button>
                <span class="sep"></span>
                <button type="button" class="sw" data-color="#1F5FA8" aria-label="Couleur bleue" aria-pressed="true" style="background:#1F5FA8"></button>
                <button type="button" class="sw" data-color="#1B7A43" aria-label="Couleur verte" aria-pressed="false" style="background:#1B7A43"></button>
                <button type="button" class="sw" data-color="#1C2530" aria-label="Couleur noire" aria-pressed="false" style="background:#1C2530"></button>
                <span class="sep"></span>
                <span class="tb-group"><span class="tb-lab">Trait</span>
                  <button type="button" data-width="fin" aria-pressed="false">Fin</button>
                  <button type="button" data-width="moyen" aria-pressed="true">Moyen</button>
                  <button type="button" data-width="epais" aria-pressed="false">Épais</button></span>
                <span class="sep"></span>
                <span class="tb-group"><span class="tb-lab">Zoom</span>
                  <button type="button" data-zoom="out" aria-label="Réduire le zoom">−</button>
                  <span class="zoom-val">100 %</span>
                  <button type="button" data-zoom="in" aria-label="Agrandir le zoom">+</button>
                  <button type="button" data-zoom="reset">Ajuster</button></span>
                <span class="sep"></span>
                <button type="button" data-act="undo">Annuler</button>
                <button type="button" data-act="clear">Tout effacer</button>
                <span class="spacer"></span>
                <button type="button" class="btn-drprint" data-act="drprint">Imprimer les DR</button>
                <button type="button" data-act="full" aria-pressed="false">Plein écran</button>
              </div>
              <div class="sk-stage"><img class="sk-bg" src="{src}" width="{w}" height="{h}" alt="" hidden>
                <canvas role="img" aria-label="Zone de tracé sur la figure {label}"></canvas></div>
              <div class="sk-foot">
                <button type="button" class="btn btn-sketch">Valider mon tracé</button>
                <label class="sk-corr-toggle"><input type="checkbox"> Superposer la correction</label>
                <span class="sk-meas" aria-live="polite"></span><span class="q-status" aria-live="polite"></span>
              </div>
              <div class="sk-print-wrap print-only"><p>Tracé de l'élève</p><img class="sk-print sk-print-student" alt="Tracé de l'élève">
                <p>Correction superposée à la figure</p><img class="sk-print sk-print-corr" alt="Correction du tracé"></div>
              <div class="selfeval" hidden>
                <p class="se-title">Auto-évaluation — {n} points sur les {total_pts} de la partie {part['num']}</p>
                <p class="se-lead">Compare ton tracé à la correction ci-dessus, puis coche uniquement ce que ton tracé comporte réellement. Sois honnête : c'est toi qui repères ce qu'il te reste à travailler.</p>
                {crit}
                <div class="se-foot"><button type="button" class="btn btn-self">Valider mon auto-évaluation</button>
                  <span class="se-score" aria-live="polite"></span></div>
                <p class="print-only se-print"></p>
              </div>
            </div>
            <div class="sk-side">{s['side']}</div>
          </div>
          <p class="sk-note sk-note-wrap">{note} <span class="sk-wait" aria-live="polite"></span></p>
          <div class="q-expl" hidden><p class="q-expected"><span>Correction du tracé</span></p>
            {s['expl']}</div>
        </div>"""


def part_points(p):
    return sum(1 if b["kind"] == "q" else len(b["criteria"]) for b in p["blocks"] if b["kind"] in ("q", "sk"))


def hm(minutes):
    h, m = divmod(minutes, 60)
    return f"{h} h {m:02d}" if h else f"{m} min"


# ============================================================ EXERCICES (découpage du contenu)
# Chaque exercice reprend une partie des PARTIES ci-dessus, renumérotées à partir de 1.
# Les documents sont renommés exercice par exercice (DP1, DT1, DT2…) ; « docs » donne la correspondance.
EXO_DEFS = [
    {"key": "traction-bp", "prefix": "b", "tag": "Exercice 1.1", "level": "Bac pro", "title": "Traction",
     "parts": PARTS_BP, "docs": {"BDP1": "DP1", "BDT1": "DT1", "BDT2": "DT2", "BDT3": "DT3"}, "fig_shift": 0,
     "hero": ("bp-treuil", "Treuil électrique de levage suspendu à une poutre, câble et crochet",
              "Un treuil de levage : son câble travaille en traction."),
     "card": "Un câble de treuil, une joue de chaîne, une barre percée et des vis d'assemblage : section, "
             "contrainte, résistance pratique et coefficient de sécurité.",
     "sub": "Cinq situations de maintenance pour vérifier une pièce tendue : lire une résistance dans un tableau, "
            "calculer une section et une contrainte, comparer à la résistance pratique, choisir une vis."},
    {"key": "traction", "prefix": "t", "tag": "Exercice 1.2", "title": "Traction et compression",
     "parts": PARTS[0:4], "docs": {"DP1": "DP1", "DT1": "DT1", "DT3": "DT2"}, "fig_shift": 0,
     "hero": ("t1-siege-fil", "Siège suspendu : poutre AC articulée sur un mur, maintenue par le fil DE",
              "Le fil d'acier DE porte le siège : on calcule sa tension, sa contrainte et son allongement."),
     "card": "Un fil de maintien, une barre tendue, un tube comprimé et un fer plat à dimensionner : effort "
             "normal, contrainte, loi de Hooke, allongement.",
     "sub": "Quatre pièces sollicitées en traction ou en compression : calculer l'effort normal et la contrainte, "
            "vérifier la condition de résistance, appliquer la loi de Hooke et dimensionner une section."},
    {"key": "cisaillement", "prefix": "c", "tag": "Exercice 2", "title": "Cisaillement",
     "parts": PARTS[4:11], "docs": {"DP1": "DP1", "DT2": "DT1", "DT3": "DT2"}, "fig_shift": 4,
     "hero": ("c2-pince", "Pince à goupille : charges P sur les poignées, force de serrage dans les mâchoires",
              "La goupille de la pince transmet tout l'effort entre les deux branches."),
     "card": "Goupilles, boulons, vis et axe de chape : compter les sections cisaillées, calculer la contrainte "
             "de cisaillement, dimensionner un diamètre.",
     "sub": "Sept assemblages à vérifier ou à dimensionner : identifier le simple ou double cisaillement, "
            "calculer l'effort tranchant et la contrainte, en déduire une section ou une charge admissible."},
]

HOUSE = ('<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.3" '
         'stroke-linejoin="round" stroke-linecap="round"><path d="M3 11.5 12 4l9 7.5"/>'
         '<path d="M5.5 9.8V20h4.5v-5.5h4V20h4.5V9.8"/></svg>')

QLABEL = {}
CUR = {"total": 1}


def pct(minutes):
    return fr(minutes / CUR["total"] * 100, 1)


def render_part(p):
    pts = part_points(p)
    body = "\n      ".join(p["intro"])
    blocks = []
    for b in p["blocks"]:
        if b["kind"] == "q":
            blocks.append(render_q(b, p))
        elif b["kind"] == "qbar":
            blocks.append(render_qbar(b))
        elif b["kind"] == "sk":
            blocks.append(render_sk(b, p, pts))
        else:
            blocks.append(b["html"])
    n = p["num"]
    return f"""
  <section class="part" id="partie-{n}" aria-labelledby="t-partie-{n}">
    <header class="part-head"><div class="part-num" aria-hidden="true">{n}</div>
      <div><h2 id="t-partie-{n}"><span class="sr-only">Partie {n} : </span>{p['title']}</h2>
        <div class="duree">Durée conseillée : {hm(p['minutes'])} · Barème : {pts} points, soit {pct(p['minutes'])} % de la note</div></div></header>
    <div class="part-body">
      {body}{''.join(blocks)}
    </div>
  </section>"""


DATA_RE = re.compile(r"data:image/png;base64,[A-Za-z0-9+/=]+")


def map_text(html_, docs, fig_shift):
    """Renomme les documents (DT3 → DT2…) et les figures, sans toucher aux images encodées."""
    def one(seg):
        seg = re.sub(r"\b(DP1|DT1|DT2|DT3)\b", lambda m: docs.get(m.group(1), m.group(1)), seg)
        if fig_shift:
            seg = re.sub(r"Figure (\d+) — ", lambda m: f"Figure {int(m.group(1)) - fig_shift} — ", seg)
        return seg
    out, last = [], 0
    for m in DATA_RE.finditer(html_):
        out.append(one(html_[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(one(html_[last:]))
    return "".join(out)


def prepare_exo(e):
    """Copie et renumérote les parties d'un exercice ; calcule sa configuration."""
    parts = copy.deepcopy(e["parts"])
    idmap = {}
    for i, p in enumerate(parts):
        p["num"] = str(i + 1)
        # « Cisaillement : goupille… » → « Goupille… » dans l'exercice Cisaillement
        if p["title"].startswith(e["title"] + " : "):
            t = p["title"][len(e["title"]) + 3:]
            p["title"] = t[0].upper() + t[1:]
        p.pop("chapitre", None)
        for b in p["blocks"]:
            if b["kind"] in ("q", "sk"):
                suffix = b["id"].split("_")[-1]
                new = (f"sk_{e['prefix']}{p['num']}_{suffix}" if b["kind"] == "sk"
                       else f"{e['prefix']}{p['num']}_{suffix}")
                idmap[b["id"]] = new
                b["id"] = new
                b["label"] = f"Q{p['num']}.{suffix}"
                QLABEL[new] = b["label"]
            elif b["kind"] == "qbar":
                b["label"] = re.sub(r"Q\d+\.", f"Q{p['num']}.", b["label"])
    for p in parts:
        for b in p["blocks"]:
            if b["kind"] == "sk":
                b["deps"] = [idmap[d] for d in b["deps"]]
    e["P"] = parts
    e["minutes"] = sum(p["minutes"] for p in parts)
    e["n_q"] = sum(1 for p in parts for b in p["blocks"] if b["kind"] == "q")
    e["n_sk"] = sum(1 for p in parts for b in p["blocks"] if b["kind"] == "sk")
    e["points"] = sum(part_points(p) for p in parts)
    qcfg, skcfg, parts_cfg = {}, {}, []
    for p in parts:
        parts_cfg.append({"num": p["num"], "title": p["title"], "minutes": p["minutes"],
                          "duration": hm(p["minutes"]), "points": part_points(p)})
        for b in p["blocks"]:
            if b["kind"] == "q":
                qcfg[b["id"]] = {"label": b["label"], "part": p["num"], "pts": 1, "grader": b["grader"]}
            elif b["kind"] == "sk":
                skcfg[b["id"]] = {"bg": b["bg"], "deps": b["deps"], "label": b["label"], "part": p["num"],
                                  "pts": len(b["criteria"]),
                                  "criteria": [re.sub(r"<[^>]+>", "", c) for c in b["criteria"]]}
    e["cfg"] = {"title": e["title"], "minutes": e["minutes"], "duree": hm(e["minutes"]),
                "cartouche": f"{e['n_q']} questions notées (unités comprises) et {e['n_sk']} tracé"
                             f"{'s' if e['n_sk'] > 1 else ''} auto-évalué{'s' if e['n_sk'] > 1 else ''}, "
                             f"répartis en {len(parts)} parties pondérées par leur durée.",
                "parts": parts_cfg, "qcfg": qcfg, "skcfg": skcfg}


def render_docs(e):
    rail, tabs, secs = [], [], []
    first_dt = True
    for key, title, kind, is_dt, content in DOCS:
        if key not in e["docs"]:
            continue
        k = e["docs"][key]
        if is_dt and first_dt:
            rail.append('<div class="grp" aria-hidden="true"></div>')
            first_dt = False
        cls = "tab dt" if is_dt else "tab"
        rail.append(f'<button type="button" class="{cls}" data-doc="{k}" aria-selected="false" title="{esc(title)}">{k}</button>')
        tabs.append(f'<button type="button" data-doc="{k}" aria-selected="false">{k}</button>')
        secs.append(f'<section class="doc" id="doc-{k}" data-title="{k} : {esc(title)}" data-kind="{kind}">'
                    f'{map_text(content, e["docs"], 0)}\n</section>')
    return "".join(rail), "".join(tabs), "\n".join(secs)


def pastille(level):
    return f' <span class="pastille">{level}</span>' if level else ""


def render_exo_home(e):
    src, w, h = png(e["hero"][0])
    docs = sorted(set(e["docs"].values()), key=lambda k: (k[:2] != "DP", k))
    docs_txt = (", ".join(docs[:-1]) + " et " + docs[-1]) if len(docs) < 4 else f"{docs[0]} à {docs[-1]}"
    facts = ('<div class="home-facts">'
             f'<div><b>{len(e["P"])} parties</b><span>{e["n_q"]} questions</span></div>'
             f'<div><b>{hm(e["minutes"])}</b><span>durée conseillée</span></div>'
             f'<div><b>{len(docs)} documents</b><span>{docs_txt}</span></div>'
             f'<div><b>{e["n_sk"]} tracé</b><span>auto-évalué</span></div></div>')
    return (f'<div class="home-top"><div class="home-top-l"><header class="home-head"><span class="mc-tag">{e["tag"]}</span>{pastille(e.get("level"))}'
            f'<h1 id="home-title">{e["title"]}</h1><p class="home-sub">{e["sub"]}</p></header>{facts}</div>'
            f'<figure class="home-hero"><img src="{src}" alt="{esc(e["hero"][1])}" width="{w}" height="{h}">'
            f'<figcaption class="small">{e["hero"][2]}</figcaption></figure></div>')


MODES_HTML = """<h2 class="home-choose">Choisis ton mode de travail</h2>
<div class="modes">
  <article class="mode-card">
    <div class="mc-head"><span class="mc-tag">Mode 1</span><h3>Mode entraînement</h3></div>
    <p class="mc-lead">Pour apprendre en avançant, question par question.</p>
    <ul><li>Chaque question se valide isolément ; la démarche corrigée s'affiche aussitôt.</li>
      <li>La note pondérée s'actualise en continu dans le bandeau.</li>
      <li>Les documents et le chronomètre restent disponibles, sans contrainte de temps.</li></ul>
    <button type="button" class="btn btn-mode" data-mode="training">Commencer l'entraînement</button>
  </article>
  <article class="mode-card exam">
    <div class="mc-head"><span class="mc-tag">Mode 2</span><h3>Mode examen</h3></div>
    <p class="mc-lead">Pour se placer dans les conditions d'une évaluation.</p>
    <ul><li>Aucune correction et aucune note pendant la composition ; les réponses restent modifiables.</li>
      <li>Le chronomètre tourne, à comparer à la durée conseillée.</li>
      <li>En fin de sujet, le bouton « J'ai fini, je fais corriger ma copie » dévoile d'un coup les corrections, les notes par partie et la note globale.</li></ul>
    <button type="button" class="btn btn-mode" data-mode="exam">Composer en mode examen</button>
  </article>
</div>
<p class="home-note small">Le mode se choisit une seule fois : pour en changer, reviens à l'accueil (onglet maison) et rouvre l'exercice. Rien n'est enregistré sur l'ordinateur.</p>
<p class="home-back"><a class="btn ghost" href="?">""" + HOUSE + """ Retour à l'accueil</a></p>"""


COURS = [
    {"key": "cours-traction-bp", "tag": "Cours 1.1", "level": "Bac pro", "title": "Traction", "ready": True,
     "desc": "L'essai de traction, la contrainte, la condition de résistance ; avec un simulateur et un quiz."},
    {"key": "cours-traction", "tag": "Cours 1.2", "title": "Traction et compression", "ready": False,
     "desc": "Effort normal, loi de Hooke, allongement et dimensionnement."},
    {"key": "cours-cisaillement-bp", "tag": "Cours 2.1", "level": "Bac pro", "title": "Cisaillement", "ready": False,
     "desc": "Simple et double cisaillement, contrainte de cisaillement, condition de résistance."},
    {"key": "cours-cisaillement", "tag": "Cours 2.2", "title": "Cisaillement", "ready": False,
     "desc": "Effort tranchant, dimensionnement des goupilles, boulons et axes, glissement."},
]


def render_hub():
    src, w, h = png("accueil")
    cards = "".join(
        f'<article class="mode-card"><div class="mc-head"><span class="mc-tag">{e["tag"]}{pastille(e.get("level"))}'
        f'</span><h3>{e["title"]}</h3></div>'
        f'<p>{e["card"]}</p><p class="small ex-meta">{len(e["P"])} parties · {e["n_q"]} questions · '
        f'{e["n_sk"]} tracé · {hm(e["minutes"])}</p>'
        f'<a class="btn" href="?ex={e["key"]}">Ouvrir l\'exercice</a></article>' for e in EXO_DEFS)
    cours = "".join(
        f'<article class="mode-card cours-card{"" if c["ready"] else " en-edition"}"><div class="mc-head">'
        f'<span class="mc-tag">{c["tag"]}{pastille(c.get("level"))}</span><h3>{c["title"]}</h3></div>'
        f'<p>{c["desc"]}</p>' +
        ('<p class="small ex-meta">Disponible</p>' if c["ready"] else '<p class="small ex-meta etat">En cours d\'édition</p>') +
        f'<a class="btn{"" if c["ready"] else " ghost"}" href="?ex={c["key"]}">'
        f'{"Lire le cours" if c["ready"] else "Voir"}</a></article>' for c in COURS)
    return (f'<div class="home-top"><div class="home-top-l"><header class="home-head"><h1 id="home-title">{TITRE}</h1>'
            '<p class="home-sub">Traction, compression et cisaillement : calculer une contrainte, vérifier une pièce '
            'ou la dimensionner. Des cours et des exercices interactifs de deux niveaux, à faire en mode '
            'entraînement ou en mode examen.</p></header></div>'
            f'<figure class="home-hero"><img src="{src}" alt="À gauche, un siège suspendu par un fil et un tube '
            f'comprimé ; à droite, une pince à goupille et un axe de chape" width="{w}" height="{h}">'
            '<figcaption class="small">Quelques-unes des pièces étudiées dans les exercices.</figcaption></figure></div>'
            f'<h2 class="home-choose">Les cours</h2><div class="ex-grid cours-grid">{cours}</div>'
            f'<h2 class="home-choose">Les exercices</h2><div class="ex-grid">{cards}</div>'
            '<p class="home-note small">La pastille <span class="pastille">Bac pro</span> signale les cours et '
            'exercices de premier niveau. Chaque exercice propose le mode entraînement (correction question par '
            'question) ou le mode examen (correction à la remise de la copie). Rien n\'est enregistré sur '
            'l\'ordinateur.</p>')


def render_cours(c):
    return (f'<div class="home-top home-top-single"><div class="home-top-l"><header class="home-head">'
            f'<span class="mc-tag">{c["tag"]}</span>{pastille(c.get("level"))}<h1 id="home-title">{c["title"]}</h1>'
            '<p class="home-sub">Ce cours est en cours d\'édition : il sera mis en ligne prochainement.</p>'
            '</header></div></div>'
            '<section class="hub-course en-cours" aria-labelledby="ec-t"><div><h2 id="ec-t">En cours d\'édition</h2>'
            '<p>Le contenu de ce cours est en préparation.</p></div>'
            f'<div class="hub-btns"><a class="btn" href="?">{HOUSE} Retour à l\'accueil</a></div></section>')


# ============================================================ COURS 1.1 — TRACTION (niveau bac pro), interactif
ESSAI_SVG = """<svg class="essai-svg" viewBox="0 0 600 320" role="img" aria-labelledby="essai-t">
<title id="essai-t">Courbe de l'essai de traction : contrainte en fonction de l'allongement</title>
<defs><pattern id="hach" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
<line x1="0" y1="0" x2="0" y2="6" stroke="#1B7A43" stroke-width="2"/></pattern>
<marker id="fl" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0 0 10 5 0 10z" fill="#1C2530"/></marker></defs>
<g class="z z-secu" data-zone="secu"><polygon points="60,280 97,205 60,205" fill="url(#hach)"/>
<line x1="60" y1="205" x2="540" y2="205" stroke="#1B7A43" stroke-width="1.5" stroke-dasharray="6 4"/>
<text x="545" y="209" class="lab" fill="#1B7A43">Rpe</text></g>
<line x1="60" y1="130" x2="540" y2="130" class="guide"/><text x="545" y="134" class="lab">Re</text>
<line x1="60" y1="46" x2="540" y2="46" class="guide"/><text x="545" y="50" class="lab">R</text>
<line x1="60" y1="285" x2="60" y2="18" stroke="#1C2530" stroke-width="2" marker-end="url(#fl)"/>
<line x1="55" y1="280" x2="535" y2="280" stroke="#1C2530" stroke-width="2" marker-end="url(#fl)"/>
<text x="68" y="24" class="ax">contrainte σ (MPa)</text><text x="530" y="300" class="ax" text-anchor="end">allongement ΔL (mm)</text>
<path class="z z-elas" data-zone="elas" d="M60 280 L130 130"/>
<path class="z z-plast" data-zone="plast" d="M130 130 q6 -6 11 0 t11 0 t11 0 t11 0"/>
<path class="z z-plast" data-zone="plast" d="M174 130 C 215 60, 260 46, 300 46"/>
<path class="z z-rupt" data-zone="rupt" d="M300 46 C 360 46, 420 62, 470 100"/>
<g class="pt" data-zone="re"><circle class="hit" cx="130" cy="130" r="16"/><circle cx="130" cy="130" r="7"/><text x="122" y="118" text-anchor="end">Re</text></g>
<g class="pt" data-zone="rm"><circle class="hit" cx="300" cy="46" r="16"/><circle cx="300" cy="46" r="7"/><text x="300" y="34" text-anchor="middle">R</text></g>
<g class="pt" data-zone="rupt"><circle class="hit" cx="470" cy="100" r="16"/><circle cx="470" cy="100" r="7"/><text x="478" y="92">rupture</text></g>
</svg>"""

ETAPES = [
    ("elas", "Zone élastique", "La pièce s'allonge un peu, proportionnellement à l'effort, et <b>reprend sa longueur</b> "
     "quand on relâche — comme un ressort. C'est dans cette zone que doivent travailler les pièces."),
    ("re", "Limite élastique Re", "Fin de la zone élastique. Au-delà de <b>Re</b>, la déformation devient "
     "permanente. Re se lit dans les tableaux de matériaux, en MPa : c'est le nombre du nom de la nuance (E295 → 295 MPa)."),
    ("plast", "Zone plastique", "La pièce <b>reste allongée</b> même quand on relâche l'effort : elle est déformée "
     "pour de bon, donc hors d'usage."),
    ("rm", "Résistance à la rupture R", "La plus grande contrainte que supporte l'éprouvette. Ensuite, elle "
     "s'amincit à un endroit (striction)…"),
    ("rupt", "Rupture", "…et finit par casser. On ne fait <b>jamais</b> travailler une pièce près de ce point."),
    ("secu", "Zone de sécurité", "Sous la résistance pratique <b>Rpe = Re / s</b>, on garde une marge : c'est la zone "
     "où l'on fait travailler les pièces. Le coefficient de sécurité <i>s</i> fixe cette marge."),
]

QUIZ = [
    ("Une contrainte s'exprime en…", ["MPa (ou N/mm²)", "N", "mm²", "kg"], 0,
     "σ = F / S : des newtons divisés par des mm², soit des N/mm², c'est-à-dire des MPa."),
    ("Même force, section deux fois plus petite : la contrainte est…",
     ["deux fois plus grande", "deux fois plus petite", "identique"], 0,
     "On divise la même force par une section deux fois plus petite : la contrainte double."),
    ("Dans la zone élastique, quand on relâche l'effort, la pièce…",
     ["reprend sa longueur", "reste allongée", "casse"], 0,
     "C'est la définition de la zone élastique : la déformation disparaît."),
    ("Acier E235, coefficient de sécurité s = 5. Que vaut Rpe ?", ["47 MPa", "1 175 MPa", "230 MPa", "235 MPa"], 0,
     "Re = 235 MPa (le nombre de la nuance), Rpe = Re / s = 235 / 5 = 47 MPa."),
    ("σ = 60 MPa et Rpe = 47 MPa : la pièce résiste-t-elle en toute sécurité ?", ["Non", "Oui"], 0,
     "La condition σ ≤ Rpe n'est pas respectée : 60 MPa > 47 MPa."),
    ("Pour un appareil de levage (manutention), on choisit un coefficient de sécurité…",
     ["entre 5 et 8", "entre 1,5 et 2", "entre 3 et 4"], 0,
     "Tableau des coefficients : 5 à 8 pour les appareils de levage, car les efforts sont difficiles à évaluer."),
]


def render_cours_bp():
    ep_src, ew, eh = png("bp-eprouvette")
    steps = "".join(f'<button type="button" class="etape" data-zone="{z}" aria-pressed="false">'
                    f'<b>{i + 1}</b> {t}</button>' for i, (z, t, _) in enumerate(ETAPES))
    expl = "".join(f'<p class="etape-txt" data-zone="{z}" hidden><strong>{t}.</strong> {d}</p>' for z, t, d in ETAPES)
    mats = "".join(f'<option value="{e}"{" selected" if n.startswith("E295") else ""}>{n} — Re = {e} MPa</option>'
                   for n, r, e in MATERIAUX)
    mat_rows = "".join(f'<tr data-re="{e}" tabindex="0"><td>{n}</td><td>{r}</td><td>{e}</td></tr>'
                       for n, r, e in MATERIAUX)
    coef_rows = "".join(f"<tr><td><b>{c}</b></td><td>{t}</td></tr>" for c, t in COEFS)
    quiz = "".join(
        f'<fieldset class="quiz-q" data-ok="{ok}"><legend><span class="q-num">{i + 1}</span> {q}</legend>' +
        "".join(f'<label><input type="radio" name="qz{i}" value="{j}"> {o}</label>' for j, o in enumerate(opts)) +
        f'<p class="quiz-fb" aria-live="polite"></p><p class="quiz-why" hidden>{why}</p></fieldset>'
        for i, (q, opts, ok, why) in enumerate(QUIZ))
    nav = "".join(f'<a href="#{a}">{n}. {t}</a>' for n, (a, t) in enumerate(
        [("c-essai", "L'essai"), ("c-sigma", "La contrainte"), ("c-cond", "La condition de résistance"),
         ("c-quiz", "Quiz")], 1))
    return f"""<div class="cours" id="cours-bp">
<div class="home-top home-top-single"><div class="home-top-l"><header class="home-head"><span class="mc-tag">Cours 1.1</span>{pastille("Bac pro")}
<h1 id="home-title">Traction</h1><p class="home-sub">Comprendre l'essai de traction, calculer une contrainte et vérifier
qu'une pièce résiste. Environ 20 minutes : explore la courbe, joue avec le simulateur, puis teste-toi avec le quiz.</p>
</header></div></div>
<nav class="cours-nav no-print" aria-label="Étapes du cours">{nav}</nav>

<section class="part cours-sec" id="c-essai" aria-labelledby="c-essai-t"><header class="part-head"><div class="part-num" aria-hidden="true">1</div>
<div><h2 id="c-essai-t" style="padding:14px 16px">L'essai de traction</h2></div></header><div class="part-body">
<div class="cours-split"><figure class="fig" style="max-width:220px"><img src="{ep_src}" width="{ew}" height="{eh}"
alt="Éprouvette cylindrique serrée entre deux mors, tirée par deux forces F opposées"><figcaption>L'éprouvette, de longueur
initiale L<sub>0</sub> et de section S<sub>0</sub>, est tirée entre deux mors.</figcaption></figure>
<div><p>On tire sur une pièce cylindrique, appelée <strong>éprouvette</strong>, avec une force de plus en plus grande. Elle
s'allonge, se déforme, puis finit par casser. La machine enregistre la courbe ci-dessous.</p>
<p class="cours-defi">À toi : clique sur chaque étape pour découvrir ce qui arrive à l'éprouvette.</p>
<div class="etapes" role="group" aria-label="Étapes de l'essai">{steps}</div></div></div>
<div class="essai">{ESSAI_SVG}<div class="essai-txt">{expl}<p class="etape-vide">Choisis une étape ou clique sur un point de la courbe.</p></div></div>
</div></section>

<section class="part cours-sec" id="c-sigma" aria-labelledby="c-sigma-t"><header class="part-head"><div class="part-num" aria-hidden="true">2</div>
<div><h2 id="c-sigma-t" style="padding:14px 16px">La contrainte σ (sigma)</h2></div></header><div class="part-body">
<p>La contrainte représente l'effort que subit chaque millimètre carré de la section. On la calcule en divisant la force
par la section :</p>
<div class="formule"><span class="f-main"><i>σ</i> = {frac("<i>F</i>", "<i>S</i>")}</span>
<span class="f-units"><i>σ</i> en MPa (N/mm²)<br><i>F</i> en newtons (N)<br><i>S</i> en mm²</span></div>
<p><strong>Retiens :</strong> plus la section est petite, plus la contrainte est grande.</p>
<div class="simu" id="simu"><h3>Simulateur</h3>
<div class="simu-grid">
<label><span>Force <i>F</i> : <output id="o-f">5 000 N</output></span><input type="range" id="s-f" min="100" max="20000" step="100" value="5000"></label>
<label><span>Diamètre <i>d</i> : <output id="o-d">8 mm</output></span><input type="range" id="s-d" min="2" max="20" step="0.5" value="8"></label>
<label><span>Matériau</span><select id="s-m">{mats}</select></label>
<label><span>Coefficient de sécurité <i>s</i></span><select id="s-s">{"".join(f'<option{" selected" if v == 5 else ""}>{v}</option>' for v in (2, 3, 4, 5, 6, 8, 10))}</select></label>
</div>
<div class="simu-out"><div><span>Section</span><b id="r-s"></b></div><div><span>Contrainte σ</span><b id="r-sig"></b></div>
<div><span>Résistance pratique Rpe</span><b id="r-rpe"></b></div></div>
<div class="jauge" aria-hidden="true"><div class="jauge-bar" id="r-bar"></div><div class="jauge-lim"></div></div>
<p class="simu-verdict" id="r-v" aria-live="polite"></p>
<details class="simu-defi"><summary>Défi : avec <i>F</i> = 10 000 N, de l'acier E295 et <i>s</i> = 5, quel est le plus petit diamètre du simulateur qui résiste ?</summary>
<p>Rpe = 295 / 5 = 59 MPa ; il faut <i>S</i> ≥ 10 000 / 59 ≈ 169,5 mm², soit <i>d</i> ≥ 14,7 mm. Dans le simulateur :
<b>d = 15 mm</b> (176,7 mm², σ ≈ 56,6 MPa).</p></details>
</div></div></section>

<section class="part cours-sec" id="c-cond" aria-labelledby="c-cond-t"><header class="part-head"><div class="part-num" aria-hidden="true">3</div>
<div><h2 id="c-cond-t" style="padding:14px 16px">La condition de résistance</h2></div></header><div class="part-body">
<p>Pour des raisons de sécurité, la contrainte doit rester inférieure à une limite appelée <strong>résistance pratique
à l'extension</strong>, notée <i>R</i><sub>pe</sub> :</p>
<div class="formule"><span class="f-main"><i>σ</i> = {frac("<i>F</i>", "<i>S</i>")} ≤ <i>R</i><sub>pe</sub> = {frac("<i>R</i><sub>e</sub>", "<i>s</i>")}</span>
<span class="f-units"><i>R</i><sub>e</sub> : résistance élastique (MPa)<br><i>s</i> : coefficient de sécurité (sans unité)</span></div>
<p>Le coefficient de sécurité obtenu se calcule aussi : <i>s</i> = <i>R</i><sub>e</sub> / <i>σ</i>. Plus il est grand,
plus la pièce a de la marge.</p>
<div class="cours-tables"><div><h3>Quelques aciers</h3><p class="small no-print">Clique sur une ligne pour l'essayer dans le simulateur.</p>
<table class="t mat-table"><thead><tr><th>Nuance</th><th>R min (MPa)</th><th>Re min (MPa)</th></tr></thead><tbody>{mat_rows}</tbody></table></div>
<div><h3>Choisir le coefficient de sécurité</h3><table class="t"><thead><tr><th>s</th><th>Conditions de calcul</th></tr></thead><tbody>{coef_rows}</tbody></table></div></div>
<div class="exemple"><h3>Exemple résolu</h3><p>Un câble Ø8 en acier E295 porte 10 kN ; on veut <i>s</i> = 5.</p><ol>
<li><i>S</i> = π × 8² / 4 ≈ 50,27 mm²</li><li><i>σ</i> = 10 000 / 50,27 ≈ 198,9 MPa</li>
<li><i>R</i><sub>pe</sub> = 295 / 5 = 59 MPa</li><li>198,9 MPa &gt; 59 MPa : le câble <strong>ne convient pas</strong>.</li></ol></div>
</div></section>

<section class="part cours-sec" id="c-quiz" aria-labelledby="c-quiz-t"><header class="part-head"><div class="part-num" aria-hidden="true">4</div>
<div><h2 id="c-quiz-t" style="padding:14px 16px">Quiz : vérifie tes connaissances</h2></div></header><div class="part-body">
<p>Choisis une réponse : la correction s'affiche aussitôt.</p>
<div class="quiz">{quiz}</div>
<div class="quiz-score" aria-live="polite"><span id="qz-score">0 / {len(QUIZ)}</span><span id="qz-stars" aria-hidden="true"></span>
<button type="button" class="btn ghost" id="qz-reset">Recommencer</button></div>
</div></section>

<div class="cours-foot no-print"><a class="btn" href="?ex=traction-bp">S'entraîner : Exercice 1.1</a>
<button type="button" class="btn ghost" id="cours-print">Imprimer le cours</button>
<a class="btn ghost" href="?">{HOUSE} Retour à l'accueil</a></div>
</div>"""


COURS_JS = r"""
  function initCoursBp(root) {
    function q(s) { return root.querySelector(s); }
    function qa(s) { return Array.prototype.slice.call(root.querySelectorAll(s)); }
    function fr(x, d) { return x.toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d }); }
    // 1. courbe de l'essai : étapes cliquables
    function show(zone) {
      qa("[data-zone]").forEach(function (el) {
        var on = el.getAttribute("data-zone") === zone;
        if (el.classList.contains("etape")) el.setAttribute("aria-pressed", on ? "true" : "false");
        else if (el.classList.contains("etape-txt")) el.hidden = !on;
        else el.classList.toggle("on", on);
      });
      q(".etape-vide").hidden = true;
    }
    qa(".etape, .essai-svg [data-zone]").forEach(function (el) {
      el.addEventListener("click", function () { show(el.getAttribute("data-zone")); });
    });
    // 2. simulateur
    var F = q("#s-f"), D = q("#s-d"), M = q("#s-m"), SF = q("#s-s");
    function calc() {
      var f = +F.value, d = +D.value, re = +M.value, s = +SF.value;
      var S = Math.PI * d * d / 4, sig = f / S, rpe = re / s, ok = sig <= rpe;
      q("#o-f").textContent = fr(f, 0) + " N";
      q("#o-d").textContent = fr(d, d % 1 ? 1 : 0) + " mm";
      q("#r-s").textContent = fr(S, 2) + " mm²";
      q("#r-sig").textContent = fr(sig, 2) + " MPa";
      q("#r-rpe").textContent = fr(rpe, 2) + " MPa";
      var bar = q("#r-bar");
      bar.style.width = Math.min(100, sig / rpe * 50) + "%";
      bar.classList.toggle("ko", !ok);
      q("#r-v").className = "simu-verdict " + (ok ? "ok" : "ko");
      q("#r-v").textContent = ok ? "✔ σ ≤ Rpe : la pièce résiste, avec la marge de sécurité choisie."
        : (sig <= re ? "✘ σ > Rpe : la marge de sécurité n'est pas respectée (mais σ reste sous Re)."
                     : "✘ σ > Re : la pièce se déforme définitivement !");
    }
    [F, D, M, SF].forEach(function (el) { el.addEventListener("input", calc); el.addEventListener("change", calc); });
    qa(".mat-table tr[data-re]").forEach(function (tr) {
      function pick() {
        M.value = tr.getAttribute("data-re"); calc();
        qa(".mat-table tr").forEach(function (x) { x.classList.toggle("sel", x === tr); });
        q("#simu").scrollIntoView({ behavior: "smooth", block: "center" });
      }
      tr.addEventListener("click", pick);
      tr.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
    });
    calc();
    // 4. quiz
    var qs = qa(".quiz-q");
    function score() {
      var n = qs.filter(function (f) { return f.classList.contains("is-ok"); }).length;
      var done = qs.filter(function (f) { return f.classList.contains("done"); }).length;
      q("#qz-score").textContent = n + " / " + qs.length;
      q("#qz-stars").textContent = done === qs.length ? "★★★".slice(0, n === qs.length ? 3 : n >= qs.length - 2 ? 2 : n >= 2 ? 1 : 0) +
        "☆☆☆".slice(0, 3 - (n === qs.length ? 3 : n >= qs.length - 2 ? 2 : n >= 2 ? 1 : 0)) : "";
    }
    qs.forEach(function (fs) {
      fs.addEventListener("change", function (e) {
        if (fs.classList.contains("done")) return;
        var ok = e.target.value === fs.getAttribute("data-ok");
        fs.classList.add("done", ok ? "is-ok" : "is-ko");
        fs.querySelector(".quiz-fb").textContent = ok ? "✔ Bonne réponse !" : "✘ Pas tout à fait.";
        fs.querySelector(".quiz-why").hidden = false;
        Array.prototype.forEach.call(fs.querySelectorAll("input"), function (i) {
          i.disabled = true;
          if (i.value === fs.getAttribute("data-ok")) i.parentNode.classList.add("good");
        });
        score();
      });
    });
    q("#qz-reset").addEventListener("click", function () {
      qs.forEach(function (fs) {
        fs.classList.remove("done", "is-ok", "is-ko");
        fs.querySelector(".quiz-fb").textContent = "";
        fs.querySelector(".quiz-why").hidden = true;
        Array.prototype.forEach.call(fs.querySelectorAll("input"), function (i) { i.disabled = false; i.checked = false; i.parentNode.classList.remove("good"); });
      });
      score();
    });
    score();
    q("#cours-print").addEventListener("click", function () { window.print(); });
  }
"""

COURS_CSS = """
/* ---------- pastille de niveau et cartes des cours ---------- */
.pastille{display:inline-block; font:700 .72rem var(--f-titre); letter-spacing:.03em; background:var(--vert); color:#fff; padding:2px 8px; margin-left:6px; vertical-align:middle}
.mc-tag .pastille{margin-left:8px; font-size:.68rem; padding:1px 6px}
.ex-grid .en-edition{border-style:dashed; border-color:var(--trait)}
.ex-grid .en-edition h3,.ex-grid .en-edition p{color:var(--encre-2)}
.ex-grid .etat{font-weight:700; color:var(--orange)}
#home .home-choose{margin-top:18px}
.cours-grid{grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}

/* ---------- cours interactif ---------- */
.cours .part{margin-bottom:22px}
.cours-nav{display:flex; flex-wrap:wrap; gap:6px; margin:0 0 16px}
.cours-nav a{font:600 .92rem var(--f-titre); color:var(--encre); background:var(--papier); border:1.5px solid var(--encre); padding:5px 12px; text-decoration:none}
.cours-nav a:hover{background:var(--jaune-pale)}
.cours-split{display:flex; gap:18px; align-items:flex-start; flex-wrap:wrap}
.cours-split>div{flex:1 1 300px}
.cours-defi{font-weight:700; color:var(--bleu)}
.etapes{display:flex; flex-wrap:wrap; gap:6px}
.etape{border:1.5px solid var(--encre); background:#fff; padding:6px 10px; cursor:pointer; font:600 .9rem var(--f-titre)}
.etape b{display:inline-block; background:var(--encre); color:var(--jaune); padding:0 6px; margin-right:4px}
.etape[aria-pressed="true"]{background:var(--jaune)}
.essai{display:grid; grid-template-columns:minmax(0,1.5fr) minmax(0,1fr); gap:14px; align-items:center; margin:12px 0 6px}
@media (max-width:760px){ .essai{grid-template-columns:1fr} }
.essai-svg{width:100%; height:auto; background:#fff; border:1px solid var(--trait-fin)}
.essai-svg .z{fill:none; stroke:var(--encre); stroke-width:3.5; cursor:pointer; transition:stroke .15s, stroke-width .15s}
.essai-svg g.z{stroke:none}
.essai-svg .z.on{stroke:var(--jaune); stroke-width:8}
.essai-svg g.z-secu{opacity:.45}
.essai-svg g.z-secu.on{opacity:1}
.essai-svg .guide{stroke:#9AA2A8; stroke-width:1; stroke-dasharray:4 4}
.essai-svg .lab,.essai-svg .ax{font:600 13px var(--f-texte); fill:var(--encre-2)}
.essai-svg .pt{cursor:pointer}
.essai-svg .pt circle{fill:#fff; stroke:var(--encre); stroke-width:2.5}
.essai-svg .pt circle.hit{fill:transparent; stroke:none}
.essai-svg .pt text{font:700 14px var(--f-titre); fill:var(--encre)}
.essai-svg .pt.on circle:not(.hit){fill:var(--jaune)}
.essai-txt{background:var(--jaune-pale); border-left:5px solid var(--jaune); padding:10px 14px; min-height:110px}
.essai-txt p{margin:0}
.formule{display:flex; flex-wrap:wrap; gap:14px 28px; align-items:center; border:2px solid var(--rouge); background:#fff; padding:10px 18px; margin:12px 0; max-width:620px}
.formule .f-main{font:700 1.5rem var(--f-titre); line-height:2}
.formule .f-units{font-size:.9rem; color:var(--encre-2)}
.simu{border:2px solid var(--bleu); background:var(--bleu-pale); padding:12px 16px; margin:14px 0}
.simu h3{margin:0 0 8px; font:700 1.15rem var(--f-titre); color:var(--bleu)}
.simu-grid{display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px 18px}
@media (max-width:640px){ .simu-grid{grid-template-columns:1fr} }
.simu-grid label{display:flex; flex-direction:column; gap:4px; font-weight:600; font-size:.92rem}
.simu-grid output{font:700 1rem var(--f-titre); color:var(--bleu)}
.simu-grid input[type=range]{width:100%; accent-color:var(--bleu)}
.simu-grid select{padding:5px; border:1.5px solid var(--encre-2); background:#fff}
.simu-out{display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; margin:12px 0 8px}
.simu-out div{background:var(--encre); color:#fff; padding:6px 10px}
.simu-out span{display:block; font-size:.78rem; color:#D7DDE2}
.simu-out b{font:700 1.1rem var(--f-titre); color:var(--jaune)}
@media (max-width:640px){ .simu-out{grid-template-columns:1fr} }
.jauge{position:relative; height:16px; background:#fff; border:1px solid var(--trait)}
.jauge-bar{height:100%; background:var(--vert); transition:width .2s}
.jauge-bar.ko{background:var(--rouge)}
.jauge-lim{position:absolute; left:50%; top:-4px; bottom:-4px; border-left:3px solid var(--encre)}
.jauge-lim::after{content:"Rpe"; position:absolute; top:-18px; left:-12px; font:700 .75rem var(--f-titre)}
.simu-verdict{font-weight:700; margin:8px 0 4px}
.simu-verdict.ok{color:var(--vert)} .simu-verdict.ko{color:var(--rouge)}
.simu-defi{margin-top:8px; background:#fff; border:1px dashed var(--bleu); padding:6px 10px}
.simu-defi summary{cursor:pointer; font-weight:600}
.cours-tables{display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.3fr); gap:18px}
@media (max-width:820px){ .cours-tables{grid-template-columns:1fr} }
.cours-tables h3,.exemple h3{font:700 1.05rem var(--f-titre); margin:10px 0 4px}
.mat-table tbody tr{cursor:pointer}
.mat-table tbody tr:hover,.mat-table tbody tr.sel{background:var(--jaune-pale)}
.exemple{background:#F6F7F4; border:1px solid var(--trait-fin); padding:6px 16px; margin-top:12px}
.quiz{display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:12px}
.quiz-q{border:1.5px solid var(--encre); background:#fff; padding:8px 14px 10px; margin:0}
.quiz-q legend{font-weight:700; padding:0 4px}
.quiz-q label{display:block; padding:3px 0; cursor:pointer}
.quiz-q.is-ok{border-color:var(--vert); background:var(--vert-pale)}
.quiz-q.is-ko{border-color:var(--rouge); background:var(--rouge-pale)}
.quiz-q label.good{font-weight:700; color:var(--vert)}
.quiz-fb{margin:4px 0 0; font-weight:700}
.quiz-q.is-ok .quiz-fb{color:var(--vert)} .quiz-q.is-ko .quiz-fb{color:var(--rouge)}
.quiz-why{margin:2px 0 0; font-size:.9rem}
.quiz-score{display:flex; align-items:center; gap:14px; margin:14px 0 0; font:700 1.3rem var(--f-titre)}
#qz-stars{color:var(--jaune); font-size:1.6rem; letter-spacing:2px}
.cours-foot{display:flex; flex-wrap:wrap; gap:10px; margin:6px 0 0}
@media print{
  body.cours-page #home{display:block!important; padding:0}
  .no-print,.cours-nav,.cours-foot,.simu-defi summary~*{display:none!important}
  .essai-txt p[hidden],.quiz-why[hidden]{display:block!important}
  .etape-vide{display:none!important}
}
"""


ROUTER_JS = r"""<script>/* Aiguillage : accueil, cours ou exercice selon ?ex=… — s'exécute avant les moteurs du gabarit */
(function () {
  "use strict";
  var EXOS = window.__EXOS__, ex = new URLSearchParams(location.search).get("ex") || "";
  function $(s) { return document.querySelector(s); }
  function tpl(id) { return document.getElementById(id).innerHTML; }__COURS_JS__
  var home = $("#home .home-inner");
  window.__PARTS__ = []; window.__QCFG__ = {}; window.__SKCFG__ = {}; window.__CONSEIL_MIN__ = 0;
  if (Object.prototype.hasOwnProperty.call(EXOS, ex)) {
    var E = EXOS[ex];
    window.__PARTS__ = E.parts; window.__QCFG__ = E.qcfg; window.__SKCFG__ = E.skcfg;
    window.__CONSEIL_MIN__ = E.minutes;
    document.title = E.title + " — __TITRE__ — exercice interactif";
    document.body.classList.add("exo-" + ex);
    $(".rail").innerHTML = tpl("tpl-rail-" + ex) + '<div class="grp" aria-hidden="true"></div>' +
      '<a class="tab tab-home" href="?" title="Retour à l\'accueil" aria-label="Retour à l\'accueil">__HOUSE__</a>';
    $(".dp-tabs").innerHTML = tpl("tpl-tabs-" + ex);
    $(".dp-body").innerHTML = tpl("tpl-docs-" + ex);
    $("#parts").innerHTML = tpl("tpl-parts-" + ex);
    home.innerHTML = tpl("tpl-home-" + ex) + tpl("tpl-modes");
    $(".cartouche h1").textContent = E.title;
    $(".cartouche .title p").textContent = E.cartouche;
    Array.prototype.forEach.call(document.querySelectorAll(".print-conseil"), function (el) { el.textContent = E.duree; });
  } else {
    document.body.classList.add("hub");
    var page = document.getElementById("tpl-" + ex) && /^cours-/.test(ex) ? "tpl-" + ex : "tpl-hub";
    home.innerHTML = tpl(page);
    if (page !== "tpl-hub") document.body.classList.add("cours-page");
    if (ex === "cours-traction-bp") initCoursBp(home);
    if (page !== "tpl-hub") document.title = home.querySelector("h1").textContent + " — cours — __TITRE__";
    else document.title = "__TITRE__ — cours et exercices interactifs";
  }
})();
</script>"""


CONTENT_CSS = """<style>
/* ---------- compléments de contenu (hors gabarit) : écriture des calculs, documents ---------- */
.eq{margin:.35rem 0 .55rem; overflow-x:auto; line-height:2.1}
.eq b{background:#fff; border:1px solid var(--trait); padding:0 .3rem; white-space:nowrap}
.frac{display:inline-flex; flex-direction:column; vertical-align:middle; text-align:center; margin:0 .12em; line-height:1.25}
.frac>span{padding:0 .25em; white-space:nowrap}
.frac>span:first-child{border-bottom:1px solid currentColor}
.sqrt{white-space:nowrap; display:inline-flex; align-items:stretch; vertical-align:middle}
.sqrt>.radix{display:flex; align-items:flex-end; font-size:1.1em; line-height:1; margin-right:-.12em}
.sqrt>.rad{border-top:1.2px solid currentColor; border-left:1.2px solid currentColor; padding:.12em .2em 0 .25em; line-height:1.35; display:inline-flex; align-items:center}
.doc-text ol,.doc-text ul{padding-left:1.2rem}
.doc-text li{margin:.2rem 0}

/* ---------- accueil, cours et retour (d'après la page « Ajustements ») ---------- */
a.btn{display:inline-flex; align-items:center; gap:8px; text-decoration:none}
a.btn svg,.c-top svg{width:18px; height:18px; flex:0 0 auto}
.tab-home{display:flex; align-items:center; justify-content:center; padding:8px 0 8px 4px; background:var(--encre); color:var(--jaune); text-decoration:none}
.tab-home svg{width:22px; height:22px; display:block}
.tab-home:hover{background:#2E3B47}
.c-top{margin:0 0 12px}
.c-top a{display:inline-flex; align-items:center; gap:6px; font:600 .95rem var(--f-titre); color:var(--encre); text-decoration:none; border:1.5px solid var(--encre); background:var(--papier); padding:5px 12px 5px 10px}
.c-top a:hover{background:var(--jaune-pale)}
#home{padding:20px 20px 32px}
.home-top{display:grid; grid-template-columns:minmax(0,1.6fr) minmax(0,1fr); gap:14px; align-items:stretch; margin:0 0 14px}
.home-top-single{grid-template-columns:1fr}
.home-top-l{display:flex; flex-direction:column; gap:10px; min-width:0}
.home-top .home-head{padding:14px 20px; flex:1}
.home-top .home-head h1{margin:6px 0 6px; font-size:clamp(1.4rem,2.4vw,1.85rem)}
.home-top .home-sub{font-size:.95rem}
.home-top .home-hero{margin:0; padding:8px; display:flex; flex-direction:column; justify-content:center; min-width:0}
.home-top .home-hero img{width:auto!important; max-width:100%; max-height:160px; margin:0 auto}
body.hub .home-top .home-hero img{max-height:200px}
.home-top .home-hero figcaption{font-size:.78rem; line-height:1.3; margin-top:4px}
.home-top .home-facts{grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; margin:0}
.home-top .home-facts div{padding:6px 10px}
.home-top .home-facts b{font-size:1.02rem}
.home-top .home-facts span{font-size:.76rem; line-height:1.3; display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
@media (max-width:980px){ .home-top .home-facts{grid-template-columns:repeat(2,minmax(0,1fr))} }
@media (max-width:820px){ .home-top{grid-template-columns:1fr} }
#home .home-choose{margin:0 0 8px; font-size:1.25rem}
#home .mode-card{padding:12px 18px 14px}
#home .mode-card .mc-lead{margin:2px 0 4px; font-size:.92rem}
#home .mode-card ul{margin:0 0 10px; font-size:.9rem; line-height:1.45}
#home .mode-card li{margin:.15rem 0}
#home .mode-card .btn{padding:9px 16px}
#home .home-note{margin:10px 0 0}
.home-back{margin:12px 0 0}
.hub-course{display:grid; grid-template-columns:minmax(0,1fr) auto; gap:14px 22px; align-items:center; background:var(--encre); color:#fff; border-left:10px solid var(--jaune); padding:14px 22px; margin:0 0 20px}
.hub-course h2{margin:0 0 4px; font:700 1.45rem var(--f-titre); color:var(--jaune)}
.hub-course p{margin:0; color:#D7DDE2; max-width:70ch}
.hub-btns{display:flex; flex-wrap:wrap; gap:10px; justify-content:flex-end}
.hub-course .btn{background:var(--jaune); color:var(--encre); border-color:var(--jaune); padding:11px 18px; white-space:nowrap}
.hub-course .btn:hover{background:#FFD24A}
@media (max-width:640px){ .hub-course{grid-template-columns:minmax(0,1fr)} .hub-btns{justify-content:flex-start} .hub-course .btn{white-space:normal} }
.ex-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:16px}
.ex-grid .mode-card p{margin:4px 0 8px; font-size:.95rem}
.ex-grid .mode-card .ex-meta{margin:0 0 12px; font-size:.85rem}
.ex-grid .mode-card h3{font-size:1.2rem}
.ex-grid .mc-head{flex-direction:column; align-items:flex-start; gap:6px}
.ex-grid .mode-card .btn{margin-top:auto; align-self:flex-start}

__COURS_CSS__
@media print{
  .c-top,.home-back{display:none!important}
  /* correctif : dans le gabarit, « .sketch .q-expl[hidden] » l'emporte sur « body:not(.corrections-open) .q-expl »
     et imprimerait la correction des tracés en mode examen avant la remise de la copie */
  body:not(.corrections-open) .sketch .q-expl[hidden]{display:none!important}
  .eq{overflow:visible; line-height:1.7}
}
</style>"""


def build():
    g = GABARIT.read_text(encoding="utf-8")

    # le commentaire d'en-tête du gabarit cite « <style> » : on part de la vraie balise
    s0 = g.index("<style>:root{")
    style = g[s0:g.index("</style>", s0) + len("</style>")]
    grading = re.search(r"<script>/\*GRADING-START\*/.*?</script>", g, re.S).group(0)
    app_start = g.index("<script>(function () {")
    app = g[app_start:g.rindex("</script>") + len("</script>")]

    def sub_once(text, pattern, repl, flags=0):
        new, n = re.subn(pattern, lambda m: repl, text, flags=flags)
        assert n == 1, f"motif introuvable ou multiple : {pattern!r} ({n})"
        return new

    # entrées du moteur réservées au sujet ; la durée conseillée dépend de l'exercice ouvert
    app = sub_once(app, r"var CONSEIL_MIN = \d+;", "var CONSEIL_MIN = window.__CONSEIL_MIN__ || 0;")
    app = sub_once(app, r"  var DECOR = \{\n.*?\n  \};\n", DECOR_JS, re.S)
    app = sub_once(app, r"  var DR_NAMES = \{\n.*?\n  \};\n", DR_NAMES_JS, re.S)
    app = sub_once(app, r"Quatre pages, une par document", "Une page par document réponse")

    templates, exos_cfg = [], {}
    for e in EXO_DEFS:
        prepare_exo(e)
    for e in EXO_DEFS:
        CUR["total"] = e["minutes"]
        parts_html = map_text("".join(render_part(p) for p in e["P"]), e["docs"], e["fig_shift"])
        rail, tabs, secs = render_docs(e)
        k = e["key"]
        templates += [f'<template id="tpl-rail-{k}">{rail}</template>',
                      f'<template id="tpl-tabs-{k}">{tabs}</template>',
                      f'<template id="tpl-docs-{k}">{secs}</template>',
                      f'<template id="tpl-home-{k}">{render_exo_home(e)}</template>',
                      f'<template id="tpl-parts-{k}">{parts_html}\n</template>']
        exos_cfg[k] = e["cfg"]
    templates.append(f'<template id="tpl-modes">{MODES_HTML}</template>')
    templates.append(f'<template id="tpl-hub">{render_hub()}</template>')
    for c in COURS:
        body = render_cours_bp() if c["key"] == "cours-traction-bp" else render_cours(c)
        templates.append(f'<template id="tpl-{c["key"]}">{body}</template>')

    config = f"<script>window.__EXOS__ = {json.dumps(exos_cfg, ensure_ascii=False)};</script>"
    router = ROUTER_JS.replace("__COURS_JS__", COURS_JS).replace("__TITRE__", TITRE).replace("__HOUSE__", HOUSE.replace("'", "\\'"))

    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITRE} — cours et exercices interactifs</title>
<meta name="description" content="Traction, compression et cisaillement : effort normal, contrainte, loi de Hooke, allongement ; effort tranchant, simple et double cisaillement, dimensionnement d'axes, de goupilles et de boulons.">
{style}
{CONTENT_CSS.replace("__COURS_CSS__", COURS_CSS)}
</head>
<body class="no-mode">

<nav class="rail" aria-label="Dossiers de présentation et dossier technique"></nav>

<aside id="docpanel" aria-label="Documents du sujet" aria-hidden="true">
  <div class="dp-head">
    <h3 id="dp-title">Documents</h3>
    <button type="button" id="dp-out" aria-label="Réduire">−</button><span id="dp-zoom" class="small">100 %</span>
    <button type="button" id="dp-in" aria-label="Agrandir">+</button>
    <button type="button" id="dp-fit">Ajuster</button>
    <button type="button" id="dp-close">Fermer</button>
  </div>
  <div class="dp-tabs" role="tablist" aria-label="Choisir un document"></div>
  <div class="dp-body"></div>
</aside>

<section id="home" aria-labelledby="home-title"><div class="home-inner"></div></section>

<main class="page">
  <section class="print-only print-summary">
    <p>Élève : <span class="print-nom"></span> | Copie imprimée le <span class="print-date"></span></p>
    <p>Mode : <span class="print-mode"></span> | Temps de rédaction : <strong class="print-time"></strong> (durée conseillée : <span class="print-conseil"></span>)</p>
    <p class="print-note-line">Note finale pondérée : <strong class="final-note"></strong></p>
    <p class="print-nograde">Copie non corrigée : les corrections et la note n'apparaissent qu'après la remise de la copie en mode examen.</p>
  </section>

  <nav class="c-top" aria-label="Navigation"><a href="?">{HOUSE} Accueil</a></nav>

  <header class="cartouche">
    <div class="title">
      <h1>{TITRE}</h1>
      <p></p></div>
    <div class="nom"><label for="nom-eleve">Nom et prénom</label><input id="nom-eleve" type="text" autocomplete="name"></div>
  </header>

  <div class="consignes">
    <p class="only-training"><strong>Mode entraînement.</strong> Réponds dans chaque champ puis clique sur « Valider » : une réponse validée est définitive et sa correction s'affiche aussitôt.</p>
    <p class="only-exam"><strong>Mode examen.</strong> Compose tout le sujet sans correction ni note : tes réponses restent modifiables jusqu'au bout. Le bouton « J'ai fini, je fais corriger ma copie », en fin de sujet, dévoile d'un coup les corrections, les notes par partie et la note globale.</p>
    <p><strong>Les unités sont notées.</strong> Pour toute question numérique, la valeur vaut la moitié des points et l'unité l'autre moitié : une valeur juste écrite sans unité, ou avec une unité fausse, ne rapporte qu'un demi-point.</p>
    <p><strong>Calculs.</strong> Garde les valeurs non arrondies dans ta calculatrice : les tolérances couvrent les arrondis des résultats intermédiaires demandés. Pour π, utilise la touche de ta calculatrice (3,14 est toléré).</p>
    <p>Le dossier de présentation (DP) et le dossier technique (DT) s'ouvrent avec les onglets sur le bord droit, ou avec les boutons des en-têtes de question.</p>
    <p><strong>Le tracé compte aussi.</strong> Quand sa correction s'affiche, tu t'attribues toi-même les points à l'aide d'une grille de critères.</p>
    <p><strong>Barème pondéré par la durée conseillée</strong> : chaque partie est notée sur 20, puis pèse au prorata de son temps. Le récapitulatif de fin de sujet donne le détail partie par partie.</p>
  </div>

  <div id="parts"></div>

  <section class="recap" id="recap" aria-labelledby="t-recap">
    <header class="recap-head"><h2 id="t-recap">Récapitulatif et note finale</h2>
      <p class="small">Les questions non validées comptent comme fausses. Chaque partie est ramenée sur 20, puis pondérée par sa durée conseillée.</p></header>
    <div id="exam-submit-wrap">
      <p class="es-lead">Ta copie n'est pas encore corrigée : aucune réponse n'est verrouillée, tu peux encore revenir sur les questions et les tracés.</p>
      <button type="button" class="btn btn-exam" id="exam-submit">J'ai fini, je fais corriger ma copie</button>
      <p class="es-warn" id="exam-warn" role="alert"></p>
    </div>
    <div id="recap-graded">
      <div class="recap-wrap">
        <table class="t recap-table">
          <thead><tr><th>Partie</th><th>Durée</th><th>Poids</th><th>Points</th><th>Note /20</th><th>Contribution</th></tr></thead>
          <tbody id="recap-body"></tbody>
          <tfoot><tr><th colspan="4">Note globale pondérée</th><th class="final-note"></th><th></th></tr></tfoot>
        </table>
      </div>
      <p class="final-detail small"></p>
    </div>
    <div class="recap-foot" id="recap-foot"><button type="button" class="btn btn-print">Imprimer ma copie</button>
      <span class="small no-print">L'impression reprend tes réponses, les corrections, tes tracés et ce récapitulatif.</span>
      <a class="btn ghost no-print" href="?">{HOUSE} Retour à l'accueil</a></div>
  </section>
</main>

<footer class="banner" aria-label="Suivi de la composition">
  <div class="score-block"><div class="lab">Note provisoire</div><div class="score" id="score-val">–<small>/20</small></div></div>
  <div class="exam-block"><div class="lab">Mode examen</div><div class="exam-state">Note masquée</div></div>
  <div class="timer-block"><div class="lab">Temps</div><div class="timer" id="timer-val">0:00:00</div></div>
  <div class="count" id="score-count" aria-live="polite"></div>
  <div class="spacer"></div>
  <button type="button" class="btn-docs" id="btn-docs">Documents</button>
</footer>

{chr(10).join(templates)}

{config}
{router}
{grading}
{app}
</body>
</html>
"""
    SORTIE.write_text(page, encoding="utf-8")
    imgs = sum(len(m) for m in DATA_RE.findall(page))
    print(f"{SORTIE.name} : {len(page.encode('utf-8')) / 1024:.0f} Kio, dont images {imgs / 1024:.0f} Kio (base64)")
    for e in EXO_DEFS:
        print(f"  ?ex={e['key']} : {len(e['P'])} parties, {e['n_q']} questions, {e['n_sk']} tracé, "
              f"{e['points']} points, {hm(e['minutes'])}")


if __name__ == "__main__":
    build()
