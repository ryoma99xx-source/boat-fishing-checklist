#!/usr/bin/env python3
"""Collect cutlassfish.tokyo's public page tree for the ledger's site map.

Reads only public pages: WordPress's wp-sitemap.xml, each page's <title>,
and the topic archive pages (to know which topic each article belongs to).

  python3 sync.py -o sitemap.json

The JSON is then stored in the ledger database (collection "sitemap", doc "wp").
"""
import argparse, html, json, re, sys, time, urllib.request
from datetime import datetime, timezone

BASE = "https://cutlassfish.tokyo"
UA = "Mozilla/5.0 (compatible; cutlassfish-ledger/1.0)"
LABELS = {"tachiuo_post": "記事", "tbt_catch": "釣果", "tbt_video": "動画", "page": "固定ページ", "post": "投稿"}
ORDER = ["page", "tachiuo_post", "tbt_catch", "tbt_video", "post"]
WITH_TITLES = {"page", "tachiuo_post", "post", "tbt_catch", "tbt_video"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def locs(xml):
    return re.findall(r"<url><loc>([^<]+)</loc>(?:<lastmod>([^<]+)</lastmod>)?", xml)


def page_info(url):
    h = get(url)
    t = re.search(r"<title>([^<]*)", h)
    title = html.unescape(t.group(1)).split(" | ")[0].strip() if t else url
    pid = re.search(r"\bpostid-(\d+)|\bpage-id-(\d+)", h)
    pid = int(pid.group(1) or pid.group(2)) if pid else None
    return title, pid, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="sitemap.json")
    ap.add_argument("--delay", type=float, default=0.25)
    a = ap.parse_args()
    index = get(BASE + "/wp-sitemap.xml")
    maps = re.findall(r"<loc>([^<]+)</loc>", index)
    sections, topics = {}, []
    for m in maps:
        kind = re.search(r"wp-sitemap-(posts|taxonomies)-([a-z_]+)-\d+\.xml", m)
        if not kind:
            continue
        group, name = kind.groups()
        rows = locs(get(m))
        if group == "posts":
            sec = sections.setdefault(name, {"key": name, "label": LABELS.get(name, name), "items": []})
            for u, lastmod in rows:
                item = {"u": u, "m": lastmod or ""}
                if name in WITH_TITLES:
                    try:
                        item["t"], item["id"], _ = page_info(u)
                    except Exception as e:  # keep going; the URL still shows in the tree
                        item["t"] = u.rstrip("/").rsplit("/", 1)[-1]
                        print("warn:", u, e, file=sys.stderr)
                    time.sleep(a.delay)
                sec["items"].append(item)
        elif name == "tachiuo_cat":
            topics += [u for u, _ in rows]
    # Topic membership for articles, read from each topic archive (with pagination).
    art = {i["u"]: i for i in sections.get("tachiuo_post", {}).get("items", [])}
    cats = []
    for tu in topics:
        try:
            first = get(tu)
        except Exception as e:
            print("warn:", tu, e, file=sys.stderr)
            continue
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", first, re.S)
        tt = re.search(r"<title>([^<]*)", first)
        name = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else (html.unescape(tt.group(1)).split(" | ")[0] if tt else tu)
        slug = tu.rstrip("/").rsplit("/", 1)[-1]
        name = re.sub(r"\s*\d+\s*記事\s*$", "", html.unescape(name)).strip()
        cats.append({"slug": slug, "name": name, "u": tu})
        pages, n = [first], 2
        while n <= 20 and re.search(rf'href="{re.escape(tu)}page/{n}/"', pages[-1]):
            try:
                pages.append(get(f"{tu}page/{n}/"))
            except Exception:
                break
            n += 1
            time.sleep(a.delay)
        for ph in pages:
            for u in set(re.findall(r'href="(https://cutlassfish\.tokyo/article/[^"#?]+/)"', ph)):
                if u in art:
                    art[u].setdefault("c", [])
                    if slug not in art[u]["c"]:
                        art[u]["c"].append(slug)
        time.sleep(a.delay)
    out = {
        "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base": BASE,
        "cats": cats,
        "sections": [sections[k] for k in ORDER if k in sections] + [v for k, v in sections.items() if k not in ORDER],
    }
    json.dump(out, open(a.out, "w"), ensure_ascii=False, separators=(",", ":"))
    print("OK", a.out, {s["label"]: len(s["items"]) for s in out["sections"]}, "topics", len(cats))


if __name__ == "__main__":
    main()
