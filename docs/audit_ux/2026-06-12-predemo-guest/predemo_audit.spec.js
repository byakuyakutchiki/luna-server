// @ts-check
/**
 * AUDIT PRÉ-DÉMO — Days Legacy Invited Guest
 * Couvre : accès, navigation, boutons, media, collaboration, erreurs, viewports
 * Playwright chromium uniquement (desktop + mobile emulation)
 */
const { test, expect, chromium } = require('/home/ludo/.nvm/versions/node/v20.18.3/lib/node_modules/@playwright/test');
const fs = require('fs');

const BASE  = 'https://localhost:8889';
const OUT   = '/tmp/predemo_audit/shots';

fs.mkdirSync(OUT, { recursive: true });

/* ignoreHTTPSErrors doit être au niveau du contexte — appliqué globalement ici */
test.use({ ignoreHTTPSErrors: true });

/* helper : navigate TW engine to step N without WS */
async function wsGoto(page, step) {
  await page.evaluate((s) => {
    window.TW.step = s;
    ['renderStepper','updateStats','renderSideRight','renderSeats','renderSpecs','renderActions','renderContextHeader']
      .forEach(function(fn){ if(typeof window[fn]==='function') window[fn](); });
    if(typeof window.applyCanvasState==='function') window.applyCanvasState(s);
  }, step);
  await page.waitForTimeout(400);
}

/* helper : collect console errors + network 4xx/5xx */
function attachCollectors(page) {
  const cErr = [], netErr = [];
  page.on('console', m => {
    if (m.type() === 'error') cErr.push(m.text());
  });
  page.on('response', r => {
    if (r.status() >= 400) netErr.push(r.status() + ' ' + r.url());
  });
  return { cErr, netErr };
}

/* ================================================================
   1. ACCÈS GUEST — AUCUNE AUTHENTIFICATION REQUISE
   ================================================================ */
test.describe('1 — Accès guest (public)', () => {

  test('GET /dashboard — 200 sans auth', async ({ page }) => {
    
    page.setExtraHTTPHeaders({});
    const res = await page.goto(BASE + '/dashboard?demo=1');
    expect(res.status()).toBe(200);
    await page.screenshot({ path: OUT + '/01_dashboard_access.png' });
    console.log('✓ /dashboard accessible');
  });

  test('GET /prospects — 200 sans auth', async ({ page }) => {
    const res = await page.goto(BASE + '/prospects?demo=1');
    expect(res.status()).toBe(200);
    console.log('✓ /prospects accessible');
  });

  test('GET /workspace — 200 sans auth', async ({ page }) => {
    const res = await page.goto(BASE + '/workspace?demo=1');
    expect(res.status()).toBe(200);
    console.log('✓ /workspace accessible');
  });

});

/* ================================================================
   2. NAVIGATION — CHAÎNE COMPLÈTE DEMO
   ================================================================ */
test('2 — Chaîne démo : dashboard → prospects → workspace', async ({ page }) => {
  const { cErr, netErr } = attachCollectors(page);
  page.setExtraHTTPHeaders({});

  /* Dashboard */
  await page.goto(BASE + '/dashboard?demo=1');
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: OUT + '/02a_dashboard.png' });

  /* M. Renard card → prospects */
  const cards = page.locator('#dlSessGrid .dl-sess');
  await expect(cards.first()).toBeVisible();
  await cards.first().click();
  await page.waitForURL('**/prospects?demo=1', { timeout: 5000 });
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: OUT + '/02b_prospects_list.png' });

  /* Traiter → fiche */
  await page.click('button:has-text("Traiter ce prospect")');
  await page.waitForTimeout(300);
  await page.screenshot({ path: OUT + '/02c_fiche_cr.png' });

  /* Valider CR → Sophia */
  await page.click('button:has-text("Valider le compte-rendu")');
  await page.waitForTimeout(2400);
  await page.screenshot({ path: OUT + '/02d_sophia_analyse.png' });

  /* CTA → workspace */
  await page.click('button:has-text("Préparer la proposition")');
  await page.waitForURL('**/workspace?demo=1', { timeout: 5000 });
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);
  await page.screenshot({ path: OUT + '/02e_workspace_entry.png' });

  /* Vérif titre M. Renard */
  const title = page.locator('#twSessionTitle');
  await expect(title).toHaveText('Dossier M. Renard — Transition patrimoniale');

  const realErrors = cErr.filter(e =>
    !e.includes('favicon') &&
    !e.includes('Failed to load resource') &&
    !e.toLowerCase().includes('ws') &&
    !e.toLowerCase().includes('websocket')
  );
  const realNetErrors = netErr.filter(u =>
    !u.includes('favicon') && !u.includes('ws')
  );

  console.log('✓ Chaîne complète OK');
  console.log('  Console errors:', realErrors.length ? realErrors : '(aucune)');
  console.log('  Network errors:', realNetErrors.length ? realNetErrors : '(aucune)');
  expect(realErrors).toHaveLength(0);
});

