import assert from 'node:assert/strict';
import fs from 'node:fs';
import {blankState,normalizeState,LIBRARY_KEYS} from '../js/core.mjs';

const read=name=>JSON.parse(fs.readFileSync(new URL(`../data/${name}`,import.meta.url)));
const basic=read('basic.json'),basicReadings=read('basic-readings.json'),articles=read('advanced-articles.json'),cloze=read('cloze-sets.json'),readingTests=read('reading-tests.json'),spacing=read('basic-word-spacing-review.json');
assert.equal(basic.length,1200);
assert.equal(spacing.auditedCount,1200);
assert.equal(spacing.fixedCount,16);
assert.equal(spacing.manualReview.length,1);
assert.ok(spacing.fixed.every(f=>basic.some(item=>item.id===f.id&&item.word===f.to)));
assert.ok(basicReadings.every(x=>x.title&&x.topic&&x.level&&x.passage&&Array.isArray(x.targetWords)&&Array.isArray(x.coveredWords)));
assert.ok(articles.every(x=>x.title&&x.topic&&x.level&&x.passage&&Array.isArray(x.targetWords)&&Array.isArray(x.targetPhrases)&&Array.isArray(x.coveredWords)));
for(const set of [...cloze,...readingTests]){assert.ok(set.questions.length>1);assert.ok(set.questions.every(q=>q.choices.includes(q.answer)));}
const state=blankState();
assert.deepEqual(Object.keys(state.libraries),LIBRARY_KEYS);
const old=normalizeState({coins:5,libraries:{basic:{level:4,mastery:{b0001:2},answers:3}}});
assert.equal(old.libraries.basic.level,4);
assert.equal(old.libraries.cloze.level,1);
assert.equal(old.wallet.total,5);
console.log(`PASS phase1 basicReadings=${basicReadings.length} articles=${articles.length} clozeSets=${cloze.length} readingTests=${readingTests.length} spacingFixed=${spacing.fixedCount}`);
