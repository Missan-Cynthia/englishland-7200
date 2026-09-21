import {buildPhraseQuestion,makeCloze} from './phrases.mjs';

export const kinds={word:'單字',phrase:'片語',reading:'文章',cloze:'克漏字'};
export const dayKey=(date=new Date())=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
const copy=value=>JSON.parse(JSON.stringify(value));
const canonical=value=>value.trim().toLowerCase();
const nextDay=(day,days)=>{const date=new Date(`${day}T12:00:00`);date.setDate(date.getDate()+days);return dayKey(date);};
export function shuffle(items,random=Math.random){const out=[...items];for(let i=out.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[out[i],out[j]]=[out[j],out[i]];}return out;}

export function lexicalQuestion(q,module){
  const phrase=module==='phrases',answer=q.answer,title=phrase?answer.phrase:answer.word;
  return {kind:phrase?'phrase':'word',module,cardKey:`${phrase?'phrase':'word'}:${canonical(title)}`,itemKey:'lexical',
    rewardId:answer.id,title,type:q.type,level:phrase?(q.type==='cloze'?2:1):(module==='basic'?1:2),
    subtitle:phrase?`Unit ${answer.lesson}`:module==='basic'?'基礎單字':'進階單字',
    prompt:q.type==='audio'?'請播放發音，選出正確單字':q.type==='cloze'?q.cloze:q.type==='phraseToZh'?title:(answer.meaningZh||answer.meaning),
    audio:q.type==='audio'?title:'',passage:'',answerId:answer.id,
    choices:q.choices.map(x=>({id:x.id,text:phrase?x.phrase:x.word,translation:x.meaningZh||(!x.meaningPending&&x.meaning)||'中文釋義尚未提供',explanation:''})),
    displayTranslation:q.type==='phraseToZh',explanation:'',evidence:''};
}

export function passageQuestion(item,q,module,index=0){
  return {kind:module==='cloze'?'cloze':'reading',module,cardKey:`${module}:${item.id}`,itemKey:q.id||`${item.id}-${index}`,
    rewardId:q.id||`${item.id}-${index}`,title:item.title,type:q.type||'reading',level:item.level||1,
    subtitle:item.topic||'閱讀理解',prompt:q.prompt,passage:item.passage||item.article?.text||'',audio:'',
    answerId:String(q.choices.indexOf(q.answer)),choices:q.choices.map((text,i)=>({id:String(i),text,translation:q.choiceTranslations?.[i]||'',explanation:q.choiceExplanations?.[i]||''})),
    explanation:q.explanation||'',evidence:q.evidence||'',displayTranslation:false};
}

export function initializeStudy(state){
  state.study ||= {version:1,cards:{},seen:{},performance:{},daily:null};
  const study=state.study;
  study.cards||={};study.seen||={};study.performance||={};
  if(!study.migratedPhrases){
    for(const old of Object.values(state.phraseMistakes||{})){
      for(const error of Object.values(old.errors||{})){
        if(!error.question?.answer)continue;
        const q=lexicalQuestion(error.question,'phrases');
        const card=study.cards[q.cardKey]||(study.cards[q.cardKey]={key:q.cardKey,kind:q.kind,title:q.title,wrongCount:0,lastWrongAt:0,items:{}});
        const item=card.items.lexical||(card.items.lexical={question:q,errors:{},wrongCount:0,dates:[],lastAttemptDay:'',due:dayKey(),reviewCount:0});
        item.errors[q.type]={question:q,selectedId:error.selectedId,at:error.at||old.lastWrongAt,count:error.count||1};
        item.wrongCount+=error.count||1;card.wrongCount+=error.count||1;card.lastWrongAt=Math.max(card.lastWrongAt,error.at||old.lastWrongAt||0);
      }
    }
    study.migratedPhrases=true;
  }
  return study;
}