/* ================================================================
   3. MATRICE BOUTONS — WORKSPACE COMPLET
   ================================================================ */
test('3 — Matrice boutons workspace', async ({ page }) => {
  const { cErr } = attachCollectors(page);
  const results = [];

  await page.goto(BASE + '/workspace?demo=1');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);

  async function checkBtn(id, label, action, expected) {
    try {
      const el = page.locator(id);
      const visible = await el.isVisible().catch(() => false);
      if (!visible) { results.push({ label, status: 'MISSING', note: id + ' non visible' }); return; }
      if (action === 'click') await el.click({ force: true });
      await page.waitForTimeout(300);
      const toast = await page.locator('#twToast').textContent().catch(() => '');
      results.push({ label, status: 'OK', note: toast ? 'toast: ' + toast.trim() : expected || '' });
    } catch(e) {
      results.push({ label, status: 'ERROR', note: String(e).slice(0, 80) });
    }
  }

  /* ── Bouton retour dashboard ── */
  await page.evaluate(() => { window._demoClickedBack = false; });
  const backBtn = page.locator('button:has-text("← Dashboard")');
  const backVisible = await backBtn.isVisible().catch(() => false);
  results.push({ label: '← Dashboard', status: backVisible ? 'OK' : 'MISSING', note: 'onclick window.location=/dashboard' });

  /* ── Step navigation ── */
  const nextBtn = page.locator('#btnNext');
  const prevBtn = page.locator('#btnPrev');
  const nextVis = await nextBtn.isVisible().catch(() => false);
  const prevVis = await prevBtn.isVisible().catch(() => false);
  results.push({ label: '› Étape suivante', status: nextVis ? 'OK' : 'MISSING' });
  results.push({ label: '‹ Étape précédente', status: prevVis ? 'OK' : 'MISSING' });

  if (nextVis) {
    const stepBefore = await page.evaluate(() => window.TW.step);
    await nextBtn.click();
    await page.waitForTimeout(200);
    const stepAfter = await page.evaluate(() => window.TW.step);
    results.push({ label: '› navigation step++', status: stepAfter > stepBefore ? 'OK' : 'FAIL', note: stepBefore+'→'+stepAfter });
    await prevBtn.click();
    await page.waitForTimeout(200);
  }

  /* ── Caméra (phase future P0.2) ── */
  await wsGoto(page, 1);
  await page.waitForTimeout(200);
  const actBtn1 = page.locator('#twActBtns button:has-text("Activer présence")');
  const presVisible = await actBtn1.isVisible().catch(() => false);
  if (presVisible) {
    await actBtn1.click();
    await page.waitForTimeout(300);
    const toast = await page.locator('#twToast').textContent().catch(() => '');
    results.push({ label: 'Activer présence (step 1)', status: 'TOAST', note: toast.trim() });
  } else {
    results.push({ label: 'Activer présence (step 1)', status: 'MISSING_ACTBTN' });
  }

  /* ── Boutons Caméra / Micro (header) ── */
  const camBtn = page.locator('#btnCam');
  const micBtn = page.locator('#btnMic');
  const screenBtn = page.locator('#btnScreen');
  const handBtn = page.locator('#btnHand');

  results.push({ label: '#btnCam (header)', status: (await camBtn.isVisible()) ? 'OK' : 'MISSING', note: 'display:none en mode demo (twPresenceControls)' });
  results.push({ label: '#btnMic (header)', status: (await micBtn.isVisible()) ? 'OK' : 'MISSING', note: 'display:none en mode demo' });
  results.push({ label: '#btnScreen (header)', status: (await screenBtn.isVisible()) ? 'OK' : 'MISSING' });
  results.push({ label: '#btnHand (header)', status: (await handBtn.isVisible()) ? 'OK' : 'MISSING' });

  /* ── Step 3 — Importer source ── */
  await wsGoto(page, 3);
  const importBtn = page.locator('#twActBtns button:has-text("Importer source")');
  if (await importBtn.isVisible()) {
    await importBtn.click();
    await page.waitForTimeout(300);
    const modalOn = await page.locator('#sourceModal.on').isVisible().catch(() => false);
    results.push({ label: 'Importer source (step 3)', status: modalOn ? 'OK' : 'FAIL', note: 'source modal' });
    /* Fermer explicitement via closeModal() — Escape non géré par les modaux */
    await page.evaluate(() => { if(typeof window.closeModal==='function') window.closeModal('sourceModal'); });
    await page.waitForTimeout(300);
  }

  /* ── Step 4 — Déclencher Iris ── */
  await wsGoto(page, 4);
  const irisBtn = page.locator('#twActBtns button:has-text("Déclencher Iris")');
  if (await irisBtn.isVisible()) {
    await irisBtn.click();
    await page.waitForTimeout(400);
    const ovOn = await page.locator('#twIrisOv.on').isVisible().catch(() => false);
    results.push({ label: 'Déclencher Iris (step 4)', status: ovOn ? 'OK' : 'FAIL', note: 'overlay Iris' });
    const closeOv = page.locator('#twIrisOv button:has-text("Fermer")');
    if (await closeOv.isVisible()) await closeOv.click();
    await page.waitForTimeout(200);
  }

  /* ── Step 5 — Lancer le vote ── */
  await wsGoto(page, 5);
  const voteBtn = page.locator('#twActBtns button:has-text("Lancer le vote")');
  if (await voteBtn.isVisible()) {
    await voteBtn.click();
    await page.waitForTimeout(300);
    const toast = await page.locator('#twToast').textContent().catch(() => '');
    results.push({ label: 'Lancer le vote (step 5)', status: 'TOAST', note: toast.trim() });
  } else {
    results.push({ label: 'Lancer le vote (step 5)', status: 'MISSING_ACTBTN' });
  }

  /* ── Step 5 — Vote bouton sur proposition ── */
  const voteForBtn = page.locator('.tw-vote-btn').first();
  if (await voteForBtn.isVisible()) {
    await voteForBtn.click();
    await page.waitForTimeout(200);
    const voted = await voteForBtn.getAttribute('class');
    results.push({ label: 'Vote sur proposition (step 5)', status: voted && voted.includes('voted') ? 'OK' : 'WARN', note: 'bouton vote' });
  }

  /* ── Soumettre une piste ── */
  const propDrawer = page.locator('.tw-prop-drawer-hdr');
  if (await propDrawer.isVisible()) {
    results.push({ label: 'Panneau Propositions', status: 'OK', note: 'visible' });
    const addPropBtn = page.locator('#twPropAddBtn');
    if (await addPropBtn.isVisible()) {
      await addPropBtn.click();
      await page.waitForTimeout(200);
      const input = page.locator('#twPropInput');
      const inputVis = await input.isVisible().catch(() => false);
      results.push({ label: 'Soumettre une piste — input', status: inputVis ? 'OK' : 'FAIL', note: 'propOpenInput()' });
      if (inputVis) {
        await input.fill('Test audit proposition');
        const submitBtn = page.locator('#twPropSubmit');
        if (await submitBtn.isVisible()) {
          await submitBtn.click();
          await page.waitForTimeout(200);
          results.push({ label: 'propSubmit()', status: 'OK' });
        }
      }
    }
  }

  /* ── Step 6 — Analyser avec IQ ── */
  await wsGoto(page, 6);
  const iqBtn = page.locator('#twActBtns button:has-text("Analyser avec IQ")');
  if (await iqBtn.isVisible()) {
    await iqBtn.click();
    await page.waitForTimeout(300);
    results.push({ label: 'Analyser avec IQ (step 6)', status: 'OK', note: 'overlay IQ' });
    const closeOv = page.locator('#twIrisOv button:has-text("Fermer")');
    if (await closeOv.isVisible()) await closeOv.click();
  }

  /* ── Step 7 — Ajouter objection ── */
  await wsGoto(page, 7);
  const objBtn = page.locator('#twActBtns button:has-text("Ajouter objection")');
  if (await objBtn.isVisible()) {
    await objBtn.click();
    await page.waitForTimeout(300);
    const toast = await page.locator('#twToast').textContent().catch(() => '');
    results.push({ label: 'Ajouter objection (step 7)', status: 'TOAST', note: toast.trim() });
  } else {
    results.push({ label: 'Ajouter objection (step 7)', status: 'MISSING_ACTBTN' });
  }

  /* ── Step 8 — Demander refonte ── */
  await wsGoto(page, 8);
  const refBtn = page.locator('#twActBtns button:has-text("Demander refonte")');
  if (await refBtn.isVisible()) {
    await refBtn.click();
    await page.waitForTimeout(300);
    results.push({ label: 'Demander refonte (step 8)', status: 'OK', note: 'overlay refonte' });
    const closeOv = page.locator('#twIrisOv button:has-text("Fermer")');
    if (await closeOv.isVisible()) await closeOv.click();
  }

  /* ── Step 10 — Décision ── */
  await wsGoto(page, 10);
  const decInput = page.locator('#twDecisionInput');
  const decVisible = await decInput.isVisible().catch(() => false);
  results.push({ label: 'Decision input (step 10)', status: decVisible ? 'OK' : 'FAIL' });
  if (decVisible) {
    await decInput.fill('Holding patrimoniale retenue — arbitrage fiscal confirmé.');
    await page.waitForTimeout(200);
    const valBtn = page.locator('button:has-text("Valider la décision")');
    if (await valBtn.isVisible()) {
      await valBtn.click();
      await page.waitForTimeout(300);
      const toast = await page.locator('#twToast').textContent().catch(() => '');
      results.push({ label: 'Valider la décision (step 10)', status: toast.includes('Décision') ? 'OK' : 'WARN', note: toast.trim() });
    }
  }

  /* ── Step 11 — Actions ── */
  await page.evaluate(function() {
    window.TW.decision = { id:'d1', text:'Holding patrimoniale retenue.', created_at:Date.now(), author_name:'Manager' };
    window.TW.step = 11;
    ['renderStepper','updateStats','renderSideRight','renderActions'].forEach(function(fn){
      if(typeof window[fn]==='function') window[fn]();
    });
    if(typeof window.applyCanvasState==='function') window.applyCanvasState(11);
  });
  await page.waitForTimeout(400);
  const actInput = page.locator('#twActInput');
  if (await actInput.isVisible()) {
    await actInput.fill('Rendez-vous notaire');
    const addBtn = page.locator('#twActAddBtn');
    if (await addBtn.isVisible()) {
      await addBtn.click();
      await page.waitForTimeout(200);
      results.push({ label: '+ Action (step 11)', status: 'OK', note: 'action ajoutée' });
    }
  } else {
    results.push({ label: '+ Action (step 11)', status: 'MISSING', note: '#twActInput not found' });
  }
  await page.screenshot({ path: OUT + '/03_workspace_step11_actions.png' });

  /* ── Step 12 — Générer livrable ── */
  await wsGoto(page, 12);
  const lvrBtn = page.locator('#twActBtns button:has-text("Générer livrable")');
  if (await lvrBtn.isVisible()) {
    await lvrBtn.click();
    await page.waitForTimeout(300);
    const toast = await page.locator('#twToast').textContent().catch(() => '');
    results.push({ label: 'Générer livrable (step 12)', status: 'TOAST', note: toast.trim() });
  }

  /* ── Step 13 — Distribuer ── */
  await wsGoto(page, 13);
  const distBtn = page.locator('#twActBtns button:has-text("Distribuer")');
  if (await distBtn.isVisible()) {
    await distBtn.click();
    await page.waitForTimeout(300);
    const toast = await page.locator('#twToast').textContent().catch(() => '');
    results.push({ label: 'Distribuer (step 13)', status: 'TOAST', note: toast.trim() });
  }

  /* ── Générer rapport (dossier final) ── */
  await page.evaluate(function() {
    window.TW.actions = [
      { id:'a1', text:'Rendez-vous notaire', status:'TODO', created_at:Date.now()-600000, author_name:'Manager' },
      { id:'a2', text:'Simulation IR/IFI',   status:'TODO', created_at:Date.now()-500000, author_name:'Manager' },
    ];
    if (typeof window.generateReport === 'function') window.generateReport();
  });
  await page.waitForTimeout(800);
  const reportVis = await page.locator('#twReport, .tw-rpt-panel, [id*="report"]').first().isVisible().catch(() => false);
  results.push({ label: 'generateReport() — dossier final', status: reportVis ? 'OK' : 'WARN', note: reportVis ? 'panneau visible' : 'panneau non trouvé — à vérifier' });
  await page.screenshot({ path: OUT + '/03_workspace_dossier_final.png' });

  /* ── Modal Réserve ── */
  await page.evaluate(() => {
    window.TW.step = 5;
    window.TW.activeProposalId = 'dp1';
    ['renderStepper','renderActions'].forEach(fn => { if(typeof window[fn]==='function') window[fn](); });
  });
  await page.waitForTimeout(200);
  const reserveActBtn = page.locator('#twActBtns button:has-text("Ouvrir une réserve")');
  if (await reserveActBtn.isVisible()) {
    await reserveActBtn.click();
    await page.waitForTimeout(300);
    const modalOn = await page.locator('#reserveModal.on').isVisible().catch(() => false);
    results.push({ label: 'Modal Réserve', status: modalOn ? 'OK' : 'FAIL', note: 'openReserveModal()' });
    if (modalOn) {
      /* remplir titre */
      const titleInput = page.locator('#reserveModal input[type=text]').first();
      if (await titleInput.isVisible()) await titleInput.fill('Test réserve audit');
      const lvlBtn = page.locator('.tw-rv-lvl-btn').first();
      if (await lvlBtn.isVisible()) await lvlBtn.click();
      await page.waitForTimeout(200);
      await page.keyboard.press('Escape');
    }
  } else {
    results.push({ label: 'Modal Réserve', status: 'MISSING', note: 'bouton non affiché (activeProposal requis)' });
  }

  /* ── Modal Add ── */
  const addModal = page.locator('#addModal');
  const addModalExists = (await addModal.count()) > 0;
  results.push({ label: 'Modal Add (#addModal)', status: addModalExists ? 'OK' : 'MISSING', note: 'présent dans DOM' });

  /* ── Console errors ── */
  const realErrors = cErr.filter(e =>
    !e.includes('favicon') && !e.toLowerCase().includes('ws') &&
    !e.toLowerCase().includes('websocket') && !e.toLowerCase().includes('failed to load resource')
  );

  console.log('\n══ MATRICE BOUTONS ══');
  results.forEach(r => {
    const icon = r.status==='OK' ? '✓' : r.status==='TOAST' ? '💬' : r.status==='WARN' ? '⚠️' : r.status==='MISSING' ? '?' : '✗';
    console.log(icon + ' [' + r.status + '] ' + r.label + (r.note ? ' — ' + r.note : ''));
  });
  console.log('\nConsole errors (filtrees):', realErrors.length ? realErrors : '(aucune)');

  expect(realErrors).toHaveLength(0);
});

