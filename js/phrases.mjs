const MASTERY_CAP=3;

function weightedPhrase(phrases,progress,random=Math.random){
  const weighted=[];
  for(const item of phrases){const mastery=progress.mastery[item.id]||0;const weight=mastery>=MASTERY_CAP?1:mastery<=1?3:2;for(let i=0;i<weight;i++)weighted.push(item);}
  if(!weighted.length)throw new Error('EMPTY_PHRASES');
  return weighted[Math.floor(random()*weighted.length)];
}

function pickChoices(phrases,answer,getValue,random){
  const used=new Set([getValue(answer)]),pool=phrases.filter(x=>x.id!==answer.id),choices=[answer];
  while(choices.length<4&&pool.length){const index=Math.floor(random()*pool.length),candidate=pool.splice(index,1)[0],value=getValue(candidate);if(value&&!used.has(value)){used.add(value);choices.push(candidate);}}
  if(choices.length<4)throw new Error('NOT_ENOUGH_PHRASES');
  for(let i=choices.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[choices[i],choices[j]]=[choices[j],choices[i]];}
  return choices;
}

function phraseForms(phrase){
  return phrase.split('/').map(x=>x.trim().replace(/^to\s+/i,'')).filter(x=>x.length>=3).sort((a,b)=>b.length-a.length);
}

export function makeCloze(item){
  for(const example of item.examples||[]){
    for(const form of phraseForms(item.phrase)){
      const match=example.match(new RegExp(`\\b${form.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}\\b`,'i'));
      if(match)return example.slice(0,match.index)+'_____'+example.slice(match.index+match[0].length);
    }
  }
  return '';
}

export function buildPhraseQuestion(phrases,progress,type,random=Math.random){
  const reliableZh=x=>x.meaningZh&&!/待人工|待確認/.test(x.meaningZh);
  const eligible=type==='cloze'?phrases.filter(x=>makeCloze(x)):(type==='zhToPhrase'||type==='phraseToZh'?phrases.filter(reliableZh):phrases);
  const answer=weightedPhrase(eligible,progress,random);
  const choiceValue=type==='phraseToZh'?x=>x.meaningZh:x=>x.phrase;
  return {type,answer,choices:pickChoices(eligible,answer,choiceValue,random),cloze:type==='cloze'?makeCloze(answer):''};
}
