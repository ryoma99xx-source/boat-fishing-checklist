"""ティップランカウンターのカタログが「足すだけ」になっているかを確かめる（月次更新で使う）。

    python3 tools/tipran_check_addonly.py <更新前の catalog.json> [<更新後の catalog.json>]

アプリは持っているエギを メーカー|製品|色、シンカーを メーカー|製品|重さ|色 で覚えている。前にあったものが1つでも
消えた・名前が変わったら、持っている人の登録が見えなくなるので、エラー（終了コード1）にして中身を出す。"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def keys(path):
    c = json.load(open(path, encoding='utf-8'))
    k = set()
    for r in c.get('heads', []):
        for col in r.get('c', []):
            k.add('エギ|%s|%s|%s' % (r['m'], r['s'], col))
        for o in r.get('o', []):
            k.add('エギ号数|%s|%s|%s|%s' % (r['m'], r['s'], o['z'], o.get('g', 0)))
    for r in c.get('skirts', []):
        for w in r.get('w', []):
            k.add('シンカー|%s|%s|%sg' % (r['m'], r['s'], w))
        for col in r.get('c', []):
            k.add('シンカー色|%s|%s|%s' % (r['m'], r['s'], col))
    return k


def main():
    old = keys(sys.argv[1])
    new = keys(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'tipran', 'catalog.json'))
    gone, added = sorted(old - new), sorted(new - old)
    print('追加 %d 件' % len(added))
    for x in added[:200]:
        print('  +', x)
    if gone:
        print('消えた・名前が変わった %d 件（足すだけにすること。直してからやり直す）' % len(gone))
        for x in gone:
            print('  -', x)
        sys.exit(1)
    print('OK：前にあったものはすべて残っています')


if __name__ == '__main__':
    main()