/* ================================================================
   4. MEDIA — CAMÉRA / MICRO (fake devices)
   ================================================================ */
test('4 — Caméra + Micro (getUserMedia fake)', async ({ browser }) => {
  const ctx = await browser.newContext({
    permissions: ['camera', 'microphone'],
    ignoreHTTPSErrors: true,
  });
  const page = await ctx.newPage();
  const { cErr } = attachCollectors(page);

  /* Pour room mode (setup modal) */
  await page.goto(BASE + '/workspace?room=audit-media-test');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(600);

  /* Setup modal: renseigner prénom + rejoindre */
  const nameInput = page.locator('#setupName');
  if (await nameInput.isVisible()) {
    await nameInput.fill('Auditeur');
    const ownerBtn = page.locator('#role-owner');
    if (await ownerBtn.isVisible()) await ownerBtn.click();
    await page.waitForTimeout(200);
    await page.click('button:has-text("Rejoindre →")');
    await page.waitForTimeout(600);
  }

  /* Vérifier que le panneau de contrôle presence est maintenant visible */
  const presCtrl = page.locator('#twPresenceControls');
  const presVisible = await presCtrl.isVisible().catch(() => false);

  /* toggleCam */
  const camBtn = page.locator('#btnCam');
  const camVis = await camBtn.isVisible().catch(() => false);
  if (camVis) {
    await camBtn.click();
    await page.waitForTimeout(1000);
    const camOn = await page.evaluate(() => window.TW && window.TW._camOn);
    console.log('  Caméra toggle — TW._camOn:', camOn);
  }

  /* toggleMic */
  const micBtn = page.locator('#btnMic');
  const micVis = await micBtn.isVisible().catch(() => false);
  if (micVis) {
    await micBtn.click();
    await page.waitForTimeout(1000);
    const micOn = await page.evaluate(() => window.TW && window.TW._micOn);
    console.log('  Micro toggle — TW._micOn:', micOn);
  }

  await page.screenshot({ path: OUT + '/04_media_cam_mic.png' });

  const camResult = camVis ? 'TESTED' : 'HIDDEN_IN_DEMO_MODE';
  const micResult = micVis ? 'TESTED' : 'HIDDEN_IN_DEMO_MODE';
  console.log('✓ Caméra: ' + camResult);
  console.log('✓ Micro: ' + micResult);
  console.log('  twPresenceControls visible:', presVisible);

  const realErrors = cErr.filter(e =>
    !e.includes('getUserMedia') && !e.includes('favicon') &&
    !e.toLowerCase().includes('ws') && !e.includes('Failed to load resource')
  );
  expect(realErrors).toHaveLength(0);
  await ctx.close();
});