export function recordStudyAnswer(state,q,selectedId,{practice=false,now=new Date()}={}){
  const study=initializeStudy(state),day=dayKey(now),correct=selectedId===q.answerId;
  study.performance[q.kind]=[...(study.performance[q.kind]||[]),correct].slice(-30);
  study.seen[`${q.cardKey}/${q.itemKey}`]={day,correct};
  let card=study.cards[q.cardKey],item=card?.items[q.itemKey];
  if(!correct){
    card ||= study.cards[q.cardKey]={key:q.cardKey,kind:q.kind,title:q.title,wrongCount:0,lastWrongAt:0,items:{}};
    item ||= card.items[q.itemKey]={question:copy(q),errors:{},wrongCount:0,dates:[],lastAttemptDay:'',due:day,reviewCount:0};
    const prior=item.errors[q.type];
    item.errors[q.type]={question:copy(q),selectedId,at:now.getTime(),count:(prior?.count||0)+1};
    item.question=copy(q);item.wrongCount++;item.dates=[];item.due=nextDay(day,1);item.lastAttemptDay=day;
    card.wrongCount++;card.lastWrongAt=now.getTime();
  }else if(item&&practice&&item.lastAttemptDay!==day){
    item.lastAttemptDay=day;item.reviewCount++;item.dates=[...new Set([...item.dates,day])].slice(-3);
    item.due=nextDay(day,item.dates.length===1?1:item.dates.length===2?3:7);
  }
  return correct;
}

export const pendingItems=card=>Object.values(card.items).filter(x=>x.dates.length<3);
export function listCards(state,{kind='',status='pending',query='',cardKey=''}={}){
  return Object.values(initializeStudy(state).cards).filter(c=>(!kind||c.kind===kind)&&
    (status==='mastered'?!pendingItems(c).length:pendingItems(c).length>0)&&
    (!cardKey||c.key===cardKey)&&(!query||`${c.title} ${Object.values(c.items).map(i=>i.question.subtitle).join(' ')}`.toLowerCase().includes(query.toLowerCase())))
    .sort(status==='frequent'?(a,b)=>b.wrongCount-a.wrongCount:
      (a,b)=>Math.min(...Object.values(a.items).map(i=>Number(i.due.replaceAll('-',''))))-Math.min(...Object.values(b.items).map(i=>Number(i.due.replaceAll('-','')))));
}

export function catalog(libraries,content){
  const out=[];
  for(const module of ['basic','advanced','phrases'])for(const item of libraries[module]||[]){
    const phrase=module==='phrases';out.push({kind:phrase?'phrase':'word',module,item,level:module==='advanced'?2:1,cardKey:`${phrase?'phrase':'word'}:${canonical(phrase?item.phrase:item.word)}`,itemKey:'lexical'});
  }
  for(const module of ['basicReading','articles','readingTest','cloze','mindmaps'])for(const item of content[module]||[]){
    if(module==='mindmaps'&&item.status!=='reviewed')continue;
    for(const [index,q] of (item.questions||[]).entries())out.push({kind:module==='cloze'?'cloze':'reading',module,item,q,index,level:item.level||1,cardKey:`${module}:${item.id}`,itemKey:q.id||`${item.id}-${index}`});
  }
  return out;
}

export function materialize(entry,libraries,{random=Math.random,challenging=false}={}){
  if(entry.q){const q=passageQuestion(entry.item,entry.q,entry.module,entry.index);q.choices=shuffle(q.choices,random);return q;}
  if(entry.module==='phrases'){
    const type=challenging&&makeCloze(entry.item)?'cloze':random()<.5?'zhToPhrase':'phraseToZh';
    return lexicalQuestion(buildPhraseQuestion(libraries.phrases,{mastery:{}},type,random,entry.item.id),'phrases');
  }
  const answer=entry.item,others=shuffle(libraries[entry.module].filter(w=>canonical(w.word)!==canonical(answer.word)),random);
  const choices=[answer],used=new Set([canonical(answer.word)]);
  for(const candidate of others){if(!used.has(canonical(candidate.word))){choices.push(candidate);used.add(canonical(candidate.word));}if(choices.length===4)break;}
  const type=!answer.meaning||answer.meaningPending||random()<.3?'audio':'meaning';
  return lexicalQuestion({type,answer,choices:shuffle(choices,random)},entry.module);
}

