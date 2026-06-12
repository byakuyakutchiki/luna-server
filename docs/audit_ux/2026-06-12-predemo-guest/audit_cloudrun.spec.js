// @ts-check
/**
 * AUDIT CLOUD RUN — dayslegacy-workspace-demo
 * Tests post-déploiement : accès, chaîne, console errors, viewports
 */
const { test, expect } = require('/home/ludo/.nvm/versions/node/v20.18.3/lib/node_modules/@playwright/test');
const fs = require('fs');

const BASE = 'https://dayslegacy-workspace-demo-674304336025.europe-west1.run.app';
const OUT  = '/tmp/predemo_audit/cloudrun_shots';

fs.mkdirSync(OUT, { recursive: true });

test.use({ ignoreHTTPSErrors: true });

async function wsGoto(page, step) {
  await page.evaluate((s) => {
    window.TW.step = s;
    ['renderStepper','updateStats','renderSideRight','renderSeats','renderSpecs','renderActions','renderContextHeader']
      .forEach(function(fn){ if(typeof window[fn]==='function') window[fn](); });
    if(typeof window.applyCanvasState==='function') window.applyCanvasState(s);
  }, step);
  await page.waitForTimeout(400);
}

/* ── 1. Accès routes ─────────────────────────────────────────── */
test('1 — /health, /dashboard, /workspace, /prospects', async ({ page }) => {
  const health = await page.goto(BASE + '/health');
  expect(health.status()).toBe(200);
  const body = await page.textContent('body');
  expect(body).toContain('"status"');
  console.log('✓ /health OK');

  expect((await page.goto(BASE + '/dashboard?demo=1')).status()).toBe(200);
  console.log('✓ /dashboard 200');
  expect((await page.goto(BASE + '/workspace?demo=1')).status()).toBe(200);
  console.log('✓ /workspace 200');
  expect((await page.goto(BASE + '/prospects?demo=1')).status()).toBe(200);
  console.log('✓ /prospects 200');
});

/* ── 2. Chaîne démo complète + zéro erreur console ──────────── */
test('2 — Chaîne démo + zéro erreur console', async ({ page }) => {
  test.setTimeout(120000);
  const cErr = [], netErr = [];
  page.on('console', m => { if (m.type() === 'error') cErr.push(m.text()); });
  page.on('response', r => { if (r.status() >= 400) netErr.push(r.status() + ' ' + r.url()); });

  await page.goto(BASE + '/dashboard?demo=1');
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: OUT + '/01_dashboard.png' });

  /* Dashboard grosse carte */
  const acceptBtn = page.locator('button:has-text("Accepter ce prospect")');
  await expect(acceptBtn).toBeVisible();
  await acceptBtn.click();
  await page.waitForURL('**/prospects**', { timeout: 8000 });
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: OUT + '/02_prospects.png' });
  await page.waitForTimeout(300);
  await page.screenshot({ path: OUT + '/03_fiche.png' });

  await page.click('button:has-text("Valider le compte-rendu")');
  await page.waitForTimeout(2400);
  await expect(page.locator('#pnSophiaZone')).toContainText('94 / 100');
  await page.screenshot({ path: OUT + '/04_sophia.png' });

  await page.click('button:has-text("Préparer la proposition")');
  await page.waitForURL('**/workspace?demo=1', { timeout: 20000 });
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await expect(page.locator('#twSessionTitle')).toHaveText('Dossier M. Renard — Transition patrimoniale');
  await page.screenshot({ path: OUT + '/05_workspace_entry.png' });

  /* Step 5 — propositions */
  await wsGoto(page, 5);
  await page.screenshot({ path: OUT + '/06_workspace_step5.png' });

  /* Step 13 — dossier final */
  await page.evaluate(function() {
    window.TW.decision = { id:'d1', text:'Holding patrimoniale retenue.', created_at:Date.now(), author_name:'Manager' };
    window.TW.actions = [{ id:'a1', text:'Rendez-vous notaire', status:'TODO', created_at:Date.now()-600000, author_name:'Manager' }];
    if(typeof window.generateReport==='function') window.generateReport();
  });
  await page.waitForTimeout(800);
  await page.screenshot({ path: OUT + '/07_dossier_final.png' });

  /* Erreurs filtrées */
  const realCE = cErr.filter(e =>
    !e.includes('favicon') && !e.toLowerCase().includes('websocket') &&
    !e.toLowerCase().includes('[ws]') && !e.includes('Failed to load resource')
  );
  const realNE = netErr.filter(e => !e.includes('favicon') && !e.includes('/ws/'));

  console.log('Console errors:', realCE.length ? realCE : '(aucune)');
  console.log('Network errors:', realNE.length ? realNE : '(aucune)');
  expect(realCE).toHaveLength(0);
  expect(realNE).toHaveLength(0);
});

/* ── 3. Multi-viewport Cloud Run ─────────────────────────────── */
test('3 — Multi-viewport Cloud Run', async ({ browser }) => {
  test.setTimeout(120000);
  const VIEWPORTS = [
    { w:1920, h:1080, lbl:'desktop' },
    { w:1366, h:768,  lbl:'laptop' },
    { w:390,  h:844,  lbl:'mobile' },
  ];

  for (const vp of VIEWPORTS) {
    const ctx = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: vp.w, height: vp.h } });
    const page = await ctx.newPage();

    await page.goto(BASE + '/dashboard?demo=1');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${OUT}/vp_${vp.lbl}_dashboard.png` });

    await page.goto(BASE + '/workspace?demo=1');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(600);
    await page.evaluate(function(){
      window.TW.step=5;
      ['renderStepper','updateStats','renderSideRight','renderActions'].forEach(function(fn){
        if(typeof window[fn]==='function') window[fn]();
      });
      if(typeof window.applyCanvasState==='function') window.applyCanvasState(5);
    });
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${OUT}/vp_${vp.lbl}_workspace.png` });

    console.log('✓ ' + vp.lbl + ' (' + vp.w + '×' + vp.h + ')');
    await ctx.close();
  }
});