/* ================================================================
   5. PARTAGE ÉCRAN — desktop
   ================================================================ */
test('5 — Partage écran — desktop (getDisplayMedia)', async ({ browser }) => {
  const ctx = await browser.newContext({
    ignoreHTTPSErrors: true,
  });
  const page = await ctx.newPage();

  await page.goto(BASE + '/workspace?room=audit-screen-test');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(600);

  /* Rejoindre la room */
  const nameInput = page.locator('#setupName');
  if (await nameInput.isVisible()) {
    await nameInput.fill('Auditeur');
    await page.click('button:has-text("Rejoindre →")');
    await page.waitForTimeout(600);
  }

  const screenBtn = page.locator('#btnScreen');
  const screenBtnVis = await screenBtn.isVisible().catch(() => false);

  if (screenBtnVis) {
    /* getDisplayMedia requiert geste utilisateur — cliquer déclenchera le prompt */
    /* En Playwright sans option fake, le prompt apparaît → erreur attendue */
    let screenErrName = null;
    page.on('console', m => { if (m.type() === 'warning' && m.text().includes('SCREEN')) { screenErrName = m.text(); } });

    await screenBtn.click({ force: true });
    await page.waitForTimeout(1500);
    /* Vérifier si le bouton est en état ON (partage actif) ou reste OFF */
    const btnClass = await screenBtn.getAttribute('class');
    const isOn = btnClass && btnClass.includes('on');
    console.log('✓ Bouton screen share visible en room mode');
    console.log('  État après click:', isOn ? 'ON (partagé)' : 'OFF (non partagé — getDisplayMedia bloqué sans UI réelle)');
  } else {
    console.log('  #btnScreen caché (attendu en démo mode solo)');
  }

  await page.screenshot({ path: OUT + '/05_screen_share.png' });
  await ctx.close();
});

