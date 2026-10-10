const fs = require('node:fs');
const [file, start = '1', count = '200'] = process.argv.slice(2);
if (!file) throw new Error('Usage: node scripts/read-context.cjs file [firstLine] [lineCount]');
const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
console.log(lines.slice(Number(start) - 1, Number(start) - 1 + Number(count)).map((line, i) => `${Number(start) + i}: ${line}`).join('\n'));
