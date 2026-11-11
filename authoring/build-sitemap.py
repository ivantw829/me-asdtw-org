#!/usr/bin/env python3
"""依 data/articles.json 重新產生 sitemap.xml（只用標準函式庫）。

lastmod 規則（可重現，沒改內容就不會變）：
  - 文章：文章日期
  - 一般頁面：相關檔案最後一次 commit 的日期；若檔案正在被修改或已 staged，則為今天
本機 pre-commit hook 會自動執行本腳本，一般不需要手動跑。
用法：python3 authoring/build-sitemap.py
"""
import datetime
import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parent.parent
today = datetime.date.today().isoformat()
domain = (root / "CNAME").read_text(encoding="utf-8").strip()
DOMAIN = f"https://{domain}"


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


# 有未提交變更（工作區或 staged）的檔案視為「今天修改」
dirty = {line[3:].strip().strip('"') for line in git("status", "--porcelain").splitlines()}


def lastmod(*files: str) -> str:
    dates = []
    for f in files:
        d = today if f in dirty else git("log", "-1", "--format=%cs", "--", f)
        dates.append(d or today)
    return max(dates)


# 頁面 → (priority, 會影響它內容的檔案)
pages = [
    ("", "1.0", ["index.html", "data/articles.json"]),
    ("about.html", "0.6", ["about.html"]),
    ("timeline.html", "0.7", ["timeline.html", "data/timeline.json"]),
    ("articles.html", "0.8", ["articles.html", "data/articles.json"]),
    ("contact.html", "0.4", ["contact.html"]),
    ("sponsor.html", "0.5", ["sponsor.html"]),
]
urls = [(f"{DOMAIN}/{p}", lastmod(*files), pr) for p, pr, files in pages]

articles = json.loads((root / "data" / "articles.json").read_text(encoding="utf-8"))
for a in sorted(articles, key=lambda a: a["date"], reverse=True):
    if a.get("draft") or a.get("adult"):
        continue
    urls.append((f"{DOMAIN}/articles/{a['slug']}.html", a["date"], "0.7"))

out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for loc, mod, pr in urls:
    out.append(f"  <url><loc>{loc}</loc><lastmod>{mod}</lastmod><priority>{pr}</priority></url>")
out.append("</urlset>")
(root / "sitemap.xml").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"sitemap.xml：{len(urls)} 個網址")