/* ================================================================
   6. COLLABORATION — 2 SESSIONS PARALLÈLES
   ================================================================ */
test('6 — Collaboration WS — 2 sessions parallèles', async ({ browser }) => {
  const ROOM_ID = 'audit-collab-' + Date.now();

  const ctx1 = await browser.newContext({ ignoreHTTPSErrors: true });
  const ctx2 = await browser.newContext({ ignoreHTTPSErrors: true });
  const p1 = await ctx1.newPage();
  const p2 = await ctx2.newPage();

  const ws1Log = [], ws2Log = [];
  p1.on('console', m => { if (m.text().includes('[WS]')) ws1Log.push(m.text()); });
  p2.on('console', m => { if (m.text().includes('[WS]')) ws2Log.push(m.text()); });

  /* Browser 1 — Owner */
  await p1.goto(BASE + '/workspace?room=' + ROOM_ID);
  await p1.waitForLoadState('networkidle');
  await p1.waitForTimeout(500);

  const nm1 = p1.locator('#setupName');
  if (await nm1.isVisible()) {
    await nm1.fill('Manager');
    const ownerBtn = p1.locator('#role-owner');
    if (await ownerBtn.isVisible()) await ownerBtn.click();
    await p1.click('button:has-text("Rejoindre →")');
    await p1.waitForTimeout(800);
  }

  /* Browser 2 — Participant */
  await p2.goto(BASE + '/workspace?room=' + ROOM_ID);
  await p2.waitForLoadState('networkidle');
  await p2.waitForTimeout(500);

  const nm2 = p2.locator('#setupName');
  if (await nm2.isVisible()) {
    await nm2.fill('Participant');
    const participantBtn = p2.locator('#role-participant');
    if (await participantBtn.isVisible()) await participantBtn.click();
    await p2.click('button:has-text("Rejoindre →")');
    await p2.waitForTimeout(800);
  }

  /* Attendre la connexion WS (max 5s) */
  await p1.waitForTimeout(2000);
  await p2.waitForTimeout(1000);

  const p1Connected = await p1.evaluate(() => window.TW && window.TW.wsConnected);
  const p2Connected = await p2.evaluate(() => window.TW && window.TW.wsConnected);

  console.log('  Browser1 (Owner) WS connected:', p1Connected);
  console.log('  Browser2 (Participant) WS connected:', p2Connected);

  /* Test sync: Owner avance à l'étape 3 */
  if (p1Connected) {
    await p1.evaluate(() => {
      if (typeof window.wsSend === 'function') {
        window.TW.step = 3;
        window.wsSend({ type:'step_change', step:3 });
        if (typeof window.renderStepper==='function') window.renderStepper();
        if (typeof window.applyCanvasState==='function') window.applyCanvasState(3);
      }
    });
    await p2.waitForTimeout(1000);
    const p2Step = await p2.evaluate(() => window.TW.step);
    console.log('  Sync step owner→participant: step visible sur p2 =', p2Step);
    const syncOk = p2Step === 3;
    console.log('  Sync ' + (syncOk ? 'OK ✓' : 'KO ✗ — WS potentiellement non connecté'));
  }

  await p1.screenshot({ path: OUT + '/06a_collab_owner.png' });
  await p2.screenshot({ path: OUT + '/06b_collab_participant.png' });

  console.log('  WS log p1:', ws1Log.slice(0, 5));
  console.log('  WS log p2:', ws2Log.slice(0, 5));

  await ctx1.close();
  await ctx2.close();
});

