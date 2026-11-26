"""タイラバカウンターのカタログが「足すだけ」になっているかを確かめる（月次更新で使う）。

    python3 tools/tairaba_check_addonly.py <更新前の catalog.json> [<更新後の catalog.json>]

アプリは持っているヘッド・ネクタイ・スカートを メーカー|製品|色（ヘッドは重さも）で覚えている。前にあったものが1つでも
消えた・名前が変わったら、持っている人の登録が見えなくなるので、エラー（終了コード1）にして中身を出す。"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = {'heads': 'ヘッド', 'ties': 'ネクタイ', 'skirts': 'スカート'}


def keys(path):
    c = json.load(open(path, encoding='utf-8'))
    k = set()
    for kind in ('heads', 'ties', 'skirts'):
        for r in c.get(kind, []):
            for col in r.get('c', []):
                k.add('%s|%s|%s|%s' % (NAME[kind], r['m'], r['s'], col))
            for w in r.get('w', []) if kind == 'heads' else []:
                k.add('ヘッドの重さ|%s|%s|%sg' % (r['m'], r['s'], w))
    return k


def main():
    old = keys(sys.argv[1])
    new = keys(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'tairaba', 'catalog.json'))
    gone, added = sorted(old - new), sorted(new - old)
    print('追加 %d 件' % len(added))
    for x in added[:300]:
        print('  +', x)
    if gone:
        print('消えた・名前が変わった %d 件（足すだけにすること。直してからやり直す）' % len(gone))
        for x in gone:
            print('  -', x)
        sys.exit(1)
    print('OK：前にあったものはすべて残っています')


if __name__ == '__main__':
    main()
