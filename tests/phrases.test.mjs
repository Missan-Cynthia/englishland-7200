import assert from 'node:assert/strict';
import fs from 'node:fs';
import {blankState,normalizeState,recordAnswer,rollBillReward,addReward} from '../js/core.mjs';
import {buildPhraseQuestion,makeCloze} from '../js/phrases.mjs';

const phrases=JSON.parse(fs.readFileSync(new URL('../data/phrases.json',import.meta.url)));
assert.equal(phrases.length,350);
assert.ok(phrases.every((x,i)=>/^docx-u\d{2}-\d{2}$/.test(x.id)));
assert.ok(phrases.every(x=>x.phrase&&x.meaningZh&&x.meaningEn===''&&x.lesson>=1&&x.lesson<=30));
assert.ok(phrases.every(x=>Object.keys(x).sort().join(',')==='examples,id,lesson,meaningEn,meaningZh,phrase'));
assert.ok(phrases.every(x=>Array.isArray(x.examples)&&x.examples.length>=0&&x.examples.length<=3));
const state=blankState();
for(const type of ['zhToPhrase','phraseToZh','cloze']){
  const question=buildPhraseQuestion(phrases,state.libraries.phrases,type,()=>0.01);
  assert.equal(question.choices.length,4);
  assert.ok(question.choices.some(x=>x.id===question.answer.id));
  if(type==='cloze')assert.ok(question.cloze.includes('_____'));
}
const target=phrases.find(x=>makeCloze(x));
recordAnswer(state,'phrases',target.id,true,1);
assert.equal(state.libraries.phrases.mastery[target.id],1);
assert.equal(state.libraries.basic.answers,0);
assert.equal(state.libraries.advanced.answers,0);
const reward=rollBillReward(1,()=>.99);addReward(state,reward);
assert.equal(state.wallet.total,1);
const restored=normalizeState(JSON.parse(JSON.stringify(state)));
assert.equal(restored.libraries.phrases.mastery[target.id],1);
assert.equal(restored.wallet.total,1);
console.log(`PASS phrases=${phrases.length} cloze=${phrases.filter(makeCloze).length} pending=${phrases.filter(x=>x.meaningZh==='待人工確認').length}`);

const units=JSON.parse(fs.readFileSync(new URL('../data/phrase-units.json',import.meta.url)));
assert.equal(units.length,30);
assert.equal(new Set(phrases.map(x=>x.id)).size,350);
assert.deepEqual(units.flatMap(x=>x.phraseIds),phrases.map(x=>x.id));
for(const unit of units){
  assert.ok(unit.passage.length>100);
  for(const item of phrases.filter(x=>x.lesson===unit.unit)){
    assert.ok(item.examples.every(example=>unit.passage.includes(example)));
  }
}
assert.equal(phrases[0].phrase,'to get up');
assert.equal(phrases.at(-1).phrase,'to look before one leaps');
