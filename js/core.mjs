export const MASTERY_CAP = 3;
export const BATCH_SIZE = 20;

export function blankLibraryState(){return {level:1,mastery:{},recent:[],answers:0};}
export function blankWallet(){return {ones:0,tens:0,hundreds:0,total:0};}
export function walletTotal(wallet){return wallet.ones+wallet.tens*10+wallet.hundreds*100;}
export const LIBRARY_KEYS=['basic','advanced','phrases','basicReading','cloze','readingTest','articles'];
export function blankState(){return {coins:0,wallet:blankWallet(),libraries:Object.fromEntries(LIBRARY_KEYS.map(key=>[key,blankLibraryState()])),updatedAt:Date.now()};}

export function normalizeState(value={}){
  const clean=blankState();
  const legacyCoins=Math.max(0,Math.floor(Number(value.coins)||0));
  if(value.wallet&&typeof value.wallet==='object'){
    clean.wallet.ones=Math.max(0,Math.floor(Number(value.wallet.ones)||0));
    clean.wallet.tens=Math.max(0,Math.floor(Number(value.wallet.tens)||0));
    clean.wallet.hundreds=Math.max(0,Math.floor(Number(value.wallet.hundreds)||0));
  }else clean.wallet.ones=legacyCoins;
  clean.wallet.total=walletTotal(clean.wallet);
  clean.coins=clean.wallet.total;
  for(const key of LIBRARY_KEYS){
    const source=value.libraries?.[key]||{};
    clean.libraries[key]={level:Math.max(1,Number(source.level)||1),mastery:source.mastery&&typeof source.mastery==='object'?source.mastery:{},recent:Array.isArray(source.recent)?source.recent.slice(-8).map(Boolean):[],answers:Math.max(0,Number(source.answers)||0)};
  }
  return clean;
}

export function rollBillReward(streak,random=Math.random){
  const reward={ones:1,tens:0,hundreds:0,total:1};
  let tenChance=0,hundredChance=0;
  if(streak>=10){tenChance=.30;hundredChance=.05;}
  else if(streak>=5){tenChance=.20;hundredChance=.01;}
  else if(streak>=3)tenChance=.10;
  if(tenChance&&random()<tenChance)reward.tens=1;
  if(hundredChance&&random()<hundredChance)reward.hundreds=1;
  reward.total=walletTotal(reward);
  return reward;
}

export function nextCorrectStreak(current,isCorrect){return isCorrect?Math.max(0,Math.floor(Number(current)||0))+1:0;}

export function addReward(appState,reward){
  appState.wallet.ones+=reward.ones;
  appState.wallet.tens+=reward.tens;
  appState.wallet.hundreds+=reward.hundreds;
  appState.wallet.total=walletTotal(appState.wallet);
  appState.coins=appState.wallet.total;
}

export function maxLevel(words){return Math.max(1,Math.ceil(words.length/BATCH_SIZE));}
export function activePool(words,libraryState){return words.slice(0,Math.min(words.length,libraryState.level*BATCH_SIZE));}
export function masteredCount(words,libraryState){return activePool(words,libraryState).filter(w=>(libraryState.mastery[w.id]||0)>=MASTERY_CAP).length;}

export function weightedWord(words,libraryState,random=Math.random){
  const pool=activePool(words,libraryState);
  if(!pool.length)throw new Error('EMPTY_LIBRARY');
  const weighted=[];
  for(const word of pool){const mastery=libraryState.mastery[word.id]||0;const weight=mastery>=MASTERY_CAP?1:mastery<=1?3:2;for(let i=0;i<weight;i++)weighted.push(word);}
  return weighted[Math.floor(random()*weighted.length)];
}

export function buildQuestion(words,libraryState,type,random=Math.random){
  const eligible=type==='meaning'?words.filter(w=>!w.meaningPending&&w.meaning):words;
  const answer=weightedWord(eligible,libraryState,random);
  const pool=eligible.filter(w=>w.id!==answer.id);
  const distractors=[];
  while(distractors.length<3&&pool.length){const index=Math.floor(random()*pool.length);distractors.push(pool.splice(index,1)[0]);}
  if(distractors.length<3)throw new Error('NOT_ENOUGH_WORDS');
  const choices=[answer,...distractors];
  for(let i=choices.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[choices[i],choices[j]]=[choices[j],choices[i]];}
  return {type,answer,choices};
}

export function recordAnswer(appState,libraryKey,wordId,isCorrect,totalLevels){
  const state=appState.libraries[libraryKey];
  const current=Number(state.mastery[wordId])||0;
  state.mastery[wordId]=isCorrect?Math.min(MASTERY_CAP,current+1):Math.max(0,current-1);
  state.recent.push(Boolean(isCorrect));state.recent=state.recent.slice(-8);state.answers++;
  let change=0;
  if(state.recent.length>=6){const correct=state.recent.filter(Boolean).length;if(correct>=6&&state.level<totalLevels){state.level++;change=1;state.recent=[];}else if(correct<=2&&state.level>1){state.level--;change=-1;state.recent=[];}}
  appState.updatedAt=Date.now();
  return change;
}
