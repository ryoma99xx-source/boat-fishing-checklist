#!/usr/bin/env python3
"""Add ChatGPT's monthly tenya list to the dragon counter catalog, add-only.

    python3 sites/dragon-counter/tools/catalog_add.py <gpt.json>            # check only
    python3 sites/dragon-counter/tools/catalog_add.py <gpt.json> --write    # write catalog-extra.json, catalog-all.json and DEPLOY
    python3 sites/dragon-counter/tools/catalog_add.py --export              # only rewrite catalog-all.json

<gpt.json> is the 【カタログ追加】 JSON: {"checked":"YYYY-MM-DD","new":[...],"status":[...]}.
- "new": tenya not in the catalog yet. Ones already there (same maker|product|size|color) are skipped.
- "status": a status change (s) for a tenya that IS in the catalog, matched by the exact same four fields.
Nothing already in the catalog is renamed or removed, so every viewer's owned tenya keep working.
"""
import json, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
INDEX = os.path.join(SITE, "public", "index.html")
EXTRA = os.path.join(SITE, "public", "catalog-extra.json")
DEPLOY = os.path.join(SITE, "DEPLOY")
MAKERS = ["DAIWA", "SHIMANO", "JACKALL", "HAYABUSA", "OWNER", "Major Craft", "PRO MARINE", "START", "YAMASHITA", "DUO", "がまかつ", "マルシン漁具"]
STATUS = ["", "発売予定", "限定色", "生産終了・在庫のみ", "売り切れあり"]


def fnv(s):  # same id as the app (FNV-1a over UTF-16 code units)
    h = 0x811C9DC5
    b = s.encode("utf-16-le")
    for i in range(0, len(b), 2):
        h ^= b[i] | (b[i + 1] << 8)
        h = (h * 0x01000193) & 0xFFFFFFFF
    n, out = h, ""
    while True:
        n, r = divmod(n, 36)
        out = "0123456789abcdefghijklmnopqrstuvwxyz"[r] + out
        if not n:
            break
    return "k" + out


def key(m, p, z, c):
    return fnv(f"{m}|{p}|{int(z)}|{c}")


