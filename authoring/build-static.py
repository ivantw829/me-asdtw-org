#!/usr/bin/env python3
"""把「不需要 JS 也該看得到」的共用區塊靜態寫進 HTML，讓爬蟲、閱讀模式與不執行 JS 的讀者都看得到。

1. 頁首與頁尾：每個根目錄頁面與 articles/*.html 的 <header data-site-header>…</header>、
   <footer data-site-footer>…</footer> 整個元素依 authoring/site.json 重寫（導覽、社群連結、友站、聲明）。
   各寫成一行，讓 merge-main.py 能從衝突區塊辨認出它們是產物。連結依頁面位置用相對路徑；404.html 用 / 開頭（會在任意深度顯示）。
   年份取文章最新日期的年份（輸出只由資料決定，--check 才不會因跨年失敗）；site.js 會把 [data-year] 換成今年。
2. 文章卡片：index.html（最新 3 篇）與 articles.html（全部）的 <!--lists:start--> … <!--lists:end-->。
   卡片結構必須與 assets/js/site.js 的 card() 完全相同：JS 載入後會用同樣的標記重畫，畫面不會跳動。
   排序與過濾同 site.js：排除 draft、依 date 新到舊。成人文章只放通用說明，不放摘要。

本機 pre-commit 與 md2article.py 會自動執行；會印出被改寫的檔案（供 pre-commit stage）。
用法：python3 authoring/build-static.py [--check]   （--check 只檢查是否最新，過期回傳 1）
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
HEADER_RE = re.compile(r"<header\b[^>]*\bdata-site-header\b[^>]*>.*?</header>", re.S)
FOOTER_RE = re.compile(r"<footer\b[^>]*\bdata-site-footer\b[^>]*>.*?</footer>", re.S)


def esc(s: str) -> str:  # 同 site.js 的 esc()
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


# ---------- 頁首／頁尾 ----------

def link(item: dict, base: str) -> str:
    if item.get("path"):
        return f'<a href="{base}{esc(item["path"])}">{esc(item["label"])}</a>'
    return f'<a href="{esc(item["href"])}" target="_blank" rel="noopener">{esc(item["label"])}</a>'


def header(site: dict, base: str, current: str) -> str:
    cur = ' aria-current="page"'
    nav = "".join(f'<a href="{base}{esc(n["path"])}"{cur if n["path"] == current else ""}>{esc(n["label"])}</a>'
                  for n in site["nav"])
    return (f'<header class="site-header" data-site-header><div class="wrap">'
            f'<a class="brand" href="{base}index.html">{esc(site["name"])}</a>'
            f'<nav class="nav" aria-label="主要導覽">{nav}</nav>'
            f'<button class="theme-toggle" type="button" aria-label="切換深色模式"></button>'
            f'</div></header>')


def footer(site: dict, base: str, year: str) -> str:
    links = "".join(link(l, base) for l in site["links"])
    friends = "".join(link(l, base) for l in site["friends"])
    return (f'<footer class="site-footer" data-site-footer><div class="wrap">'
            f'<div class="footer-links">{links}</div>'
            f'<div class="footer-friends"><span class="footer-label">友站</span>{friends}</div>'
            f'<small>{esc(site["disclaimer"])}</small>'
            f'<small>© <span data-year>{year}</span> {esc(site["name"])}</small>'
            f'</div></footer>')


def shell_pages():
    """(相對路徑, 連結前綴, 導覽中標成目前頁面的 path)"""
    for p in sorted(ROOT.glob("*.html")):
        if p.name == "404.html":
            yield p.name, "/", None
        else:
            yield p.name, "", p.name
    for p in sorted((ROOT / "articles").glob("*.html")):
        yield f"articles/{p.name}", "../", "articles.html"


def apply_shell(rel: str, text: str, head: str, foot: str) -> str:
    for rx, block, what in ((HEADER_RE, head, "<header data-site-header>"), (FOOTER_RE, foot, "<footer data-site-footer>")):
        text, n = rx.subn(lambda m: block, text, count=1)
        if not n:
            sys.exit(f"{rel}：找不到 {what} 掛載點")
    return text


# ---------- 文章卡片 ----------

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


def apply_list(text: str, attr: str, inner: str) -> str:
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
    site = json.loads((ROOT / "authoring" / "site.json").read_text(encoding="utf-8"))
    data = json.loads((ROOT / "data" / "articles.json").read_text(encoding="utf-8"))
    articles = sorted((a for a in data if not a.get("draft")), key=lambda a: a["date"], reverse=True)
    year = max((a.get("updated") or a["date"] for a in data), default="2026")[:4]
    lists = {rel: "".join(card(a) for a in articles[:limit]) or EMPTY for rel, _, limit in TARGETS}

    stale = []
    for rel, base, current in shell_pages():
        p = ROOT / rel
        old = p.read_text(encoding="utf-8")
        new = apply_shell(rel, old, header(site, base, current), footer(site, base, year))
        for target, attr, _ in TARGETS:
            if rel == target:
                new = apply_list(new, attr, lists[rel])
        if new != old:
            stale.append(rel)
            if not check:
                p.write_text(new, encoding="utf-8")
                print(rel)
    if check and stale:
        print("頁首頁尾或文章列表的靜態內容過期：", "、".join(stale), "（請執行 python3 authoring/build-static.py）", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
