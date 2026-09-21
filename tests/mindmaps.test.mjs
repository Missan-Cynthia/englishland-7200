import assert from 'node:assert/strict';
import fs from 'node:fs';

const root=new URL('../',import.meta.url);
const reviewed=JSON.parse(fs.readFileSync(new URL('data/mindmaps.json',root),'utf8'));
const imageNames=fs.readdirSync(new URL('思維導圖/',root)).filter(name=>/\.jpg$/i.test(name));
assert.equal(imageNames.length,94);
assert.equal(new Set(imageNames).size,94);
assert.ok(reviewed.length>0);
for(const item of reviewed){
  assert.ok(item.id&&item.title&&item.image);
  assert.ok(['reviewed','needsReview'].includes(item.status));
  assert.ok(fs.existsSync(new URL(item.image,root)));
  assert.ok(item.words.length>=4);
  assert.ok(item.article?.text&&item.article?.translation);
  assert.ok(item.questions.length>=2);
  for(const question of item.questions){
    assert.ok(question.choices.includes(question.answer));
  }
}
console.log(`PASS mindmaps images=${imageNames.length} enriched=${reviewed.length}`);
