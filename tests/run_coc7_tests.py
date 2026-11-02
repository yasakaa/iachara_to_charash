"""Synthetic 7th-edition view fixtures; no real character data."""
from pathlib import Path
import runpy
import json
import re

repo=Path(__file__).resolve().parents[1]
helpers=runpy.run_path(str(repo/'tests/run_review_tests.py'))
render,pair,card,section=map(helpers.get,['render','pair','card','section'])
convert=helpers['mod'].convert
out=repo/'tests/coc7_results'
(out/'入力HTML').mkdir(parents=True,exist_ok=True)
(out/'Python出力').mkdir(exist_ok=True)


def skill_table(rows):
    s='<div class="skills"><div><div class="AbilityTable_tableLeftHeaderSkill">技能名</div>'
    for base,special,nums in rows:
        s+='<div class="AbilityTable_tableLeftHeaderSkill">'+base+(f'<input value="{special}" readonly>' if special else '')+'</div>'
    s+='</div>'
    for i,key in enumerate(['初期','職業','興味','成長','他','合計']):
        s+='<div><div>'+key+'</div>'+''.join(f'<input type="number" value="{nums[i]}" readonly>'for base,special,nums in rows)+'</div>'
    return s+'</div>'


def fixture(name,age='39',mov='9',abilities=None):
    data={'name':name,'profile':{'職業':'架空の調査員','年齢':age},
          'items':[{'name':'メモ帳','qty':'2','note':'7版でも所持品へ'}],
          'sessions':[{'name':'7版架空シナリオ','body':'7版の通過メモ。'}],
          'memos':['一般メモ。バックストーリーはここに重複させない。']}
    s=render(data)
    a=abilities or dict(zip('STR CON POW DEX APP SIZ INT EDU'.split(),[65,45,80,80,60,60,80,80]))
    for k,v in a.items():s=s.replace(pair(k,10),pair(k,v),1)
    s=s.replace(pair('正気度','47/99'),pair('正気度','71/99')).replace(pair('MP','10'),pair('MP','16'))
    s=s.replace('職業P 0/200 残 200　興味P 0/100 残 100','職業P 320/320 残 0　興味P 160/160 残 0')
    s=s.replace(pair('知識','50'),pair('知識','50')+pair('ビルド','+1')+pair('MOV',mov))
    start=s.index('<div class="skills">');end=s.index('<section>',start)
    # Separate credit table exercises multiple read-only column groups.
    s=s[:start]+skill_table([('信用','',[0,20,0,0,0,20])])+skill_table([
        ('射撃','拳銃',[20,70,0,0,0,90]),('芸術/製作','服飾',[5,60,0,0,0,65]),
        ('言語','英語',[1,0,34,0,0,35])])+s[end:]
    s=s.replace('冒険の装備とその他の所持品','装備と所持品')
    extras=section('バックストーリー',card('容姿の描写','<p>七版の容姿テスト。</p>')+card('重要な人々（キー・コネクション）','<p>架空の友人。</p>')+card('イデオロギー/信念','<p>架空の信念。</p>')+section('魔導書、呪文、アーティファクト',card('架空の石','<p>秘匿扱いのテスト。</p>')))
    extras+=section('収入と財産',pair('現金','$120')+pair('資産','$5000')+pair('支出レベル','$20'))
    # Render's existing assets section is empty; remove it so the populated one is used.
    s=s.replace(section('収入と財産',''),'').replace(section('魔導書、呪文、アーティファクト',''),'')
    return s.replace('</div></body>',extras+'</div></body>')


checks=[]
for filename,html,choice,delta in [
    ('07_7版標準',fixture('7版テスト探索者'),'auto',0),
    ('08_7版年齢補正',fixture('7版年齢テスト','49','8'),'auto',0),
    ('09_7版特殊MOV',fixture('7版MOVテスト','39','12'),'auto',3),
    ('10_7版低能力値',fixture('7版低能力値テスト','25','8',{k:10 for k in 'STR CON POW DEX APP SIZ INT EDU'.split()}),'auto',0),
]:
    path=out/'入力HTML'/(filename+'.html');path.write_text(html,encoding='utf-8')
    txt,r=convert(path,choice)
    assert r['edition']==7
    assert '【クトゥルフ7版】'in txt and '【クトゥルフ6版】'not in txt
    assert f'SAN補正: {71-r["abilities"]["POW"]}'in txt
    assert f'MOVその他: {delta}'in txt
    assert '職業ポイント計算式: EDU×4'in txt
    assert '射撃（拳銃）'in txt and '芸術/製作（服飾）'in txt and 'ほかの言語（英語）'in txt
    assert len(r['skills'])==4 and len(r['items'])==1 and len(r['sessions'])==1
    assert r['memo_count']==2 # one ordinary memo and one artifact spoiler memo
    assert len(r['backstories'])==3 and '【★ 重要な人々】'in txt
    assert '【収入と財産】\n\n現金: $120\n資産: $5000\n支出レベル: $20'in txt
    assert txt.index('【魔導書・呪文・アーティファクト】')<txt.index('【クトゥルフ7版】')
    (out/'Python出力'/(filename+'.txt')).write_text(txt,encoding='utf-8-sig')
    checks.append({'case':filename,'result':'OK','edition':r['edition'],'MOV補正':delta})

ambiguous=render({'name':'高能力値6版テスト','profile':{'年齢':'30'}}).replace(pair('STR',10),pair('STR',45))
p=out/'入力HTML/11_高能力値6版.html';p.write_text(ambiguous,encoding='utf-8')
try:convert(p)
except ValueError as e:assert '版を判定' in str(e)
else:raise AssertionError('ambiguous edition should require choice')
txt,r=convert(p,'6');assert r['edition']==6 and '【クトゥルフ6版】'in txt
(out/'Python出力/11_高能力値6版.txt').write_text(txt,encoding='utf-8-sig')
checks.append({'case':'11_高能力値6版','result':'OK（自動判定は停止、6版指定で変換）'})
(out/'テスト結果.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False,indent=2))
