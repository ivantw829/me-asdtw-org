#!/usr/bin/env python3
"""依 data/articles.json 產生 Atom 訂閱源 feed.xml（只用標準函式庫）。

內容：標題、摘要、標籤、連結與全文（<content type="html">，取自文章頁的 .prose 與延伸閱讀，
站內相對網址改成完整網址，讓閱讀器能直接顯示圖片與連結；留言區仍需點進網站）。
排除草稿（draft）與 18+（adult）文章。輸出只取決於文章資料與文章頁，所以可重現。
本機 pre-commit 會自動執行並 stage feed.xml，一般不需要手動跑；check.py 以 --check 驗證是否最新。
用法：python3 authoring/build-feed.py [--check]
"""
import json
import pathlib
import re
import sys
from urllib.parse import urljoin
from xml.sax.saxutils import escape, quoteattr

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = f"https://{(ROOT / 'CNAME').read_text(encoding='utf-8').strip()}"
TITLE = "賴奕帆｜文章"
SUBTITLE = "倡議現場的心得與思考"
TZ = "T00:00:00+08:00"  # 站長在臺灣；只有日期，沒有時間


TAG = re.compile(r"<(/?)(div|aside)\b[^>]*>")
URL_ATTR = re.compile(r'\b(src|href)="([^"]*)"')


def element(html: str, opening: str) -> str:
    """回傳以 opening 開頭的整個 <div>／<aside> 元素（處理巢狀），找不到回傳空字串。"""
    start = html.find(opening)
    if start < 0:
        return ""
    name = re.match(r"<(\w+)", opening).group(1)
    depth = 0
    for m in TAG.finditer(html, start):
        if m.group(2) != name:
            continue
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return html[start:m.end()]
    raise SystemExit(f"build-feed：{opening} 沒有對應的結束標籤")


def full_content(slug: str, url: str) -> str:
    html = (ROOT / "articles" / f"{slug}.html").read_text(encoding="utf-8")
    prose = element(html, '<div class="prose">')
    if not prose:
        raise SystemExit(f"build-feed：articles/{slug}.html 找不到 <div class=\"prose\">")
    body = prose + element(html, '<aside class="article-sources"')
    body = URL_ATTR.sub(lambda m: f'{m.group(1)}="{urljoin(url, m.group(2))}"', body)
    return "\n".join(line.strip() for line in body.splitlines() if line.strip())


def render() -> str:
    articles = json.loads((ROOT / "data" / "articles.json").read_text(encoding="utf-8"))
    items = sorted((a for a in articles if not a.get("draft") and not a.get("adult") and not a.get("externalUrl")),
                   key=lambda a: (a.get("updated") or a["date"], a["date"]), reverse=True)
    feed_updated = (items[0].get("updated") or items[0]["date"]) if items else "1970-01-01"

    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="zh-Hant-TW">',
           f"  <title>{escape(TITLE)}</title>",
           f"  <subtitle>{escape(SUBTITLE)}</subtitle>",
           f'  <link rel="alternate" type="text/html" href="{BASE}/articles.html"/>',
           f'  <link rel="self" type="application/atom+xml" href="{BASE}/feed.xml"/>',
           f"  <id>{BASE}/</id>",
           f"  <updated>{feed_updated}{TZ}</updated>",
           f"  <author><name>賴奕帆</name><uri>{BASE}/about.html</uri></author>"]
    for a in items:
        url = f"{BASE}/articles/{a['slug']}.html"
        out += ["  <entry>",
                f"    <title>{escape(a['title'])}</title>",
                f'    <link rel="alternate" type="text/html" href="{url}"/>',
                f"    <id>{url}</id>",
                f"    <published>{a['date']}{TZ}</published>",
                f"    <updated>{(a.get('updated') or a['date'])}{TZ}</updated>",
                f'    <summary type="text">{escape(a["summary"])}</summary>',
                f'    <content type="html">{escape(full_content(a["slug"], url))}</content>']
        out += [f"    <category term={quoteattr(t)}/>" for t in a.get("tags", [])]
        out.append("  </entry>")
    out.append("</feed>")
    return "\n".join(out) + "\n"


def main() -> None:
    text = render()
    feed = ROOT / "feed.xml"
    if "--check" in sys.argv[1:]:
        if not feed.exists() or feed.read_text(encoding="utf-8") != text:
            sys.exit("feed.xml 不是最新（內容與文章頁不一致），請執行 python3 authoring/build-feed.py")
        return
    feed.write_text(text, encoding="utf-8")
    print(f"feed.xml：{text.count('<entry>')} 篇文章（含全文）")


if __name__ == "__main__":
    main()
