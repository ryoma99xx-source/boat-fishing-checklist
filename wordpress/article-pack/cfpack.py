#!/usr/bin/env python3
"""Build, check and upload cutlassfish.tokyo article packs.

  python3 cfpack.py build <folder> [-o out.zip]   # folder has article.json, article.html, images/
  python3 cfpack.py check <pack.zip>
  python3 cfpack.py ping
  python3 cfpack.py upload <pack.zip> --type <post_type>

Auth comes from env WP_USER and WP_APP_PASSWORD (a WordPress application password).
WP_URL defaults to https://cutlassfish.tokyo. Uploads always become drafts.
"""
import argparse, base64, hashlib, io, json, os, re, sys, urllib.error, urllib.request, zipfile

ALLOWED = re.compile(r"\A(?:article\.json|article\.html|images/|images/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|gif|webp))\Z")
ID_RE = re.compile(r"\A[a-zA-Z0-9_-]+\Z")
MB = 1024 * 1024


def fail(msg):
    sys.exit(f"NG: {msg}")


def check_pack(data: bytes):
    """Same rules as the WordPress importer's validate()."""
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
    if m.get("featured_image") and m["featured_image"] not in seen:
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
            z.writestr(im["file"], shrink(os.path.join(folder, im["file"])), compress_type=zipfile.ZIP_STORED)
    data = buf.getvalue()
    meta, n = check_pack(data)
    open(out, "wb").write(data)
    print(f"OK: {out}  {len(data)/MB:.1f}MB  画像{n}枚  SHA256 {hashlib.sha256(data).hexdigest()}")


def api(path, data=None, ctype=None):
    url = os.environ.get("WP_URL", "https://cutlassfish.tokyo").rstrip("/") + "/wp-json/cfai/v1" + path
    user, pw = os.environ.get("WP_USER"), os.environ.get("WP_APP_PASSWORD")
    if not user or not pw:
        fail("環境変数 WP_USER と WP_APP_PASSWORD が未設定です")
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode())
    req.add_header("User-Agent", "cfpack/1.0")
    if ctype:
        req.add_header("Content-Type", ctype)
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


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("folder"); b.add_argument("-o", "--out", default="article-pack.zip")
    c = sub.add_parser("check"); c.add_argument("zip")
    sub.add_parser("ping")
    u = sub.add_parser("upload"); u.add_argument("zip"); u.add_argument("--type", required=True)
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.folder, a.out)
    elif a.cmd == "check":
        data = open(a.zip, "rb").read()
        m, n = check_pack(data)
        print(f"OK: {m['title']}  画像{n}枚  SHA256 {hashlib.sha256(data).hexdigest()}")
    elif a.cmd == "ping":
        print(json.dumps(api("/ping")[1], ensure_ascii=False, indent=2))
    elif a.cmd == "upload":
        data = open(a.zip, "rb").read()
        check_pack(data)
        status, res = api(f"/import?post_type={a.type}", data, "application/zip")
        print(json.dumps(res, ensure_ascii=False, indent=2))
        print("既存の下書きを返しました（同じZIP）" if res.get("existing") else "下書きを作成しました（公開はしていません）")


if __name__ == "__main__":
    main()
