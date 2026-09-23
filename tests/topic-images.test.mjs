import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html=fs.readFileSync(new URL('../index.html',import.meta.url),'utf8');
const raw=html.match(/<script id="topic-image-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const records=JSON.parse(raw);
assert.equal(records.length,94);
assert.equal(new Set(records.map(x=>x.id)).size,94);
for(const item of records){
 assert.ok(item.category&&item.subcategory&&item.title);
 assert.ok(item.height>item.width);
 const bytes=Buffer.from(item.image.split(',')[1],'base64');
 assert.equal(bytes.toString('ascii',0,4),'RIFF');
 assert.equal(bytes.toString('ascii',8,12),'WEBP');
}
assert.ok(!html.includes('主題思維導圖'));
assert.equal(records.find(x=>x.id==='66').subcategory,'動物');
assert.equal(records.find(x=>x.id==='58').category,'衣');
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.handlers={};this.value='';this.checked=false;}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=nodes;}
 addEventListener(name,fn){this.handlers[name]=fn;}
 setAttribute(name,value){this[name]=value;}
}
const nodes=Object.fromEntries(['mindmap-grid','mindmap-search','mindmap-favorites-only','topic-image-data'].map(x=>[x,new Element('div')]));
nodes['topic-image-data'].textContent=raw;
let scroll;
const context={document:{getElementById:id=>nodes[id],createElement:tag=>new Element(tag),createTextNode:text=>({textContent:text})},window:{scrollY:430,scrollTo:x=>scroll=x.top},requestAnimationFrame:fn=>fn()};
vm.createContext(context);
const inline=html.match(/<script>\s*(\(\(\)=>\{\s*const records=JSON.parse[\s\S]*?)<\/script>/)[1];
vm.runInContext(inline,context);
const api=context.window.topicImages;
let opened;
api.render(records,id=>opened=id);
const host=nodes['mindmap-grid'];
assert.deepEqual(host.children[0].children.map(x=>x.textContent),['食','衣','住','行','育','樂']);
assert.equal(host.children[2].children[0].children[0].textContent,'水果');
assert.equal(host.children[2].children[1].children[0].textContent,'蔬菜');
assert.equal(host.children[2].children.length,4,'All four food subcategories occupy one horizontal row');
assert.ok(html.includes('flex-wrap:nowrap'));assert.ok(html.includes('background:#FF6666'));
const tag=host.children[2].children[0].children[1].children[0];tag.onclick();assert.equal(opened,'09');
api.render(records,id=>opened=id);assert.equal(scroll,430);
host.children[0].children[1].onclick();assert.ok(host.children[1].textContent.startsWith('衣：'));
assert.equal(host.children[2].children[0].children[1].children.length,1);
host.children[0].children[3].onclick();assert.equal(host.children[2].children[0].children[0].textContent,'購物與廚房');assert.equal(host.children[2].children[0].children[1].children.length,3);
nodes['mindmap-search'].value='鯨魚';api.render(records.filter(x=>x.id==='66'),()=>{});
assert.ok(host.children[1].textContent.startsWith('育：'));assert.equal(host.children[2].children.length,1);
api.render([],()=>{});assert.equal(host.children.at(-1).textContent,'這個分類沒有符合搜尋或收藏條件的主題。');
console.log('PASS 94 WebP images; six horizontal categories, single-row subcategories, vertical labels, switching, navigation, search and return position');
