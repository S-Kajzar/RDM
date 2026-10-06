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


# ============================================================ TRACÉS (fonds et décor)
SK_BG = {
    # clé : (image, largeur déclarée, hauteur déclarée)
    "POUTRE": ("t1-siege-fil", 810, 460),
    "AXE": ("c7-axe-chape", 860, 373),
}

DECOR_JS = r"""  var DECOR = {
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
    src, _, _ = png(img_name)
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
    {"key": "traction", "prefix": "t", "tag": "Exercice 1", "title": "Traction et compression",
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


def render_exo_home(e):
    src, w, h = png(e["hero"][0])
    docs = sorted(set(e["docs"].values()))
    docs_txt = ", ".join(docs[:-1]) + " et " + docs[-1]
    facts = ('<div class="home-facts">'
             f'<div><b>{len(e["P"])} parties</b><span>{e["n_q"]} questions</span></div>'
             f'<div><b>{hm(e["minutes"])}</b><span>durée conseillée</span></div>'
             f'<div><b>{len(docs)} documents</b><span>{docs_txt}</span></div>'
             f'<div><b>{e["n_sk"]} tracé</b><span>auto-évalué</span></div></div>')
    return (f'<div class="home-top"><div class="home-top-l"><header class="home-head"><span class="mc-tag">{e["tag"]}</span>'
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


COURS = [("cours-traction", "Cours 1", "Traction et compression"),
         ("cours-cisaillement", "Cours 2", "Cisaillement")]


def render_hub():
    src, w, h = png("accueil")
    cards = "".join(
        f'<article class="mode-card"><div class="mc-head"><span class="mc-tag">{e["tag"]}</span><h3>{e["title"]}</h3></div>'
        f'<p>{e["card"]}</p><p class="small ex-meta">{len(e["P"])} parties · {e["n_q"]} questions · '
        f'{e["n_sk"]} tracé · {hm(e["minutes"])}</p>'
        f'<a class="btn" href="?ex={e["key"]}">Ouvrir l\'exercice</a></article>' for e in EXO_DEFS)
    btns = "".join(f'<a class="btn" href="?ex={k}">{tag} — {t}</a>' for k, tag, t in COURS)
    return (f'<div class="home-top"><div class="home-top-l"><header class="home-head"><h1 id="home-title">{TITRE}</h1>'
            '<p class="home-sub">Traction, compression et cisaillement : calculer une contrainte et une déformation, '
            'vérifier une pièce ou la dimensionner. Deux cours et des exercices interactifs, à faire en mode '
            'entraînement ou en mode examen.</p></header></div>'
            f'<figure class="home-hero"><img src="{src}" alt="À gauche, un siège suspendu par un fil et un tube '
            f'comprimé ; à droite, une pince à goupille et un axe de chape" width="{w}" height="{h}">'
            '<figcaption class="small">Quelques-unes des pièces étudiées dans les exercices.</figcaption></figure></div>'
            '<section class="hub-course" aria-labelledby="hub-c"><div><h2 id="hub-c">Les cours</h2>'
            '<p>Les notions, les formules et des exemples commentés, chapitre par chapitre.</p></div>'
            f'<div class="hub-btns">{btns}</div></section>'
            f'<h2 class="home-choose">Les exercices</h2><div class="ex-grid">{cards}</div>'
            '<p class="home-note small">Chaque exercice propose ensuite le mode entraînement (correction question par '
            'question) ou le mode examen (correction à la remise de la copie). Rien n\'est enregistré sur '
            'l\'ordinateur.</p>')


def render_cours(tag, title):
    return (f'<div class="home-top home-top-single"><div class="home-top-l"><header class="home-head">'
            f'<span class="mc-tag">{tag}</span><h1 id="home-title">{title}</h1>'
            '<p class="home-sub">Ce cours est en cours d\'édition : il sera mis en ligne prochainement.</p>'
            '</header></div></div>'
            '<section class="hub-course en-cours" aria-labelledby="ec-t"><div><h2 id="ec-t">En cours d\'édition</h2>'
            '<p>Le contenu de ce cours est en préparation.</p></div>'
            f'<div class="hub-btns"><a class="btn" href="?">{HOUSE} Retour à l\'accueil</a></div></section>')


ROUTER_JS = r"""<script>/* Aiguillage : accueil, cours ou exercice selon ?ex=… — s'exécute avant les moteurs du gabarit */
(function () {
  "use strict";
  var EXOS = window.__EXOS__, ex = new URLSearchParams(location.search).get("ex") || "";
  function $(s) { return document.querySelector(s); }
  function tpl(id) { return document.getElementById(id).innerHTML; }
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
    for k, tag, t in COURS:
        templates.append(f'<template id="tpl-{k}">{render_cours(tag, t)}</template>')

    config = f"<script>window.__EXOS__ = {json.dumps(exos_cfg, ensure_ascii=False)};</script>"
    router = ROUTER_JS.replace("__TITRE__", TITRE).replace("__HOUSE__", HOUSE.replace("'", "\\'"))

    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITRE} — cours et exercices interactifs</title>
<meta name="description" content="Traction, compression et cisaillement : effort normal, contrainte, loi de Hooke, allongement ; effort tranchant, simple et double cisaillement, dimensionnement d'axes, de goupilles et de boulons.">
{style}
{CONTENT_CSS}
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
