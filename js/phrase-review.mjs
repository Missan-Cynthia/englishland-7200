import {buildPhraseQuestion} from './phrases.mjs';

export const typeLabels={zhToPhrase:'中文選片語',phraseToZh:'片語選中文',cloze:'例句克漏字'};
export function recordPhraseReview(state,question,selected,{sessionId=null,now=Date.now()}={}){
  const book=state.phraseMistakes||(state.phraseMistakes={});
  const id=question.answer.id,correct=selected.id===id;
  const phraseKey=question.answer.phrase.trim().toLowerCase();
  let card=book[id]||Object.values(book).find(c=>c.phraseKey===phraseKey);
  if(!correct){
    card=card||(book[id]={id,phraseKey,phraseIds:[],wrongCount:0,streak:0,reviewCount:0,errors:{}});
    if(!card.phraseIds.includes(id))card.phraseIds.push(id);
    card.wrongCount++;card.lastWrongAt=now;card.streak=0;
    const previous=card.errors[question.type];
    card.errors[question.type]={count:(previous?.count||0)+1,at:now,selectedId:selected.id,question:JSON.parse(JSON.stringify(question))};
  }
  if(card&&sessionId&&card.lastSession!==sessionId){
    card.lastSession=sessionId;card.reviewCount++;card.lastReviewAt=now;
    if(correct)card.streak=Math.min(3,card.streak+1);
  }
  return card;
}

export function reviewCards(book,phrases,{status='pending',unit='',type=''}={}){
  const available=new Set(phrases.filter(p=>!unit||p.lesson===Number(unit)).map(p=>p.id));
  return Object.values(book||{}).filter(c=>(c.phraseIds||[c.id]).some(id=>available.has(id))&&
    (status==='mastered'?c.streak>=3:c.streak<3)&&(!type||c.errors[type]))
    .sort(status==='frequent'?(a,b)=>b.wrongCount-a.wrongCount||b.lastWrongAt-a.lastWrongAt:
      (a,b)=>(a.lastReviewAt||0)-(b.lastReviewAt||0)||b.lastWrongAt-a.lastWrongAt);
}

export function buildReviewQuestion(card,phrases,type='',random=Math.random){
  const errors=Object.entries(card.errors).filter(([key])=>!type||key===type)
    .sort((a,b)=>b[1].count-a[1].count);
  if(!errors.length)throw new Error('EMPTY_REVIEW');
  const [kind,error]=errors[(card.reviewCount||0)%errors.length];
  if(!card.reviewCount){
    const question=JSON.parse(JSON.stringify(error.question));
    for(let i=question.choices.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[question.choices[i],question.choices[j]]=[question.choices[j],question.choices[i]];}
    return question;
  }
  return buildPhraseQuestion(phrases,{mastery:{}},kind,random,error.question.answer.id);
}