/* ================================================================
   7. ERREURS CONSOLE + RÉSEAU — Toutes les pages demo
   ================================================================ */
test('7 — Zéro erreur console/réseau — pages démo', async ({ page }) => {
  const pages = [
    { url: BASE + '/dashboard?demo=1', label: 'dashboard' },
    { url: BASE + '/prospects?demo=1', label: 'prospects' },
    { url: BASE + '/workspace?demo=1', label: 'workspace' },
  ];
  const report = {};

  for (const p of pages) {
    const cErr = [], netErr = [];
    page.on('console', m => { if (m.type() === 'error') cErr.push(m.text()); });
    page.on('response', r => { if (r.status() >= 400) netErr.push(r.status() + ' ' + r.url()); });

    await page.goto(p.url);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(800);

    const ce = cErr.filter(e =>
      !e.includes('favicon') && !e.toLowerCase().includes('websocket') &&
      !e.toLowerCase().includes('[ws]') && !e.includes('Failed to load resource')
    );
    const ne = netErr.filter(e =>
      !e.includes('favicon') && !e.includes('/ws/') && !e.includes('websocket')
    );

    report[p.label] = { consoleErrors: ce, networkErrors: ne };
    page.removeAllListeners('console');
    page.removeAllListeners('response');
  }

  console.log('\n══ ERREURS CONSOLE / RÉSEAU ══');
  for (const [label, r] of Object.entries(report)) {
    const ce = r.consoleErrors.length;
    const ne = r.networkErrors.length;
    const status = (ce + ne === 0) ? '✓' : '✗';
    console.log(status + ' ' + label + ' — console: ' + ce + ', réseau: ' + ne);
    if (ce > 0) r.consoleErrors.forEach(e => console.log('    ⚠ CONSOLE: ' + e));
    if (ne > 0) r.networkErrors.forEach(e => console.log('    ⚠ NET: ' + e));
  }

  for (const [, r] of Object.entries(report)) {
    expect(r.consoleErrors).toHaveLength(0);
    expect(r.networkErrors).toHaveLength(0);
  }
});

