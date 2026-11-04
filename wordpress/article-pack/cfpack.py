#!/usr/bin/env python3
"""Build, check and upload cutlassfish.tokyo article packs.

  python3 cfpack.py build <folder> [-o out.zip]   # folder has article.json, article.html, images/
  python3 cfpack.py check <pack.zip>
  python3 cfpack.py ping
  python3 cfpack.py upload <pack.zip> --type <post_type>
  python3 cfpack.py list [--status draft|publish|any] [--search 語] [--type tachiuo_post|post]
  python3 cfpack.py get <id> [--out <folder>]       # folder can be edited and rebuilt as a pack
  python3 cfpack.py update <id> <pack.zip> [--allow-published]
  python3 cfpack.py publish <id> [--slug s] [--topics a,b] [--date 2026-11-05T07:00]
  python3 cfpack.py unpublish <id>

Auth comes from env WP_USER and WP_APP_PASSWORD (a WordPress application password).
WP_URL defaults to https://cutlassfish.tokyo. Uploads and updates never publish;
only the publish command does.
"""
import argparse, base64, hashlib, io, json, os, re, sys, urllib.error, urllib.parse, urllib.request, zipfile

ALLOWED = re.compile(r"\A(?:article\.json|article\.html|images/|images/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|gif|webp))\Z")
ID_RE = re.compile(r"\A[a-zA-Z0-9_-]+\Z")
MEDIA_RE = re.compile(r"\{\{media:([^}]*)\}\}")
MEDIA_ID_RE = re.compile(r"\A[1-9][0-9]*\Z")
MB = 1024 * 1024


def fail(msg):
    sys.exit(f"NG: {msg}")


def check_pack(data: bytes, allow_media=False):
    """Same rules as the WordPress importer's validate().

    allow_media: also accept {{media:<attachment_id>}} in the body and featured_image
    "media:<attachment_id>" (existing WordPress images; only the update command resolves them).
    """
    z = zipfile.ZipFile(io.BytesIO(data))
    infos = z.infolist()
    if len(infos) > 100:
        fail("ZIP内のファイル数が多すぎます")
    entries, total = {}, 0
    for i in infos:
        if not ALLOWED.match(i.filename):
            fail(f"未対応のファイル: {i.filename}")
        if i.filename in entries:
            fail("重複したファイル名")
        total += i.file_size
        limit = 20 * MB if i.filename.startswith("images/") else MB
        if i.file_size > limit or total > 100 * MB:
            fail(f"大きすぎます: {i.filename}")
        entries[i.filename] = i
    if "article.json" not in entries or "article.html" not in entries:
        fail("article.json と article.html が必要です")
    m = json.loads(z.read("article.json"))
    if not isinstance(m, dict) or m.get("version") != 1:
        fail("version は 1 が必要です")
    for k in ("title", "excerpt", "featured_image"):
        if k in m and not isinstance(m[k], str):
            fail(f"{k} は文字列で")
    if not (m.get("title") or "").strip():
        fail("タイトルがありません")
    html = z.read("article.html").decode("utf-8")
    if not html.strip():
        fail("本文が空です")
    images = m.get("images", [])
    if not isinstance(images, list) or len(images) > 30:
        fail("画像は30枚まで")
    seen = set()
    for im in images:
        if not isinstance(im, dict):
            fail("画像情報が不正")
        for k in ("id", "file", "alt", "caption", "title"):
            if k in im and not isinstance(im[k], str):
                fail(f"画像の {k} は文字列で")
        iid, f = im.get("id", ""), im.get("file", "")
        if not ID_RE.match(iid) or iid in seen or f not in entries or f == "images/" or not f.startswith("images/"):
            fail(f"画像IDまたはファイルが不正: {iid} {f}")
        seen.add(iid)
    for iid in re.findall(r"\{\{image:([^}]+)\}\}", html):
        if iid not in seen:
            fail(f"本文の画像が見つかりません: {iid}")
    media = MEDIA_RE.findall(html)
    feat = m.get("featured_image") or ""
    if feat.startswith("media:"):
        media.append(feat[6:])
    for mid in media:
        if not MEDIA_ID_RE.match(mid):
            fail(f"既存画像の指定が不正です: media:{mid}（{{{{media:数字}}}} の形）")
    if media and not allow_media:
        fail("{{media:N}}（既存画像）は既存記事の update でだけ使えます。新規の upload では画像ファイルを入れてください")
    if feat and feat not in seen and not (allow_media and feat.startswith("media:")):
        fail("アイキャッチ画像が見つかりません")
    if re.search(r"<h1[\s>]", html, re.I):
        print("注意: 本文に h1 があります（タイトルは投稿タイトルに入るので不要）")
    return m, len(images)


