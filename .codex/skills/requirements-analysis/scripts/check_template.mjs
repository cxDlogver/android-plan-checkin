// Static HTML/JavaScript inspection only. No DOM, browser, or interaction execution.
import {readFileSync} from 'node:fs';
import {Script} from 'node:vm';
import assert from 'node:assert/strict';

const html=readFileSync(new URL('../assets/review.html',import.meta.url),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x=>x[1]);
assert.equal(scripts.length,1);
new Script(scripts[0],{filename:'review-template.js'});
const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]));
for(const match of scripts[0].matchAll(/\$\('([^']+)'\)/g))assert(ids.has(match[1]),`missing element ${match[1]}`);
assert(!/innerHTML|document\.write\s*\(|<script[^>]+src=|<link[^>]+href=|\bfetch\s*\(/i.test(html));
assert.equal(html.split('__PAYLOAD__').length-1,1);
assert.equal(html.split('__DATA_DIGEST__').length-1,1);
console.log('PASS: JS parses, referenced elements exist, offline read-only template; static checks only.');
