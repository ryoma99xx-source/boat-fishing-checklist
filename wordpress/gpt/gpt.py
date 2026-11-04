#!/usr/bin/env python3
"""Small OpenAI helper for article work (standard library only; Pillow optional for --jpeg).

  python3 gpt.py image "<prompt>" -o out.png [--size 1536x1024] [--quality medium] [--jpeg]
  python3 gpt.py text "<instruction>" [--context file.txt]
  python3 gpt.py usage-note

The API key comes from env OPENAI_API_KEY and is never printed or written anywhere.
Models: env OPENAI_IMAGE_MODEL / OPENAI_TEXT_MODEL, otherwise chosen automatically.
"""
import argparse, base64, io, json, os, re, sys, urllib.error, urllib.request

API = "https://api.openai.com/v1"
IMAGE_MODELS = ["gpt-image-2", "gpt-image-1.5", "gpt-image-1"]
# Non-text variants that also start with "gpt-5" but do not answer plain Responses requests.
TEXT_SKIP = re.compile(r"realtime|audio|tts|transcribe|image|search", re.I)
MB = 1024 * 1024

USAGE_NOTE = """OpenAI API の利用料について
- API の利用料は、ChatGPT（Plus / Pro / Team など）の月額プランとは別に請求されます。
  ChatGPT を契約していても、API は platform.openai.com 側の支払い設定・クレジットから引かれます。
- 画像生成は 1 枚ごとに料金がかかります（品質 high・大きいサイズほど高い）。下書き確認用は
  --quality low や medium で十分です。
- 使用量と上限は https://platform.openai.com/usage と Billing の「Limits」で確認・設定できます。"""


def die(msg, code=1):
    print(f"NG: {msg}", file=sys.stderr)
    sys.exit(code)


def redact(text):
    # OpenAI echoes part of a wrong key in 401 messages; never show any of it.
    return re.sub(r"sk-[A-Za-z0-9_\-*.]+", "sk-***", str(text))


def api_key():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        die("環境変数 OPENAI_API_KEY が設定されていません。Claude Code の作業環境（環境設定のシークレット／環境変数）に "
            "OpenAI の API キーを OPENAI_API_KEY という名前で登録してから、もう一度実行してください。"
            "（ChatGPT のログインやプランとは別に、platform.openai.com で発行する API キーが必要です）", 2)
    return key


class ApiError(Exception):
    def __init__(self, status, message, code=""):
        super().__init__(message)
        self.status, self.message, self.code = status, message, code or ""


def call(method, path, payload=None, timeout=300):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + api_key())
    req.add_header("User-Agent", "cutlassfish-gpt/1.0")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        msg, code = raw[:500], ""
        try:
            err = json.loads(raw).get("error") or {}
            msg, code = err.get("message") or msg, err.get("code") or err.get("type") or ""
        except Exception:
            pass
        raise ApiError(e.code, redact(msg), str(code))
    except urllib.error.URLError as e:
        die(f"api.openai.com に接続できません：{redact(e.reason)}")
    except TimeoutError:
        die("OpenAI API の応答がタイムアウトしました。少し待ってからやり直してください。")


HINTS = {
    400: "リクエストの内容（サイズ・品質・プロンプト）を確認してください。安全性の理由で拒否された場合はプロンプトを言い換えてください。",
    401: "API キーが無効です。OPENAI_API_KEY を確認してください。",
    403: "このキー（組織・プロジェクト）ではこの機能やモデルが使えません。組織の認証（Verification）が必要な場合があります。",
    404: "モデルまたは API が見つかりません。",
    429: "利用上限・残高不足、または混雑です。Billing の残高と Limits を確認してください。",
}


def explain(e):
    hint = HINTS.get(e.status) or ("OpenAI 側の一時的なエラーです。少し待ってからやり直してください。" if e.status >= 500 else "")
    code = f" [{e.code}]" if e.code else ""
    return f"OpenAI API エラー（HTTP {e.status}{code}）：{e.message}" + (f"\n→ {hint}" if hint else "")


def model_unavailable(e):
    if e.code in ("model_not_found", "invalid_model"):
        return True
    m = e.message.lower()
    if "model" not in m and e.status != 404:
        return False
    return e.status == 404 or any(s in m for s in (
        "does not exist", "not found", "not available", "unknown", "invalid model", "not supported",
        "do not have access", "does not have access", "must be verified", "unsupported model"))


def to_jpeg(png_bytes, path, target=MB):
    try:
        from PIL import Image
    except ImportError:
        return None
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    for side in (None, 1600, 1280, 1024):
        if side:
            im.thumbnail((side, side))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=85, optimize=True, progressive=True)
        if out.tell() <= target or side == 1024:
            break
    with open(path, "wb") as f:
        f.write(out.getvalue())
    return {"path": path, "bytes": out.tell(), "width": im.width, "height": im.height}


