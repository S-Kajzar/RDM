// Tests unitaires du moteur de correction appliqué aux 83 questions des trois exercices.
//   node --test tests/
// Le moteur (Grading) et la configuration (__QCFG__) sont lus dans la page générée :
// on teste exactement ce que l'élève utilisera.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const PAGE = path.join(__dirname, "..", "index.html");
const html = fs.readFileSync(PAGE, "utf8");
const code = html.slice(html.indexOf("/*GRADING-START*/"), html.indexOf("/*GRADING-END*/"));
const mod = { exports: {} };
new Function("module", code + "\nmodule.exports = Grading;")(mod);
const G = mod.exports;
const EXOS = JSON.parse(html.match(/window\.__EXOS__ = (.*?);<\/script>/)[1]);
const QCFG = Object.assign({}, ...Object.values(EXOS).map((e) => e.qcfg));
const REP = require("./reponses.js");

function score(id, ans) {
  const r = G.grade(ans, QCFG[id].grader);
  return r.invalid ? "invalid" : r.score;
}

// [saisie, score attendu] : 1 juste, 0.5 demi-point d'unité, 0 faux, "invalid" refusée sans être notée
const CASES = {
  b1_1: [["295 MPa", 1], ["295", 0.5], ["295 N", 0.5], ["470 MPa", 0], ["235 MPa", 0]],
  b1_2: [["oui", 1], ["Oui, 40 < 295", 1], ["non", 0]],
  b1_3: [["7,38", 1], ["7,375", 1], ["7,37", 1], ["7.4", 0], ["0,14", 0]],
  b2_1: [["28,27 mm²", 1], ["28,26 mm2", 1], ["28,27", 0.5], ["113,1 mm²", 0], ["0,2827 cm²", 1]],
  b2_2: [["1746,18 N", 1], ["1 746 N", 1], ["1,746 kN", 1], ["1746,18", 0.5], ["1780 N", 0], ["178 N", 0]],
  b2_3: [["2530,98 N", 1], ["2531 N", 1], ["2530,98", 0.5], ["1746,18 N", 0], ["2580 N", 0]],
  b2_4: [["89,52 MPa", 1], ["89,53 MPa", 1], ["89,52", 0.5], ["61,77 MPa", 0], ["22,4 MPa", 0]],
  b2_5: [["45 MPa", 1], ["45,00 MPa", 1], ["45", 0.5], ["36 MPa", 0], ["2880 MPa", 0]],
  b2_6: [["non", 1], ["Non, 89,52 > 45", 1], ["oui", 0]],
  b3_1: [["24 mm²", 1], ["24", 0.5], ["12 mm²", 0], ["36 mm²", 0]],
  b3_2: [["24 mm²", 1], ["24 mm2", 1], ["36 mm²", 0], ["12 mm²", 0]],
  b3_3: [["83,33 MPa", 1], ["83,333 MPa", 1], ["83,33", 0.5], ["166,67 MPa", 0]],
  b3_4: [["83,33 MPa", 1], ["83,33 N/mm²", 1], ["55,56 MPa", 0]],
  b3_5: [["7,2", 1], ["7,20", 1], ["3,6", 0], ["0,14", 0]],
  b4_2: [["360 mm²", 1], ["360", 0.5], ["240 mm²", 0]],
  b4_3: [["240 mm²", 1], ["240", 0.5], ["300 mm²", 0], ["120 mm²", 0]],
  b4_4: [["210 mm²", 1], ["210 mm2", 1], ["150 mm²", 0], ["281,46 mm²", 0]],
  b4_5: [["13,89 MPa", 1], ["13,9 MPa", 0], ["13,89", 0.5], ["20,83 MPa", 0]],
  b4_6: [["20,83 MPa", 1], ["20,83", 0.5], ["23,81 MPa", 0]],
  b4_7: [["23,81 MPa", 1], ["23,81", 0.5], ["33,33 MPa", 0]],
  b4_8: [["S3", 1], ["s3", 1], ["la section 3", 1], ["S1", 0], ["S2", 0], ["S2 et S3", 0]],
  b4_9: [["49,17 MPa", 1], ["49,167 MPa", 1], ["49,17", 0.5], ["78,33 MPa", 0], ["1770 MPa", 0]],
  b4_10: [["oui", 1], ["Oui : 23,81 < 49,17", 1], ["non", 0]],
  b5_1: [["333,33 N", 1], ["333,333 N", 1], ["333,33", 0.5], ["2000 N", 0], ["333 N", 0]],
  b5_2: [["86,67 MPa", 1], ["86,667 MPa", 1], ["86,67", 0.5], ["780 MPa", 0]],
  b5_3: [["3,85 mm²", 1], ["3,846 mm²", 1], ["3,85", 0.5], ["23,08 mm²", 0], ["4,47 mm²", 0]],
  b5_4: [["3 mm", 1], ["3", 0.5], ["2,5 mm", 0], ["4 mm", 0]],
  b5_5: [["186,43 MPa", 1], ["186,4 MPa", 1], ["186,43", 0.5], ["74,57 MPa", 0], ["156,25 MPa", 0]],
  b5_6: [["non", 1], ["Non, 186 > 86,67", 1], ["oui", 0]],
  b5_7: [["5 mm", 1], ["5", 0.5], ["4 mm", 0], ["6 mm", 0]],
  t1_1: [["833,85 N", 1], ["833.85 N", 1], ["P = 833,85 N", 1], ["833,85", 0.5], ["833,85 kg", 0.5],
         ["833,85 kN", 0.5], ["0,83385 kN", 1], ["833 N", 0], ["850 N", 0], ["environ", "invalid"]],
  t1_2: [["1200 mm", 1], ["1 200 mm", 1], ["1,2 m", 1], ["120 cm", 1], ["1200", 0.5], ["1,2", 0], ["700 mm", 0]],
  t1_3: [["860,23 mm", 1], ["860,24 mm", 1], ["0,86023 m", 1], ["860,23", 0.5], ["860,2 mm", 0], ["860 mm", 0]],
  t1_4: [["0,581", 1], ["0.581", 1], ["0,580", 1], ["0,58124", 1], ["0,574", 0], ["0,814", 0], ["35,5", 0]],
  t1_6: [["2459 N", 1], ["2460 N", 1], ["2 459 N", 1], ["2,459 kN", 1], ["2459", 0.5], ["2492 N", 0], ["2465 N", 0]],
  t1_7: [["28,27 mm²", 1], ["28,27 mm2", 1], ["28,26 mm^2", 1], ["28,27 mm", 0.5], ["28,27", 0.5],
         ["0,2827 cm²", 1], ["113,1 mm²", 0]],
  t1_8: [["86,98 MPa", 1], ["87 MPa", 1], ["87,02 N/mm²", 1], ["86,98 Mpa", 1], ["86,98", 0.5], ["86,98 GPa", 0.5],
         ["86,98 N.mm-2", 1], ["90 MPa", 0], ["0,087 MPa", 0]],
  t1_9: [["4,35e-4", 1], ["4,35×10^-4", 1], ["4.35*10^(-4)", 1], ["0,000435", 1], ["4,349E-04", 1],
         ["4,35", 0], ["4,35e-7", 0], ["4,35e-1", 0]],
  t1_10: [["0,374 mm", 1], ["0,3742 mm", 1], ["374 µm", 1], ["374 um", 1], ["0,374", 0.5], ["0,374 m", 0.5],
          ["0,37 mm", 0], ["0,4 mm", 0]],
  t2_1: [["1200 mm²", 1], ["12 cm²", 1], ["1200", 0.5], ["1200 mm", 0.5], ["120 mm²", 0]],
  t2_2: [["100 MPa", 1], ["100,00 MPa", 1], ["100 N/mm2", 1], ["100", 0.5], ["100 Pa", 0.5], ["1e8 Pa", 1], ["0,1 MPa", 0]],
  t2_3: [["oui", 1], ["Oui, 100 < 144", 1], ["OUI", 1], ["non", 0], ["Non, elle ne l'est pas", 0], ["peut-être", "invalid"]],
  t2_4: [["2,38 mm", 1], ["2,381 mm", 1], ["2,38", 0.5], ["2,4 mm", 0], ["23,8 mm", 0]],
  t3_1: [["-49050 N", 1], ["−49 050 N", 1], ["N = -49050 N", 1], ["-49,05 kN", 1], ["-49050", 0.5],
         ["49050 N", 0], ["-5000 N", 0]],
  t3_2: [["16,67 mm", 1], ["16,666 mm", 1], ["16,67", 0.5], ["16,7 mm", 0], ["150 mm", 0]],
  t3_3: [["400 mm", 1], ["0,4 m", 1], ["40 cm", 1], ["400", 0.5], ["400 cm", 0.5], ["40 mm", 0]],
  t3_4: [["1745,33 mm²", 1], ["1745,24 mm²", 1], ["1744,44 mm²", 1], ["1745,33", 0.5], ["1963,5 mm²", 0], ["1745 mm²", 1]],
  t3_5: [["-28,10 MPa", 1], ["-28,1 MPa", 1], ["−28,10 MPa", 1], ["-28,10", 0.5], ["28,10 MPa", 0], ["-25 MPa", 0]],
  t3_6: [["-0,054 mm", 1], ["-0,0535 mm", 1], ["-53,5 µm", 1], ["-0,054", 0.5], ["0,054 mm", 0], ["-0,053 mm", 0],
         ["-0,06 mm", 0]],
  t4_1: [["140 MPa", 1], ["140", 0.5], ["144 MPa", 0], ["14 MPa", 0]],
  t4_2: [["oui", 1], ["Oui, 140 < 144", 1], ["non", 0]],
  t4_3: [["57,14 mm", 1], ["57,143 mm", 1], ["57,14", 0.5], ["55,56 mm", 0], ["57 mm", 0]],
  t4_4: [["60 mm", 1], ["6 cm", 1], ["60", 0.5], ["55 mm", 0], ["57,14 mm", 0], ["50 mm", 0]],
  c1_1: [["57,01 kN", 1], ["57,01kN", 1], ["57008,77 N", 1], ["57,01", 0.5], ["57,01 N", 0.5], ["80 kN", 0], ["57 kN", 0]],
  c1_2: [["2", 1], ["2 sections", 1], ["1", 0], ["4", 0], ["deux", "invalid"]],
  c1_3: [["28,50 kN", 1], ["28,51 kN", 1], ["28,5 kN", 1], ["28504 N", 1], ["28,50", 0.5], ["57,01 kN", 0]],
  c1_4: [["962,11 mm²", 1], ["961,63 mm²", 1], ["962,11", 0.5], ["3848,45 mm²", 0], ["962,11 mm", 0.5]],
  c1_5: [["29,63 MPa", 1], ["29,62 MPa", 1], ["29,63", 0.5], ["59,25 MPa", 0], ["14,81 MPa", 0]],
  c2_1: [["2,98", 1], ["2.98", 1], ["2,980", 1], ["0,34", 0], ["3", 0]],
  c2_2: [["1", 1], ["1 section", 1], ["2", 0], ["une", "invalid"]],
  c2_3: [["6774,06 N", 1], ["6 774,06 N", 1], ["6772,35 N", 1], ["6,774 kN", 1], ["6774,06", 0.5], ["3387,03 N", 0]],
  c2_4: [["5072,20 N", 1], ["5,0722 kN", 1], ["5072,2", 0.5], ["6774,06 N", 0], ["1701,86 N", 0]],
  c2_5: [["1701,86 N", 1], ["1,70186 kN", 1], ["1701,86", 0.5], ["5072,20 N", 0], ["567,29 N", 0]],
  c2_6: [["567,29 N", 1], ["567,3 N", 1], ["0,56729 kN", 1], ["567,29", 0.5], ["1701,86 N", 0], ["1690,73 N", 0]],
  c3_1: [["2", 1], ["2 sections cisaillées", 1], ["1", 0]],
  c3_2: [["2,50 kN", 1], ["2,5 kN", 1], ["2500 N", 1], ["2,5", 0.5], ["2500", 0], ["5 kN", 0]],
  c3_3: [["28,27 mm²", 1], ["28,26 mm²", 1], ["28,27", 0.5], ["113,1 mm²", 0]],
  c3_4: [["88,42 MPa", 1], ["88,43 MPa", 1], ["88,42", 0.5], ["176,84 MPa", 0], ["89,29 MPa", 0]],
  c4_1: [["1", 1], ["1 section", 1], ["2", 0]],
  c4_2: [["2,50 kN", 1], ["2500 N", 1], ["2,5", 0.5], ["10 kN", 0], ["1,25 kN", 0]],
  c4_3: [["78,54 mm²", 1], ["78,5 mm²", 1], ["78,54", 0.5], ["314,16 mm²", 0]],
  c4_4: [["31,83 MPa", 1], ["31,85 MPa", 1], ["31,83", 0.5], ["127,32 MPa", 0], ["15,92 MPa", 0]],
  c5_1: [["4", 1], ["2 x 2 = 4", 1], ["4 sections", 1], ["2", 0], ["8", 0]],
  c5_2: [["133,33 MPa", 1], ["133,333 MPa", 1], ["133,33", 0.5], ["1200 MPa", 0], ["133 MPa", 0]],
  c5_3: [["12,93 mm", 1], ["12,927 mm", 1], ["0,01293 m", 1], ["12,93", 0.5], ["18,28 mm", 0], ["25,85 mm", 0]],
  c6_1: [["1", 1], ["1 section", 1], ["3", 0], ["2", 0]],
  c6_2: [["108,57 MPa", 1], ["108,571 MPa", 1], ["108,57", 0.5], ["1330 MPa", 0], ["108,6 MPa", 0]],
  c6_3: [["33,33 kN", 1], ["33333 N", 1], ["33,33", 0.5], ["100 kN", 0], ["33,3 kN", 0]],
  c6_4: [["307,02 mm²", 1], ["307,0 mm²", 1], ["306,99 mm²", 1], ["3,07 cm²", 1], ["307,02", 0.5],
          ["921,05 mm²", 0], ["87,72 mm²", 0]],
  c7_1: [["2", 1], ["2 sections", 1], ["1", 0]],
  c7_3: [["10,87 mm", 1], ["10,873 mm", 1], ["10,88 mm", 1], ["10,87", 0.5], ["15,38 mm", 0], ["7,69 mm", 0]],
  c7_4: [["70,04 MPa", 1], ["70 MPa", 1], ["70,00 MPa", 1], ["70,04", 0.5], ["140 MPa", 0], ["175 MPa", 0]],
  c7_5: [["7,78e-4 rad", 1], ["7,78×10^-4 rad", 1], ["0,000778 rad", 1], ["778 µrad", 1], ["0,778 mrad", 1],
          ["7,78e-4", 0.5], ["7,78e-4 °", 0.5], ["7,78e-3 rad", 0], ["1,94e-3 rad", 0]],
};

