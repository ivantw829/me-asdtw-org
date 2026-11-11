#!/usr/bin/env python3
"""產生社群分享圖（1200×630 JPG）。使用本機 Chrome 無頭截圖，只用標準函式庫。

輸出：
  assets/img/og.jpg            首頁
  images/og/<頁面>.jpg         關於、經歷、文章列表、聯絡、贊助
  images/og/<slug>.jpg         每篇已發布文章（標題、標籤、日期取自 data/articles.json）

用法：
  python3 authoring/build-og.py            只補缺少的圖（pre-commit 會自動執行）
  python3 authoring/build-og.py --all      全部重新產生（改了卡片設計時）
  python3 authoring/build-og.py <slug>…    只重新產生指定文章
環境變數 CHROME 可指定瀏覽器路徑。
"""
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

PAGES = {
    "assets/img/og.jpg": dict(kind="site", title="多元平權倡議者"),
    "images/og/about.jpg": dict(kind="page", eyebrow="ABOUT", title="關於我", sub="高三學生、多元平權倡議者"),
    "images/og/timeline.jpg": dict(kind="page", eyebrow="EXPERIENCE", title="經歷", sub="倡議、政策參與、社會服務與研習"),
    "images/og/articles.jpg": dict(kind="page", eyebrow="ARTICLES", title="文章", sub="倡議現場的心得與思考"),
    "images/og/contact.jpg": dict(kind="page", eyebrow="CONTACT", title="聯絡我", sub="電子郵件、Discord、社群"),
    "images/og/sponsor.jpg": dict(kind="page", eyebrow="SUPPORT", title="贊助我的倡議行動", sub="支持內容製作與現場行動"),
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

    todo = [(out, p) for out, p in jobs if force_all or only or not out.exists()]
    if not todo:
        return
    print(f"產生 {len(todo)} 張分享圖…")
    for out, p in todo:
        render(p, out)


if __name__ == "__main__":
    main()