def shrink(path, max_side=1800, target=MB):
    """Return image bytes, resized/re-encoded when over ~1MB (README recommends ~1MB per photo)."""
    raw = open(path, "rb").read()
    if len(raw) <= target:
        return raw
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return raw
    im = ImageOps.exif_transpose(Image.open(path))
    im.thumbnail((max_side, max_side))
    out = io.BytesIO()
    ext = path.lower().rsplit(".", 1)[-1]
    if ext in ("jpg", "jpeg"):
        im.convert("RGB").save(out, "JPEG", quality=85, optimize=True)
    elif ext == "png":
        im.save(out, "PNG", optimize=True)
    elif ext == "webp":
        im.save(out, "WEBP", quality=85)
    else:
        return raw
    return out.getvalue() if len(out.getvalue()) < len(raw) else raw


def build(folder, out):
    m = json.load(open(os.path.join(folder, "article.json"), encoding="utf-8"))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("article.json", json.dumps(m, ensure_ascii=False, indent=2))
        z.writestr("article.html", open(os.path.join(folder, "article.html"), encoding="utf-8").read())
        z.writestr(zipfile.ZipInfo("images/"), b"")
        for im in m.get("images", []):
            # Deflate images too: the host's firewall (SiteGuard) rejects some uploads that carry raw image bytes.
            z.writestr(im["file"], shrink(os.path.join(folder, im["file"])), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    data = buf.getvalue()
    meta, n = check_pack(data, allow_media=True)
    open(out, "wb").write(data)
    print(f"OK: {out}  {len(data)/MB:.1f}MB  画像{n}枚  SHA256 {hashlib.sha256(data).hexdigest()}")
    if uses_media(data):
        print("注意: {{media:N}}（既存画像）を使っています。このZIPは update 専用です（upload では使えません）")


def uses_media(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    m = json.loads(z.read("article.json"))
    return bool(MEDIA_RE.search(z.read("article.html").decode("utf-8"))) or str(m.get("featured_image") or "").startswith("media:")


def api(path, data=None, ctype=None, method=None):
    url = os.environ.get("WP_URL", "https://cutlassfish.tokyo").rstrip("/") + "/wp-json/cfai/v1" + path
    user, pw = os.environ.get("WP_USER"), os.environ.get("WP_APP_PASSWORD")
    if not user or not pw:
        fail("環境変数 WP_USER と WP_APP_PASSWORD が未設定です")
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data is not None else "GET"))
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode())
    req.add_header("User-Agent", "cfpack/1.1")
    req.add_header("Accept", "application/json")
    if ctype:
        req.add_header("Content-Type", ctype)
        if ctype == "application/zip":
            req.add_header("Content-Disposition", 'attachment; filename="article-pack.zip"')
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(body).get("message", body)
        except Exception:
            pass
        fail(f"HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        fail(f"接続できません: {e.reason}")


def post_json(path, payload):
    return api(path, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json")


def show(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def get_to_folder(art, out):
    """Write article.json + article.html so the folder can be edited and rebuilt with build.

    Existing images whose full URL appears in the body become {{media:<attachment_id>}};
    other URLs (resized variants, external images) are left as they are and still work."""
    html = art.get("content", "")
    images = art.get("images", [])
    # Longest URL first so ".../a-1.jpg" is not partly replaced by ".../a.jpg" style overlaps.
    for im in sorted(images, key=lambda i: -len(i.get("url") or "")):
        if im.get("url"):
            html = re.sub(r'(["\'(])' + re.escape(im["url"]) + r'(?=["\')])', lambda mo, i=im["id"]: mo.group(1) + "{{media:%d}}" % i, html)
    manifest = {"version": 1, "title": art.get("title", ""), "excerpt": art.get("excerpt", ""), "images": []}
    if art.get("featured_image_id"):
        manifest["featured_image"] = f"media:{art['featured_image_id']}"
    os.makedirs(os.path.join(out, "images"), exist_ok=True)
    with open(os.path.join(out, "article.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(out, "article.html"), "w", encoding="utf-8") as f:
        f.write(html)
    info = {k: art.get(k) for k in ("id", "title", "status", "modified", "post_type", "slug", "topics", "link", "edit_link", "preview_link", "content_format", "word_count", "todo")}
    info["images"] = images
    with open(os.path.join(out, "source.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return {"folder": out, "id": art.get("id"), "status": art.get("status"), "content_format": art.get("content_format"),
            "media_placeholders": sorted(set(int(x) for x in MEDIA_RE.findall(html))), "todo": art.get("todo", []),
            "files": ["article.json", "article.html", "source.json (参照用・ZIPには入らない)"]}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("folder"); b.add_argument("-o", "--out", default="article-pack.zip")
    c = sub.add_parser("check"); c.add_argument("zip")
    sub.add_parser("ping")
    u = sub.add_parser("upload"); u.add_argument("zip"); u.add_argument("--type", required=True)
    l = sub.add_parser("list"); l.add_argument("--status", default="any", choices=["draft", "pending", "future", "private", "publish", "any"])
    l.add_argument("--search", default=""); l.add_argument("--type", default=""); l.add_argument("--per-page", type=int, default=20); l.add_argument("--page", type=int, default=1)
    g = sub.add_parser("get"); g.add_argument("id", type=int); g.add_argument("--out")
    up = sub.add_parser("update"); up.add_argument("id", type=int); up.add_argument("zip"); up.add_argument("--allow-published", action="store_true")
    p = sub.add_parser("publish"); p.add_argument("id", type=int); p.add_argument("--slug"); p.add_argument("--topics"); p.add_argument("--date")
    un = sub.add_parser("unpublish"); un.add_argument("id", type=int)
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.folder, a.out)
    elif a.cmd == "check":
        data = open(a.zip, "rb").read()
        m, n = check_pack(data, allow_media=True)
        print(f"OK: {m['title']}  画像{n}枚  SHA256 {hashlib.sha256(data).hexdigest()}")
        if uses_media(data):
            print("注意: {{media:N}}（既存画像）を使っています。このZIPは update 専用です")
    elif a.cmd == "ping":
        print(json.dumps(api("/ping")[1], ensure_ascii=False, indent=2))
    elif a.cmd == "upload":
        data = open(a.zip, "rb").read()
        check_pack(data)
        status, res = api(f"/import?post_type={a.type}", data, "application/zip")
        print(json.dumps(res, ensure_ascii=False, indent=2))
        print("既存の下書きを返しました（同じZIP）" if res.get("existing") else "下書きを作成しました（公開はしていません）")
    elif a.cmd == "list":
        q = {"status": a.status, "per_page": a.per_page, "page": a.page}
        if a.search:
            q["search"] = a.search
        if a.type:
            q["post_type"] = a.type
        show(api("/articles?" + urllib.parse.urlencode(q))[1])
    elif a.cmd == "get":
        art = api(f"/articles/{a.id}")[1]
        show(get_to_folder(art, a.out) if a.out else art)
    elif a.cmd == "update":
        data = open(a.zip, "rb").read()
        check_pack(data, allow_media=True)
        path = f"/articles/{a.id}/content" + ("?allow_published=1" if a.allow_published else "")
        show(api(path, data, "application/zip")[1])
    elif a.cmd == "publish":
        body = {}
        if a.slug:
            body["slug"] = a.slug
        if a.topics is not None:
            body["topics"] = [t.strip() for t in a.topics.split(",") if t.strip()]
        if a.date:
            body["date"] = a.date
        show(post_json(f"/articles/{a.id}/publish", body)[1])
    elif a.cmd == "unpublish":
        show(post_json(f"/articles/{a.id}/unpublish", {})[1])


if __name__ == "__main__":
    main()