def export_all(have, updated):
    """Public list of every catalog tenya, for ChatGPT to read before the monthly update."""
    rows = sorted(({"m": x["m"], "p": x["p"], "z": int(x["z"]), "c": x["c"], "s": x.get("s", "")} for x in have.values()),
                  key=lambda r: (r["m"], r["p"], r["z"], r["c"]))
    out = {"updated": updated, "count": len(rows), "note": "ドラゴンカウンターのテンヤカタログ全件（表記はこのまま使う）", "items": rows}
    json.dump(out, open(os.path.join(SITE, "public", "catalog-all.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


def refresh_hashes(name):
    """Keep SHA256SUMS and mirror-manifest.json in step with a changed public file."""
    import hashlib
    b = open(os.path.join(SITE, "public", name), "rb").read(); h = hashlib.sha256(b).hexdigest()
    sums = os.path.join(SITE, "SHA256SUMS")
    lines = open(sums).read().splitlines()
    open(sums, "w").write("\n".join((h + "  " + name) if l.endswith("  " + name) else l for l in lines) + "\n")
    mp = os.path.join(SITE, "mirror-manifest.json"); m = json.load(open(mp, encoding="utf-8"))
    for r in m["files"]:
        if r["file"] == name: r["sha256"] = h; r["bytes"] = len(b)
    json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); open(mp, "a").write("\n")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    gpt = {} if sys.argv[1] == "--export" else json.load(open(sys.argv[1], encoding="utf-8"))
    write = "--write" in sys.argv
    src = open(INDEX, encoding="utf-8").read()
    cat = json.loads(re.search(r"const TENYA_CAT=(\{.*?\});\n", src, re.S).group(1))
    have = {}
    for pi, z, c, st in cat["items"]:
        m, p, u, h = cat["products"][pi]
        have[key(m, p, z, c)] = {"m": m, "p": p, "z": z, "c": c, "s": st}
    extra = json.load(open(EXTRA, encoding="utf-8"))
    for x in extra["items"]:
        have.setdefault(key(x["m"], x["p"], x["z"], x["c"]), x)
    today = datetime.date.today().isoformat()
    if sys.argv[1] == "--export":
        export_all(have, extra.get("updated", "")); print(f"catalog-all.json を書き出しました（{len(have)} 件）"); return
    errs, added, changed, skipped = [], [], [], []
    for i, x in enumerate(gpt.get("new", [])):
        where = f"new[{i}] {x.get('m')} {x.get('p')} {x.get('z')}号 {x.get('c')}"
        miss = [k for k in ("m", "p", "z", "c", "u") if not str(x.get(k, "")).strip()]
        if miss: errs.append(f"{where}: {','.join(miss)} がありません"); continue
        if x["m"] not in MAKERS: errs.append(f"{where}: メーカー表記は {MAKERS} のどれか"); continue
        if int(x["z"]) not in (20, 30, 40, 50, 60, 80): errs.append(f"{where}: 号数がおかしい"); continue
        if x.get("s", "") not in STATUS: errs.append(f"{where}: 状態は {STATUS} のどれか"); continue
        if not str(x["u"]).startswith("https://"): errs.append(f"{where}: u はメーカー公式の https URL"); continue
        k = key(x["m"], x["p"], x["z"], x["c"])
        if k in have: skipped.append(where); continue
        it = {"m": x["m"], "p": x["p"], "u": x["u"], "h": bool(x.get("h")), "z": int(x["z"]), "c": x["c"], "s": x.get("s", ""), "a": today}
        have[k] = it; added.append(it)
    for i, x in enumerate(gpt.get("status", [])):
        where = f"status[{i}] {x.get('m')} {x.get('p')} {x.get('z')}号 {x.get('c')}"
        k = key(x.get("m", ""), x.get("p", ""), x.get("z", 0) or 0, x.get("c", ""))
        if k not in have: errs.append(f"{where}: カタログに同じ表記のテンヤがありません（表記を変えずに書く）"); continue
        if x.get("s", "") not in STATUS: errs.append(f"{where}: 状態は {STATUS} のどれか"); continue
        old = have[k]
        changed.append({"m": old["m"], "p": old["p"], "u": old.get("u", "") or x.get("u", ""), "h": bool(old.get("h")), "z": int(old["z"]), "c": old["c"], "s": x.get("s", ""), "a": old.get("a", "")})
    print(f"追加 {len(added)} 件 / 状態の更新 {len(changed)} 件 / 既にあるので飛ばした {len(skipped)} 件 / エラー {len(errs)} 件")
    for e in errs: print("  NG", e)
    for s in skipped: print("  skip", s)
    for a in added: print("  +", a["m"], a["p"], f"{a['z']}号", a["c"], a["s"])
    for c in changed: print("  ~", c["m"], c["p"], f"{c['z']}号", c["c"], "→", c["s"] or "（通常）")
    if errs: sys.exit(1)
    if not write: print("（確認のみ。書き込むときは --write）"); return
    extra["items"].extend(added + changed)  # later entries win for status; ids never change
    extra["updated"] = gpt.get("checked") or today
    json.dump(extra, open(EXTRA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(EXTRA, "a").write("\n")
    for c in changed:
        have[key(c["m"], c["p"], c["z"], c["c"])] = c
    export_all(have, extra["updated"])
    refresh_hashes("catalog-extra.json")
    open(DEPLOY, "w").write("Changing this file deploys sites/dragon-counter/public to dragon-counter.cutlassfish.tokyo.\n"
                            f"Last request: {datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
    print("catalog-extra.json・catalog-all.json・DEPLOY を更新しました。commit・push すると公開されます。")


if __name__ == "__main__":
    main()
