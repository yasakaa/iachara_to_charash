'use strict';
// Source sections are independent: headings elsewhere must never become sessions.
function iacharaSections(root) {
  const nodes=r=>[r,...r.querySelectorAll('*')];
  const read=n=>n.nodeName==='INPUT'?(n.getAttribute('value')||''):n.nodeName==='BR'?'\n':[...n.childNodes].map(c=>c.nodeType===3?c.nodeValue:read(c)).join('');
  function section(id,title){const byId=root.querySelector('#'+id);if(byId)return byId;const header=nodes(root).find(n=>n.classList.contains('no-select')&&read(n).trim()===title);return header?.parentElement||null;}
  const sections={item:section('item','冒険の装備とその他の所持品')||section('item','装備と所持品'),scenario:section('newScenario','通過したシナリオ'),artifact:section('artifact','魔導書、呪文、アーティファクト'),creature:section('mythosCreature','遭遇した超自然の存在'),assets:section('assets','収入と財産'),battle:section('battle','武器'),backstory:section('backstory','バックストーリー')};
  function records(r){
    if(!r)return [];
    const inputs=[...r.querySelectorAll('input')].filter(n=>n.getAttribute('type')!=='checkbox');
    if(inputs.length)return inputs.filter(n=>n.parentElement.querySelector('textarea')).map(n=>({name:read(n).trim(),body:read(n.parentElement.querySelector('textarea'))})).filter(x=>x.name||x.body);
    return [...r.querySelectorAll('span')].filter(n=>n.parentElement?.parentElement?.classList.contains('no-select')&&read(n).trim()).map(n=>{
      const header=n.parentElement.parentElement,card=header.parentElement;
      const body=[...card.children].filter(c=>c!==header).map(read).join('\n').replaceAll('ここをクリックして内容を見る','').trim();
      return {name:read(n).trim(),body};
    });
  }
  const items=[];
  if(sections.item){
    for(const row of nodes(sections.item)){
      const inputs=[...row.querySelectorAll('input')];
      if(inputs.length!==5 || [...row.children].some(c=>c.querySelectorAll('input').length===5))continue;
      const v=inputs.map(read);if(!v[0].trim())continue;
      const note=[v[4],v[1]?'単価: '+v[1]:'',v[3]?'価格: '+v[3]:'',v[2]?'':'元の個数は未記入（1を仮設定）'].filter(Boolean).join(' / ');
      if(v[2]&&!/^\d+$/.test(v[2]))throw new Error('所持品の個数が整数ではありません: '+v[0]);
      items.push([v[0],v[2]||1,note]);
    }
    // Read-only cards use label/value pairs, not input rows.
    if(!sections.item.querySelector('input'))for(const h of sections.item.querySelectorAll('span')){
      if(!h.parentElement?.parentElement?.classList.contains('no-select')||!read(h).trim())continue;
      let card=h.parentElement.parentElement.parentElement;
      function field(label){const n=nodes(card).find(n=>!n.children.length&&read(n).trim()===label);return n?.nextElementSibling?read(n.nextElementSibling).trim():'';}
      const quantity=field('個数');if(quantity&&!/^\d+$/.test(quantity))throw new Error('所持品の個数が整数ではありません。');
      const note=[field('効果・備考など')||field('効果・備考')||field('備考')||field('その他'),field('単価')?'単価: '+field('単価'):'',field('価格')?'価格: '+field('価格'):'',quantity?'':'元の個数は未記入（1を仮設定）'].filter(Boolean).join(' / ');
      items.push([read(h).trim(),quantity||1,note]);
    }
  }
  let sessions=records(sections.scenario);
  if(sections.scenario&&!sessions.length)sessions=[...sections.scenario.querySelectorAll('span')].filter(n=>n.parentElement?.parentElement?.classList.contains('no-select')&&read(n).trim()).map(n=>({name:read(n).trim(),body:[...n.parentElement.parentElement.parentElement.querySelectorAll('textarea')].map(read).join('\n')}));
  const artifact=records(sections.artifact),creatures=records(sections.creature);
  const extraMemos=[];
  if(artifact.length)extraMemos.push({title:'魔導書・呪文・アーティファクト',body:artifact.map(r=>r.name+(r.body?'\n'+r.body:'')).join('\n\n')});
  const assets=[];
  if(sections.assets)for(const label of ['収入','手持ち現金','預金','個人資産','不動産','生活水準','現金','資産','支出レベル']){
    const n=nodes(sections.assets).find(n=>!n.children.length&&read(n).trim()===label);
    const next=n?.nextElementSibling;const v=next?read(next).trim():'';
    if(v)assets.push([label,v]);
  }
  const excluded=[sections.item,sections.scenario,sections.artifact,sections.creature,sections.assets,sections.battle,sections.backstory].filter(Boolean);
  const memos=[...root.querySelectorAll('textarea')].filter(n=>!excluded.some(s=>s.contains(n))).map(read).filter(s=>s.trim());
  const backstories=[];
  if(sections.backstory)for(const label of ['容姿の描写','イデオロギー/信念','重要な人々','意味のある場所','秘蔵の品','特徴','負傷、傷跡','恐怖症、マニア']){
    const header=nodes(sections.backstory).find(n=>n.classList.contains('no-select')&&read(n).replaceAll(' ','').startsWith(label));
    if(!header)continue;
    const body=[...header.parentElement.children].filter(c=>c!==header).map(read).join('\n').replaceAll('ここをクリックして内容を見る','').trim();
    if(body)backstories.push({title:(label==='イデオロギー/信念'?'イデオロギー / 信念':label),body,key:read(header).includes('キー・コネクション')});
  }
  return {items,sessions,artifact,creatures,assets,extraMemos,memos,sections,backstories};
}

