const fs = require('fs');
const path = require('path');

const resource = path.resolve(__dirname, '..');
const docName = '设计需求文档-计划打卡-Android-v1.md';
const prd = fs.readFileSync(path.join(resource, docName), 'utf8').replace(/\r\n/g, '\n');
const map = JSON.parse(fs.readFileSync(path.join(__dirname, 'page-map.json'), 'utf8'));
const sections = new Map();
for (const match of prd.matchAll(/^### (FR\d{2})｜([^\n]+)\n([\s\S]*?)(?=^## |^### FR|$(?![\s\S]))/gm)) {
  sections.set(match[1], {
    title: match[2],
    body: match[3].replace(/<!-- page-context:start -->[\s\S]*?<!-- page-context:end -->\n*/g, '').trim()
  });
}
const acceptance = new Map();
for (const line of prd.split('\n')) {
  const match = line.match(/^\| (AT\d{2}) \/ ([^|]+)\| ([^|]+)\| ([^|]+)\|$/);
  if (match) acceptance.set(match[1], { refs: match[2].trim(), steps: match[3].trim(), result: match[4].trim() });
}
if (sections.size !== 32 || acceptance.size !== 28) throw new Error('需求或验收正文不完整');

function escape(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function inline(text) {
  return escape(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, href) => {
      if (/^(https?:\/\/|#)/.test(href)) return `<a href="${href}">${label}</a>`;
      return `<a href="../${href}">${label}</a>`;
    });
}
function markdown(body) {
  const lines = body.split('\n');
  const output = [];
  for (let i = 0; i < lines.length;) {
    const line = lines[i].trim();
    if (!line) { i++; continue; }
    if (line.startsWith('|')) {
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        const cells = lines[i++].trim().slice(1, -1).split('|').map(x => x.trim());
        if (!cells.every(x => /^:?-+:?$/.test(x))) rows.push(cells);
      }
      output.push(`<div class="table-scroll"><table><thead><tr>${rows.shift().map(x => `<th>${inline(x)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(x => `<td>${inline(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
      continue;
    }
    const list = line.match(/^(?:- |\d+\. )/);
    if (list) {
      const ordered = /^\d/.test(line);
      const tag = ordered ? 'ol' : 'ul';
      const items = [];
      while (i < lines.length && (ordered ? /^\d+\. / : /^- /).test(lines[i].trim())) {
        items.push(`<li>${inline(lines[i++].trim().replace(/^(?:- |\d+\. )/, ''))}</li>`);
      }
      output.push(`<${tag}>${items.join('')}</${tag}>`);
      continue;
    }
    const paragraph = [];
    while (i < lines.length && lines[i].trim() && !/^(?:\||- |\d+\. )/.test(lines[i].trim())) paragraph.push(lines[i++].trim());
    output.push(`<p>${inline(paragraph.join(' '))}</p>`);
  }
  return output.join('\n');
}

const seen = new Set();
function requirement(id, shared = false) {
  const section = sections.get(id);
  if (!section) throw new Error(`缺少${id}`);
  const anchor = seen.has(id) ? '' : ` id="requirement-${id.toLowerCase()}"`;
  seen.add(id);
  const inner = `<h3>${id}｜${escape(section.title)}</h3>${markdown(section.body)}`;
  if (!shared) return `<section class="requirement"${anchor}>${inner}</section>`;
  return `<details class="shared"${anchor}><summary>${id}｜${escape(section.title)}</summary><div class="shared-body">${markdown(section.body)}</div></details>`;
}
const cards = map.screens.map(screen => {
  const number = String(screen.order).padStart(2, '0');
  const primary = requirement(screen.primaryRequirement);
  const shared = screen.requirements.filter(id => id !== screen.primaryRequirement).map(id => requirement(id, true)).join('\n');
  const cases = screen.acceptance.map(id => {
    const test = acceptance.get(id);
    if (!test) throw new Error(`缺少${id}`);
    return `<section class="test"><h4>${id} · ${escape(test.refs)}</h4><p><strong>前置及操作：</strong>${inline(test.steps)}</p><p><strong>期望结果：</strong>${inline(test.result)}</p></section>`;
  }).join('\n');
  return `<article id="${screen.documentAnchor}">
    <div class="page-heading"><div><span class="eyebrow">图${number} · Pen真实导出</span><h2>${escape(screen.title)}</h2></div><a href="#page-index">回到目录 ↑</a></div>
    <div class="pair"><figure><a href="${screen.preview}" target="_blank" rel="noopener" aria-label="查看${escape(screen.title)}原图"><img src="${screen.preview}" width="${screen.canvasSize.width}" height="${screen.canvasSize.height}" alt="${escape(screen.title)}设计截图" loading="lazy"></a><figcaption>${escape(screen.designCaption)}<br>点击截图查看原图</figcaption></figure>
      <div class="spec"><p class="refs"><strong>需求：</strong>${screen.requirements.join('、')}<br><strong>验收：</strong>${screen.acceptance.join('、')} · <span class="not-run">尚未执行</span></p>${primary}
      ${shared ? `<div class="related"><h3>相关共用规则</h3><p class="hint">按需展开，正文与当前需求文档一致。</p>${shared}</div>` : ''}
      <details class="tests"><summary>验收场景与期望结果（${screen.acceptance.length}组）</summary>${cases}</details>
      <p class="source"><a href="../${docName}#fr${screen.primaryRequirement.slice(2)}">查看需求文档中的本页</a></p></div>
    </div></article>`;
});
if (seen.size !== 32) throw new Error(`图文预览未覆盖全部需求：${seen.size}/32`);
const testsCovered = new Set(map.screens.flatMap(screen => screen.acceptance));
if (testsCovered.size !== 28) throw new Error(`图文预览未覆盖全部验收：${testsCovered.size}/28`);
const index = map.screens.map(screen => `<a href="#${screen.documentAnchor}"><span>${String(screen.order).padStart(2, '0')}</span>${escape(screen.title)}</a>`).join('\n');
const html = `<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>计划打卡 Android V1 · 截图与需求对照</title>
<style>
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:20px}body{margin:0;background:#e8ecf0;color:#17212b;font:15px/1.8 "Microsoft YaHei",sans-serif}a{color:#253f53;text-underline-offset:3px}a:focus-visible,summary:focus-visible{outline:3px solid #277056;outline-offset:4px}header{padding:32px max(24px,calc((100vw - 1280px)/2));background:linear-gradient(125deg,#fafbfc,#c4cdd5 48%,#f2f5f7 55%,#dde3e9);border-bottom:1px solid #abb6c1}h1{font-size:30px;margin:0 0 12px}h2{font-size:24px;margin:0}h3{font-size:18px;margin:0 0 12px}h4{font-size:15px;margin:0 0 6px}h1,h2,h3,h4,summary{font-weight:700}header p{margin:8px 0}main{max-width:1280px;margin:28px auto;padding:0 24px}.index{padding:24px;border:1px solid #abb6c1;background:#f7f9fb;margin-bottom:32px}.index h2{font-size:20px;margin-bottom:16px}.index-links{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px 18px}.index a{display:block;text-decoration:none;padding:7px 4px}.index a:hover{background:#e5ebf0}.index a span{font-size:12px;margin-right:9px;color:#657581}article{border:1px solid #aab7c2;border-radius:3px;background:linear-gradient(#fff,#f3f6f8);box-shadow:0 3px 8px #2134461f;margin-bottom:32px;padding:24px}.page-heading{display:flex;justify-content:space-between;gap:24px;align-items:center;padding-bottom:20px;border-bottom:1px solid #cad3db;margin-bottom:24px}.eyebrow{font-size:12px;letter-spacing:.04em;color:#526271}.page-heading>a{flex-shrink:0;font-size:13px}.pair{display:grid;grid-template-columns:minmax(0,320px) minmax(0,1fr);gap:32px;align-items:start}figure{position:sticky;top:20px;margin:0}figure img{display:block;width:100%;height:auto;border:1px solid #b9c4cf;box-shadow:0 3px 8px #21344622}figcaption{font-size:12px;line-height:1.7;color:#526271;margin-top:12px}.refs{padding:12px 16px;margin:0 0 20px;background:#edf2f5;border-left:3px solid #5f7284;font-size:13px;overflow-wrap:anywhere}.not-run{color:#9a570c}.spec{min-width:0}.spec p{margin:0 0 14px}.spec li{margin-bottom:7px}.spec ul,.spec ol{padding-left:22px;margin:0 0 18px}.table-scroll{max-width:100%;overflow:auto;margin:16px 0 22px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #ccd5dc;padding:9px 11px;vertical-align:top;text-align:left}th{background:#e9eff4}.related{margin-top:24px}.related>h3{margin-bottom:4px}.hint,.source{font-size:13px;color:#617180}details{border:1px solid #c8d2da;margin:10px 0;background:#f6f8fa}summary{cursor:pointer;padding:12px 14px;font-size:14px}.shared-body{padding:4px 16px 8px}.tests{margin-top:24px}.test{padding:16px;border-top:1px solid #d1d9df}.test p{font-size:14px}.source{margin-top:18px!important}footer{padding:16px 24px 40px;text-align:center;font-size:13px;color:#617180}code{background:#e8edf1;padding:1px 4px;overflow-wrap:anywhere}@media(max-width:1000px){.index-links{grid-template-columns:repeat(3,minmax(0,1fr))}.pair{grid-template-columns:minmax(0,270px) minmax(0,1fr);gap:24px}}@media(max-width:760px){header{padding:24px 16px}h1{font-size:24px}main{padding:0 12px}.index{padding:16px}.index-links{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}article{padding:16px}.page-heading{align-items:flex-start;gap:12px}h2{font-size:20px}.pair{display:block}figure{position:static;max-width:330px;margin:0 auto 24px}.page-heading>a{font-size:12px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{body{background:white}header{background:white}.index,.page-heading>a,footer{display:none}main{max-width:none;padding:0}article{box-shadow:none;break-before:page}.pair{grid-template-columns:240px 1fr}figure{position:static}details{break-inside:avoid}}
</style></head>
<body><header><h1>计划打卡 · Android V1</h1><p>${map.screens.length}张设计截图与对应需求放在同一页；宽屏左图右文，手机按图文顺序阅读。</p><p><a href="../${docName}">完整需求文档</a> · <a href="../需求分析与待确认项.md">需求审查记录</a> · <a href="../UIUX-计划打卡-Android-v1.md">UI/UX规格</a> · <a href="../技术设计文档-计划打卡-Android-v1.md">技术设计与详细规格</a></p><p>v${escape(map.baseline.version)} ${map.baseline.status === 'confirmed' ? '已确认' : '修订复核'} · 32项功能需求 · 28组验收场景 · Pen${map.diskSave === 'saved' ? '已保存' : '待保存最新改动'}。截图为设计示例；应用验收尚未执行。</p></header>
<main><nav class="index" id="page-index" aria-label="按页面浏览"><h2>按页面浏览</h2><div class="index-links">${index}</div></nav>${cards.join('\n')}</main>
<footer>更新：2026-10-09 · 图文内容由当前需求正文生成 · 无需联网即可浏览</footer>
<script>
function revealHash(){const node=document.getElementById(location.hash.slice(1));if(!node)return;for(let parent=node;parent;parent=parent.parentElement){if(parent.tagName==='DETAILS')parent.open=true;}}
window.addEventListener('hashchange',revealHash);revealHash();
</script></body></html>`;
fs.writeFileSync(path.join(__dirname, 'preview.html'), html);
console.log(JSON.stringify({ pairedPages: map.screens.length, requirementsCovered: seen.size, acceptanceCovered: testsCovered.size, output: 'design/preview.html' }));
