#!/usr/bin/env python3
"""發布後驗證：等線上頁面出現，檢查 canonical、og:title、og:image（HTTP 200 且為 JPEG）。只用標準函式庫。

用法：python3 authoring/verify-live.py <slug> [--wait 秒數，預設 300]
全部通過回傳 0，否則回傳 1。
"""
import html
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = f"https://{(ROOT / 'CNAME').read_text(encoding='utf-8').strip()}"


def fetch(url: str, head: bool = False):
    req = urllib.request.Request(url + ("&" if "?" in url else "?") + f"_={int(time.time())}",
                                 method="HEAD" if head else "GET", headers={"User-Agent": "verify-live"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.headers, ("" if head else r.read().decode("utf-8", "replace"))


def meta(text: str, key: str, attr: str = "property"):
    m = re.search(rf'<meta {attr}="{re.escape(key)}" content="([^"]*)"', text)
    return html.unescape(m.group(1)) if m else None


def main() -> None:
    argv = sys.argv[1:]
    wait = 300
    if "--wait" in argv:
        k = argv.index("--wait")
        wait = int(argv[k + 1])
        del argv[k:k + 2]
    if len(argv) != 1:
        sys.exit(__doc__)
    slug = argv[0]
    art = next((a for a in json.loads((ROOT / "data" / "articles.json").read_text(encoding="utf-8"))
                if a["slug"] == slug), None)
    if not art:
        sys.exit(f"data/articles.json 找不到 {slug}")
    url = f"{BASE}/articles/{slug}.html"

    text, deadline = None, time.time() + wait
    print(f"等待 {url} 上線…")
    while time.time() < deadline:
        try:
            status, _, text = fetch(url)
            if status == 200 and f'data-slug="{slug}"' in text:
                break
        except (urllib.error.URLError, TimeoutError):
            pass
        text = None
        time.sleep(10)
    if text is None:
        sys.exit(f"✗ {wait} 秒內線上仍抓不到頁面（GitHub Pages 可能還在部署，稍後再跑一次）")

    ok = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        ok &= cond
        print(f"  {'✓' if cond else '✗'} {label}{'：' + detail if detail and not cond else ''}")

    m = re.search(r'<link rel="canonical" href="([^"]*)"', text)
    check("canonical", bool(m) and m.group(1) == url, m.group(1) if m else "找不到")
    check("og:title", meta(text, "og:title") == art["title"], str(meta(text, "og:title")))
    check("og:description", meta(text, "og:description") == art["summary"])
    if art.get("draft") or art.get("adult"):
        check("robots noindex", "noindex" in (meta(text, "robots", "name") or ""), str(meta(text, "robots", "name")))
    else:
        check("robots 可索引", "noindex" not in (meta(text, "robots", "name") or ""))
    img = meta(text, "og:image") or ""
    try:
        status, headers, _ = fetch(img, head=True)
        check("分享圖 200 且為 JPEG", status == 200 and headers.get("content-type", "").startswith("image/jpeg"),
              f"{status} {headers.get('content-type')}")
    except (urllib.error.URLError, ValueError) as e:
        check("分享圖可下載", False, str(e))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