test("chaque question a des cas de test et une réponse de référence", () => {
  assert.deepEqual(Object.keys(CASES).sort(), Object.keys(QCFG).sort());
  assert.deepEqual(Object.keys(REP).sort(), Object.keys(QCFG).sort());
});

for (const id of Object.keys(CASES)) {
  test(`${QCFG[id].label} (${id})`, () => {
    for (const [ans, expected] of CASES[id]) assert.equal(score(id, ans), expected, `saisie « ${ans} »`);
    assert.equal(score(id, REP[id]), 1, "réponse de référence");
    const g = QCFG[id].grader;
    if (g.type === "num" && g.unit) {
      // la même valeur sans unité ne vaut que la moitié des points
      const bare = REP[id].replace(/\s*[^\d,.\-−eE×^*()]+$/u, "");
      assert.equal(score(id, bare), 0.5, `valeur sans unité « ${bare} »`);
    }
  });
}

test("questions vides et saisies non numériques refusées sans être notées", () => {
  for (const id of Object.keys(QCFG)) {
    assert.equal(score(id, ""), "invalid");
    assert.equal(score(id, "   "), "invalid");
  }
});

test("barème : points des parties cohérents, durées 65 et 80 min, tracés et dépendances", () => {
  assert.deepEqual(Object.keys(EXOS), ["traction-bp", "traction", "cisaillement"]);
  assert.equal(EXOS["traction-bp"].minutes, 90);
  assert.equal(Object.keys(EXOS["traction-bp"].qcfg).length, 30);
  assert.equal(EXOS.traction.minutes, 65);
  assert.equal(EXOS.cisaillement.minutes, 80);
  assert.equal(Object.keys(EXOS.traction.qcfg).length, 23);
  assert.equal(Object.keys(EXOS.cisaillement.qcfg).length, 30);
  for (const [key, E] of Object.entries(EXOS)) {
    let total = 0;
    for (const p of E.parts) {
      let pts = 0;
      for (const id in E.qcfg) if (E.qcfg[id].part === p.num) pts += E.qcfg[id].pts;
      for (const id in E.skcfg) if (E.skcfg[id].part === p.num) pts += E.skcfg[id].pts;
      assert.equal(pts, p.points, `${key} partie ${p.num}`);
      total += p.minutes;
    }
    assert.equal(total, E.minutes);
    for (const id in E.qcfg) assert.equal(E.qcfg[id].label, "Q" + id.slice(1).replace("_", "."), id);
    for (const id in E.skcfg) {
      assert.equal(E.skcfg[id].criteria.length, E.skcfg[id].pts);
      assert.ok(E.skcfg[id].pts >= 3 && E.skcfg[id].pts <= 5);
      for (const d of E.skcfg[id].deps) assert.ok(E.qcfg[d], `dépendance ${d}`);
    }
  }
});
