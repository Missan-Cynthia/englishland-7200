from pathlib import Path
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import json,base64,re,shutil
from PIL import Image

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'output/手機直式版'
data=json.loads((SOURCE/'資料.json').read_text(encoding='utf-8'))
groups={
('食','水果'):'西瓜 蘋果 香蕉 葡萄 櫻桃 芒果 藍莓 草莓 水蜜桃 哈密瓜 檸檬 荔枝 柳橙 綠葡萄 奇異果 覆盆子 火龍果 山竹 椰子 榴槤 木瓜 石榴 桃子 梨子 柿子 橘子'.split(),
('食','蔬菜與菇類'):'番茄 小黃瓜 青花菜 大蒜 辣椒 玉米 南瓜 紅蘿蔔 茄子 蘑菇 馬鈴薯 地瓜 大白菜 生薑 洋蔥 白蘿蔔'.split(),
('食','穀物與食材'):'花生 蜂蜜 稻米與米飯 甘蔗'.split(),
('食','料理與用餐'):'食物口感 包粽子 沙拉 披薩 火鍋 糖葫蘆 年夜飯 早餐 包餃子 蛋炒飯 漢堡'.split(),
('行','購物與廚房'):'超市購物 廚房與廚具 廚具'.split(),
('衣','衣物清潔'):['洗衣服'],
('住','居家生活'):'做家事 浴室與洗澡 春節大掃除'.split(),
('育','動物'):'螃蟹 鯨魚 老虎 蝦子'.split(),
('育','植物'):'向日葵 荷花'.split(),
('育','身體與成長'):['量身高'],
('樂','戶外活動'):['露營野餐'],
('樂','節慶文化'):'中秋節與月餅 聖誕節 冬至 春節 清明節'.split(),
}
lookup={title:pair for pair,titles in groups.items() for title in titles}
webpdir=ROOT/'output/手機直式WEBP';webpdir.mkdir(exist_ok=True)
def convert(d):
    title=d['title'].removesuffix('英語心智圖')
    assert title in lookup,title
    im=Image.open(SOURCE/'長頁PNG'/f"{d['sequence']:03}.png").convert('RGB')
    buf=BytesIO();im.save(buf,format='WEBP',quality=88,method=6)
    raw=buf.getvalue();(webpdir/f"{d['number']}.webp").write_bytes(raw)
    category,subcategory=lookup[title]
    return dict(id=d['number'],title=title,category=category,subcategory=subcategory,width=im.width,height=im.height,image='data:image/webp;base64,'+base64.b64encode(raw).decode('ascii'))
with ThreadPoolExecutor(max_workers=4) as pool: records=list(pool.map(convert,data))
page=ROOT/'index.html';original=page.read_text(encoding='utf-8')
backup=ROOT/'output/主題圖更新前';backup.mkdir(exist_ok=True)
for name in ['index.html','js/app.mjs']:
    target=backup/Path(name).name
    if not target.exists():shutil.copy2(ROOT/name,target)
