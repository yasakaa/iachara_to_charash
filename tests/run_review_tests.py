from pathlib import Path
import html
import importlib.util
import json
import zipfile

OUT = Path(__file__).resolve().parent / 'results'
(OUT/'入力HTML').mkdir(parents=True,exist_ok=True)
(OUT/'Python出力').mkdir(exist_ok=True)
(OUT/'Web出力').mkdir(exist_ok=True)
repo=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('converter',repo/'iachara_to_charash.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
E=lambda s:html.escape(str(s),quote=True)
def pair(k,v):return f'<div class="pair"><div>{E(k)}</div><div>{E(v)}</div></div>'
def card(name,body):return '<article><div class="no-select"><div><span style="font-weight: bold;">'+E(name)+'</span></div></div><div>'+body+'</div></article>'
def section(title,body):return '<section><div class="no-select">'+E(title)+'</div><div>'+body+'</div></section>'
def render(data):
    name=data['name']
    body='<p>架空データによる閲覧HTMLのテストです。技能は検証に必要な1行だけです。</p>'
    body+='<div><div>けんしょうよう</div><div>'+E(name)+'</div></div>'
    for k,v in data['profile'].items():body+=pair(k,v)
    body+='<div class="pair"><div>カラー</div><div style="background-color: rgb(18, 52, 86);">色見本</div></div>'
    for k in 'STR CON POW DEX APP SIZ INT EDU'.split():body+=pair(k,10)
    for k,v in {'正気度':'47/99','HP':'10','MP':'10','DB':'0','アイデア':'50','幸運':'50','知識':'50'}.items():body+=pair(k,v)
    body+='<p>職業P 0/200 残 200　興味P 0/100 残 100</p>'
    body+='<div class="skills"><div><div class="AbilityTable_tableLeftHeaderSkill">技能名</div><div class="AbilityTable_tableLeftHeaderSkill">クトゥルフ神話</div></div>'
    for label in ['初期','職業','興味','成長','他','合計']:body+='<div><div>'+label+'</div><input type="number" value="0" readonly></div>'
    body+='</div>'
    weapons=[]
    for w in data.get('weapons',[]):weapons.append(card(w['name'],''.join(pair(k,v)for k,v in w['fields'].items())))
    body+=section('武器',''.join(weapons))
    items=[]
    for item in data.get('items',[]):items.append(card(item['name'],''.join(pair(k,v)for k,v in [('個数',item['qty']),('単価',item.get('unit','')),('価格',item.get('price','')),('備考',item['note'])])))
    body+=section('冒険の装備とその他の所持品',''.join(items))
    body+=section('収入と財産',''.join(pair(k,v)for k,v in data.get('assets',{}).items()))
    for label,key in [('魔導書、呪文、アーティファクト','artifacts'),('遭遇した超自然の存在','encounters'),('通過したシナリオ','sessions')]:
        body+=section(label,''.join(card(r['name'],'<p>'+E(r['body']).replace('\n','<br>')+'</p>')for r in data.get(key,[])))
    for i,m in enumerate(data.get('memos',[]),1):body+='<h2>メモ'+str(i)+'</h2><textarea readonly>'+E(m)+'</textarea>'
    return '<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>'+E(name)+' - いあきゃら</title><style>body{font-family:Meiryo,sans-serif;max-width:900px;margin:32px auto;background:#f5f5ee;color:#243d3c;padding:20px}.pair{display:flex;gap:20px;padding:4px}.pair>div:first-child{min-width:100px}section{border:1px solid #abb;padding:16px;margin:16px 0}article{background:white;margin:10px 0;padding:14px}.no-select{font-weight:bold}textarea{width:95%;height:140px}.skills{display:flex;gap:12px}input{width:60px}</style></head><body><h1>変換テスト用・架空データ</h1><div id="__next">'+body+'</div></body></html>'

cases=[
 {'file':'01_標準入力','name':'検証用探索者01','profile':{'職業':'司書','年齢':'28','性別':'女','出身':'架空県','身長':'165','体重':'55','髪の色':'黒','瞳の色':'茶','誕生日':'7 /29'},
  'items':[{'name':'懐中電灯','qty':'2','unit':'1200','price':'2400','note':'予備を含む'}, {'name':'ホイッスル','qty':'','note':'元の個数が空欄'}, {'name':'所持数ゼロ','qty':'0','note':'ゼロを保持'}],
  'weapons':[{'name':'練習用ナイフ','fields':{'成功率':'45','ダメージ':'1d4+DB','射程':'タッチ','回数':'1','装弾数':'','耐久力':'10','故障':'','その他':'演習用'}}],
  'sessions':[{'name':'架空シナリオA','body':'2026年に通過。\n2行目：NPCを救出。'}, {'name':'架空シナリオB','body':''}],
  'assets':{'収入':'400万円','手持ち現金':'12,000円','預金':'80万円','個人資産':'自転車','不動産':'なし'},
  'artifacts':[{'name':'星の書','body':'魔導書のテスト。'},{'name':'光る石','body':'種別は混合欄なので推測しない。'}],
  'encounters':[{'name':'架空の影','body':'図書館で遭遇。'},{'name':'架空の鳥','body':'名前だけでは分類しない。'}],
  'memos':['一般設定メモ。\nこの文はセッション本文ではありません。','秘匿メモ：架空の秘密。']},
 {'file':'02_空欄中心','name':'検証用探索者02','profile':{'職業':'','年齢':'','性別':'','出身':'','身長':'','体重':'','髪の色':'','瞳の色':'','誕生日':''},'sessions':[{'name':'タイトルのみの通過記録','body':''}]},
 {'file':'03_特殊文字と改行','name':'検証用探索者03','profile':{'職業':'研究員 | "助手"','年齢':'30歳','性別':'未設定','出身':'A&B <テスト>','誕生日':'12 /31'},
  'items':[{'name':'工具 | "特注"','qty':'3','unit':'1,000','price':'3,000','note':'1行目：A&B <記号>\n2行目：C:\\tools\\file | 終了'}],
  'sessions':[{'name':'架空シナリオ「境界」','body':'---\n区切り線を含む本文\n\\---\n記号 | "引用" & <保持>'}],
  'memos':['通常メモ\n---\n区切り線の後\n\\---\n末尾。']},
 {'file':'04_同名所持品','name':'検証用探索者04','profile':{'職業':'警備員','年齢':'35'},
  'items':[{'name':'乾電池','qty':'2','unit':'100','price':'200','note':'新品'}, {'name':'乾電池','qty':'4','unit':'50','price':'200','note':'使用済み・別の行'}],
  'sessions':[{'name':'乾電池','body':'所持品と同名でも、この1件だけがセッション。'}]},
 {'file':'05_異常系_個数が文字','name':'検証用探索者05','profile':{'職業':'学生','年齢':'20'},'items':[{'name':'ペン','qty':'数個','note':'変換を止めるべき入力'}],'expected_error':True},
]
results=[]
for case in cases:
    path=OUT/'入力HTML'/(case['file']+'.html');path.write_text(render(case),encoding='utf-8')
    try:
        txt,report=mod.convert(path)
        (OUT/'Python出力'/(case['file']+'.txt')).write_text(txt,encoding='utf-8-sig')
        checks=[]
        def check(label,ok):checks.append({'確認':label,'結果':'OK' if ok else 'NG'})
        check('異常系の入力は拒否',not case.get('expected_error',False))
        check('名前・SAN補正を保持',('名前: '+case['name'])in txt and 'SAN補正: -3' in txt)
        check('所持品の件数',len(report['items'])==len(case.get('items',[])))
        for i,item in enumerate(case.get('items',[])):
            actual=report['items'][i]
            check(f'所持品{i+1}の名称・個数・備考',actual[0]==item['name'] and actual[1]==(int(item['qty'])if item['qty'] else 1) and item['note'] in actual[2])
        check('セッションの名称・本文・件数',report['sessions']==case.get('sessions',[]))
        check('メモ件数',report['memo_count']==len(case.get('memos',[]))+bool(case.get('artifacts')))
        check('旧タイトル控えを作らない','タイトル控え' not in txt)
        if case.get('assets'):check('全ての資産を自由項目へ',all(f'{k}: {v}' in txt for k,v in case['assets'].items()))
        if case.get('artifacts'):check('混合欄を保持',all(r['name']in txt and r['body']in txt for r in case['artifacts']))
        if case.get('encounters'):check('遭遇欄を保持',all(r['name']in txt and r['body']in txt for r in case['encounters']))
        if case.get('weapons'):check('武器件数とダメージ',len(report['weapons'])==len(case['weapons'])and report['weapons'][0][3]=='1d4+DB')
        if case.get('artifacts'):
            check('魔導書等はネタバレメモの別枠',txt.index('【ネタバレ用メモ】')<txt.index('【魔導書・呪文・アーティファクト】')<txt.index('【セッション記録】') and '元の混合欄' not in txt)
        results.append({'ケース':case['file'],'判定':'NG' if any(c['結果']=='NG'for c in checks)else'OK','確認':checks})
    except Exception as e:
        ok=case.get('expected_error',False)
        results.append({'ケース':case['file'],'判定':'OK（想定どおり拒否）'if ok else'NG','エラー':str(e)})
        (OUT/'Python出力'/(case['file']+'_エラー.txt')).write_text(str(e),encoding='utf-8')
(OUT/'期待する入力値.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'自動照合結果.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
