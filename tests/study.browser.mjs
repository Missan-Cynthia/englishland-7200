// Isolated browser test: Firebase is replaced with local storage only in this test context.
import {createRequire} from 'node:module';
import {createServer} from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_PACKAGE||'C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve('.'),output=path.join(root,'output','study-qa');fs.mkdirSync(output,{recursive:true});
const mime={'.html':'text/html','.mjs':'text/javascript','.js':'text/javascript','.json':'application/json','.css':'text/css','.png':'image/png','.jpg':'image/jpeg'};
const server=createServer((req,res)=>{const url=new URL(req.url,'http://localhost');const file=path.resolve(root,'.'+decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname));if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}try{res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));}catch{res.writeHead(404).end();}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser;
try{
  browser=await chromium.launch({headless:true,channel:'msedge'});
  const context=await browser.newContext({viewport:{width:760,height:1000}});
  await context.route('**/js/firebase-config.js',route=>route.fulfill({contentType:'text/javascript',body:'export const firebaseConfig=null;'}));
  const page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
  const url=`http://127.0.0.1:${server.address().port}`;
  const state=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('english-land-mvp-v1:user:study-test')));
  await page.goto(url);await page.waitForFunction(()=>document.querySelector('#auth-note').textContent.length>0);
  await page.fill('#username','study-test');await page.fill('#password','test-only');await page.click('#login-button');
  await page.waitForSelector('#auth-gate.hidden',{state:'attached'});await page.click('#open-daily');await page.waitForSelector('#study-practice.active');
  let saved=await state();assert.equal(saved.study.daily.questions.length,8);
  let q=saved.study.daily.questions[0];let bad=q.choices.find(c=>c.id!==q.answerId);
  await page.locator(`#study-choices button[data-choice-id="${bad.id}"]`).click();
  await page.waitForFunction(()=>!!JSON.parse(localStorage.getItem('english-land-mvp-v1:user:study-test')).study.daily.answers[0]);
  await page.reload();await page.waitForSelector('#auth-gate.hidden',{state:'attached'});await page.click('#open-daily');
  await page.waitForFunction(()=>document.querySelector('#study-session-title').textContent.includes('2/8'));
  for(let i=1;i<8;i++){
    saved=await state();q=saved.study.daily.questions[i];bad=q.choices.find(c=>i===1?c.id===q.answerId:c.id!==q.answerId);
    if(q.kind==='reading')await page.screenshot({path:path.join(output,'daily-reading.png'),fullPage:true});
    await page.locator(`#study-choices button[data-choice-id="${bad.id}"]`).click();
    await page.waitForFunction(index=>!!JSON.parse(localStorage.getItem('english-land-mvp-v1:user:study-test')).study.daily.answers[index],i);
    if(i===1){
      assert.match(await page.locator('#study-feedback').innerText(),/答對了/);
      assert.equal(await page.locator('#study-feedback .study-option-note').count(),4);
      assert.equal(await page.locator('#study-feedback').evaluate(e=>getComputedStyle(e).color),'rgb(94, 63, 163)');
    }
    await page.click('#study-next');
  }
  await page.waitForSelector('#study-result.active');assert.match(await page.locator('#study-summary').innerText(),/8 題/);
  await page.click('#result-review');await page.waitForSelector('#review-book.active');
  saved=await state();assert.deepEqual(new Set(Object.values(saved.study.cards).map(c=>c.kind)),new Set(['word','phrase','reading','cloze']));
  assert.equal(Object.keys(saved.study.cards).length,6,'two cloze questions share one card; correct-only word is not added');
  await page.selectOption('#review-kind','cloze');assert.equal(await page.locator('#review-cards article').count(),1);
  await page.locator('#review-cards details summary').first().click();
  assert.ok(await page.locator('#review-cards').getByText('原文依據：',{exact:false}).count());
  await page.screenshot({path:path.join(output,'cloze-mistakes.png'),fullPage:true});
  await page.click('#start-review');await page.waitForSelector('#study-practice.active');
  assert.equal(await page.locator('#study-feedback').innerText(),'');
  await page.click('#study-back');await page.click('#open-daily');await page.waitForSelector('#study-result.active');
  const answersBefore=JSON.stringify((await state()).study.daily.answers);
  const walletBefore=(await state()).wallet.total;assert.ok(walletBefore>0);
  await page.reload();await page.waitForSelector('#auth-gate.hidden',{state:'attached'});await page.click('#open-daily');await page.waitForSelector('#study-result.active');
  assert.equal(JSON.stringify((await state()).study.daily.answers),answersBefore);
  assert.equal((await state()).wallet.total,walletBefore,'completed daily quiz cannot award twice');

  // Existing regular quiz entry points must feed the same book.
  await page.locator('#study-result [data-screen="home"]').click();
  await page.locator('#home [data-screen="foundation-home"]').click();await page.click('[data-library="basic"]');await page.click('#start-meaning-quiz');
  const basic=JSON.parse(fs.readFileSync('data/basic.json','utf8'));let prompt=await page.locator('#quiz-prompt').innerText();
  const correctWords=basic.filter(x=>x.meaning===prompt).map(x=>x.word);const choices=await page.locator('#choices button').allTextContents();
  await page.locator('#choices button').nth(choices.findIndex(x=>!correctWords.includes(x))).click();
  await page.locator('header .logo').click();await page.locator('#home [data-screen="advanced-home"]').click();await page.click('#open-phrases');await page.click('#start-phrase-zh');
  const phrases=JSON.parse(fs.readFileSync('data/phrases.json','utf8'));prompt=await page.locator('#quiz-prompt').innerText();
  const correctPhrases=phrases.filter(x=>x.meaningZh===prompt).map(x=>x.phrase);const pc=await page.locator('#choices button').allTextContents();
  await page.locator('#choices button').nth(pc.findIndex(x=>!correctPhrases.includes(x))).click();
  await page.locator('header .logo').click();await page.locator('#home [data-screen="advanced-home"]').click();await page.click('[data-content="articles"]');
  await page.locator('#content-items button').first().click();await page.locator('#detail-activity .inline-choices button').nth(1).click();
  await page.waitForFunction(()=>!!JSON.parse(localStorage.getItem('english-land-mvp-v1:user:study-test')).study.cards['articles:ar001']);
  assert.ok((await page.locator('#detail-activity').innerText()).includes('原文依據'));
  await page.locator('header .logo').click();await page.locator('#home [data-screen="advanced-home"]').click();await page.click('[data-content="cloze"]');
  await page.locator('#content-items button').first().click();await page.locator('#detail-activity .inline-choices button').nth(1).click();
  await page.waitForFunction(()=>!!JSON.parse(localStorage.getItem('english-land-mvp-v1:user:study-test')).study.cards['cloze:cz001']?.items.cz001q1);
  await page.locator('header .logo').click();await page.locator('#home [data-screen="mindmaps"]').click();await page.locator('#mindmap-grid .mindmap-cover').first().click();
  await page.locator('#mindmap-quiz .inline-choices button').nth(1).click();
  await page.waitForFunction(()=>!!JSON.parse(localStorage.getItem('english-land-mvp-v1:user:study-test')).study.cards['mindmaps:05']);
  assert.deepEqual(errors,[]);
  console.log('PASS browser daily 8 questions, reload/resume, four categories, grouped cloze, explanations, completed-day stability, regular word/phrase/article/mindmap capture');
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