export function retryQuestion(item,entries,libraries,random=Math.random){
  if(item.reviewCount>0&&['word','phrase'].includes(item.question.kind)){
    const entry=entries.find(e=>e.cardKey===item.question.cardKey&&e.item.id===item.question.rewardId);
    if(entry)return materialize(entry,libraries,{random,challenging:item.dates.length>0});
  }
  const errors=Object.values(item.errors).sort((a,b)=>b.count-a.count);
  const q=copy(errors[item.reviewCount%errors.length]?.question||item.question);
  q.choices=shuffle(q.choices,random);return q;
}

export function reviewQueue(state,entries,libraries,filters={},random=Math.random){
  const cards=listCards(state,filters),queue=[];
  // Round-robin keeps a long article from filling the whole session.
  const groups=cards.map(c=>Object.values(c.items).filter(i=>filters.status==='mastered'?i.dates.length>=3:i.dates.length<3));
  while(queue.length<10&&groups.some(g=>g.length))for(const group of groups){if(group.length&&queue.length<10)queue.push(retryQuestion(group.shift(),entries,libraries,random));}
  return queue;
}

export function ability(state,kind){
  const recent=initializeStudy(state).performance[kind]||[];
  if(recent.length<8)return 1;
  const rate=recent.filter(Boolean).length/recent.length;return rate>=.8?3:rate>=.55?2:1;
}

export function getDaily(state,entries,libraries,{now=new Date(),random=Math.random}={}){
  const study=initializeStudy(state),day=dayKey(now);
  if(study.daily?.day===day)return study.daily;
  const questions=[],used=new Set();
  for(const [kind,count] of [['word',3],['phrase',2],['reading',1],['cloze',2]]){
    const level=ability(state,kind),pool=shuffle(entries.filter(e=>e.kind===kind),random);
    const recent=study.performance[kind]||[],needsReview=recent.length>=8&&recent.filter(Boolean).length/recent.length<.55;
    const due=Object.values(study.cards).filter(c=>c.kind===kind).flatMap(c=>Object.values(c.items)).filter(i=>i.dates.length<3&&i.due<=day).sort((a,b)=>a.due.localeCompare(b.due));
    let group=null;
    for(let slot=0;slot<count;slot++){
      let q=null;
      const error=due.find(i=>!used.has(`${i.question.cardKey}/${i.question.itemKey}`)&&(!group||i.question.cardKey===group));
      // Keep one slot for learning when there is more than one question in this category.
      if(error&&(slot<count-1||count===1||needsReview))q=retryQuestion(error,entries,libraries,random);
      if(!q){
        let candidates=pool.filter(e=>!used.has(`${e.cardKey}/${e.itemKey}`)&&(!group||e.cardKey===group));
        const within=candidates.filter(e=>e.level<=level);if(within.length)candidates=within;
        const known=e=>study.seen[`${e.cardKey}/${e.itemKey}`]||state.libraries?.[e.module]?.mastery?.[e.item.id];
        const learned=candidates.filter(known);
        const fresh=candidates.filter(e=>!known(e));
        const prefer=slot===count-1&&!needsReview?fresh:learned;
        const entry=(prefer.length?prefer:candidates)[0];
        if(entry)q=materialize(entry,libraries,{random,challenging:level>=2});
      }
      if(q){questions.push(q);used.add(`${q.cardKey}/${q.itemKey}`);if(kind==='cloze')group=q.cardKey;}
    }
  }
  study.daily={day,questions,answers:{},createdAt:now.getTime(),levels:Object.fromEntries(Object.keys(kinds).map(k=>[k,ability(state,k)]))};
  return study.daily;
}

export function answerDaily(state,index,selectedId,{now=new Date()}={}){
  const daily=initializeStudy(state).daily;
  if(!daily||daily.day!==dayKey(now)||daily.answers[index]||!daily.questions[index])return null;
  const q=daily.questions[index];if(!q.choices.some(c=>c.id===selectedId))return null;
  const correct=recordStudyAnswer(state,q,selectedId,{practice:true,now});
  daily.answers[index]={selectedId,correct,at:now.getTime()};return {correct,question:q};
}