original=re.sub(r'<!-- TOPIC_IMAGES_START -->.*?<!-- TOPIC_IMAGES_END -->\s*','',original,flags=re.S)
original=original.replace('主題思維導圖','主題圖').replace('放大的思維導圖','放大的主題圖')
original=original.replace('先看圖建立情境，再用劍橋繁體中文釋義學單字。可搜尋編號、主題或單字。','先選上方食衣住行育樂分類，再點下方主題標籤查看直式圖片。可搜尋頁碼、分類、主題或英文單字。')
original=original.replace('從圖片認識情境單字，再讀短文、聽發音與做小測驗。','展開生活分類，點選主題標籤，閱讀手機與平板適用的直式圖。')
original=original.replace('← 返回圖庫','← 返回主題樹').replace('搜尋主題或英文單字','搜尋分類、主題或英文單字')
original=original.replace('js/app.mjs?v=20260921-unified-v1','js/app.mjs?v=20260923-topic-tree')
css='''
.mindmap-grid{display:block}.topic-root{display:inline-block;padding:10px 20px;border-radius:14px;background:#193f52;color:white;font-weight:700;font-size:20px}.topic-branches{border-left:2px solid #b8cec4;margin:0 0 0 18px;padding:12px 0 8px 18px}.topic-branch{position:relative;margin:10px 0}.topic-branch:before{content:"";position:absolute;width:18px;height:2px;left:-18px;top:22px;background:#b8cec4}.topic-branch>summary{cursor:pointer;padding:12px 14px;border-radius:12px;background:#eaf3ee;font-weight:700;overflow-wrap:anywhere}.topic-branch>summary:focus-visible,.topic-tag:focus-visible{outline:3px solid #6855a7;outline-offset:3px}.topic-branch>summary small{font-weight:400;margin-left:8px;color:#52675c}.topic-leaves{display:flex;flex-wrap:wrap;gap:10px;padding:16px 0 12px 12px;border-left:2px solid #ceddd6;margin-left:18px}.topic-tag{max-width:100%;white-space:normal;text-align:left;border-radius:99px;padding:10px 14px;background:white;color:#193f52;border:1px solid #bad0c4;font-size:16px;line-height:1.5}.topic-tag small{font-size:12px;color:#64796b;margin-left:6px}.topic-tag:hover{background:#e5f3e9}.mindmap-study{max-width:900px;padding:20px}.mindmap-image-button{width:100%;max-width:780px;background:#f2f7f7}.mindmap-image-button img{width:100%;height:auto;max-width:100%;object-fit:contain}.mindmap-lightbox img{width:100%;max-width:780px;height:auto;object-fit:contain}.mindmap-lightbox{padding:60px 12px 20px}.mindmap-heading{min-width:0}.mindmap-heading h1{overflow-wrap:anywhere}@media(max-width:600px){#mindmap-detail{padding-left:0;padding-right:0;margin-left:-16px;margin-right:-16px}.mindmap-study{padding:6px;border-radius:12px}.mindmap-heading,.mindmap-detail-nav{padding:8px}.mindmap-heading h1{font-size:27px}.topic-branches{margin-left:8px;padding-left:14px}.topic-branch:before{width:14px;left:-14px}.topic-leaves{margin-left:8px;padding-left:10px}.topic-tag{font-size:16px}.mindmap-grid{display:block}.mindmap-lightbox{padding:60px 0 16px}}
.topic-categories{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;width:100%;margin:0 0 18px}.topic-category{padding:12px 4px;background:#eaf3ee;color:#193f52;border:1px solid #c8dcd1;border-radius:12px;font-size:21px;min-width:0}.topic-category.selected{background:#193f52;color:white;border-color:#193f52}.topic-category:focus-visible,.topic-tag:focus-visible{outline:3px solid #8063ba;outline-offset:3px}.topic-category-summary{line-height:1.7;color:#536d60;margin:0 0 24px;overflow-wrap:anywhere}.topic-columns{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px 20px;align-items:start}.topic-column{min-width:0}.topic-column h2{margin:0;text-align:center;font-size:20px;padding:12px 8px;background:#eaf3ee;color:#193f52;border-radius:12px;border:1px solid #c8dcd1}.topic-vertical-labels{display:flex;flex-direction:column;align-items:stretch;gap:10px;padding:16px 8px 0;border-top:2px solid #cadcd2;margin:12px 0 0;position:relative}.topic-vertical-labels:before{content:'';position:absolute;height:12px;width:2px;background:#cadcd2;top:-14px;left:50%}.topic-vertical-labels .topic-tag{display:block;width:100%;text-align:center;border-radius:12px;white-space:normal;overflow-wrap:anywhere;min-height:48px}.topic-tag small{display:block;margin:2px 0 0;font-weight:400}@media(max-width:600px){.topic-categories{gap:5px}.topic-category{font-size:19px;padding:11px 2px}.topic-columns{gap:24px 12px}.topic-column h2{font-size:18px}.topic-vertical-labels{padding-left:0;padding-right:0}.topic-vertical-labels .topic-tag{padding:10px 6px;font-size:16px}}

/* Topic categories: horizontal parents and subcategories, vertical leaves. */
.topic-columns{display:flex;flex-direction:row;flex-wrap:nowrap;gap:12px;align-items:flex-start;overflow-x:auto;padding-bottom:14px;-webkit-overflow-scrolling:touch}
.topic-column{flex:1 0 145px;min-width:145px}
.topic-categories .topic-category{background:#fff1f1;color:#853333;border-color:#ffb3b3}
.topic-categories .topic-category.selected{background:#FF6666;color:#352020;border-color:#FF6666}
.topic-column h2{background:#FF6666;color:#352020;border-color:#FF6666}
.topic-vertical-labels{border-color:#ffb3b3}.topic-vertical-labels:before{background:#ffb3b3}
.topic-vertical-labels .topic-tag{background:#fffafa;color:#543333;border-color:#ffb3b3}
.topic-vertical-labels .topic-tag:hover{background:#ffe1e1}
.topic-tag small,.topic-category-summary{color:#805757}
.topic-category:focus-visible,.topic-tag:focus-visible{outline-color:#c43f3f}
.library-grid .mindmap-library{background:#fff1f1}.mindmap-library>span,.mindmap-library button{background:#FF6666;color:#352020}
@media(max-width:600px){.topic-columns{gap:10px}.topic-column{flex-basis:135px;min-width:135px}}

'''
js='''
(()=>{
const records=JSON.parse(document.getElementById('topic-image-data').textContent);
let selected='食',galleryScroll=0,returning=false,lastFilter='';
const order=['食','衣','住','行','育','樂'];
const subOrder=['水果','蔬菜與菇類','穀物與食材','料理與用餐','購物與廚房','衣物清潔','居家生活','動物','植物','身體與成長','戶外活動','節慶文化'];
const labels={'蔬菜與菇類':'蔬菜','穀物與食材':'穀物','料理與用餐':'料理'};
function render(items,onOpen){
 const host=document.getElementById('mindmap-grid');host.replaceChildren();
 const filter=document.getElementById('mindmap-search').value.trim()+'|'+document.getElementById('mindmap-favorites-only').checked;
 if(filter!==lastFilter&&items.length&&!items.some(x=>x.category===selected))selected=items[0].category;
 lastFilter=filter;
 const nav=document.createElement('div');nav.className='topic-categories';nav.setAttribute('role','group');nav.setAttribute('aria-label','主題六大分類');host.append(nav);
 for(const category of order){const button=document.createElement('button');button.type='button';button.className='topic-category'+(category===selected?' selected':'');button.textContent=category;button.setAttribute('aria-pressed',String(category===selected));button.onclick=()=>{selected=category;render(items,onOpen);};nav.append(button);}
 const group=items.filter(x=>x.category===selected);const subs=subOrder.filter(sub=>group.some(x=>x.subcategory===sub));
 const summary=document.createElement('p');summary.className='topic-category-summary';summary.textContent=selected+'：'+(subs.map(s=>labels[s]||s).join('、')||'目前沒有符合的主題');host.append(summary);
 const columns=document.createElement('div');columns.className='topic-columns';host.append(columns);
 for(const sub of subs){const section=document.createElement('section');section.className='topic-column';const heading=document.createElement('h2');heading.textContent=labels[sub]||sub;section.append(heading);const leaves=document.createElement('div');leaves.className='topic-vertical-labels';section.append(leaves);columns.append(section);
 for(const item of group.filter(x=>x.subcategory===sub)){const tag=document.createElement('button');tag.type='button';tag.className='topic-tag';tag.append(document.createTextNode(item.title));const number=document.createElement('small');number.textContent='第 '+Number(item.id)+' 頁';tag.append(number);tag.setAttribute('aria-label',item.title+'，第 '+Number(item.id)+' 頁，查看直式圖片');tag.onclick=()=>{galleryScroll=window.scrollY;returning=true;onOpen(item.id);};leaves.append(tag);}}
 if(!group.length){const empty=document.createElement('p');empty.className='panel empty-result';empty.textContent=records.some(x=>x.category===selected)?'這個分類沒有符合搜尋或收藏條件的主題。':'這個分類尚未收錄主題圖。';host.append(empty);}
 if(returning){requestAnimationFrame(()=>window.scrollTo({top:galleryScroll,behavior:'instant'}));returning=false;}
}
window.topicImages={records,render};
})();
'''
block='<!-- TOPIC_IMAGES_START -->\n<style>'+css+'</style>\n<script id="topic-image-data" type="application/json">'+json.dumps(records,ensure_ascii=False,separators=(',',':'))+'</script>\n<script>'+js+'</script>\n<!-- TOPIC_IMAGES_END -->\n'
page.write_text(original.replace('</body>',block+'</body>'),encoding='utf-8')
app=ROOT/'js/app.mjs';code=app.read_text(encoding='utf-8')
old="mindmaps=mindmapIds.map(id=>reviewed.get(id)||{id,title:`主題 ${Number(id)}`,image:`思維導圖/${id}.jpg`,status:'pending',words:[],questions:[]});"
new="mindmaps=window.topicImages.records.map(topic=>({...{status:'pending',words:[],questions:[]},...reviewed.get(topic.id),...topic}));"
assert old in code or new in code
code=code.replace(old,new)
start=code.index('function renderMindmapGallery()');end=code.index('\nfunction renderMindmapDetail()',start)
code=code[:start]+'''function renderMindmapGallery(){const query=$('mindmap-search').value.trim().toLowerCase(),favoritesOnly=$('mindmap-favorites-only').checked;const filtered=mindmaps.filter(item=>(!favoritesOnly||state.mindMaps.favorites.includes(item.id))&&(!query||`${item.id} ${item.title} ${item.category} ${item.subcategory} ${(item.words||[]).map(x=>x.word).join(' ')}`.toLowerCase().includes(query)));$('mindmap-progress').textContent=`已讀 ${state.mindMaps.read.length} / ${mindmaps.length}`;window.topicImages.render(filtered,openMindmap);}'''+code[end:]
code=code.replace('${item.title}思維導圖','${item.title}主題圖')
code=code.replace("$('mindmap-image').src=item.image;","$('mindmap-image').src=item.image;$('mindmap-image').width=item.width;$('mindmap-image').height=item.height;")
code=code.replace('不採用圖片中的簡體翻譯。','圖片沿用原版繁體中文。').replace('目前可先閱讀及收藏原圖；在查核完成前不顯示原圖簡體翻譯，也不產生未驗證題目。','可先閱讀及收藏直式主題圖；重點單字、短文與測驗將於校對完成後提供。')
app.write_text(code,encoding='utf-8')
print(json.dumps({'images':len(records),'html_bytes':page.stat().st_size,'webp_bytes':sum(f.stat().st_size for f in webpdir.glob('*.webp')),'categories':{c:sum(r['category']==c for r in records) for c in ['食','衣','住','行','育','樂']}},ensure_ascii=True))
