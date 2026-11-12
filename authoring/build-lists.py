#!/usr/bin/env python3
"""把文章卡片靜態寫進 index.html（最新 3 篇）與 articles.html（全部），讓沒有執行 JS 的爬蟲也看得到文章連結。

卡片結構必須與 assets/js/site.js 的 card() 完全相同：JS 載入後會用同樣的標記重畫，畫面不會跳動。
區段以 <!--lists:start--> … <!--lists:end--> 標記；第一次執行會把原本的「載入中…」與 noscript 換掉。
排序與過濾同 site.js：排除 draft、依 date 新到舊。成人文章只放通用說明，不放摘要。
本機 pre-commit 與 md2article.py 會自動執行；會印出被改寫的檔案（供 pre-commit stage）。
用法：python3 authoring/build-lists.py [--check]   （--check 只檢查是否最新，過期回傳 1）
"""
import json
import pathlib
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
START, END = "<!--lists:start-->", "<!--lists:end-->"
TARGETS = [("index.html", "data-latest-articles", 3), ("articles.html", "data-article-list", None)]
EMPTY = '<p class="empty">還沒有文章，敬請期待。</p>'


def esc(s: str) -> str:  # 同 site.js 的 esc()
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def fmt_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{y} 年 {int(m)} 月 {int(d)} 日"


def card(a: dict) -> str:
    cover = f'<img class="card-cover" src="{esc(a["cover"])}" alt="" loading="lazy">' if a.get("cover") and not a.get("adult") else ""
    rt = f' · 約 {a["readingTime"]} 分鐘' if a.get("readingTime") else ""
    summary = "此文章含成人內容，需年滿 18 歲才能閱讀。" if a.get("adult") else esc(a.get("summary", ""))
    chips = ""
    if a.get("adult"):
        chips += '<span class="tag tag-adult">18+</span>'
    if a.get("category"):
        chips += f'<a class="tag" href="articles.html?category={urllib.parse.quote(a["category"], safe="")}">{esc(a["category"])}</a>'
    cover = f"\n    {cover}" if cover else ""
    return (f'<article class="card">{cover}\n    <div class="meta">{fmt_date(a["date"])}{rt}</div>\n'
            f'    <h3><a href="articles/{esc(a["slug"])}.html">{esc(a["title"])}</a></h3>\n    <p>{summary}</p>\n'
            f'    <div class="chips">{chips}</div>\n  </article>')


def render(attr: str, limit, articles: list) -> str:
    return "".join(card(a) for a in articles[:limit]) or EMPTY


def apply(text: str, attr: str, inner: str) -> str:
    block = f"{START}{inner}{END}"
    if START in text:
        return re.sub(rf"({re.escape(attr)}[^>]*>){re.escape(START)}.*?{re.escape(END)}", lambda m: m.group(1) + block, text, count=1, flags=re.S)
    new, n = re.subn(rf"({re.escape(attr)}[^>]*>)<p class=\"empty\">載入中…</p><noscript>.*?</noscript>(</div>)",
                     lambda m: m.group(1) + block + m.group(2), text, count=1, flags=re.S)
    if not n:
        sys.exit(f"找不到 {attr} 掛載點")
    return new


def main() -> None:
    check = "--check" in sys.argv
    data = json.loads((ROOT / "data" / "articles.json").read_text(encoding="utf-8"))
    articles = sorted((a for a in data if not a.get("draft")), key=lambda a: a["date"], reverse=True)
    stale = []
    for rel, attr, limit in TARGETS:
        p = ROOT / rel
        old = p.read_text(encoding="utf-8")
        new = apply(old, attr, render(attr, limit, articles))
        if new != old:
            stale.append(rel)
            if not check:
                p.write_text(new, encoding="utf-8")
                print(rel)
    if check and stale:
        print("文章列表靜態內容過期：", "、".join(stale), "（請執行 python3 authoring/build-lists.py）", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
