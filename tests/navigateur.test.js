// Tests navigateur (Playwright + Chromium) : accueil, cours, parcours entraînement et examen des deux exercices.
//   NODE_PATH=$(npm root -g) node --test tests/navigateur.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");
const { chromium } = require("playwright");
const REP = require("./reponses.js");

const FILE = path.join(__dirname, "..", "index.html");
const URL = "file://" + FILE;
const EXO = {
  "cisaillement-n1": { prefix: "d", sketches: ["sk_d1_1", "sk_d2_1", "sk_d3_1"], sketch: "sk_d3_1", dr: /DR3 Q3\.1/,
    sheets: 3, parts: 3, items: 30, points: 38 },
  "traction-n1": { prefix: "b", sketch: "sk_b4_1", dr: /DR1 Q4\.1/, parts: 5, items: 31, points: 34 },
  traction: { prefix: "t", sketch: "sk_t1_5", dr: /DR1 Q1\.5/, parts: 4, items: 24, points: 27 },
  cisaillement: { prefix: "c", sketch: "sk_c7_2", dr: /DR1 Q7\.2/, parts: 7, items: 31, points: 34 },
};
const answers = (key) => Object.entries(REP).filter(([id]) => id.startsWith(EXO[key].prefix));
let browser;

test.before(async () => { browser = await chromium.launch(); });
test.after(async () => { await browser.close(); });