'use strict';
/* Input stays in a detached template. Its nodes are never attached to the page. */
function convertIachara(html, editionChoice='auto') {
  const template = document.createElement('template');
  template.innerHTML = html;
  const doc = template.content;
  doc.querySelectorAll('script,style,iframe,object,embed,link,base,svg,template').forEach(n => n.remove());
  let root = doc.querySelector('#__next');
  if (!root) throw new Error('いあきゃらの閲覧HTMLを確認できません。表示完了後に保存してください。');
  const sourceRoot=root;
  if(sourceRoot.querySelector('#ability'))throw new Error('編集HTMLは項目確認用です。変換には閲覧画面を保存したHTMLを選んでください。');
  const extra=iacharaSections(sourceRoot);
  const all = r => [r, ...r.querySelectorAll('*')];
  const txt = n => {
    if (n.nodeType === 3) return n.nodeValue;
    if (n.nodeName === 'INPUT') return n.getAttribute('value') || '';
    if (n.nodeName === 'BR') return '\n';
    return [...n.childNodes].map(txt).join('');
  };
  function val(label, r = root, required = false) {
    for (const n of all(r)) {
      if (n.nodeName === 'TEXTAREA') continue;
      for (const c of n.childNodes) {
        if (c.nodeType === 3 && c.nodeValue.trim() === label && c.nextSibling?.nodeType === 1) return txt(c.nextSibling).trim();
      }
    }
    for (const n of all(r)) {
      if (txt(n).trim() === label && ![...n.children].some(c => txt(c).trim() === label) && n.nextElementSibling) return txt(n.nextElementSibling).trim();
    }
    if (required) throw new Error(`「${label}」が見つかりません。HTMLの形式を確認してください。`);
    return '';
  }
  const num = s => {if (!/^[+-]?\d+$/.test(s)) throw new Error(`整数に変換できません: ${s}`); return Number(s);};
  const cell = v => {const s=String(v).replaceAll('\\','\\\\').replaceAll('"','\\"').replaceAll('|','\\|');return s.includes('\n') ? `"${s}"` : s;};
  const table = (head, rows) => [head,...rows].map(r=>'| '+r.map(cell).join(' | ')+' |').join('\n');
  const memo = (title,body) => `---\n【${title}】\n${body.replace(/^(\\*---(?:\s.*)?)$/gm,'\\$1')}\n---`;
  const abilities=Object.fromEntries('STR CON POW DEX APP SIZ INT EDU'.split(' ').map(k=>[k,num(val(k,root,true))]));
  const marker7=Boolean(val('ビルド')||val('MOV'));
  if(!['auto','6','7'].includes(String(editionChoice)))throw new Error('版の指定が不正です。');
  const edition=editionChoice==='auto'?(marker7?7:6):Number(editionChoice);
  if(editionChoice==='auto'&&!marker7&&Math.max(...Object.values(abilities))>40)throw new Error('版を判定できません。「入力の版」で6版か7版を指定してください。');
  if(edition===6&&marker7)throw new Error('7版の項目があります。「入力の版」を自動判定か7版にしてください。');
  const system=`クトゥルフ${edition}版`;
  const occFactor=edition===7?4:20, interestFactor=edition===7?2:10;

  const title=doc.querySelector('title')?.textContent || '';
  const name=title.replace(/\s*[-－–]\s*いあきゃら.*$/,'').trim();
  if (!name || name===title) throw new Error('ページタイトルからキャラクター名を読み取れません。');
  const out=['キャラッシュテキスト v2','キャラクターID:','','【共通情報】','','【基本情報】','',`名前: ${cell(name)}`];
  const nameNode=all(root).find(n=>!n.children.length && txt(n).trim()===name);
  if (nameNode?.previousElementSibling) out.push('なまえ（かな）: '+cell(txt(nameNode.previousElementSibling).trim()));
  for(const label of ['職業','年齢','性別','出身','身長','体重','髪の色','瞳の色']) {
    let v=val(label);if(!v)continue;
    if(label==='年齢'){const m=v.match(/^(\d+)\s*歳?$/);if(!m)continue;v=m[1];}
    out.push(`${label}: ${cell(v)}`);
  }
  const birthday=val('誕生日').match(/^\s*(\d{1,2})\s*\/\s*(\d{1,2})\s*$/);
  if(birthday)out.push(`誕生日: ${Number(birthday[1])}月${Number(birthday[2])}日`);
  out.push('年齢の自動算出: いいえ');
  const colorLabel=all(root).find(n=>!n.children.length && txt(n).trim()==='カラー');
  if(colorLabel){const styles=all(colorLabel.parentElement).map(n=>n.getAttribute('style')||'').join(' ');const colors=[...styles.matchAll(/background-color:\s*rgb\((\d+),\s*(\d+),\s*(\d+)\)/g)];if(colors.length)out.push('イメージカラー: #'+colors.at(-1).slice(1).map(v=>Number(v).toString(16).padStart(2,'0')).join(''));}
  const memos=extra.memos;
  out.push('','【ネタバレ用メモ】','');
  memos.forEach((body,i)=>out.push(memo(`いあきゃら元メモ ${i+1}`,body),''));
  for(const r of extra.extraMemos)out.push(memo(r.title,r.body),'');
  const names=[...root.querySelectorAll('[class*="AbilityTable_tableLeftHeaderSkill"]')].filter(n=>txt(n).trim()!=='技能名');
  if(!names.length)throw new Error('技能一覧を読み取れません。技能を表示して保存してください。');
  const skillRows=[];
  for(const parent of new Set(names.map(n=>n.parentElement))){
    const rows=names.filter(n=>n.parentElement===parent),columns={};
    for(const col of parent.parentElement.children){const key=col.firstElementChild&&txt(col.firstElementChild).trim();if(['初期','職業','興味','成長','他','合計'].includes(key))columns[key]=[...col.querySelectorAll('input[type="number"]')].map(n=>n.getAttribute('value')||'0');}
    if(Object.keys(columns).length!==6||Object.values(columns).some(c=>c.length!==rows.length))throw new Error('技能表の列数が一致しません。この表示形式には未対応です。');
    rows.forEach((node,i)=>skillRows.push({node,nums:['初期','職業','興味','成長','他','合計'].map(k=>num(columns[k][i]))}));
  }
  const groups={
    '戦闘技能':'回避 投擲 キック 組みつき こぶし／パンチ 頭突き マーシャルアーツ 拳銃 サブマシンガン ショットガン マシンガン ライフル',
    '探索技能':'応急手当 鍵開け 隠す 隠れる 聞き耳 忍び歩き 写真術 精神分析 追跡 登攀 図書館 目星',
    '行動技能':'運転 機械修理 重機械操作 乗馬 水泳 製作 操縦 跳躍 電気修理 ナビゲート 変装',
    '交渉技能':'言いくるめ 信用 説得 値切り 母国語 ほかの言語',
    '知識技能':'医学 オカルト 化学 クトゥルフ神話 芸術 経理 考古学 コンピューター 心理学 人類学 生物学 地質学 電子工学 天文学 博物学 物理学 法律 薬学 歴史'};
  if(edition===7)Object.assign(groups,{
    '戦闘技能':'回避 投擲 近接戦闘 射撃',
    '探索技能':'応急手当 鍵開け 手さばき 聞き耳 隠密 精神分析 追跡 登攀 図書館 目星 鑑定 読唇術',
    '行動技能':'運転 機械修理 重機械操作 乗馬 水泳 芸術/製作 操縦 跳躍 電気修理 ナビゲート 変装',
    '交渉技能':'言いくるめ 信用 説得 母国語 威圧 魅惑 ほかの言語',
    '知識技能':'医学 オカルト クトゥルフ神話 経理 考古学 コンピューター 科学 心理学 人類学 電子工学 自然 法律 歴史 サバイバル 催眠術 ダイビング 動物使い 爆破'
  });
  const grouped=Object.fromEntries(Object.keys(groups).map(k=>[k,[]]));
  skillRows.forEach(({node:n,nums})=>{
    let base=n.textContent.trim();base=({'こぶし（パンチ）':'こぶし／パンチ','組み付き':'組みつき','コンピュータ':'コンピューター'})[base]||base;
    if(edition===7)base=({'言語':'ほかの言語','芸術／製作':'芸術/製作','芸術/制作':'芸術/製作','魅了':'魅惑'})[base]||base;
    const specialization=n.querySelector('input')?.getAttribute('value')?.trim();
    let skill=base?(base+(specialization?`（${specialization}）`:'')):(specialization||'');
    let group=Object.keys(groups).find(g=>groups[g].split(' ').includes(base));
    if(!group){group='知識技能';skill='独自技能：'+skill;}
    if(nums.slice(0,5).reduce((a,b)=>a+b,0)!==nums[5])throw new Error(`技能「${skill}」の内訳と合計が一致しません。`);
    grouped[group].push([skill,...nums]);
  });
  const sm=val('正気度',root,true).match(/^(\d+)\s*\/\s*(\d+)$/);
  if(!sm)throw new Error('正気度の形式を読み取れません。');
  out.push(`【${system}】`,'','【能力値】','',table(['能力','元の値','増減','その他','合計（参照用）'],Object.entries(abilities).map(([k,v])=>[k,v,0,0,v])),'');
  for(const [src,dst] of (edition===7?[['HP','HP'],['MP','MP'],['DB','ダメージボーナス'],['幸運','幸運'],['ビルド','ビルド']]:[['HP','HP'],['MP','MP'],['DB','ダメージボーナス'],['アイデア','アイデア'],['幸運','幸運'],['知識','知識']]))out.push(`${dst}: ${cell(val(src,root,true))}`);
  out.push(`SAN（参照用）: ${sm[1]}`,`SAN最大（参照用）: ${sm[2]}`,`SAN補正: ${Number(sm[1])-abilities.POW*(edition===7?1:5)}`,'','【採用ルールとポイント】','',`職業ポイント計算式: EDU×${occFactor}`);
  for(const [label,initial] of [['職業',abilities.EDU*occFactor],['興味',abilities.INT*interestFactor]]){const m=txt(root).match(new RegExp(label+'P\\s*(\\d+)\\s*/\\s*(\\d+)'));const total=m?Number(m[2]):initial;out.push(`${label}ポイント補正: ${total-initial}`,`${label}ポイント総量（参照用）: ${total}`);}
  if(edition===7){
    let observed=val('MOV',root,true);
    const movLabel=all(root).find(n=>!n.children.length&&txt(n).trim()==='MOV');
    const eq=movLabel&&txt(movLabel.parentElement).match(/=\s*([+-]?\d+)\s*$/);if(eq)observed=eq[1];
    const mov=num(observed),a=abilities;
    const ageMatch=val('年齢').match(/^(\d+)\s*歳?$/);const age=ageMatch?Number(ageMatch[1]):0;
    let baseline=(a.STR<a.SIZ&&a.DEX<a.SIZ)?7:(a.STR>a.SIZ&&a.DEX>a.SIZ)?9:8;
    baseline-=Math.max(0,Math.min(5,Math.floor(age/10)-3));
    const at=out.indexOf('【採用ルールとポイント】');out.splice(at,0,`MOV（参照用）: ${mov}`,'MOV増減: 0',`MOVその他: ${mov-baseline}`,'');
    if(extra.backstories.length){out.push('【バックストーリー】','');let keyed=false;for(const r of extra.backstories){const key=r.key&&!keyed;if(key)keyed=true;out.push(memo((key?'★ ':'')+r.title,r.body),'');}}
    const money=extra.assets.filter(([k])=>['生活水準','現金','資産','支出レベル'].includes(k));if(money.length)out.push('【収入と財産】','',...money.map(([k,v])=>`${k}: ${cell(v)}`),'');
  }
  out.push('','【技能】','');
  for(const [g,rows] of Object.entries(grouped))if(rows.length)out.push(`［${g}］`,'',table(['技能名','初期値','職業P','興味P','成長分','その他','合計（参照用）'],rows),'');
  const weaponRoot=extra.sections.battle;
  const headings=[...(weaponRoot||document.createElement('div')).querySelectorAll('span')].filter(n=>(n.getAttribute('style')||'').includes('font-weight: bold') && n.parentElement?.parentElement?.classList.contains('no-select'));
  const weapons=[],scenarios=[];
  for(const heading of headings){let n=heading.parentElement;for(let i=0;i<4;i++){if(!n||val('ダメージ',n))break;n=n.parentElement;}if(n && val('ダメージ',n)){const note=val('その他',n);weapons.push([txt(heading).trim(),1,(note?note+' / ':'')+'元の成功率: '+val('成功率',n),...['ダメージ','故障','射程','回数','装弾数','耐久力'].map(k=>val(k,n))]);}else scenarios.push(txt(heading).trim());}
  if(weapons.length)out.push('【武器】','',table(['名称','個数','備考','ダメージ','故障NO','射程','攻撃回数','装弾数','耐久力'],weapons),'');
  if(extra.items.length)out.push('【システム別の所持品】','',table(['名前','個数','備考'],extra.items),'');
  if(extra.sessions.length){
    const at=out.indexOf(`【${system}】`);const block=['【セッション記録】',''];
    for(const session of extra.sessions){
      if(/[\r\n［］]/.test(session.name))throw new Error('シナリオ名に改行または見出し記号が含まれています。');
      block.push(`［${session.name||'名称未記入'}］`,'',`システム: ${system}`,'URLを公開: いいえ','');
      if(session.body)block.push(memo('ひとことメモ',session.body),'');
    }out.splice(at,0,...block);
  }
  if(extra.creatures.length){out.push('【システム別の経験の記録】','','遭遇した存在:',memo('遭遇した存在',extra.creatures.map(r=>r.name+(r.body?'\n'+r.body:'')).join('\n\n')),'');}
  const freeAssets=extra.assets.filter(([k])=>edition!==7||!['生活水準','現金','資産','支出レベル'].includes(k));
  if(freeAssets.length){const at=out.indexOf('【ネタバレ用メモ】');out.splice(at,0,'【自由項目】','',...freeAssets.map(([k,v])=>`${k}: ${cell(v)}`),'');}
  const warnings=['非表示技能は出力していません。新規キャラクターでは標準初期値になります。既存キャラクターの更新では、その技能の値が維持されます。','能力値は表示最終値を元の値として保存し、技能初期値・HP等は固定値にしています。','メモはネタバレ用メモに保存します。公開設定・合言葉は引き継ぎません。','画像は別途登録してください。HTMLに保存されていない情報は復元できません。',`職業ポイントはEDU×${occFactor}との差を補正として保持。採用ルールは推測していません。`];
  if(extra.items.some(r=>String(r[2]).includes('元の個数は未記入')))warnings.push('個数が空欄の所持品は1を仮設定し、備考に元が空欄である旨を残しています。');
  if(weapons.length)warnings.push('武器の個数は1を仮設定し、成功率は備考に保存しています。取り込み後、武器の「使用技能」を手動で指定してください。');
  if(edition===7)warnings.push('7版のMOVは表示値と能力値・年齢による計算との差を補正として保存します。バックストーリーの公開設定・キーコネクション、年齢が不明な場合のMOVを確認してください。');
  return {name,edition,text:out.join('\n')+'\n',skillCount:names.length,memoCount:memos.length+extra.extraMemos.length,weaponCount:weapons.length,itemCount:extra.items.length,sessionCount:extra.sessions.length,warnings};
}
