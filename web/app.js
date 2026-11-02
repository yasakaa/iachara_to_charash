'use strict';
const input=document.getElementById('files'), drop=document.getElementById('drop'),results=document.getElementById('results'),status=document.getElementById('status');
const convertButton=document.getElementById('convert'),selection=document.getElementById('selection');
const editionInput=document.getElementById('edition');
let busy=false,selectedFiles=[];
function selectFiles(files){
  if(busy)return;
  selectedFiles=[...files];
  results.replaceChildren();
  selection.textContent=selectedFiles.length ? `${selectedFiles.length}件選択: ${selectedFiles.map(f=>f.name).join('、')}` : 'ファイル未選択';
  convertButton.disabled=selectedFiles.length===0;
  status.textContent=selectedFiles.length?'「変換する」を押してください。':'';
}
function element(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
async function processFiles(files){
  if(busy)return;
  if(!files.length){status.textContent='先にHTMLファイルを選択してください。';return;}
  busy=true;input.disabled=true;editionInput.disabled=true;convertButton.disabled=true;results.replaceChildren();status.textContent='変換しています…';
  let success=0;
  const list=[...files];
  try {
    if(list.length>200)throw new Error('一度に選べるファイルは200件までです。');
    for(const file of list){
      const card=element('article',undefined,'result');results.append(card);
      try{
        if(!/\.html?$/i.test(file.name))throw new Error('HTMLファイルを選択してください。');
        if(file.size>5*1024*1024)throw new Error('HTMLは1ファイル5MBまでです。');
        const buffer=await file.arrayBuffer();let html;
        try{html=new TextDecoder('utf-8',{fatal:true}).decode(buffer);}catch{html=new TextDecoder('shift_jis',{fatal:true}).decode(buffer);}
        const r=convertIachara(html,editionInput.value);success++;
        card.append(element('h2',r.name),element('p',`クトゥルフ${r.edition}版 · 技能 ${r.skillCount}件 · 武器 ${r.weaponCount}件 · メモ ${r.memoCount}件 · 所持品 ${r.itemCount}件 · 通過記録 ${r.sessionCount}件`));
        const download=element('button','TXTを保存');download.type='button';
        download.addEventListener('click',()=>{const url=URL.createObjectURL(new Blob(['\uFEFF',r.text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=file.name.replace(/\.html?$/i,'')+'_charash.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
        const details=element('details'),summary=element('summary','引き継ぎ内容の注意'),ul=element('ul');r.warnings.forEach(w=>ul.append(element('li',w)));details.append(summary,ul);
        const preview=element('details');preview.append(element('summary','出力テキストを見る'),element('pre',r.text));card.append(download,details,preview);
      }catch(error){card.classList.add('error');card.append(element('h2',file.name),element('p',error.message));}
    }
    status.textContent=`${list.length}件中 ${success}件を変換しました。`;
  }catch(error){status.textContent=error.message;}
  finally{busy=false;input.disabled=false;editionInput.disabled=false;convertButton.disabled=selectedFiles.length===0;}
}
input.addEventListener('change',()=>selectFiles(input.files));
convertButton.addEventListener('click',()=>processFiles(selectedFiles));
for(const name of ['dragover','drop'])window.addEventListener(name,e=>e.preventDefault());
drop.addEventListener('dragover',()=>drop.classList.add('active'));
drop.addEventListener('dragleave',()=>drop.classList.remove('active'));
drop.addEventListener('drop',e=>{drop.classList.remove('active');selectFiles(e.dataTransfer.files);});
status.textContent='';

editionInput.addEventListener('change',()=>{results.replaceChildren();status.textContent=selectedFiles.length?'版の指定を変更しました。「変換する」を押してください。':'';});