async function open(query, viewport) {
  const context = await browser.newContext({ viewport: viewport || { width: 1366, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("dialog", (d) => d.accept());
  await page.goto(URL + (query || ""));
  return { context, page, errors };
}

// Trace une flèche sur le canevas d'un tracé (coordonnées en fraction de la zone)
async function drawArrow(page, sk, x1, y1, x2, y2) {
  await page.click(`#${sk} [data-tool=arrow]`);
  const box = await page.locator(`#${sk} canvas`).boundingBox();
  await page.mouse.move(box.x + box.width * x1, box.y + box.height * y1);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * (x1 + x2) / 2, box.y + box.height * (y1 + y2) / 2, { steps: 4 });
  await page.mouse.move(box.x + box.width * x2, box.y + box.height * y2, { steps: 4 });
  await page.mouse.up();
}
const nStrokes = (page, sk) => page.evaluate((id) => window.__app__.sketches[id].strokes.length, sk);
const text = (page, sel) => page.locator(sel).first().innerText();

test("accueil : quatre cartes de cours, quatre cartes d'exercices, pastilles Niveau 1 et Niveau 2", async () => {
  const { context, page, errors } = await open();
  assert.ok(await page.locator("body.hub").count());
  assert.ok(await page.isVisible("#home"));
  assert.ok(!(await page.isVisible("main.page")));
  assert.ok(!(await page.isVisible(".banner")));
  assert.match(await text(page, "#home h1"), /Résistance des matériaux/);
  const card = (sel) => page.locator(sel).evaluateAll((cs) => cs.map((c) => [
    c.querySelector(".mc-tag").textContent.trim(), c.querySelector("h3").textContent, c.querySelector("a").getAttribute("href")]));
  assert.deepEqual(await card(".cours-grid .mode-card"), [
    ["Cours 1.1 Niveau 1", "Traction", "?ex=cours-traction-n1"], ["Cours 1.2 Niveau 2", "Traction et compression", "?ex=cours-traction"],
    ["Cours 2.1 Niveau 1", "Cisaillement", "?ex=cours-cisaillement-n1"], ["Cours 2.2 Niveau 2", "Cisaillement", "?ex=cours-cisaillement"]]);
  assert.equal(await page.locator(".cours-grid .en-edition").count(), 2);
  assert.deepEqual(await card(".ex-grid:not(.cours-grid) .mode-card"), [
    ["Exercice 1.1 Niveau 1", "Traction", "?ex=traction-n1"], ["Exercice 1.2 Niveau 2", "Traction et compression", "?ex=traction"],
    ["Exercice 2.1 Niveau 1", "Cisaillement", "?ex=cisaillement-n1"], ["Exercice 2.2 Niveau 2", "Cisaillement", "?ex=cisaillement"]]);
  assert.equal(await page.locator("#home .btn-mode").count(), 0);
  // pas de débordement horizontal sur téléphone
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  const src = fs.readFileSync(FILE, "utf8").replace(/data:[^"]+/g, "");
    assert.doesNotMatch(src, /\b(BTS|bac(calaur[ée]at)?|session \d|[ée]preuve|acad[ée]mie|sujet z[ée]ro|brevet)\b/i);
  assert.deepEqual(errors, []);
  await context.close();
});

test("cours : page « En cours d'édition » avec retour à l'accueil", async () => {
  for (const [q, title] of [["cours-traction", "Traction et compression"], ["cours-cisaillement", "Cisaillement"]]) {
    const { context, page, errors } = await open("?ex=" + q);
    assert.equal((await text(page, "#home h1")).trim(), title);
    assert.match(await text(page, "#home"), /En cours d'édition/);
    await page.click("#home a[href='?']");
    await page.waitForURL(/index\.html\?$/);
    assert.ok(await page.locator(".cours-grid").count(), "retour à l'accueil");
    assert.deepEqual(errors, []);
    await context.close();
  }
  // adresse inconnue : accueil
  const { context, page } = await open("?ex=inconnu");
  assert.ok(await page.locator(".cours-grid").count());
  await context.close();
});

test("cours 2.1 (niveau 1) : animation, simulateur à 1 ou 2 sections, jeu, quiz", async () => {
  const { context, page, errors } = await open("?ex=cours-cisaillement-n1");
  assert.match(await text(page, "#home .home-head"), /Cours 2\.1[\s\S]*Niveau 1[\s\S]*Cisaillement/);
  const set = (sel, v) => page.locator(sel).evaluate((e, x) => { e.value = x; e.dispatchEvent(new Event("input")); }, v);
  await set("#gl-s", "100");
  assert.match(await text(page, "#gl-txt"), /Rupture/);
  assert.match(await page.getAttribute("#gl-droite", "transform"), /translate\(0,60\)/);
  // réglages de départ : 1 section → ne résiste pas ; 2 sections → résiste
  assert.match(await text(page, "#c-rtau"), /132,63 MPa/);
  assert.match(await text(page, "#c-rpg"), /70,00 MPa/);
  assert.match(await text(page, "#c-v"), /ne résiste pas/);
  await page.check("input[name=c-n][value='2']");
  assert.match(await text(page, "#c-rt"), /7\s500 N/);
  assert.match(await text(page, "#c-rtau"), /66,31 MPa/);
  assert.match(await text(page, "#c-v"), /résiste/);
  // jeu : toutes justes
  const lignes = page.locator(".jeu-l");
  for (let i = 0; i < await lignes.count(); i++) {
    const ok = await lignes.nth(i).getAttribute("data-ok");
    await lignes.nth(i).locator(`button[data-n="${ok}"]`).click();
  }
  assert.equal((await text(page, "#jeu-s")).trim(), "5 / 5");
  // quiz : tout juste → 3 étoiles
  const n = await page.locator(".quiz-q").count();
  for (let i = 0; i < n; i++) {
    const fs = page.locator(".quiz-q").nth(i);
    await fs.locator(`input[value="${await fs.getAttribute("data-ok")}"]`).check();
  }
  assert.equal((await text(page, "#qz-score")).trim(), `${n} / ${n}`);
  assert.equal((await text(page, "#qz-stars")).trim(), "★★★");
  assert.deepEqual(errors, []);
  await context.close();
});

test("cours 1.1 (niveau 1) : courbe cliquable, simulateur, quiz noté", async () => {
  const { context, page, errors } = await open("?ex=cours-traction-n1");
  assert.match(await text(page, "#home h1"), /Traction/);
  assert.match(await text(page, "#home .home-head"), /Niveau 1/);
  // courbe : une étape affiche son explication et met la courbe en valeur
  await page.click(".etape[data-zone=plast]");
  assert.ok(await page.isVisible(".etape-txt[data-zone=plast]"));
  assert.ok(await page.locator(".essai-svg .z-plast.on").count());
  await page.click(".essai-svg .pt[data-zone=re] circle:not(.hit)");
  assert.ok(await page.isVisible(".etape-txt[data-zone=re]"));
  assert.ok(!(await page.isVisible(".etape-txt[data-zone=plast]")));
  // simulateur : réglages du défi (F = 10 000 N, E295, s = 5)
  const set = (sel, v) => page.locator(sel).evaluate((e, x) => { e.value = x; e.dispatchEvent(new Event("input")); }, v);
  await set("#s-f", "10000"); await page.selectOption("#s-m", "295"); await page.selectOption("#s-s", "5");
  await set("#s-d", "14.5");
  assert.match(await text(page, "#r-v"), /σ > Rpe/);
  await set("#s-d", "15");
  assert.match(await text(page, "#r-sig"), /56,59 MPa/);
  assert.match(await text(page, "#r-rpe"), /59,00 MPa/);
  assert.match(await text(page, "#r-v"), /la pièce résiste/);
  // un clic sur une ligne du tableau des aciers règle le simulateur
  await page.click(".mat-table tr[data-re='360']");
  assert.equal(await page.inputValue("#s-m"), "360");
  // quiz : 5 bonnes réponses sur 6
  const n = await page.locator(".quiz-q").count();
  for (let i = 0; i < n; i++) {
    const fs = page.locator(".quiz-q").nth(i);
    const ok = await fs.getAttribute("data-ok");
    await fs.locator(`input[value="${i === 2 ? (ok === "0" ? "1" : "0") : ok}"]`).check();
  }
  assert.equal((await text(page, "#qz-score")).trim(), "5 / 6");
  assert.equal(await page.locator(".quiz-q.is-ko").count(), 1);
  assert.ok(await page.locator(".quiz-q input:disabled").count() > 0);
  await page.click("#qz-reset");
  assert.equal((await text(page, "#qz-score")).trim(), "0 / 6");
  assert.equal(await page.locator(".quiz-q.done").count(), 0);
  // impression : le cours s'imprime (l'accueil ne disparaît pas)
  await page.emulateMedia({ media: "print" });
  assert.ok(await page.isVisible("#c-quiz"));
  assert.ok(!(await page.isVisible(".cours-foot")));
  await page.emulateMedia({ media: "screen" });
  await page.click(".cours-foot a[href='?ex=traction-n1']");
  await page.waitForURL(/\?ex=traction-n1$/);
  assert.equal(await page.locator("#home .btn-mode").count(), 2);
  assert.deepEqual(errors, []);
  await context.close();
});

for (const key of Object.keys(EXO)) {
  const X = EXO[key];
  test(`${key} : accueil de l'exercice puis sujet entièrement juste = 20/20, impression`, async () => {
    const { context, page, errors } = await open("?ex=" + key);
    assert.equal(await page.locator("#home .btn-mode").count(), 2);
    assert.match(await text(page, ".home-facts"), new RegExp(`${X.parts} parties`));
    await page.click("[data-mode=training]");
    assert.ok(await page.isVisible("main.page"));
    assert.equal(await page.locator(".part").count(), X.parts);
    assert.deepEqual(await page.locator(".rail .tab:not(.tab-home)").allInnerTexts(),
      /-n1$/.test(key) ? ["DP1", "DT1", "DT2", "DT3"] : ["DP1", "DT1", "DT2"]);
    assert.ok(await page.isVisible(".rail .tab-home"));
    assert.ok(await page.isVisible(".c-top a[href='?']"));

    const sk = X.sketch, sks = X.sketches || [sk];
    for (const k of sks) {
      const deps = await page.evaluate((id) => window.__SKCFG__[id].deps, k);
      await drawArrow(page, k, 0.4, 0.4, 0.6, 0.4);
      await page.click(`#${k} .btn-sketch`);
      if (deps.length) {
        assert.match(await text(page, `#${k} .sk-wait`), /Q7\.1/);
        assert.ok(!(await page.isVisible(`#${k} .selfeval`)));
      }
    }
    for (const [id, ans] of answers(key)) {
      await page.fill(`#in-${id}`, ans);
      await page.click(`#${id} .btn-validate`);
      assert.match(await text(page, `#${id} .q-status`), /Juste/, id);
      assert.ok(await page.isDisabled(`#in-${id}`), id + " verrouillée");
      assert.ok(await page.isVisible(`#${id} .q-expl`));
    }
    for (const k of sks) {
      assert.ok(await page.isVisible(`#${k} .selfeval`));
      assert.ok(await page.isChecked(`#${k} .sk-corr-toggle input`));
      const n = await page.locator(`#${k} .selfeval input[data-crit]`).count();
      for (const cb of await page.locator(`#${k} .selfeval input[data-crit]`).all()) await cb.check();
      await page.click(`#${k} .btn-self`);
      assert.match(await text(page, `#${k} .se-score`), new RegExp(`${n} points sur ${n}`));
    }

    assert.match(await text(page, "#score-val"), /20,0/);
    assert.equal((await text(page, "#recap .final-note")).trim(), "20,0/20");
    const notes = await page.locator("#recap-body .rc-note").allInnerTexts();
    assert.equal(notes.length, X.parts);
    notes.forEach((n) => assert.equal(n.trim(), "20,0"));
    assert.match(await text(page, "#score-count"), new RegExp(`${X.items} items validés sur ${X.items} · ${X.points},0 / ${X.points} points`));

    await page.fill("#nom-eleve", "Élève Test");
    await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
    await page.emulateMedia({ media: "print" });
    assert.ok(!(await page.isVisible(".c-top")));
    assert.ok(!(await page.isVisible(".print-nograde")));
    assert.match(await text(page, ".print-summary"), /Élève Test[\s\S]*entraînement[\s\S]*durée conseillée : 1 h [0-9]{2}[\s\S]*20,0\/20/);
    if (key === "traction-n1") assert.ok(await page.evaluate(() => window.__app__.sketches.sk_b4_1.dec.pxPerCm === 50));
    assert.match(await page.getAttribute(`#${sk} .sk-print-student`, "src"), /^data:image\/png/);
    assert.match(await page.getAttribute(`#${sk} .sk-print-corr`, "src"), /^data:image\/png/);
    const pdf = await page.pdf({ format: "A4" });
    assert.ok(pdf.length > 50000);
    await page.emulateMedia({ media: "screen" });

    // fenêtre des documents réponses : la feuille vierge de l'exercice
    const [popup] = await Promise.all([context.waitForEvent("page"), page.click(`#${sk} [data-act=drprint]`)]);
    await popup.waitForLoadState();
    assert.equal(await popup.locator(".sheet").count(), X.sheets || 1);
    assert.match(await popup.locator(".sheet h2").last().innerText(), X.dr);
    assert.deepEqual(errors, []);
    await context.close();
  });
}

test("traction : demi-point d'unité, saisie vide refusée, note provisoire pondérée", async () => {
  const { context, page, errors } = await open("?ex=traction");
  await page.click("[data-mode=training]");
  await page.click("#t1_1 .btn-validate");
  assert.match(await text(page, "#t1_1 .q-msg"), /Saisis une réponse/);
  await page.fill("#in-t1_1", "833,85");
  await page.click("#t1_1 .btn-validate");
  assert.match(await text(page, "#t1_1 .q-unit-msg"), /Unité manquante.*\(N\)/);
  assert.match(await text(page, "#score-val"), /10,0/);
  await page.fill("#in-t2_2", "100 kN");
  await page.click("#t2_2 .btn-validate");
  assert.match(await text(page, "#t2_2 .q-unit-msg"), /Unité incorrecte/);
  await page.fill("#in-t1_2", "700 mm");
  await page.click("#t1_2 .btn-validate");
  assert.ok(await page.locator("#t1_2.is-ko").count());
  // partie 1 : 0,5/2 → 5/20 (30 min) ; partie 2 : 0,5/1 → 10/20 (10 min) → 6,25
  assert.match(await text(page, "#score-val"), /6,[23]/);
  assert.deepEqual(errors, []);
  await context.close();
});

test("traction en examen : rien ne filtre avant la remise, y compris à l'impression ; remise en deux temps", async () => {
  const { context, page, errors } = await open("?ex=traction");
  await page.click("[data-mode=exam]");
  assert.ok(!(await page.isVisible("#score-val")));
  assert.ok(!(await page.isVisible("#t1_1 .btn-validate")));
  for (const [id, ans] of answers("traction")) if (id !== "t1_1" && id !== "t2_3") await page.fill(`#in-${id}`, ans);
  await page.fill("#in-t3_1", "49050 N"); // signe oublié : faux
  await drawArrow(page, "sk_t1_5", 0.6, 0.6, 0.6, 0.9);
  assert.match(await text(page, "#score-count"), /21 réponse\(s\) renseignée\(s\) sur 23/);

  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  await page.emulateMedia({ media: "print" });
  assert.ok(await page.isVisible(".print-nograde"));
  assert.ok(!(await page.isVisible(".print-note-line")));
  assert.ok(!(await page.isVisible("#t2_2 .q-expl")));
  assert.ok(!(await page.isVisible("#sk_t1_5 .q-expl")));
  assert.ok(!(await page.isVisible("#sk_t1_5 .sk-print-corr")));
  assert.ok(!(await page.isVisible("#recap-graded")));
  await page.emulateMedia({ media: "screen" });

  await page.click("#exam-submit");
  assert.match(await text(page, "#exam-warn"), /2 réponse\(s\) encore vide\(s\)/);
  await page.click("#exam-submit");
  assert.ok(await page.locator("body.graded").count());
  assert.match(await text(page, "#t1_1 .q-status"), /Non répondue/);
  assert.match(await text(page, "#t3_1 .q-status"), /Faux/);
  assert.ok(await page.isVisible("#sk_t1_5 .selfeval"));
  const t1 = await text(page, "#timer-val");
  await page.waitForTimeout(1300);
  assert.equal(await text(page, "#timer-val"), t1, "chronomètre arrêté");
  for (const cb of await page.locator("#sk_t1_5 .selfeval input[data-crit]").all()) await cb.check();
  await page.click("#sk_t1_5 .btn-self");
  // P1 : 12/13 ; P2 : 3/4 ; P3 : 5/6 ; P4 : 4/4 → (30×18,46 + 10×15 + 15×16,67 + 10×20) / 65 = 17,8
  assert.equal((await text(page, "#recap .final-note")).trim(), "17,8/20");
  assert.deepEqual(errors, []);
  await context.close();
});

test("cisaillement : outils de tracé, documents, téléphone", async () => {
  const { context, page, errors } = await open("?ex=cisaillement");
  await page.click("[data-mode=training]");
  const sk = "sk_c7_2";
  await drawArrow(page, sk, 0.2, 0.2, 0.4, 0.2);
  await drawArrow(page, sk, 0.2, 0.7, 0.4, 0.7);
  assert.equal(await nStrokes(page, sk), 2);
  await page.click(`#${sk} [data-tool=erase]`);
  const box = await page.locator(`#${sk} canvas`).boundingBox();
  await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.2);
  assert.equal(await nStrokes(page, sk), 1);
  await page.click(`#${sk} [data-act=undo]`);
  assert.equal(await nStrokes(page, sk), 0);
  await page.click(`#${sk} [data-tool=text]`);
  const box2 = await page.locator(`#${sk} canvas`).boundingBox();
  await page.mouse.click(box2.x + box2.width * 0.8, box2.y + box2.height * 0.3);
  // le gabarit donne le focus au champ de texte au tick suivant
  await page.waitForFunction(() => document.activeElement && document.activeElement.classList.contains("sk-text"));
  await page.keyboard.type("S1");
  await page.keyboard.press("Enter");
  assert.equal(await nStrokes(page, sk), 1);
  await page.click(`#${sk} [data-zoom=in]`);
  assert.equal((await text(page, `#${sk} .zoom-val`)).trim(), "150 %");
  await page.click(`#${sk} [data-act=full]`);
  assert.ok(await page.locator(`#${sk}.is-full`).count());
  await page.keyboard.press("Escape");
  assert.ok(!(await page.locator(`#${sk}.is-full`).count()));

  await page.click(".rail [data-doc=DT1]");
  assert.match(await text(page, "#dp-title"), /DT1 : Formulaire — cisaillement/);
  await page.click("#partie-1 .doc-chip[data-doc=DT2]");
  assert.match(await text(page, "#doc-DT2"), /Aire des sections usuelles/);
  await page.keyboard.press("Escape");
  assert.ok(!(await page.locator("body.panel-open").count()));
  // figures renumérotées dans l'exercice
  assert.match(await text(page, "#partie-1 figcaption"), /^Figure 1 — Levier et chape/);
  await context.close();

  const m = await open("?ex=cisaillement", { width: 420, height: 800 });
  await m.page.click("[data-mode=exam]");
  assert.ok(!(await m.page.isVisible(".rail")));
  assert.ok(await m.page.isVisible(".c-top a"));
  await m.page.click("#btn-docs");
  assert.ok(await m.page.isVisible("#doc-DP1"));
  assert.ok(await m.page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  assert.deepEqual([...errors, ...m.errors], []);
  await m.context.close();
});
