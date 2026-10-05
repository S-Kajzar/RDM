// Tests navigateur (Playwright + Chromium) des parcours entraînement et examen.
//   NODE_PATH=$(npm root -g) node --test tests/navigateur.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");
const { chromium } = require("playwright");
const REP = require("./reponses.js");

const FILE = path.join(__dirname, "..", "exercice-rdm-traction-compression-cisaillement.html");
const URL = "file://" + FILE;
const SKETCHES = ["sk_q1_5", "sk_q11_2"];
let browser;

test.before(async () => { browser = await chromium.launch(); });
test.after(async () => { await browser.close(); });

async function open(viewport) {
  const context = await browser.newContext({ viewport: viewport || { width: 1366, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("dialog", (d) => d.accept());
  await page.goto(URL);
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

test("page d'accueil : seul écran visible, aucune mention d'origine, un seul bouton d'impression", async () => {
  const { context, page, errors } = await open();
  assert.ok(await page.isVisible("#home"));
  assert.ok(!(await page.isVisible("main.page")));
  assert.ok(!(await page.isVisible(".banner")));
  assert.equal(await page.locator(".home-facts > div").count(), 4);
  assert.match(await text(page, ".home-facts"), /11 parties[\s\S]*2 h 25[\s\S]*4 documents[\s\S]*2 tracés/);
  assert.equal(await page.locator(".btn-print").count(), 1);
  const src = fs.readFileSync(FILE, "utf8").replace(/data:[^"]+/g, "");
  assert.doesNotMatch(src, /\b(BTS|bac(calaur[ée]at)?|session \d|[ée]preuve|acad[ée]mie|sujet z[ée]ro|brevet)\b/i);
  assert.deepEqual(errors, []);
  await context.close();
});

test("entraînement : sujet entièrement juste = 20/20, verrouillage, corrections et impression", async () => {
  const { context, page, errors } = await open();
  await page.click("[data-mode=training]");
  assert.ok(await page.isVisible("main.page"));
  assert.ok(!(await page.isVisible("#exam-submit")));

  // tracé de l'axe validé avant Q11.1 : la correction attend la question
  await drawArrow(page, "sk_q11_2", 0.3, 0.4, 0.5, 0.4);
  await page.click("#sk_q11_2 .btn-sketch");
  assert.match(await text(page, "#sk_q11_2 .sk-wait"), /Q11\.1/);
  assert.ok(!(await page.isVisible("#sk_q11_2 .selfeval")));
  assert.ok(!(await page.isVisible("#sk_q11_2 .sk-corr-toggle")));

  for (const [id, ans] of Object.entries(REP)) {
    await page.fill(`#in-${id}`, ans);
    if (id.endsWith("_2") || id === "q1_9") await page.press(`#in-${id}`, "Enter");
    else await page.click(`#${id} .btn-validate`);
    assert.match(await text(page, `#${id} .q-status`), /Juste/, id);
    assert.ok(await page.isDisabled(`#in-${id}`), id + " verrouillée");
    assert.ok(await page.isDisabled(`#${id} .btn-validate`));
    assert.ok(await page.isVisible(`#${id} .q-expl`));
  }
  // la correction de l'axe est apparue avec la validation de Q11.1
  assert.ok(await page.isVisible("#sk_q11_2 .selfeval"));
  assert.ok(await page.isChecked("#sk_q11_2 .sk-corr-toggle input"));

  await drawArrow(page, "sk_q1_5", 0.6, 0.6, 0.6, 0.9);
  await page.click("#sk_q1_5 .btn-sketch");
  assert.ok(await page.isVisible("#sk_q1_5 .selfeval"));
  for (const sk of SKETCHES) {
    for (const cb of await page.locator(`#${sk} .selfeval input[data-crit]`).all()) await cb.check();
    await page.click(`#${sk} .btn-self`);
    assert.match(await text(page, `#${sk} .se-score`), /4 points sur 4/);
    assert.ok(await page.isDisabled(`#${sk} .btn-self`));
  }
  assert.match(await text(page, "#score-val"), /20,0/);
  assert.equal((await text(page, "#recap .final-note")).trim(), "20,0/20");
  const notes = await page.locator("#recap-body .rc-note").allInnerTexts();
  assert.equal(notes.length, 11);
  notes.forEach((n) => assert.equal(n.trim(), "20,0"));
  assert.match(await text(page, "#score-count"), /55 items validés sur 55 · 61,0 \/ 61 points/);

  // chronomètre au format h:mm:ss
  await page.waitForTimeout(1200);
  assert.match(await text(page, "#timer-val"), /^0:\d{2}:\d{2}$/);
  assert.notEqual(await text(page, "#timer-val"), "0:00:00");

  // impression : en-tête de copie, corrections visibles, deux images par tracé
  await page.fill("#nom-eleve", "Élève Test");
  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  await page.emulateMedia({ media: "print" });
  assert.ok(await page.isVisible(".print-summary"));
  assert.ok(await page.isVisible(".print-note-line"));
  assert.ok(!(await page.isVisible(".print-nograde")));
  assert.ok(!(await page.isVisible(".banner")));
  assert.ok(!(await page.isVisible(".rail")));
  assert.match(await text(page, ".print-summary"), /Élève Test[\s\S]*entraînement[\s\S]*\d+ min \d{2} s[\s\S]*20,0\/20/);
  for (const sk of SKETCHES) {
    assert.match(await page.getAttribute(`#${sk} .sk-print-student`, "src"), /^data:image\/png/);
    assert.match(await page.getAttribute(`#${sk} .sk-print-corr`, "src"), /^data:image\/png/);
  }
  assert.ok(await page.isVisible("#q1_1 .q-expl"));
  const pdf = await page.pdf({ format: "A4" });
  assert.ok(pdf.length > 100000);
  assert.deepEqual(errors, []);
  await context.close();
});

test("entraînement : demi-point d'unité, réponse fausse, saisie vide refusée, note provisoire pondérée", async () => {
  const { context, page, errors } = await open();
  await page.click("[data-mode=training]");
  await page.click("#q1_1 .btn-validate");
  assert.match(await text(page, "#q1_1 .q-msg"), /Saisis une réponse/);
  assert.ok(!(await page.isDisabled("#in-q1_1")));

  await page.fill("#in-q1_1", "833,85");
  await page.click("#q1_1 .btn-validate");
  assert.match(await text(page, "#q1_1 .q-status"), /unité manquante — ½ point/);
  assert.match(await text(page, "#q1_1 .q-unit-msg"), /Unité manquante.*\(N\)/);
  assert.ok(await page.locator("#q1_1.is-half").count());
  assert.match(await text(page, "#score-val"), /10,0/);

  await page.fill("#in-q2_2", "100 kN");
  await page.click("#q2_2 .btn-validate");
  assert.match(await text(page, "#q2_2 .q-unit-msg"), /Unité incorrecte/);

  await page.fill("#in-q1_2", "700 mm");
  await page.click("#q1_2 .btn-validate");
  assert.ok(await page.locator("#q1_2.is-ko").count());
  // partie 1 : 0,5/2 → 5/20 (poids 30) ; partie 2 : 0,5/1 → 10/20 (poids 10) → (30×5 + 10×10)/40 = 6,25
  assert.match(await text(page, "#score-val"), /6,[23]/);
  assert.deepEqual(errors, []);
  await context.close();
});

test("examen : rien ne filtre avant la remise, y compris à l'impression ; remise en deux temps", async () => {
  const { context, page, errors } = await open();
  await page.click("[data-mode=exam]");
  assert.ok(!(await page.isVisible("#score-val")));
  assert.match(await text(page, ".exam-state"), /Note masquée/);
  assert.ok(!(await page.isVisible("#q1_1 .btn-validate")));
  assert.ok(!(await page.isVisible("#sk_q1_5 .btn-sketch")));
  assert.ok(!(await page.isVisible("#recap-graded")));

  for (const [id, ans] of Object.entries(REP)) if (id !== "q1_1" && id !== "q2_3") await page.fill(`#in-${id}`, ans);
  await page.fill("#in-q3_1", "49050 N"); // signe oublié : faux
  await drawArrow(page, "sk_q1_5", 0.6, 0.6, 0.6, 0.9);
  assert.match(await text(page, "#score-count"), /51 réponse\(s\) renseignée\(s\) sur 53/);
  // une réponse reste modifiable
  await page.fill("#in-q2_2", "1 MPa");
  await page.fill("#in-q2_2", REP.q2_2);

  // impression avant la remise : copie non corrigée, aucune correction
  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  await page.emulateMedia({ media: "print" });
  assert.ok(await page.isVisible(".print-nograde"));
  assert.ok(!(await page.isVisible(".print-note-line")));
  assert.ok(!(await page.isVisible("#q2_2 .q-expl")));
  assert.ok(!(await page.isVisible("#sk_q1_5 .q-expl")));
  assert.ok(!(await page.isVisible("#sk_q1_5 .sk-print-corr")));
  assert.ok(!(await page.isVisible("#recap-graded")));
  assert.match(await text(page, ".print-summary"), /examen — copie non corrigée/);
  await page.emulateMedia({ media: "screen" });

  await page.click("#exam-submit");
  assert.match(await text(page, "#exam-warn"), /2 réponse\(s\) encore vide\(s\)/);
  assert.ok(!(await page.locator("body.graded").count()));
  await page.click("#exam-submit");
  assert.ok(await page.locator("body.graded").count());
  assert.ok(await page.isDisabled("#in-q2_2"));
  assert.match(await text(page, "#q1_1 .q-status"), /Non répondue/);
  assert.match(await text(page, "#q3_1 .q-status"), /Faux/);
  assert.match(await text(page, "#q2_2 .q-status"), /Juste/);
  assert.ok(await page.isVisible("#q2_2 .q-expl"));
  for (const sk of SKETCHES) assert.ok(await page.isVisible(`#${sk} .selfeval`), sk);

  const t1 = await text(page, "#timer-val");
  await page.waitForTimeout(1300);
  assert.equal(await text(page, "#timer-val"), t1, "chronomètre arrêté");

  for (const sk of SKETCHES) {
    for (const cb of await page.locator(`#${sk} .selfeval input[data-crit]`).all()) await cb.check();
    await page.click(`#${sk} .btn-self`);
  }
  // P1 : 12/13 ; P2 : 3/4 ; P3 : 5/6 ; autres parties 20/20
  // (30×240/13 + 10×15 + 15×100/6 + 90×20) / 145 = 18,99
  assert.equal((await text(page, "#recap .final-note")).trim(), "19,0/20");
  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  await page.emulateMedia({ media: "print" });
  assert.ok(await page.isVisible(".print-note-line"));
  assert.ok(!(await page.isVisible(".print-nograde")));
  assert.match(await text(page, ".print-summary"), /examen \(copie corrigée\)[\s\S]*19,0\/20/);
  assert.deepEqual(errors, []);
  await context.close();
});

test("tracés : outils, gomme, annuler, texte, zoom, plein écran, fenêtre des DR", async () => {
  const { context, page, errors } = await open();
  await page.click("[data-mode=training]");
  const sk = "sk_q1_5";
  await drawArrow(page, sk, 0.2, 0.2, 0.4, 0.2);
  await drawArrow(page, sk, 0.2, 0.7, 0.4, 0.7);
  await page.click(`#${sk} [data-tool=line]`);
  const box = await page.locator(`#${sk} canvas`).boundingBox();
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.5, { steps: 3 });
  await page.mouse.up();
  assert.equal(await nStrokes(page, sk), 3);
  // gomme : un clic sur la première flèche ne supprime qu'elle
  await page.click(`#${sk} [data-tool=erase]`);
  const box1 = await page.locator(`#${sk} canvas`).boundingBox();
  await page.mouse.click(box1.x + box1.width * 0.3, box1.y + box1.height * 0.2);
  assert.equal(await nStrokes(page, sk), 2);
  await page.click(`#${sk} [data-act=undo]`);
  assert.equal(await nStrokes(page, sk), 1);
  // texte
  await page.click(`#${sk} [data-tool=text]`);
  const box2 = await page.locator(`#${sk} canvas`).boundingBox(); // la page a pu défiler
  await page.mouse.click(box2.x + box2.width * 0.8, box2.y + box2.height * 0.3);
  // le gabarit donne le focus au champ de texte au tick suivant
  await page.waitForFunction(() => document.activeElement && document.activeElement.classList.contains("sk-text"));
  await page.keyboard.type("P");
  await page.keyboard.press("Enter");
  assert.equal(await nStrokes(page, sk), 2);
  // zoom et plein écran
  await page.click(`#${sk} [data-zoom=in]`);
  assert.equal((await text(page, `#${sk} .zoom-val`)).trim(), "150 %");
  await page.click(`#${sk} [data-zoom=reset]`);
  await page.click(`#${sk} [data-act=full]`);
  assert.ok(await page.locator(`#${sk}.is-full`).count());
  await page.keyboard.press("Escape");
  assert.ok(!(await page.locator(`#${sk}.is-full`).count()));
  // tout effacer : confirmation en deux temps
  await page.click(`#${sk} [data-act=clear]`);
  assert.equal(await nStrokes(page, sk), 2);
  await page.click(`#${sk} [data-act=clear]`);
  assert.equal(await nStrokes(page, sk), 0);

  // fenêtre des documents réponses : les deux fonds vierges, un par page
  const [popup] = await Promise.all([context.waitForEvent("page"), page.click(`#${sk} [data-act=drprint]`)]);
  await popup.waitForLoadState();
  assert.equal(await popup.locator(".sheet").count(), 2);
  const heads = await popup.locator(".sheet h2").allInnerTexts();
  assert.match(heads[0], /DR1 Q1\.5/);
  assert.match(heads[1], /DR2 Q11\.2/);
  assert.match(await popup.locator(".bar p").innerText(), /Deux pages/);
  assert.match(await popup.locator(".sheet img").first().getAttribute("src"), /^data:image\/png/);
  assert.deepEqual(errors, []);
  await context.close();
});

test("documents : rail, boutons des en-têtes de question, fermeture ; rail remplacé par un bouton sous 760 px", async () => {
  const { context, page, errors } = await open();
  await page.click("[data-mode=training]");
  await page.click(".rail [data-doc=DT1]");
  assert.ok(await page.locator("body.panel-open").count());
  assert.ok(await page.isVisible("#doc-DT1"));
  assert.match(await text(page, "#dp-title"), /DT1 : Formulaire — traction et compression/);
  await page.click("#partie-4 .doc-chip[data-doc=DT3]");
  assert.ok(await page.isVisible("#doc-DT3"));
  assert.match(await text(page, "#doc-DT3"), /60/);
  await page.click("#dp-in");
  assert.equal((await text(page, "#dp-zoom")).trim(), "125 %");
  await page.keyboard.press("Escape");
  assert.ok(!(await page.locator("body.panel-open").count()));
  await context.close();

  const m = await open({ width: 420, height: 800 });
  await m.page.click("[data-mode=exam]");
  assert.ok(!(await m.page.isVisible(".rail")));
  assert.ok(await m.page.isVisible("#btn-docs"));
  await m.page.click("#btn-docs");
  assert.ok(await m.page.isVisible("#doc-DP1"));
  const overflow = await m.page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  assert.ok(overflow <= 0, "pas de défilement horizontal");
  assert.deepEqual([...errors, ...m.errors], []);
  await m.context.close();
});