def cmd_image(a):
    api_key()
    env_model = os.environ.get("OPENAI_IMAGE_MODEL", "").strip()
    models = [env_model] if env_model else IMAGE_MODELS
    tried = []
    for model in models:
        body = {"model": model, "prompt": a.prompt, "size": a.size, "quality": a.quality, "n": 1}
        try:
            res = call("POST", "/images/generations", body, timeout=600)
        except ApiError as e:
            tried.append(model)
            if not env_model and model_unavailable(e) and model != models[-1]:
                print(f"注意: {model} は使えないため次のモデルを試します（{e.message[:120]}）", file=sys.stderr)
                continue
            die(explain(e))
        item = (res.get("data") or [{}])[0]
        b64 = item.get("b64_json")
        if not b64:
            die("画像データ（b64_json）が返ってきませんでした。")
        png = base64.b64decode(b64)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "wb") as f:
            f.write(png)
        result = {"ok": True, "model": model, "size": a.size, "quality": a.quality, "png": a.out, "png_bytes": len(png)}
        if item.get("revised_prompt"):
            result["revised_prompt"] = item["revised_prompt"]
        if a.jpeg:
            jpg_path = os.path.splitext(a.out)[0] + ".jpg"
            j = to_jpeg(png, jpg_path)
            if j:
                result["jpeg"] = j
            else:
                result["jpeg"] = None
                result["note"] = "Pillow が無いため JPEG は作れませんでした（pip install pillow）。cfpack.py build でも約1MBに縮められます。"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    die("使える画像モデルがありません（試したモデル：" + ", ".join(tried) + "）。OPENAI_IMAGE_MODEL で指定できます。")


def pick_text_model():
    env_model = os.environ.get("OPENAI_TEXT_MODEL", "").strip()
    if env_model:
        return env_model
    try:
        models = call("GET", "/models").get("data") or []
    except ApiError as e:
        die(explain(e))
    cands = [m for m in models if str(m.get("id", "")).startswith("gpt-5") and not TEXT_SKIP.search(m["id"])]
    if not cands:
        die("gpt-5 系のモデルが見つかりません。環境変数 OPENAI_TEXT_MODEL で使うモデル名を指定してください。")
    return max(cands, key=lambda m: (m.get("created") or 0, m["id"]))["id"]


def output_text(res):
    if isinstance(res.get("output_text"), str):
        return res["output_text"]
    parts = []
    for item in res.get("output") or []:
        if item.get("type") == "message":
            for c in item.get("content") or []:
                if c.get("type") in ("output_text", "text") and isinstance(c.get("text"), str):
                    parts.append(c["text"])
    return "".join(parts)


def cmd_text(a):
    api_key()
    prompt = a.instruction
    if a.context:
        try:
            with open(a.context, encoding="utf-8") as f:
                ctx = f.read()
        except OSError as e:
            die(f"--context のファイルを読めません：{e}")
        prompt += "\n\n--- 参考資料 ---\n" + ctx
    model = pick_text_model()
    try:
        res = call("POST", "/responses", {"model": model, "input": prompt}, timeout=600)
    except ApiError as e:
        die(explain(e))
    text = output_text(res)
    if not text.strip():
        die(f"テキストが返ってきませんでした（status: {res.get('status')}）。")
    print(f"[model: {model}]", file=sys.stderr)
    print(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description="OpenAI helper (images / text) for cutlassfish.tokyo articles")
    sub = ap.add_subparsers(dest="cmd", required=True)
    im = sub.add_parser("image", help="画像を生成して PNG（と任意で JPEG）に保存")
    im.add_argument("prompt")
    im.add_argument("-o", "--out", required=True)
    im.add_argument("--size", default="1536x1024", choices=["1536x1024", "1024x1024", "1024x1536"])
    im.add_argument("--quality", default="medium", choices=["low", "medium", "high"])
    im.add_argument("--jpeg", action="store_true", help="同じ名前の .jpg（品質85%%・約1MB以下）も作る（Pillow が必要）")
    tx = sub.add_parser("text", help="Responses API で文章を作る")
    tx.add_argument("instruction")
    tx.add_argument("--context", help="参考資料のテキストファイル")
    sub.add_parser("usage-note", help="API 料金についての注意を表示")
    a = ap.parse_args(argv)
    if a.cmd == "usage-note":
        print(USAGE_NOTE)
    elif a.cmd == "image":
        cmd_image(a)
    elif a.cmd == "text":
        cmd_text(a)


if __name__ == "__main__":
    main()
