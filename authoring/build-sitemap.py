#!/usr/bin/env python3
"""依 data/articles.json 重新產生 sitemap.xml（只用標準函式庫）。
用法：在專案根目錄執行  python3 authoring/build-sitemap.py
"""
import json, datetime, pathlib

DOMAIN = "https://me.asdtw.org"
root = pathlib.Path(__file__).resolve().parent.parent
today = datetime.date.today().isoformat()

pages = [("", "1.0"), ("about.html", "0.6"),
         ("timeline.html", "0.7"), ("articles.html", "0.8"), ("contact.html", "0.4"), ("sponsor.html", "0.5")]
urls = [(f"{DOMAIN}/{p}", today, pr) for p, pr in pages]

articles = json.loads((root / "data" / "articles.json").read_text(encoding="utf-8"))
for a in sorted(articles, key=lambda a: a["date"], reverse=True):
    if a.get("draft"):
        continue
    urls.append((f"{DOMAIN}/articles/{a['slug']}.html", a["date"], "0.7"))

out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for loc, lastmod, pr in urls:
    out.append(f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><priority>{pr}</priority></url>")
out.append("</urlset>")
(root / "sitemap.xml").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"sitemap.xml：{len(urls)} 個網址")
