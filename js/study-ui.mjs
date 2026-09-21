import {kinds,dayKey,initializeStudy,listCards,pendingItems,reviewQueue,getDaily,answerDaily,recordStudyAnswer} from './study.mjs';

const $=id=>document.getElementById(id);
function add(parent,tag,text,className=''){const node=document.createElement(tag);node.textContent=text;node.className=className;parent.appendChild(node);return node;}
const escapeRegex=text=>text.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
export function explanation(parent,q,selectedId){
  for(const [index,c] of q.choices.entries()){
    const row=add(parent,'span',`${index+1}. ${c.text}${c.translation?'：'+c.translation:''}${c.id===q.answerId?' ✓ 正確答案':c.id===selectedId?'（你的選擇）':''}`,'study-option-note');
    if(c.id===q.answerId)row.classList.add('review-correct');else if(c.id===selectedId)row.classList.add('review-wrong');
    if(c.explanation)add(row,'span',c.explanation,'study-reason');
  }
  if(q.explanation)add(parent,'span',q.explanation,'study-explanation');
  if(q.evidence)add(parent,'span',`原文依據：${q.evidence}`,'study-evidence');
}

export function setupStudyUI({getState,getCatalog,getLibraries,save,reward,showScreen,speak}){
  let session=null,busy=false;
  const filters=()=>({kind:$('review-kind').value,status:$('review-status').value,query:$('review-search').value.trim()});
  function renderBook(){
    const state=getState(),cards=listCards(state,filters()),box=$('review-cards');box.replaceChildren();
    $('review-count').textContent=`${cards.length} 張卡`;$('start-review').disabled=!cards.length;
    if(!cards.length)add(box,'p','這個分類目前沒有錯題。各區新答錯的題目會自動收錄。','panel review-card');
    for(const card of cards){
      const article=add(box,'article','','panel review-card');add(article,'small',kinds[card.kind]);add(article,'h2',card.title);
      const items=Object.values(card.items),pending=pendingItems(card);
      add(article,'p',`累計答錯 ${card.wrongCount} 次・${pending.length?`${pending.length} 項待複習`:'已熟練'}・最近答錯 ${new Date(card.lastWrongAt).toLocaleDateString('zh-TW')}`,pending.length?'review-wrong':'review-correct');
      for(const item of items){
        add(article,'p',`${item.question.subtitle}・跨日答對 ${item.dates.length}/3 次・${item.dates.length>=3?'已熟練':item.due<=dayKey()?'今天可複習':`建議 ${item.due} 複習`}`);
        const details=add(article,'details','');add(details,'summary',items.length>1?`看解析：${item.question.prompt}`:'看解析（不計入熟練度）');
        if(item.question.passage)add(details,'p',item.question.passage,'study-passage');
        for(const error of Object.values(item.errors)){
          const section=add(details,'div','','review-error');add(section,'p',`${error.question.prompt}（此題型答錯 ${error.count} 次）`);
          explanation(section,error.question,error.selectedId);
        }
      }
      const button=add(article,'button','複習這張卡','ghost');button.onclick=()=>{
        const keys=new Set(items.map(i=>`${card.key}/${i.question.itemKey}`));
        const all=reviewQueue(state,getCatalog(),getLibraries(),{...filters(),cardKey:card.key});
        launch(all.filter(q=>keys.has(`${q.cardKey}/${q.itemKey}`)),'review');
      };
    }
  }
  function openBook(){session=null;renderBook();showScreen('review-book');}
  function launch(questions,mode){if(!questions.length)return;session={questions,mode,index:0,correct:0,answered:false};renderPractice();}
  async function openDaily(){
    if(busy)return;busy=true;
    try{
      const daily=getDaily(getState(),getCatalog(),getLibraries());const saved=await save();
      session={questions:daily.questions,mode:'daily',index:daily.questions.findIndex((_,i)=>!daily.answers[i]),answered:false};
      if(session.index<0)finish();else renderPractice();
      if(!saved)$('study-feedback').textContent='同步失敗，題目暫存在本頁；請保持頁面開啟並確認網路。';
    }finally{busy=false;}
  }
  function renderPractice(){
    const q=session.questions[session.index];session.answered=false;
    $('study-session-title').textContent=`${session.mode==='daily'?'今日考題':'錯題複習'} ${session.index+1}/${session.questions.length}・${kinds[q.kind]}`;
    $('study-meta').textContent=`${q.subtitle}${q.kind==='reading'||q.kind==='cloze'?'・'+q.title:''}`;
    $('study-prompt').textContent=q.prompt;
    let passage=q.passage;
    if(q.kind==='cloze'){
      const answer=q.choices.find(c=>c.id===q.answerId).text;
      passage=passage.replace(new RegExp(`\\b${escapeRegex(answer)}\\b`,'gi'),'_____');
    }
    $('study-passage').textContent=passage;$('study-passage').classList.toggle('hidden',!passage);
    $('study-audio').classList.toggle('hidden',!q.audio);$('study-audio').onclick=()=>speak(q.audio);
    $('study-feedback').replaceChildren();$('study-feedback').className='feedback';
    $('study-next').classList.add('hidden');$('study-choices').replaceChildren();
    for(const c of q.choices){const b=add($('study-choices'),'button',q.displayTranslation?c.translation:c.text,'choice');b.dataset.choiceId=c.id;b.onclick=()=>submit(c.id);}
    showScreen('study-practice');
  }
  async function submit(selectedId){
    if(!session||session.answered||busy)return;
    if(session.mode==='daily'&&initializeStudy(getState()).daily.day!==dayKey()){
      $('study-feedback').textContent='已跨日，請返回首頁重新開啟今日考題。';return;
    }
    session.answered=true;busy=true;
    try{
      const q=session.questions[session.index];
      const result=session.mode==='daily'?answerDaily(getState(),session.index,selectedId):{correct:recordStudyAnswer(getState(),q,selectedId,{practice:true})};
      if(!result)return;
      const correct=result.correct;if(correct)session.correct=(session.correct||0)+1;
      const gain=reward(q.module,q.rewardId,correct);
      $('study-choices').querySelectorAll('button').forEach(b=>{b.disabled=true;b.classList.toggle('correct',b.dataset.choiceId===q.answerId);b.classList.toggle('wrong',!correct&&b.dataset.choiceId===selectedId);});
      const feedback=$('study-feedback');feedback.textContent=correct?`答對了！獲得 $${gain.total}`:'答錯了，已收錄至錯題本。';feedback.className=`feedback ${correct?'good':'bad'}`;
      explanation(feedback,q,selectedId);
      add(feedback,'span','熟練度只計不同日期的複習；同一天重做不會重複累計。','study-reason');
      $('study-next').textContent=session.index===session.questions.length-1?'查看結果':'下一題';$('study-next').classList.remove('hidden');
      if(!await save())add(feedback,'span','同步失敗，請保持頁面開啟並確認網路，再繼續作答。','review-wrong');
    }finally{busy=false;}
  }
  function finish(){
    const box=$('study-summary');box.replaceChildren();
    const mode=session.mode;
    add(box,'h2',mode==='daily'?'今日考題已完成':'本回合複習完成');
    if(mode==='daily'){
      const daily=initializeStudy(getState()).daily;
      add(box,'p',`${daily.day}・${daily.questions.length} 題・答對 ${Object.values(daily.answers).filter(a=>a.correct).length} 題`);
      for(const [kind,label] of Object.entries(kinds)){
        const indices=daily.questions.map((q,i)=>q.kind===kind?i:-1).filter(i=>i>=0),correct=indices.filter(i=>daily.answers[i]?.correct).length;
        add(box,'p',`${label}：${correct}/${indices.length} 題・${indices.length?Math.round(correct/indices.length*100):0}%`);
      }
      const wrong=daily.questions.filter((q,i)=>!daily.answers[i]?.correct);
      if(wrong.length)add(box,'p',`待複習：${[...new Set(wrong.map(q=>q.title))].join('、')}`);
      add(box,'p','今日題目與成績已保留，明天會依各類作答表現安排新一回。');
    }else add(box,'p',`${session.questions.length} 題・答對 ${session.correct} 題。到錯題本查看各項跨日複習進度。`);
    session=null;showScreen('study-result');
  }
  $('study-next').onclick=()=>{
    if(busy||!session?.answered)return;session.index++;
    if(session.index>=session.questions.length)finish();else renderPractice();
  };
  $('study-back').onclick=()=>{if(!busy){session=null;showScreen('home');}};
  $('open-review').onclick=openBook;$('open-phrase-review').onclick=openBook;$('result-review').onclick=openBook;
  $('open-daily').onclick=openDaily;
  for(const id of ['review-kind','review-status'])$(id).onchange=renderBook;
  $('review-search').oninput=renderBook;
  $('start-review').onclick=()=>launch(reviewQueue(getState(),getCatalog(),getLibraries(),filters()),'review');
  return {openBook,openDaily};
}
