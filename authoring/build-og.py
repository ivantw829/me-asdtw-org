#!/usr/bin/env python3
"""產生社群分享圖（1200×630 JPG）。使用本機 Chrome 無頭截圖，只用標準函式庫。

輸出：
  assets/img/og.jpg            首頁
  images/og/<頁面>.jpg         關於、經歷、文章列表、贊助
  images/og/<slug>.jpg         每篇已發布文章（標題、標籤、日期取自 data/articles.json）

用法：
  python3 authoring/build-og.py            補缺少或過期的圖（標題、標籤、日期或卡片設計改了就算過期；pre-commit 會自動執行）
  python3 authoring/build-og.py --all      全部重新產生
  python3 authoring/build-og.py <slug>…    只重新產生指定文章
環境變數 CHROME 可指定瀏覽器路徑。
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
CARD = ROOT / "authoring" / "og" / "card.html"
MANIFEST = ROOT / "images" / "og" / ".manifest.json"  # 每張圖「上次產生時的輸入」雜湊，用來偵測過期

# 站台頁面清單的單一來源：authoring/pages.json
PAGES = {
    pg["og"]["image"]: {k: v for k, v in pg["og"].items() if k != "image"}
    for pg in json.loads((ROOT / "authoring" / "pages.json").read_text(encoding="utf-8"))
}


def find_chrome() -> str:
    for c in (os.environ.get("CHROME"),
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome")):
        if c and pathlib.Path(c).exists():
            return c
    sys.exit("找不到 Chrome。請安裝 Google Chrome，或用 CHROME=/path/to/chrome 指定。")


def render(params: dict, out: pathlib.Path) -> None:
    chrome = find_chrome()
    url = CARD.as_uri() + "?" + urllib.parse.urlencode(params)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        png = pathlib.Path(tmp) / "card.png"
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", "--window-size=1200,630",
                        "--virtual-time-budget=15000", f"--screenshot={png}", url],
                       check=True, capture_output=True, timeout=90)
        # PNG → JPEG（macOS 內建 sips；其他系統請改用 ImageMagick）
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "88", str(png), "--out", str(out)],
                       check=True, capture_output=True)
    print(f"  ✓ {out.relative_to(ROOT)}")


def fingerprint(params: dict, card_hash: str) -> str:
    raw = json.dumps(params, sort_keys=True, ensure_ascii=False) + card_hash
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def main() -> None:
    args = sys.argv[1:]
    force_all = "--all" in args
    only = {a for a in args if not a.startswith("--")}

    jobs = []
    if not only:
        jobs += [(ROOT / rel, p) for rel, p in PAGES.items()]
    articles = json.loads((ROOT / "data" / "articles.json").read_text(encoding="utf-8"))
    if not only and any(a.get("adult") and not a.get("draft") for a in articles):
        jobs.append((ROOT / "images" / "og" / "adult.jpg",
                     dict(kind="page", eyebrow="18+", title="成人內容", sub="需年滿 18 歲才能閱讀")))
    for a in articles:
        if a.get("draft") or a.get("adult") or (only and a["slug"] not in only):
            continue
        jobs.append((ROOT / "images" / "og" / f"{a['slug']}.jpg",
                     dict(kind="article", title=a["title"], tags=",".join(a.get("tags", [])), date=a["date"])))

    card_hash = hashlib.sha256(CARD.read_bytes()).hexdigest()
    seeding = not MANIFEST.exists()  # 第一次：把現有圖視為最新，只記錄不重產
    manifest = {} if seeding else json.loads(MANIFEST.read_text(encoding="utf-8"))

    def key(out):
        return out.relative_to(ROOT).as_posix()

    todo = []
    for out, p in jobs:
        fp = fingerprint(p, card_hash)
        if out.exists() and seeding and not only:
            manifest[key(out)] = fp
        elif force_all or only or not out.exists() or manifest.get(key(out)) != fp:
            todo.append((out, p, fp))
    if todo:
        print(f"產生 {len(todo)} 張分享圖…")
        for out, p, fp in todo:
            render(p, out)
            manifest[key(out)] = fp
    if not only or todo:
        MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")


if __name__ == "__main__":
    main()
