const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require('C:/Users/xiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const resource = path.resolve(__dirname, '..');
(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const errors = [], rows = [];
  try {
    for (const width of [1366, 760, 393, 360]) {
      const page = await browser.newPage({ viewport: { width, height: 1050 } });
      page.on('pageerror', error => errors.push({ width, message: error.message }));
      await page.goto(pathToFileURL(path.join(resource, 'acceptance', '浏览.html')).href);
      await page.locator('#search').waitFor();
      async function openNav() {
        const toggle = page.locator('#navToggle');
        if (await toggle.isVisible() && await toggle.getAttribute('aria-expanded') === 'false') await toggle.click();
      }
      const planCount = await page.locator('#list .navitem').count();
      await page.locator('[data-mode="bdd"]').click();
      const scenarioCount = await page.locator('#list .navitem').count();
      await page.locator('#search').fill('日历');
      const filtered = await page.locator('#list .navitem').count();
      await page.locator('#search').fill('');
      await page.locator('#list [data-go="AC120"]').click();
      await page.locator('#rowSelect').selectOption('2');
      const parameterSwitch = (await page.locator('.step.result').textContent()).includes('one_time');
      const expandedScope = await page.evaluate(() => {
        const content = document.querySelector('#main').textContent;
        return content.includes('验收证据 checklist') && content.includes('主责') && content.includes('对应设计参考');
      });
      await page.locator('#main [data-go="IP19"]').first().click();
      const reverseLink = (await page.locator('#main h2').textContent()).includes('新建');
      await page.locator('[data-mode="trace"]').click();
      const traceCount = await page.locator('#list .navitem').count();
      await openNav();
      await page.locator('#list [data-go="FR14"]').click();
      const traceLinks = await page.locator('#main .related [data-go]').count();
      await page.locator('[data-mode="bdd"]').click();
      await openNav();
      await page.locator('#list [data-go="AC072"]').click();
      const reference = page.locator('details').filter({ has: page.locator('summary', { hasText: '对应设计参考' }) });
      await reference.locator('summary').click();
      await reference.evaluate(async node => {
        const images = [...node.querySelectorAll('img')];
        images.forEach(image => image.loading = 'eager');
        await Promise.all(images.map(image => image.decode()));
      });
      const imageCount = await reference.locator('img').count();
      await reference.locator('summary').click();
      const result = await page.evaluate(() => ({ viewport: innerWidth, documentWidth: document.documentElement.scrollWidth,
        mainWithinViewport: document.querySelector('#main').getBoundingClientRect().right <= innerWidth,
        requiredSections: ['场景 · Given', '操作 · When', '预期结果 · Then', '预期断言 checklist'].every(s => document.querySelector('#main').textContent.includes(s)),
        readOnlyNotice: document.querySelector('footer').textContent.includes('文档') && document.querySelector('footer').textContent.includes('不能写入')
      }));
      rows.push({ width, planCount, scenarioCount, filtered, parameterSwitch, reverseLink, traceCount, traceLinks, imageCount, expandedScope, ...result });
      if (width === 1366 || width === 360) {
        await page.locator('#main h2').scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(__dirname, width === 1366 ? '验收浏览-桌面.png' : '验收浏览-手机.png') });
      }
      await page.close();
    }
  } finally { await browser.close(); }
  const pass = !errors.length && rows.every(row => row.planCount === 30 && row.scenarioCount === 120 && row.filtered > 0 && row.filtered < 120 && row.parameterSwitch && row.reverseLink && row.traceCount === 60 && row.traceLinks > 0 && row.imageCount > 0 && row.expandedScope && row.viewport === row.documentWidth && row.mainWithinViewport && row.requiredSections && row.readOnlyNotice);
  const report = { checkedAt: new Date().toISOString(), scope: 'documentation viewer only', status: pass ? 'PASS' : 'FAIL', rows, errors, productAcceptance: 'NOT_RUN' };
  fs.writeFileSync(path.join(__dirname, '验收浏览检查结果.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, widths: rows.map(row => row.width), search: pass ? 'PASS' : 'SEE_REPORT', links: pass ? 'PASS' : 'SEE_REPORT', productAcceptance: 'NOT_RUN' }));
  if (!pass) throw new Error(JSON.stringify(report));
})().catch(error => { console.error(error); process.exitCode = 1; });
