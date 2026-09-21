import {firebaseConfig} from './firebase-config.js';

const PREFIX='english-land-mvp-v1:';
const FORBIDDEN_PROJECT='elementary-chinese';
let cloud=null;
let storageInitialized=false;

export async function initializeStorage(){
  if(!firebaseConfig){storageInitialized=true;return {mode:'local'};}
  if(firebaseConfig.projectId===FORBIDDEN_PROJECT)throw new Error('禁止使用國字版 Firebase 專案');
  const [{initializeApp},{getAuth,signInWithEmailAndPassword,createUserWithEmailAndPassword,signOut},{getFirestore,doc,getDoc,setDoc,serverTimestamp}]=await Promise.all([
    import('https://www.gstatic.com/firebasejs/12.17.1/firebase-app.js'),
    import('https://www.gstatic.com/firebasejs/12.17.1/firebase-auth.js'),
    import('https://www.gstatic.com/firebasejs/12.17.1/firebase-firestore.js')]);
  const app=initializeApp(firebaseConfig);cloud={auth:getAuth(app),db:getFirestore(app),signInWithEmailAndPassword,createUserWithEmailAndPassword,signOut,doc,getDoc,setDoc,serverTimestamp};storageInitialized=true;
  return {mode:'firebase'};
}

const emailFor=name=>`${name.toLowerCase().replace(/[^a-z0-9._-]/g,'_')}@english-land.local`;
export async function login(username,password){
  if(!storageInitialized)throw new Error('登入服務尚未初始化完成，請確認頁面下方的啟動錯誤，重新整理後再試');
  if(!cloud){localStorage.setItem(PREFIX+'current',username);return {uid:username,username};}
  const result=await cloud.signInWithEmailAndPassword(cloud.auth,emailFor(username),password);return {uid:result.user.uid,username};
}
export async function register(username,password){
  if(!storageInitialized)throw new Error('Firebase 尚未初始化完成，請稍後再試');
  if(!cloud){const key=PREFIX+'user:'+username;if(localStorage.getItem(key))throw new Error('這個帳號已存在');localStorage.setItem(PREFIX+'current',username);return {uid:username,username};}
  const result=await cloud.createUserWithEmailAndPassword(cloud.auth,emailFor(username),password);return {uid:result.user.uid,username};
}
export function currentLocalUser(){const username=localStorage.getItem(PREFIX+'current');return username?{uid:username,username}:null;}
export async function loadState(user){
  if(!cloud){const raw=localStorage.getItem(PREFIX+'user:'+user.uid);return raw?JSON.parse(raw):null;}
  const snap=await cloud.getDoc(cloud.doc(cloud.db,'englishUsers',user.uid));return snap.exists()?snap.data().state:null;
}
export async function saveState(user,state){
  if(!cloud){localStorage.setItem(PREFIX+'user:'+user.uid,JSON.stringify(state));return;}
  await cloud.setDoc(cloud.doc(cloud.db,'englishUsers',user.uid),{state,updatedAt:cloud.serverTimestamp()},{merge:true});
}
export async function logout(){if(cloud)await cloud.signOut(cloud.auth);localStorage.removeItem(PREFIX+'current');}
