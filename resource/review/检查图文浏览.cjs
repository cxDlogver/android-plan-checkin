const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const runtimeModules = process.env.REVIEW_PLAYWRIGHT_MODULE || 'C:/Users/xiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright';
const { chromium } = require(runtimeModules);
const resource = path.resolve(__dirname, '..');
const baseline = JSON.parse(fs.readFileSync(path.join(resource, 'design', 'page-map.json'), 'utf8')).baseline;
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.REVIEW_EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const errors = [], widths = [];
  try {
    for (const width of [1366, 760, 390, 360]) {
      const page = await browser.newPage({ viewport: { width, height: 1050 } });
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(pathToFileURL(path.join(resource, 'design', 'preview.html')).href);
      await page.evaluate(async () => { const images = [...document.images]; images.forEach(image => image.loading = 'eager'); await Promise.all(images.map(image => image.decode())); document.querySelectorAll('details').forEach(node => node.open = true); });
      const result = await page.evaluate(() => ({
        width: innerWidth, documentWidth: document.documentElement.scrollWidth,
        pairedPages: document.querySelectorAll('article').length,
        allImagesLoaded: [...document.images].every(image => image.complete && image.naturalWidth > 0),
        articlesWithinViewport: [...document.querySelectorAll('article')].every(node => { const rect = node.getBoundingClientRect(); return rect.left >= 0 && rect.right <= innerWidth; }),
        brokenAnchors: [...document.querySelectorAll('a[href^="#"]')].map(node => node.getAttribute('href').slice(1)).filter(id => !document.getElementById(id)),
        calendarTodayDocumented: document.querySelector('#screen-11').textContent.includes('浅色填充') && document.querySelector('#screen-11').textContent.includes('不显示✓'),
        calendarFractionDocumented: document.querySelector('#screen-11').textContent.includes('10sp') && document.querySelector('#screen-11').textContent.includes('金黄色'),
        pairColumns: getComputedStyle(document.querySelector('#screen-11 .pair')).gridTemplateColumns
      }));
      widths.push(result);
      await page.locator('#screen-11').evaluate(node => { document.documentElement.style.scrollBehavior = 'auto'; node.scrollIntoView({ behavior: 'instant' }); });
      if (width === 1366) await page.screenshot({ path: path.join(__dirname, '图文预览-桌面.png') });
      if (width === 390) await page.screenshot({ path: path.join(__dirname, '图文预览-手机.png') });
      if (width === 1366) { await page.locator('#screen-15').evaluate(node => node.scrollIntoView({ behavior: 'instant' })); await page.screenshot({ path: path.join(__dirname, '图文预览-字段与验收.png') }); }
      await page.close();
    }
  } finally { await browser.close(); }
  const report = { date: '2026-10-09', browser: 'Edge headless', type: 'document_layout_only', baseline: `${baseline.version} ${baseline.status}`, widths, errors };
  fs.writeFileSync(path.join(__dirname, '图文浏览检查结果.json'), JSON.stringify(report, null, 2) + '\n');
  if (errors.length || widths.some(row => row.width !== row.documentWidth || row.pairedPages !== 23 || !row.allImagesLoaded || !row.articlesWithinViewport || row.brokenAnchors.length || !row.calendarTodayDocumented || !row.calendarFractionDocumented)) throw new Error(JSON.stringify(report));
  console.log(JSON.stringify({ widths: widths.map(row => row.width), pages: 23, images: 'PASS', anchors: 'PASS', overflow: 'PASS', calendar: 'PASS' }));
})().catch(error => { console.error(error); process.exitCode = 1; });
