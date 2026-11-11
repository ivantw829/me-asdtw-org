#!/usr/bin/env python3
"""依 data/articles.json 產生 Atom 訂閱源 feed.xml（只用標準函式庫）。

內容：只放標題、摘要、標籤與連結（讀者點進網站讀全文，留言與 18+ 確認才會維持原樣）。
排除草稿（draft）與 18+（adult）文章。日期取自文章資料，沒有改內容就不會變，所以可重現。
本機 pre-commit 會自動執行並 stage feed.xml，一般不需要手動跑。
用法：python3 authoring/build-feed.py
"""
import json
import pathlib
from xml.sax.saxutils import escape, quoteattr

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = f"https://{(ROOT / 'CNAME').read_text(encoding='utf-8').strip()}"
TITLE = "賴奕帆｜文章"
SUBTITLE = "倡議現場的心得與思考"
TZ = "T00:00:00+08:00"  # 站長在臺灣；只有日期，沒有時間


def main() -> None:
    articles = json.loads((ROOT / "data" / "articles.json").read_text(encoding="utf-8"))
    items = sorted((a for a in articles if not a.get("draft") and not a.get("adult")),
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
                f'    <summary type="text">{escape(a["summary"])}</summary>']
        out += [f"    <category term={quoteattr(t)}/>" for t in a.get("tags", [])]
        out.append("  </entry>")
    out.append("</feed>")
    (ROOT / "feed.xml").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"feed.xml：{len(items)} 篇文章")


if __name__ == "__main__":
    main()