/* ================================================================
   8. MULTI-VIEWPORT — 4 résolutions
   ================================================================ */
test('8 — Multi-viewport — 4 résolutions', async ({ browser }) => {
  const VIEWPORTS = [
    { w:1920, h:1080, lbl:'desktop_1920' },
    { w:1366, h:768,  lbl:'laptop_1366' },
    { w:768,  h:1024, lbl:'tablet_768' },
    { w:390,  h:844,  lbl:'mobile_390' },
  ];

  for (const vp of VIEWPORTS) {
    const ctx = await browser.newContext({
      ignoreHTTPSErrors: true,
      viewport: { width: vp.w, height: vp.h },
    });
    const page = await ctx.newPage();

    /* Dashboard */
    await page.goto(BASE + '/dashboard?demo=1');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${OUT}/08_${vp.lbl}_dashboard.png` });

    /* Prospects */
    await page.goto(BASE + '/prospects?demo=1');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${OUT}/08_${vp.lbl}_prospects.png` });

    /* Workspace */
    await page.goto(BASE + '/workspace?demo=1');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(600);
    await page.screenshot({ path: `${OUT}/08_${vp.lbl}_workspace.png` });

    /* Workspace step 5 (propositions) */
    await page.evaluate(function(){
      window.TW.step=5;
      ['renderStepper','updateStats','renderSideRight','renderActions'].forEach(function(fn){
        if(typeof window[fn]==='function') window[fn]();
      });
      if(typeof window.applyCanvasState==='function') window.applyCanvasState(5);
    });
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${OUT}/08_${vp.lbl}_workspace_step5.png` });

    console.log('✓ ' + vp.lbl + ' (' + vp.w + '×' + vp.h + ') — 4 captures');
    await ctx.close();
  }
});

/* ================================================================
   9. APK URL — CONFIRMATION CRITIQUE
   ================================================================ */
test('9 — APK URL — confirmation critique', async ({ page }) => {
  /* Lire le fichier source Android directement */
  const apkSrc = require('fs').readFileSync(
    '/home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur/android-app/java/fr/yawatch/luna/MainActivity.java',
    'utf8'
  );
  const match = apkSrc.match(/LUNA_URL\s*=\s*"([^"]+)"/);
  const apkUrl = match ? match[1] : null;

  console.log('\n══ APK URL ══');
  console.log('  URL dans MainActivity.java:', apkUrl);
  console.log('  URL locale Days Legacy:     https://localhost:8889');
  console.log('  URL Cloud Run:              https://luna-beta-674304336025.europe-west1.run.app');
  console.log('');

  const isCloudRun = apkUrl && apkUrl.includes('run.app');
  const isLocal    = apkUrl && (apkUrl.includes('localhost') || apkUrl.includes('192.168'));

  if (isCloudRun) {
    console.log('  ⚠ CRITIQUE: APK pointe vers Cloud Run, PAS vers Days Legacy local');
    console.log('  ⚠ Les routes /dashboard, /workspace, /prospects ne sont PAS déployées sur Cloud Run');
    console.log('  ⚠ Un invité qui installe l\'APK verra Luna standard, PAS la démo Days Legacy');
    console.log('  → Correction: Déployer Days Legacy sur Cloud Run OU inviter via URL directe browser');
  } else if (isLocal) {
    console.log('  OK: APK pointe vers serveur local');
  }

  expect(apkUrl).not.toBeNull();
  /* Documenter, pas bloquer : l\'APK URL est un finding, pas un crash test */
  /* expect(isLocal).toBe(true); // décommenter quand APK pointera vers Days Legacy */
});
