"""いあきゃら保存HTML → キャラッシュテキストv2。Python 3.10+、追加ライブラリ不要。"""
from __future__ import annotations
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys


class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def text(self):
        if self.tag in ('script', 'style', 'svg', 'template'):
            return ''
        if self.tag == 'input':
            return self.attrs.get('value', '')
        if self.tag == 'br':
            return '\n'
        return ''.join(c.text() if isinstance(c, Node) else c for c in self.children)


class DOM(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = self.current = Node()
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in self.VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        n = self.current
        while n.parent:
            if n.tag == tag:
                self.current = n.parent
                return
            n = n.parent

    def handle_data(self, data):
        self.current.children.append(data)


def read_html(path):
    raw = path.read_bytes()
    for encoding in ('utf-8-sig', 'cp932'):
        try:
            return raw.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            pass
    raise ValueError('UTF-8 / CP932 として読めません。')


def direct(node):
    return [c for c in node.children if isinstance(c, Node)]


def value(root, label, required=False):
    # 最小のラベル要素と、その兄弟の値を読む。CSSの生成ハッシュに依存しない。
    for n in root.walk():
        if n.tag in ('script', 'style', 'textarea'):
            continue
        for i, c in enumerate(n.children):
            if isinstance(c, str) and c.strip() == label:
                following = n.children[i+1:]
                if following and isinstance(following[0], Node):
                    return following[0].text().strip()
    for n in root.walk():
        if n.text().strip() == label and not any(c.text().strip() == label for c in direct(n)):
            siblings = direct(n.parent) if n.parent else []
            if n in siblings and siblings.index(n) + 1 < len(siblings):
                return siblings[siblings.index(n) + 1].text().strip()
    if required:
        raise ValueError(f'「{label}」が見つかりません。表示完了後の閲覧ページHTMLを保存してください。')
    return ''


def integer(text):
    if not re.fullmatch(r'[+-]?\d+', text.strip()):
        raise ValueError(f'整数を期待しました: {text!r}')
    return int(text)


def cell(v):
    s = str(v).replace('\\', '\\\\').replace('"', '\\"').replace('|', '\\|')
    return '"' + s + '"' if '\n' in s else s


def table(header, rows):
    return '\n'.join('| ' + ' | '.join(cell(x) for x in r) + ' |' for r in [header, *rows])


def memo(title, body):
    body = re.sub(r'(?m)^(\\*---(?:\s.*)?)$', r'\\\1', body)
    return f'---\n【{title}】\n{body}\n---'


GROUPS = {
    '戦闘技能': '回避 投擲 キック 組みつき こぶし／パンチ 頭突き マーシャルアーツ 拳銃 サブマシンガン ショットガン マシンガン ライフル'.split(),
    '探索技能': '応急手当 鍵開け 隠す 隠れる 聞き耳 忍び歩き 写真術 精神分析 追跡 登攀 図書館 目星'.split(),
    '行動技能': '運転 機械修理 重機械操作 乗馬 水泳 製作 操縦 跳躍 電気修理 ナビゲート 変装'.split(),
    '交渉技能': '言いくるめ 信用 説得 値切り 母国語 ほかの言語'.split(),
    '知識技能': '医学 オカルト 化学 クトゥルフ神話 芸術 経理 考古学 コンピューター 心理学 人類学 生物学 地質学 電子工学 天文学 博物学 物理学 法律 薬学 歴史'.split(),
}


def section(root, ident, title):
    found = next((n for n in root.walk() if n.attrs.get('id') == ident), None)
    if found:
        return found
    return next((n.parent for n in root.walk() if 'no-select' in n.attrs.get('class', '').split() and n.text().strip() == title), None)


def inputs(n):
    return [x for x in n.walk() if x.tag == 'input'] if n else []


def source_sections(root):
    sections = {k: section(root, k, t) for k, t in {
        'item':'冒険の装備とその他の所持品', 'newScenario':'通過したシナリオ',
        'artifact':'魔導書、呪文、アーティファクト', 'mythosCreature':'遭遇した超自然の存在',
        'assets':'収入と財産', 'battle':'武器'}.items()}
    def records(s):
        result=[]
        for n in inputs(s):
            ta=next((x for x in n.parent.walk() if x.tag=='textarea'),None)
            if ta:
                name=n.attrs.get('value','').strip();body=ta.text()
                if name or body:result.append({'name':name,'body':body})
        if s and not inputs(s):
            for n in s.walk():
                if n.tag=='span' and n.parent and n.parent.parent and 'no-select' in n.parent.parent.attrs.get('class','').split() and n.text().strip():
                    header=n.parent.parent
                    body='\n'.join(x.text() for x in direct(header.parent) if x is not header).replace('ここをクリックして内容を見る','').strip()
                    result.append({'name':n.text().strip(),'body':body})
        return result
    if not sections['item']:sections['item']=section(root,'item','装備と所持品')
    sections['backstory']=section(root,'backstory','バックストーリー')
    items=[]
    s=sections['item']
    if s:
        for row in s.walk():
            fields=inputs(row)
            if len(fields)!=5 or any(len(inputs(c))==5 for c in direct(row)):continue
            v=[n.attrs.get('value','') for n in fields]
            if not v[0].strip():continue
            quantity=integer(v[2]) if v[2] else 1
            note=' / '.join(x for x in [v[4],('単価: '+v[1]) if v[1] else '',('価格: '+v[3]) if v[3] else '', '' if v[2] else '元の個数は未記入（1を仮設定）'] if x)
            items.append([v[0],quantity,note])
        if not inputs(s):
            for heading in s.walk():
                if not (heading.tag=='span' and heading.parent and heading.parent.parent and 'no-select' in heading.parent.parent.attrs.get('class','').split() and heading.text().strip()):continue
                r={'name':heading.text().strip()}
                card=heading.parent.parent.parent
                q=value(card,'個数');note=value(card,'効果・備考など') or value(card,'効果・備考') or value(card,'備考') or value(card,'その他')
                for k in ['単価','価格']:
                    v=value(card,k)
                    if v:note+=(' / ' if note else '')+k+': '+v
                if not q:note+=(' / ' if note else '')+'元の個数は未記入（1を仮設定）'
                items.append([r['name'],integer(q) if q else 1,note])
    excluded={id(n) for s in sections.values() if s for n in s.walk()}
    memos=[n.text() for n in root.walk() if n.tag=='textarea' and id(n) not in excluded and n.text().strip()]
    assets=[]
    if sections['assets']:
        for label in ['収入','手持ち現金','預金','個人資産','不動産','生活水準','現金','資産','支出レベル']:
            v=value(sections['assets'],label)
            if v:assets.append([label,v])
    backstories=[]
    if sections['backstory']:
        for label in ['容姿の描写','イデオロギー/信念','重要な人々','意味のある場所','秘蔵の品','特徴','負傷、傷跡','恐怖症、マニア']:
            h=next((n for n in sections['backstory'].walk() if 'no-select' in n.attrs.get('class','').split() and n.text().replace(' ','').startswith(label)),None)
            if h:
                body='\n'.join(n.text() for n in direct(h.parent) if n is not h).replace('ここをクリックして内容を見る','').strip()
                if body:backstories.append({'title':'イデオロギー / 信念' if label=='イデオロギー/信念' else label,'body':body,'key':'キー・コネクション' in h.text()})
    return {'sections':sections,'items':items,'sessions':records(sections['newScenario']),
            'artifact':records(sections['artifact']),'creatures':records(sections['mythosCreature']),
            'memos':memos,'assets':assets,'backstories':backstories}


def convert(path, edition_choice='auto'):
    html = read_html(path)
    dom = DOM(html).root
    root = next((n for n in dom.walk() if n.attrs.get('id') == '__next'), None)
    if root is None:
        raise ValueError('いあきゃら閲覧ページの #__next が見つかりません。')
    extra=source_sections(root)
    source_root=root
    if any(n.attrs.get('id')=='ability' for n in root.walk()):raise ValueError('編集HTMLは項目確認用です。変換には閲覧画面を保存したHTMLを選んでください。')
    abilities = {k: integer(value(root, k, True)) for k in 'STR CON POW DEX APP SIZ INT EDU'.split()}
    marker7=bool(value(root,'ビルド') or value(root,'MOV'))
    if str(edition_choice) not in ['auto','6','7']:raise ValueError('版の指定が不正です。')
    edition=(7 if marker7 else 6) if edition_choice=='auto' else int(edition_choice)
    if edition_choice=='auto' and not marker7 and max(abilities.values())>40:raise ValueError('版を判定できません。--edition 6 または --edition 7 を指定してください。')
    if edition==6 and marker7:raise ValueError('7版の項目があります。版を自動判定か7版にしてください。')
    system=f'クトゥルフ{edition}版'
    occ_factor,interest_factor=(4,2) if edition==7 else (20,10)
    title = next((n.text() for n in dom.walk() if n.tag == 'title'), '')
    name = re.sub(r'\s*[-－–]\s*いあきゃら.*$', '', title).strip()
    if not name or name == title:
        raise ValueError('キャラクター名をページタイトルから判定できません。')
    warnings = [
        '保存HTMLに存在する情報だけを変換しました。非表示技能は省略し、新規取り込み時は移行先の標準値を使用します。閉じた記録・別ページ・秘匿欄は復元できません。',
        '能力値は表示された最終値を「元の値」に保存。元のロール値・補正の内訳はHTMLから復元しません。',
        '技能初期値とHP/MP/DB/アイデア/幸運/知識は固定値で保存します。移行後に自動計算へ戻すか確認してください。',
        'メモはネタバレ用メモに保存します。公開区分や合言葉は引き継ぎません。公開設定を確認してください。',
        '画像本体はTXTでは移せません。画像は元ファイルから別途登録してください。',
    ]
    parts = ['キャラッシュテキスト v2', 'キャラクターID:', '', '【共通情報】', '', '【基本情報】', '', f'名前: {cell(name)}']
    # 名前表示の直前にあるルビ（ローマ字も原文のまま保持）。
    for n in root.walk():
        if n.text().strip() == name and not direct(n) and n.parent:
            sib = direct(n.parent)
            i = sib.index(n)
            if i > 0 and sib[i-1].text().strip():
                parts.append('なまえ（かな）: ' + cell(sib[i-1].text().strip()))
            break
    for label in ['職業', '年齢', '性別', '出身', '身長', '体重', '髪の色', '瞳の色']:
        v = value(root, label)
        if v:
            if label == '年齢':
                m = re.fullmatch(r'(\d+)\s*歳?', v)
                if not m:
                    warnings.append('年齢は数値に変換できないため自由項目に保存: ' + v)
                    continue
                v = m[1]
            parts.append(f'{label}: {cell(v)}')
    birthday = value(root, '誕生日')
    m = re.fullmatch(r'\s*(\d{1,2})\s*/\s*(\d{1,2})\s*', birthday)
    if m:
        parts.append(f'誕生日: {int(m[1])}月{int(m[2])}日')
    parts.append('年齢の自動算出: いいえ')
    for n in root.walk():
        if n.text().strip() == 'カラー' and not direct(n) and n.parent:
            colors = re.findall(r'background-color:\s*rgb\((\d+),\s*(\d+),\s*(\d+)\)', ' '.join(x.attrs.get('style','') for x in n.parent.walk()))
            if colors:
                parts.append('イメージカラー: #' + ''.join(f'{int(c):02x}' for c in colors[-1]))
            break
    memos = extra['memos']
    parts += ['', '【ネタバレ用メモ】', '']
    for i, body in enumerate(memos, 1):
        parts += [memo(f'いあきゃら元メモ {i}', body), '']
    if extra['artifact']:
        parts += [memo('魔導書・呪文・アーティファクト','\n\n'.join(e['name']+('\n'+e['body'] if e['body'] else '') for e in extra['artifact'])),'']
    # HTMLの技能表は行ではなく列ごとに並ぶ。
    names = [n for n in root.walk() if 'AbilityTable_tableLeftHeaderSkill' in n.attrs.get('class', '')]
    names = [n for n in names if n.text().strip() != '技能名']
    if not names:
        raise ValueError('技能一覧が見つかりません。表示設定で技能を表示してください。')
    skill_rows=[]
    parents=list(dict.fromkeys(n.parent for n in names))
    for parent in parents:
        rows=[n for n in names if n.parent is parent];columns={}
        for col in direct(parent.parent):
            nodes=direct(col);key=nodes[0].text().strip() if nodes else ''
            if key in ('初期','職業','興味','成長','他','合計'):
                columns[key]=[n.attrs.get('value','') for n in col.walk() if n.tag=='input' and n.attrs.get('type')=='number']
        if set(columns)!={'初期','職業','興味','成長','他','合計'} or any(len(c)!=len(rows) for c in columns.values()):raise ValueError('技能表の列数が一致しません。このHTML形式には対応できません。')
        for i,n in enumerate(rows):skill_rows.append((n,[integer(columns[k][i] or '0') for k in ('初期','職業','興味','成長','他','合計')]))
    groups=dict(GROUPS)
    if edition==7:
        groups={
            '戦闘技能':'回避 投擲 近接戦闘 射撃'.split(),
            '探索技能':'応急手当 鍵開け 手さばき 聞き耳 隠密 精神分析 追跡 登攀 図書館 目星 鑑定 読唇術'.split(),
            '行動技能':'運転 機械修理 重機械操作 乗馬 水泳 芸術/製作 操縦 跳躍 電気修理 ナビゲート 変装'.split(),
            '交渉技能':'言いくるめ 信用 説得 母国語 威圧 魅惑 ほかの言語'.split(),
            '知識技能':'医学 オカルト クトゥルフ神話 経理 考古学 コンピューター 科学 心理学 人類学 電子工学 自然 法律 歴史 サバイバル 催眠術 ダイビング 動物使い 爆破'.split()}
    grouped = {k: [] for k in groups}
    skills = []
    for n,nums in skill_rows:
        inputs = [x for x in n.walk() if x.tag == 'input']
        specialization = inputs[0].attrs.get('value', '').strip() if inputs else ''
        # 入力欄を除いて基本技能名を読む。
        base = ''.join(c for x in n.walk() for c in x.children if isinstance(c, str)).strip()
        base = {'こぶし（パンチ）': 'こぶし／パンチ', '組み付き': '組みつき', 'コンピュータ': 'コンピューター'}.get(base, base)
        if edition==7:base={'言語':'ほかの言語','芸術／製作':'芸術/製作','芸術/制作':'芸術/製作','魅了':'魅惑'}.get(base,base)
        skill = (f'{base}（{specialization}）' if specialization else base) if base else specialization
        group = next((g for g, values in groups.items() if base in values), '知識技能')
        if not any(base in v for v in groups.values()):
            skill = '独自技能：' + skill
        if sum(nums[:5]) != nums[5]:
            raise ValueError(f'技能「{skill}」の内訳と合計が不一致です: {nums}')
        grouped[group].append([skill, *nums])
        skills.append({'name': skill, 'values': nums})
    san_text = value(root, '正気度', True)
    sm = re.fullmatch(r'(\d+)\s*/\s*(\d+)', san_text)
    if not sm:
        raise ValueError('正気度の形式が未対応です: ' + san_text)
    san, san_max = map(int, sm.groups())
    parts += [f'【{system}】', '', '【能力値】', '', table(['能力', '元の値', '増減', 'その他', '合計（参照用）'], [[k, v, 0, 0, v] for k, v in abilities.items()]), '']
    fields=[('HP','HP'),('MP','MP'),('DB','ダメージボーナス'),('幸運','幸運'),('ビルド','ビルド')] if edition==7 else [('HP','HP'),('MP','MP'),('DB','ダメージボーナス'),('アイデア','アイデア'),('幸運','幸運'),('知識','知識')]
    for src,dst in fields:
        parts.append(f'{dst}: {cell(value(root, src, True))}')
    parts += [f'SAN（参照用）: {san}', f'SAN最大（参照用）: {san_max}', f'SAN補正: {san - abilities["POW"] * (1 if edition==7 else 5)}', '', '【採用ルールとポイント】', '', f'職業ポイント計算式: EDU×{occ_factor}']
    plain = root.text()
    totals = {}
    for label, default in [('職業', abilities['EDU']*occ_factor), ('興味', abilities['INT']*interest_factor)]:
        m = re.search(label + r'P\s*(\d+)\s*/\s*(\d+)', plain)
        total = int(m[2]) if m else default
        totals[label] = total
        parts += [f'{label}ポイント補正: {total-default}', f'{label}ポイント総量（参照用）: {total}']
    warnings.append(f'職業ポイント計算式はEDU×{occ_factor}を基準に、表示総量との差を補正として保存しました。採用ルールは推測しません。')
    if edition==7:
        observed=value(root,'MOV',True)
        mov_label=next((n for n in root.walk() if not direct(n) and n.text().strip()=='MOV'),None)
        eq=re.search(r'=\s*([+-]?\d+)\s*$',mov_label.parent.text()) if mov_label else None
        if eq:observed=eq[1]
        mov=integer(observed);age_match=re.fullmatch(r'(\d+)\s*歳?',value(root,'年齢'));age=int(age_match[1]) if age_match else 0
        baseline=7 if abilities['STR']<abilities['SIZ'] and abilities['DEX']<abilities['SIZ'] else 9 if abilities['STR']>abilities['SIZ'] and abilities['DEX']>abilities['SIZ'] else 8
        baseline-=max(0,min(5,age//10-3))
        i=parts.index('【採用ルールとポイント】');parts[i:i]=[f'MOV（参照用）: {mov}','MOV増減: 0',f'MOVその他: {mov-baseline}','']
        if extra['backstories']:
            parts+=['【バックストーリー】',''];keyed=False
            for r in extra['backstories']:
                key=r['key'] and not keyed
                if key:keyed=True
                parts += [memo(('★ ' if key else '')+r['title'],r['body']),'']
        money=[(k,v) for k,v in extra['assets'] if k in ['生活水準','現金','資産','支出レベル']]
        if money:parts+=['【収入と財産】','',*[f'{k}: {cell(v)}' for k,v in money],'']
        warnings.append('7版のMOVは表示値と能力値・年齢の計算との差を補正で保存します。バックストーリーの公開設定・キーコネクション、年齢不明時のMOVを確認してください。')
    parts += ['', '【技能】', '']
    for g, rows in grouped.items():
        if rows:
            parts += [f'［{g}］', '', table(['技能名','初期値','職業P','興味P','成長分','その他','合計（参照用）'], rows), '']
    weapons = []
    for heading_node in (extra['sections']['battle'].walk() if extra['sections']['battle'] else []):
        if heading_node.tag != 'span' or 'font-weight: bold' not in heading_node.attrs.get('style', ''):
            continue
        if heading_node.parent is None or heading_node.parent.parent is None or 'no-select' not in heading_node.parent.parent.attrs.get('class', ''):
            continue
        n = heading_node.parent
        for _ in range(4):
            if n is None or value(n, 'ダメージ'):
                break
            n = n.parent
        if n is None or not value(n, 'ダメージ'):
            continue
        heading = heading_node.text().strip()
        if heading:
            note = value(n, 'その他')
            success = value(n, '成功率')
            note += (' / ' if note else '') + '元の成功率: ' + success
            weapons.append([heading, 1, note, value(n,'ダメージ'), value(n,'故障'), value(n,'射程'), value(n,'回数'), value(n,'装弾数'), value(n,'耐久力')])
    if weapons:
        parts += ['【武器】', '', table(['名称','個数','備考','ダメージ','故障NO','射程','攻撃回数','装弾数','耐久力'], weapons), '']
        warnings.append('武器の個数はHTMLから判別できないため1を仮設定。成功率は備考に保存しました。取り込み後、使用技能を手動で指定してください。')
    if extra['items']:
        parts += ['【システム別の所持品】','',table(['名前','個数','備考'],extra['items']),'']
    if extra['sessions']:
        block=['【セッション記録】','']
        for entry in extra['sessions']:
            if re.search(r'[\r\n［］]',entry['name']):raise ValueError('シナリオ名に改行または見出し記号が含まれています。')
            block += [f"［{entry['name'] or '名称未記入'}］",'', f'システム: {system}','URLを公開: いいえ','']
            if entry['body']:block += [memo('ひとことメモ',entry['body']),'']
        i=parts.index(f'【{system}】');parts[i:i]=block
    if extra['creatures']:
        parts += ['【システム別の経験の記録】','','遭遇した存在:',memo('遭遇した存在','\n\n'.join(e['name']+('\n'+e['body'] if e['body'] else '') for e in extra['creatures'])),'']
    free_assets=[(k,v) for k,v in extra['assets'] if edition!=7 or k not in ['生活水準','現金','資産','支出レベル']]
    if free_assets:
        i=parts.index('【ネタバレ用メモ】');parts[i:i]=['【自由項目】','',*[f'{k}: {cell(v)}' for k,v in free_assets],'']
    if any('元の個数は未記入' in str(r[2]) for r in extra['items']):warnings.append('個数未記入の所持品は1を仮設定し、備考に元が空欄である旨を残しました。')
    images = [n.attrs.get('src','') for n in source_root.walk() if n.tag == 'img']
    report = {'source': str(path.resolve()), 'name': name, 'edition':edition,'backstories':extra['backstories'],'abilities': abilities, 'san': san, 'san_max': san_max, 'skills': skills, 'weapons': weapons, 'items':extra['items'],'sessions':extra['sessions'],'memo_count': len(memos)+bool(extra['artifact']), 'point_totals': totals, 'image_references': images, 'warnings': warnings}
    if san_max != 99 - next((s['values'][-1] for s in skills if s['name'] == 'クトゥルフ神話'), 0):
        warnings.append('SAN最大と神話技能が一致しません。SAN最大は参照項目のため別途確認してください。')
    return '\n'.join(parts) + '\n', report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='*', help='HTMLファイルまたはHTMLを入れたフォルダー（直下のみ）')
    parser.add_argument('-o', '--output', type=Path, help='出力先フォルダー')
    parser.add_argument('--edition',choices=['auto','6','7'],default='auto',help='入力の版（既定は自動判定）')
    args = parser.parse_args()
    gui = not args.inputs
    if gui:
        import tkinter as tk
        from tkinter import filedialog
        app = tk.Tk(); app.withdraw()
        args.inputs = list(filedialog.askopenfilenames(title='いあきゃらの保存HTMLを選択（複数可）', filetypes=[('HTML', '*.html *.htm')]))
        if not args.inputs:
            return 0
        destination = filedialog.askdirectory(title='変換ファイルの保存先')
        if not destination:
            return 0
        args.output = Path(destination)
    files = []
    for entry in args.inputs:
        p = Path(entry)
        files.extend(sorted(x for x in p.iterdir() if x.suffix.lower() in ('.html','.htm')) if p.is_dir() else [p])
    files = list(dict.fromkeys(p.resolve() for p in files))
    if not files:
        parser.error('HTMLファイルがありません。')
    errors, successes = [], []
    for p in files:
        try:
            text, report = convert(p,args.edition)
            out = args.output or p.parent / 'charash_output'
            out.mkdir(parents=True, exist_ok=True)
            base = out / (p.stem + '_charash')
            index = 1
            while base.with_suffix('.txt').exists() or base.with_suffix('.report.json').exists():
                base = out / (p.stem + f'_charash_{index}'); index += 1
            base.with_suffix('.txt').write_text(text, encoding='utf-8-sig')
            base.with_suffix('.report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            successes.append(str(base.with_suffix('.txt')))
        except Exception as e:
            errors.append(f'{p.name}: {e}')
    result = f'{len(successes)}件を変換しました。\n' + '\n'.join(successes)
    if errors:
        result += '\n\n変換できなかったファイル:\n' + '\n'.join(errors)
    if gui:
        from tkinter import messagebox
        (messagebox.showwarning if errors else messagebox.showinfo)('変換結果', result)
    else:
        print(result)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
